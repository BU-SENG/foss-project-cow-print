#!/usr/bin/env python3
"""
AetherDB - SQL Reasoning Module (SQLM)

How to get this running:
  - First, grab these packages:
      pip install python-dotenv sqlglot sqlparse google-generativeai

  - CLI usage:
      python sqlm.py --schema schema.txt

  - Quick test:
      python sqlm.py --run-test
"""

from __future__ import annotations
import os
import json
import re
import argparse
import contextlib
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple

from dotenv import load_dotenv

load_dotenv()

# Import optional dependencies with fallbacks
try:
    import importlib
    _sqlglot_mod = importlib.import_module("sqlglot")
    sqlglot = _sqlglot_mod
    parse_one = getattr(_sqlglot_mod, "parse_one", None)
    exp = getattr(_sqlglot_mod, "exp", None)
except Exception:
    sqlglot = None
    parse_one = None
    exp = None

try:
    import importlib
    _sqlparse_mod = importlib.import_module("sqlparse")
    sqlparse = _sqlparse_mod
except Exception:
    sqlparse = None

try:
    import importlib
    _genai_mod = importlib.import_module("google.generativeai")
    genai = _genai_mod
    GENAI_AVAILABLE = True
except Exception:
    genai = None
    GENAI_AVAILABLE = False

# Config from env
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-2.0-flash") # Default to flash for speed
GEMINI_MAX_TOKENS = int(os.getenv("GEMINI_MAX_TOKENS", "8192"))
DEFAULT_DIALECT = os.getenv("DEFAULT_DIALECT", "mysql")
MAX_SCHEMA_PROMPT_CHARS = int(os.getenv("MAX_SCHEMA_PROMPT_CHARS", "14000"))


# -----------------------------
# Data models
# -----------------------------
@dataclass
class CommandPayload:
    """Input contract from Command Processing Layer."""
    intent: str
    raw_nl: str
    normalized: Optional[str] = None
    target_db: Optional[str] = None
    dialect: Optional[str] = None
    allow_destructive: bool = False
    session_context: Optional[Dict[str, Any]] = None
    entities: Optional[Dict[str, Any]] = None


@dataclass
class ReasonerOutput:
    """Output contract returning SQL and AI reasoning."""
    sql: Optional[str]
    intent: str
    dialect: str
    warnings: List[str]
    errors: List[str]
    metadata: Dict[str, Any]
    explain_text: Optional[str]
    confidence: float
    safe_to_execute: bool
    thought_process: Optional[str] = None  # Added for CoT transparency


# -----------------------------
# Prompt templates (Improved)
# -----------------------------
BASE_SYSTEM_PROMPT = """You are an expert SQL dialect translator.
Your goal is to convert natural language into accurate, safe, and optimized SQL.

### GUIDELINES:
1. **Schema Fidelity**: ONLY use tables/columns defined in SCHEMA_SNAPSHOT. Do not hallucinate columns.
2. **Dialect Specifics**: Respect the requested DIALECT (e.g., use `"` for Postgres/SQLite identifiers, `` ` `` for MySQL).
3. **Date Handling**: If the user mentions "today", "last month", etc., use the CURRENT_DATE provided below.
4. **Chain of Thought**: Briefly analyze the request and schema linkages before writing SQL.
5. **Safety**: Mark `destructive: true` for DROP, DELETE, UPDATE, ALTER, TRUNCATE.

### OUTPUT FORMAT:
Return ONLY a valid JSON object with this structure:
{
  "thought_process": "Brief analysis of which tables to join and filters to apply",
  "sql": "The valid SQL query string (or null if ambiguous)",
  "intent": "select|insert|update|delete|create|alter|other",
  "destructive": boolean,
  "clarify_required": boolean,
  "explanation": "Short user-friendly summary (max 1 sentence)"
}
"""

