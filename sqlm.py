#!/usr/bin/env python3
"""

How to get this kini running:
  - First, grab these packages (trust me, you'll need them):
      pip install python-dotenv sqlglot sqlparse google-generativeai

  - If you wanna play with it in the command line:
      python sqlm.py --schema schema.txt

  - Or just run my quick test to see if everything's working:
      python sqlm.py --run-test

Quick heads up:
  - If you've got google-genai installed and set up your GEMINI_API_KEY, 
    it'll use the real Gemini AI. If not, no worries - I made a simple mock
    version for testing. Not as smart, but gets the job done!
"""

from __future__ import annotations
import os
import json
import re
import argparse
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple

from dotenv import load_dotenv


load_dotenv()

# Hey, trying to import the cool extras - don't sweat it if they're not installed
try:
    import importlib
    _sqlglot_mod = importlib.import_module("sqlglot")
    # expose module and commonly used symbols if available
    sqlglot = _sqlglot_mod
    parse_one = getattr(_sqlglot_mod, "parse_one", None)
    exp = getattr(_sqlglot_mod, "exp", None)
except Exception:
    # Fallbacks when sqlglot is not installed or cannot be imported
    sqlglot = None
    parse_one = None
    exp = None

try:
    import importlib
    _sqlparse_mod = importlib.import_module("sqlparse")
    sqlparse = _sqlparse_mod
except Exception:
    sqlparse = None

# Trying to hook up with Gemini - if it fails, we'll just use my backup plan
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
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-2.5-pro")
GEMINI_MAX_TOKENS = int(os.getenv("GEMINI_MAX_TOKENS", "8192"))  # Default to 8192 tokens
DEFAULT_DIALECT = os.getenv("DEFAULT_DIALECT", "mysql")
MAX_SCHEMA_PROMPT_CHARS = int(os.getenv("MAX_SCHEMA_PROMPT_CHARS", "14000"))



# -----------------------------
# Data models
# -----------------------------
@dataclass
class CommandPayload:
    """
    Input contract from Command Processing Layer.
    - intent: basic operation family (select/insert/update/delete/create_table/alter/other)
    - raw_nl: original natural language
    - normalized: preprocessed NL (optional)
    - target_db: optional DB name
    - dialect: optional SQL dialect (mysql/postgres/sqlite)
    - allow_destructive: bool to allow destructive ops
    - session_context: optional dict with active_table, etc.
    - entities: optional extracted entities (tables/cols) from command processor
    """
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
    sql: Optional[str]
    intent: str
    dialect: str
    warnings: List[str]
    errors: List[str]
    metadata: Dict[str, Any]
    explain_text: Optional[str]
    confidence: float
    safe_to_execute: bool


# -----------------------------
# Prompt templates
# -----------------------------
BASE_SYSTEM_PROMPT = """You are a strict SQL generation assistant.
Rules (gotta follow these or things get messy):
1) Just give me a JSON object - nothing else! Follow the schema below exactly.
2) Don't make up fake tables or columns - stick to what's in SCHEMA_SNAPSHOT.
3) If something's not clear, set "clarify_required": true and play it safe.
4) Flag anything destructive - I don't want accidents!
5) Keep track of which tables and columns you're using.

Here's what I need in that JSON:
{
  "sql": "<your SQL query or null if you're not sure>",
  "intent": "<select|insert|update|delete|create_table|alter|other>",
  "used_tables": ["t1","t2"],
  "used_columns": ["t1.col1","t2.col2"],
  "clarify_required": false,
  "destructive": false,
  "explanation": "keep it short and sweet (30 words max)"
}
JSON ONLY - NO EXTRA STUFF!
"""

def build_user_prompt(schema_snapshot: str, command_text: str, dialect: str) -> str:
    # Ensure schema isn't ridiculously large; responsibility for pre-filtering is on caller.
    if len(schema_snapshot) > MAX_SCHEMA_PROMPT_CHARS:
        schema_snapshot = schema_snapshot[:MAX_SCHEMA_PROMPT_CHARS] + "\n...[TRUNCATED]"
    prompt = (
        f"{BASE_SYSTEM_PROMPT}\n\n"
        f"SCHEMA_SNAPSHOT:\n{schema_snapshot}\n\n"
        f"DIALECT: {dialect}\n\n"
        f"USER_REQUEST: {command_text}\n\n"
        f"Produce the JSON output matching the structure above."
    )
    return prompt