def build_user_prompt(schema_snapshot: str, command_text: str, dialect: str) -> str:
    # Ensure schema isn't ridiculously large
    if len(schema_snapshot) > MAX_SCHEMA_PROMPT_CHARS:
        schema_snapshot = schema_snapshot[:MAX_SCHEMA_PROMPT_CHARS] + "\n...[TRUNCATED]"
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return (
        f"{BASE_SYSTEM_PROMPT}\n\n"
        f"### CONTEXT\n"
        f"CURRENT_DATE: {current_time}\n"
        f"DIALECT: {dialect}\n\n"
        f"### DATABASE SCHEMA\n"
        f"{schema_snapshot}\n\n"
        f"### USER REQUEST\n"
        f"{command_text}\n\n"
        f"Provide the JSON response:"
    )


# -----------------------------
# Validator
# -----------------------------
def parse_and_validate_sql(sql: str, dialect: str) -> Tuple[bool, List[str], Dict[str, Any]]:
    """Parse SQL and return (ok, warnings, metadata)."""
    warnings: List[str] = []
    metadata: Dict[str, Any] = {"tables": [], "columns": [], "pretty": sql}

    if not sql:
        return False, ["No SQL provided"], metadata

    # Basic destructive detection via keywords
    lowered = sql.lower()
    if re.search(r'\b(drop|alter|delete|truncate)\b', lowered):
        warnings.append("Destructive keyword detected (drop/alter/delete/truncate)")

    # Try sqlglot parsing
    if sqlglot:
        try:
            ast = parse_one(sql, read=dialect)
            
            # Collect tables
            tables = set()
            for node in ast.find_all(exp.Table):
                with contextlib.suppress(Exception):
                    if hasattr(node.this, "name"):
                        tables.add(node.this.name)
                    else:
                        tables.add(str(node.this))

            # Collect columns
            cols = set()
            for col in ast.find_all(exp.Column):
                with contextlib.suppress(Exception):
                    name = col.name
                    if tbl := (col.table or None):
                        cols.add(f"{tbl}.{name}")
                    else:
                        cols.add(name)

            metadata["tables"] = list(tables)
            metadata["columns"] = list(cols)

            # Pretty print
            if sqlparse:
                try:
                    metadata["pretty"] = sqlparse.format(sql, reindent=True, keyword_case='upper')
                except Exception:
                    metadata["pretty"] = sql
            
            # Warn on potential Cartesian products
            if len(tables) > 1 and "join" not in lowered and "where" not in lowered:
                warnings.append("Multiple tables referenced without explicit JOIN/WHERE")

            return True, warnings, metadata

        except Exception as e:
            return False, [f"sqlglot parse error: {e}"], metadata

    # Fallback: minimal parsing
    simple_tables = re.findall(r'\bfrom\s+([`"]?)(\w+)\1|\binto\s+([`"]?)(\w+)\3', sql, flags=re.IGNORECASE)
    tnames = []
    tnames.extend(g for grp in simple_tables for g in grp if g and re.fullmatch(r'\w+', g))
    metadata["tables"] = list(set(tnames))
    return True, warnings, metadata


# -----------------------------
# Mock LLM (Updated for new JSON structure)
# -----------------------------
def simple_mock_llm_generate(prompt: str) -> str:
    """Deterministic rule-based mapper for testing without API key."""
    m = re.search(r'### USER REQUEST\n(.+)', prompt, flags=re.IGNORECASE | re.DOTALL)
    cmd = m.group(1).strip() if m else prompt
    cmd_lower = cmd.lower()

    # Count
    if re.search(r'\bcount\b', cmd_lower):
        m_from = re.search(r'from\s+([`"]?)(\w+)\1', cmd_lower)
        tbl = m_from.group(2) if m_from else "unknown_table"
        out = {
            "thought_process": f"User wants to count rows in {tbl}. Generating simple count query.",
            "sql": f"SELECT COUNT(*) FROM {tbl};",
            "intent": "select",
            "destructive": False,
            "clarify_required": False,
            "explanation": "Count rows"
        }
        return json.dumps(out)

    # Starts with
    if m_sw := re.search(r"surname\s+(?:that\s+)?starts\s+with\s+'?\"?([a-zA-Z0-9])", cmd_lower):
        ch = m_sw.group(1).upper()
        out = {
            "thought_process": "Detected pattern matching request. Using LIKE operator.",
            "sql": f"SELECT * FROM students WHERE surname LIKE '{ch}%';",
            "intent": "select",
            "destructive": False,
            "clarify_required": False,
            "explanation": f"Surname starts with {ch}"
        }
        return json.dumps(out)

    # Create table
    if m_ct := re.search(r'create\s+(?:a\s+)?(?:new\s+)?table\s+called\s+(\w+)', cmd_lower):
        tbl = m_ct.group(1)
        out = {
            "thought_process": "User wants to create a new table. This is a DDL operation.",
            "sql": f"CREATE TABLE {tbl} (id INT PRIMARY KEY);",
            "intent": "create",
            "destructive": True,
            "clarify_required": False,
            "explanation": "Create table"
        }
        return json.dumps(out)

    # Fallback
    out = {
        "thought_process": "Unrecognized pattern in mock mode.",
        "sql": None,
        "intent": "other",
        "destructive": False,
        "clarify_required": True,
        "explanation": "Ambiguous request"
    }
    return json.dumps(out)


# -----------------------------
# GeminiReasoner class
# -----------------------------
class GeminiReasoner:
    def __init__(self, schema_snapshot: str = "", model: str = GEMINI_MODEL, api_key: Optional[str] = GEMINI_API_KEY):
        self.schema_snapshot = schema_snapshot or "NO_SCHEMA_PROVIDED"
        self.model_name = model 
        self.api_key = api_key
        self.default_dialect = DEFAULT_DIALECT
        self.model = None 
        self._init_client() 

    def _init_client(self):
        if self._use_real_genai():
            genai.configure(api_key=self.api_key)
            try:
                self.model = genai.GenerativeModel(self.model_name)
            except Exception as e:
                print(f"Warning: Failed to init model {self.model_name}: {e}")
        else:
            self.model = None

    def _use_real_genai(self) -> bool:
        return GENAI_AVAILABLE and bool(self.api_key)

    def update_schema(self, schema_snapshot: str):
        self.schema_snapshot = schema_snapshot

    def _prepare_prompt(self, cmd: CommandPayload) -> str:
        dialect = cmd.dialect or self.default_dialect
        command_text = cmd.normalized or cmd.raw_nl
        return build_user_prompt(self.schema_snapshot, command_text, dialect)

    def _call_llm(self, prompt: str) -> str:
        if not self._use_real_genai():
            return simple_mock_llm_generate(prompt)

        try:
            if self.model is None:
                self.model = genai.GenerativeModel(self.model_name)

            response = self.model.generate_content(prompt)

            if hasattr(response, "text") and response.text:
                return response.text
            elif hasattr(response, "candidates") and response.candidates:
                return response.candidates[0].content.parts[0].text
            else:
                raise RuntimeError("Gemini API returned no text.")
        except Exception as e:
            raise RuntimeError(f"Failed to call Gemini API: {e}")

    def generate(self, cmd: CommandPayload) -> ReasonerOutput:
        dialect = (cmd.dialect or self.default_dialect).lower()
        prompt = self._prepare_prompt(cmd)

        # Generate Raw Output
        try:
            raw_model_output = self._call_llm(prompt)
        except RuntimeError as e:
            return ReasonerOutput(
                sql=None, intent=cmd.intent, dialect=dialect, warnings=[],
                errors=[f"LLM call failed: {e}"], metadata={},
                explain_text=None, confidence=0.0, safe_to_execute=False
            )

        # Extract JSON
        text = raw_model_output.strip()
        if text.startswith("```json"):
            parts = text.split("```json", 1)
            if len(parts) > 1:
                text = parts[1].split("```", 1)[0].strip()
        elif text.startswith("```"):
            parts = text.split("```", 1)
            if len(parts) > 1:
                text = parts[1].split("```", 1)[0].strip()

        # Parse JSON
        json_obj = None
        try:
            json_obj = json.loads(text)
        except json.JSONDecodeError as ex:
            # Salvage attempt
            s, e = text.find("{"), text.rfind("}")
            if s != -1 and e != -1 and e > s:
                try:
                    json_obj = json.loads(text[s:e+1])
                except:
                    pass
            
            if not json_obj:
                return ReasonerOutput(
                    sql=None, intent=cmd.intent, dialect=dialect, warnings=[],
                    errors=[f"Invalid JSON output: {ex}"], metadata={},
                    explain_text=None, confidence=0.0, safe_to_execute=False
                )

        # Extract Fields
        sql = json_obj.get("sql")
        intent = json_obj.get("intent") or cmd.intent or "select"
        destructive_flag = bool(json_obj.get("destructive", False))
        clarify_required = bool(json_obj.get("clarify_required", False))
        explanation = json_obj.get("explanation", None)
        thought_process = json_obj.get("thought_process", None)

        # Validate
        ok, warnings, metadata = parse_and_validate_sql(sql, dialect) if sql else (False, ["No SQL returned"], {})
        
        errors: List[str] = []
        if not ok:
            errors.append("SQL parse/validation failed.")
        if destructive_flag and not cmd.allow_destructive:
            errors.append("Destructive operation detected but not allowed.")
            warnings.append("Blocked destructive operation")

        safe_to_execute = ok and (not destructive_flag or cmd.allow_destructive) and (not clarify_required)
        confidence = 0.9 if ok and not clarify_required else 0.4

        return ReasonerOutput(
            sql=sql,
            intent=intent,
            dialect=dialect,
            warnings=warnings,
            errors=errors,
            metadata=metadata,
            explain_text=explanation,
            confidence=confidence,
            safe_to_execute=safe_to_execute,
            thought_process=thought_process
        )