# -----------------------------
# Validator (uses sqlglot if available)
# -----------------------------
def parse_and_validate_sql(sql: str, dialect: str) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Parse SQL and return (ok, warnings, metadata).
    If sqlglot not installed, perform lightweight checks.
    """
    warnings: List[str] = []
    metadata: Dict[str, Any] = {"tables": [], "columns": [], "pretty": sql}

    if not sql:
        return False, ["No SQL provided"], metadata

    # Basic destructive detection via keywords
    lowered = sql.lower()
    if re.search(r'\b(drop|alter|delete|truncate)\b', lowered):
        warnings.append("Destructive keyword detected (drop/alter/delete/truncate)")

    # Try sqlglot parsing for stronger analysis
    if sqlglot:
        try:
            ast = parse_one(sql, read=dialect)
        except Exception as e:
            return False, [f"sqlglot parse error: {e}"], metadata

        # collect tables
        tables = set()
        for node in ast.find_all(exp.Table):
            try:
                if hasattr(node.this, "name"):
                    tables.add(node.this.name)
                else:
                    tables.add(str(node.this))
            except Exception:
                # Some AST nodes may not have the expected structure; safely skip these.
                pass

        cols = set()
        for col in ast.find_all(exp.Column):
            try:
                tbl = col.table or None
                name = col.name
                if tbl:
                    cols.add(f"{tbl}.{name}")
                else:
                    cols.add(name)
            except Exception:
                pass

        metadata["tables"] = list(tables)
        metadata["columns"] = list(cols)

        # pretty print
        if sqlparse:
            try:
                metadata["pretty"] = sqlparse.format(sql, reindent=True, keyword_case='upper')
            except Exception:
                metadata["pretty"] = sql
        else:
            metadata["pretty"] = sql

        # warn on potential Cartesian products (no joins but multiple tables used)
        if len(tables) > 1 and "join" not in lowered and "where" not in lowered:
            warnings.append("Multiple tables referenced without explicit JOIN/WHERE — possible Cartesian product")

        return True, warnings, metadata

    # Fallback: minimal parsing, attempt to extract table names after FROM or INTO
    simple_tables = re.findall(r'\bfrom\s+([`"]?)(\w+)\1|\binto\s+([`"]?)(\w+)\3', sql, flags=re.IGNORECASE)
    tnames = []
    for grp in simple_tables:
        # groups may contain matches in different positions
        for g in grp:
            if g and re.fullmatch(r'\w+', g):
                tnames.append(g)
    metadata["tables"] = list(set(tnames))
    metadata["columns"] = []  # can't infer reliably without parser
    return True, warnings, metadata


# -----------------------------
# Simple deterministic mock LLM for local testing
# -----------------------------
def simple_mock_llm_generate(prompt: str) -> str:
    """
    Very small deterministic rule-based mapper that extracts simple intent patterns
    and returns the JSON structure as a string. This is used when real genai client is unavailable.
    Covers basics: SELECT * WHERE <col> starts with X, COUNT, CREATE TABLE.
    """
    # Extract USER_REQUEST
    m = re.search(r'USER_REQUEST:\s*(.+)', prompt, flags=re.IGNORECASE | re.DOTALL)
    cmd = m.group(1).strip() if m else prompt

    cmd_lower = cmd.lower()

    # handle 'count' requests
    if re.search(r'\bcount\b', cmd_lower):
        # find table name simple heuristic: "count .* from <table>" or "count how many <table>"
        tbl = None
        m_from = re.search(r'from\s+([`"]?)(\w+)\1', cmd_lower)
        if m_from:
            tbl = m_from.group(2)
        else:
            m_howmany = re.search(r'how many (\w+)', cmd_lower)
            if m_howmany:
                tbl = m_howmany.group(1)
        sql = f"SELECT COUNT(*) FROM {tbl};" if tbl else None
        out = {
            "sql": sql,
            "intent": "select",
            "used_tables": [tbl] if tbl else [],
            "used_columns": [],
            "clarify_required": False if tbl else True,
            "destructive": False,
            "explanation": "Count rows"
        }
        return json.dumps(out)

    # handle "starts with" pattern
    m_sw = re.search(r"surname\s+(?:that\s+)?starts\s+with\s+'?\"?([a-zA-Z0-9])", cmd_lower)
    if m_sw:
        ch = m_sw.group(1).upper()
        sql = f"SELECT * FROM students WHERE surname LIKE '{ch}%';"
        out = {
            "sql": sql,
            "intent": "select",
            "used_tables": ["students"],
            "used_columns": ["students.surname"],
            "clarify_required": False,
            "destructive": False,
            "explanation": f"Surname starts with {ch}"
        }
        return json.dumps(out)

    # handle create table simple pattern: "create a new table called X with fields a (int), b (varchar)"
    m_ct = re.search(r'create\s+(?:a\s+)?(?:new\s+)?table\s+called\s+(\w+)\s+with\s+fields\s+(.+)', cmd_lower)
    if m_ct:
        tbl = m_ct.group(1)
        raw_fields = m_ct.group(2)
        # naive field extraction: split by comma, take first word as name and default type varchar
        fields = []
        for part in raw_fields.split(","):
            name = part.strip().split()[0]
            fields.append(f"{name} VARCHAR(255)")
        sql = f"CREATE TABLE {tbl} ({', '.join(fields)});"
        out = {
            "sql": sql,
            "intent": "create_table",
            "used_tables": [tbl],
            "used_columns": [],
            "clarify_required": False,
            "destructive": True,
            "explanation": "Create table"
        }
        return json.dumps(out)

    # fallback: if "show me" or "show" and mention table
    m_show = re.search(r'\bshow(?: me)?(?: all)?(?: the)?(?: rows)?(?: of)?\s*(\w+)', cmd_lower)
    if m_show:
        tbl = m_show.group(1)
        sql = f"SELECT * FROM {tbl};"
        out = {
            "sql": sql,
            "intent": "select",
            "used_tables": [tbl],
            "used_columns": [],
            "clarify_required": False,
            "destructive": False,
            "explanation": f"Select all rows from {tbl}"
        }
        return json.dumps(out)

    # ultimate fallback: ask for clarification
    out = {
        "sql": None,
        "intent": "other",
        "used_tables": [],
        "used_columns": [],
        "clarify_required": True,
        "destructive": False,
        "explanation": "Ambiguous request — clarification required"
    }
    return json.dumps(out)


# -----------------------------
# GeminiReasoner class
# -----------------------------
class GeminiReasoner:
    def __init__(self, schema_snapshot: str = "", model: str = GEMINI_MODEL, api_key: Optional[str] = GEMINI_API_KEY):
        self.schema_snapshot = schema_snapshot or "NO_SCHEMA_PROVIDED"
        self.model_name = model # Renamed to avoid conflict with `self.model` instance
        self.api_key = api_key
        self.default_dialect = DEFAULT_DIALECT
        self.model = None # Initialize model to None
        self._init_client() # Call init client after model_name and api_key are set

    def _init_client(self):
        if self._use_real_genai():
            genai.configure(api_key=self.api_key)
            try:
                # List available models
                available_models = genai.list_models()
                model_names = [model.name for model in available_models]
                if self.model_name not in model_names:
                    raise RuntimeError(
                        f"Model '{self.model_name}' is not available. Available models: {', '.join(model_names)}"
                    )
                # Initialize the generative model
                self.model = genai.GenerativeModel(self.model_name)
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Gemini client: {e}")
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
        """
        Call Gemini API to generate a response using the proper client call.
        """
        if not self._use_real_genai():
            return simple_mock_llm_generate(prompt)

        try:
            if self.model is None:
                # Lazily initialize if not already done
                self.model = genai.GenerativeModel(self.model_name)

            # ✅ Correct API call for Gemini SDK
            response = self.model.generate_content(prompt)

            # Extract text safely
            if hasattr(response, "text") and response.text:
                return response.text
            elif hasattr(response, "candidates") and response.candidates:
                return response.candidates[0].content.parts[0].text
            else:
                raise RuntimeError("Gemini API returned no text in the response.")
        except Exception as e:
            raise RuntimeError(f"Failed to call Gemini API: {e}")

    def generate(self, cmd: CommandPayload) -> ReasonerOutput:
        dialect = (cmd.dialect or self.default_dialect).lower()
        prompt = self._prepare_prompt(cmd)

        # Determine whether to use mock LLM or real LLM
        if not self._use_real_genai():
            raw_model_output = simple_mock_llm_generate(prompt)
        else:
            try:
                raw_model_output = self._call_llm(prompt)
            except RuntimeError as e:
                return ReasonerOutput(
                    sql=None,
                    intent=cmd.intent,
                    dialect=dialect,
                    warnings=[],
                    errors=[f"LLM call failed: {e}"],
                    metadata={},
                    explain_text=None,
                    confidence=0.0,
                    safe_to_execute=False
                )


        # Model should return only JSON. Attempt to extract JSON blob.
        text = raw_model_output.strip()
        if text.startswith("```json"): # Expecting '```json' for code fences
            # remove code fences
            parts = text.split("```json", 1) # Split only once
            if len(parts) > 1:
                text_after_fence = parts[1].strip()
                if text_after_fence.endswith("```"):
                    text = text_after_fence[:-3].strip()
                else:
                    text = text_after_fence.strip()
            else:
                # if it started with ```json but didn't have content after, assume an issue
                pass
        elif text.startswith("```"): # If it's just '```'
            parts = text.split("```", 1) # Split only once
            if len(parts) > 1:
                text_after_fence = parts[1].strip()
                if text_after_fence.endswith("```"):
                    text = text_after_fence[:-3].strip()
                else:
                    text = text_after_fence.strip()
            else:
                pass


        # try direct json load
        json_obj = None
        try:
            json_obj = json.loads(text)
        except json.JSONDecodeError as ex: # Catch specific JSON decode error
            # salvage attempt: find first {...}
            s = text.find("{")
            e = text.rfind("}")
            if s != -1 and e != -1 and e > s:
                try:
                    json_obj = json.loads(text[s:e+1])
                except json.JSONDecodeError as ex2: # Catch specific JSON decode error for salvage
                    # fail: return structured error
                    return ReasonerOutput(
                        sql=None,
                        intent=cmd.intent,
                        dialect=dialect,
                        warnings=[],
                        errors=[f"Failed to parse model JSON: {ex}. Salvage attempt also failed: {ex2}", "raw_output_snippet:" + text[:1000]],
                        metadata={},
                        explain_text=None,
                        confidence=0.0,
                        safe_to_execute=False
                    )
            else:
                return ReasonerOutput(
                    sql=None,
                    intent=cmd.intent,
                    dialect=dialect,
                    warnings=[],
                    errors=[f"Model output not valid JSON and no JSON blob found: {ex}. Raw output snippet: {text[:1000]}"],
                    metadata={},
                    explain_text=None,
                    confidence=0.0,
                    safe_to_execute=False
                )

        # Read expected fields
        sql = json_obj.get("sql")
        intent = json_obj.get("intent") or cmd.intent or "select"
        destructive_flag = bool(json_obj.get("destructive", False))
        clarify_required = bool(json_obj.get("clarify_required", False))
        explanation = json_obj.get("explanation", None)

        ok, warnings, metadata = parse_and_validate_sql(sql, dialect) if sql else (False, ["No SQL returned"], {})

        errors: List[str] = []
        if not ok:
            errors.append("SQL parse/validation failed.")
        if destructive_flag and not cmd.allow_destructive:
            errors.append("Destructive operation detected but allow_destructive is False.")
            warnings.append("Blocked destructive operation because allow_destructive=False")

        # safety decision
        safe_to_execute = ok and (not destructive_flag or cmd.allow_destructive) and (not clarify_required)
        confidence = 0.9 if ok and not clarify_required else 0.4

        # assemble reasoner output
        return ReasonerOutput(
            sql=sql,
            intent=intent,
            dialect=dialect,
            warnings=warnings,
            errors=errors,
            metadata=metadata,
            explain_text=explanation,
            confidence=confidence,
            safe_to_execute=safe_to_execute
        )


# -----------------------------
# CLI and quick tests
# -----------------------------
def interactive_cli(schema_file: Optional[str], dialect: Optional[str]):
    if schema_file:
        with open(schema_file, "r", encoding="utf-8") as f:
            schema = f.read()
    else:
        print("No schema file provided; using example schema.")
        schema = ("Database: studentdb\n"
                  "  Table students: id (int), surname (varchar), firstname (varchar), age (int), class_id (int)\n"
                  "  Table classes: id (int), classname (varchar)\n")

    # Pass the API key to the Reasoner
    reasoner = GeminiReasoner(schema_snapshot=schema, model=GEMINI_MODEL, api_key=GEMINI_API_KEY)

    print("\nGemini Reasoner (single-file) ready.")
    print("Type 'exit' to quit. Example NL:\n  show me students whose surname starts with A\n  count how many classes exist\n  create a new table called pets with fields name, species, age\n")
    
    # Check if real genai is available and print status
    if reasoner._use_real_genai():
        print(f"Using real Gemini model: {reasoner.model_name}")
    else:
        print("Using mock LLM (Gemini API not available or API key missing).")

    while True:
        nl = input("NL> ").strip()
        if not nl:
            continue
        if nl.lower() in ("exit", "quit"):
            break
        payload = CommandPayload(intent="select", raw_nl=nl, normalized=nl, dialect=dialect)
        out = reasoner.generate(payload)
        print("\n--- REASONER OUTPUT ---")
        print("SQL:", out.sql)
        print("Intent:", out.intent)
        print("Dialect:", out.dialect)
        print("Safe to execute:", out.safe_to_execute)
        print("Warnings:", out.warnings)
        print("Errors:", out.errors)
        print("Metadata:", json.dumps(out.metadata, indent=2))
        print("Confidence:", out.confidence)
        print("Explanation:", out.explain_text)
        print("-----------------------\n")


def quick_test():
    """Runs a few deterministic tests using the mock LLM (works even without genai)."""
    print("Running quick tests...")

    schema = ("Database: studentdb\n"
              "  Table students: id (int), surname (varchar), firstname (varchar), age (int)\n"
              "  Table classes: id (int), classname (varchar)\n")

    r = GeminiReasoner(schema_snapshot=schema, api_key=None)  # ensure mock mode
    # Ensure it reports using mock LLM for consistency in tests
    if r._use_real_genai():
        print("Warning: Real Gemini API is unexpectedly available in quick_test. Tests might behave differently.")
    else:
        print("Using mock LLM for quick tests.")

    tests = [
        ("Show me students whose surname starts with A", "SELECT * FROM students WHERE surname LIKE 'A%';"),
        ("Count how many classes exist", "SELECT COUNT(*) FROM classes;"),
        ("Create a new table called pets with fields name, species, age", "CREATE TABLE pets"),
        ("Show me all users", "SELECT * FROM users;"),  # ambiguous table not in schema: mock will still return SELECT * FROM users
    ]

    for nl, expected_frag in tests:
        payload = CommandPayload(intent="select", raw_nl=nl, normalized=nl, dialect="mysql")
        out = r.generate(payload)
        # Check if out.sql is not None before calling lower()
        ok = (out.sql is not None) and (expected_frag.split()[0].lower() in out.sql.lower())
        print(f"Test NL: {nl}")
        print(" -> SQL:", out.sql)
        print(" -> Safe:", out.safe_to_execute, "Warnings:", out.warnings, "Errors:", out.errors)
        print(" -> PASS" if ok else " -> FAIL")
        print()

    print("Quick tests complete.")


# -----------------------------
# Entrypoint
# -----------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gemini Reasoner single-file CLI")
    parser.add_argument("--schema", dest="schema_file", help="Path to schema snapshot file", default=None)
    parser.add_argument("--dialect", dest="dialect", help="SQL dialect (mysql/postgres/sqlite)", default=None)
    parser.add_argument("--run-test", dest="run_test", action="store_true", help="Run quick tests and exit")
    args = parser.parse_args()

    if args.run_test:
        quick_test()
    else:
        interactive_cli(args.schema_file, args.dialect)