# -----------------------------
# CLI
# -----------------------------
def interactive_cli(schema_file: Optional[str], dialect: Optional[str]):
    if schema_file:
        with open(schema_file, "r", encoding="utf-8") as f:
            schema = f.read()
    else:
        print("No schema file provided; using example schema.")
        schema = "Table students: id (int), surname (varchar), firstname (varchar), age (int)"

    reasoner = GeminiReasoner(schema_snapshot=schema)

    print("\nGemini Reasoner Ready.")
    print(f"Mode: {'Real Gemini' if reasoner._use_real_genai() else 'Mock LLM'}")
    print("Type 'exit' to quit.\n")

    while True:
        nl = input("NL> ").strip()
        if not nl: continue
        if nl.lower() in ("exit", "quit"): break
        
        payload = CommandPayload(intent="select", raw_nl=nl, normalized=nl, dialect=dialect)
        out = reasoner.generate(payload)
        
        print("\n--- OUTPUT ---")
        if out.thought_process:
            print(f"💭 Thought: {out.thought_process}")
        print(f"📝 SQL: {out.sql}")
        print(f"⚙️  Intent: {out.intent}")
        print(f"🛡️  Safe: {out.safe_to_execute}")
        if out.errors: print(f"❌ Errors: {out.errors}")
        print("--------------\n")


def quick_test():
    print("Running quick tests...")
    r = GeminiReasoner(api_key=None) # Force mock
    
    tests = [
        ("Show me students whose surname starts with A", "LIKE 'A%'"),
        ("Count how many students exist", "COUNT(*)"),
    ]

    for nl, expected in tests:
        print(f"Testing: {nl}")
        out = r.generate(CommandPayload(intent="select", raw_nl=nl, dialect="mysql"))
        
        if out.sql and expected in out.sql:
            print("✅ PASS")
        else:
            print(f"❌ FAIL: Got {out.sql}")
            
    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", dest="schema_file", help="Path to schema file")
    parser.add_argument("--dialect", dest="dialect", help="SQL dialect", default="mysql")
    parser.add_argument("--run-test", dest="run_test", action="store_true", help="Run tests")
    args = parser.parse_args()

    if args.run_test:
        quick_test()
    else:
        interactive_cli(args.schema_file, args.dialect)