import google.generativeai as genai
import os
from dotenv import load_dotenv
import streamlit as st
from typing import Dict, List, Optional, Any
import json
import re
import time

load_dotenv()

class GeminiSQLGenerator:
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        
        # Gemini models in order of preference for SQL tasks
        self.sql_models = [
            'gemini-2.0-flash-001',      # Best for free tier
            'gemini-2.5-flash',          # Good alternative
            'gemini-2.0-flash',          # Another option
            'gemini-2.0-flash-lite-001', # Lite version
        ]
        
        self.model_name = model or os.getenv('GEMINI_MODEL', 'gemini-2.0-flash-001')
        self.client = None
        self.initialized_model = None
        self.schema_snapshot = {}  # Add schema storage
        self.last_request_time = 0
        self.request_delay = 2
        
        if self.api_key:
            self._initialize_client()
    
    def update_schema(self, schema_data: Dict):
        """Update the schema snapshot that will be used in prompts"""
        self.schema_snapshot = schema_data
        st.success(f"📊 Schema updated with {len(schema_data.get('tables', {}))} tables")
    
    def _initialize_client(self):
        """Initialize the Gemini client"""
        try:
            genai.configure(api_key=self.api_key)
            
            # Try the configured model first
            try:
                self.client = genai.GenerativeModel(self.model_name)
                self.initialized_model = self.model_name
                st.success(f"✅ Using: {self.model_name}")
                return
            except Exception as e:
                st.warning(f"⚠️ Model {self.model_name} not available, trying alternatives...")
            
            # Try alternative models
            for model_name in self.sql_models:
                if model_name == self.model_name:
                    continue
                    
                try:
                    self.client = genai.GenerativeModel(model_name)
                    self.initialized_model = model_name
                    self.model_name = model_name
                    
                    st.success(f"✅ Using: {model_name}")
                    
                    # Update environment
                    os.environ['GEMINI_MODEL'] = model_name
                    return
                    
                except Exception as e:
                    continue
            
            raise Exception("No working Gemini models found")
            
        except Exception as e:
            st.error(f"❌ Failed to initialize Gemini: {str(e)}")
    
    def _build_efficient_prompt(self, payload: 'CommandPayload') -> str:
        """Build efficient prompt to minimize token usage"""
        
        schema_context = ""
        if self.schema_snapshot and 'tables' in self.schema_snapshot:
            # Better schema representation with relationships
            schema_context = "DATABASE SCHEMA (Important: Use exact column names):\n"
            
            for table_name, table_info in list(self.schema_snapshot['tables'].items())[:8]:
                schema_context += f"\nTABLE: {table_name}\n"
                
                # Show columns with types
                for col in table_info['columns'][:10]:
                    pk_indicator = " [PRIMARY KEY]" if col.get('primary_key') else ""
                    schema_context += f"  - {col['name']} ({col['type']}){pk_indicator}\n"
                
                # Show relationships if any
                if table_info.get('foreign_keys'):
                    schema_context += "  RELATIONSHIPS:\n"
                    for fk in table_info['foreign_keys']:
                        schema_context += f"  - {fk['constrained_columns']} -> {fk['referred_table']}({fk['referred_columns']})\n"

        prompt = f"""
You are a SQL expert. Convert natural language to {payload.dialect} SQL.

USER QUERY: "{payload.raw_nl}"

SCHEMA:
{schema_context}

CRITICAL RULES:
1. Generate ONLY ONE SQL statement per request
2. NEVER use semicolons (;) to separate multiple statements
3. If the query is ambiguous, choose the most likely single table
4. For "show all tables" type requests, use: SELECT name FROM sqlite_master WHERE type='table'
5. Use EXACT column and table names from the schema
6. Output ONLY the SQL query, no explanations
7. Use proper {payload.dialect} syntax
8. No markdown formatting
9. No destructive operations unless explicitly allowed
10. Remove any trailing semicolons from the SQL

SQL QUERY:
"""
        return prompt

    def generate_sql(self, payload: 'CommandPayload') -> 'ReasonerOutput':
        """Generate SQL from natural language"""
        if not self.client:
            return ReasonerOutput(
                errors=["Gemini client not initialized. Please check API key."],
                safe_to_execute=False,
                confidence=0.0
            )
        
        # Rate limiting protection
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.request_delay:
            time.sleep(self.request_delay - time_since_last_request)
        
        try:
            prompt = self._build_efficient_prompt(payload)
            
            # Conservative generation config for free tier
            generation_config = {
                'temperature': 0.1,
                'max_output_tokens': 512,
            }
            
            response = self.client.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            self.last_request_time = time.time()
            
            sql_query = response.text.strip()
            sql_query = self._clean_sql_response(sql_query)
            
            # Basic validation
            validation_result = self._validate_sql_query(sql_query, payload)
            
            return ReasonerOutput(
                sql=sql_query,
                intent=payload.intent,
                dialect=payload.dialect,
                warnings=validation_result['warnings'],
                errors=validation_result['errors'],
                explain_text=f"Generated by {self.initialized_model}",
                confidence=validation_result['confidence'],
                safe_to_execute=validation_result['safe_to_execute']
            )
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                return ReasonerOutput(
                    errors=["Rate limit exceeded. Please wait 1 minute."],
                    safe_to_execute=False,
                    confidence=0.0
                )
            else:
                return ReasonerOutput(
                    errors=[f"Generation failed: {error_msg}"],
                    safe_to_execute=False,
                    confidence=0.0
                )
    
    def _clean_sql_response(self, sql_query: str) -> str:
        """Clean SQL response"""
        # Remove markdown code blocks
        sql_query = re.sub(r'^```sql\s*', '', sql_query)
        sql_query = re.sub(r'^```\s*', '', sql_query)
        sql_query = re.sub(r'\s*```$', '', sql_query)
        
        # Remove common prefixes
        prefixes = ["SQL:", "Query:", "Here's the SQL:", "Generated SQL:"]
        for prefix in prefixes:
            if sql_query.lower().startswith(prefix.lower()):
                sql_query = sql_query[len(prefix):].strip()
        
        # Remove trailing semicolons
        sql_query = sql_query.strip().rstrip(';')
        
        return sql_query.strip()

    def _validate_sql_query(self, sql_query: str, payload: 'CommandPayload') -> Dict:
        """Basic SQL validation"""
        errors = []
        warnings = []
        safe_to_execute = True
        
        if not sql_query or len(sql_query.strip()) < 10:
            errors.append("Generated SQL is too short")
            return {'errors': errors, 'warnings': warnings, 'safe_to_execute': False, 'confidence': 0.1}
        
        sql_upper = sql_query.upper()
        
        # Check for multiple statements (semicolons)
        if sql_query.count(';') > 0:
            errors.append("Multiple SQL statements detected. Please ask for one table at a time.")
            safe_to_execute = False
        
        # Destructive operations check
        destructive_ops = ['DROP', 'TRUNCATE', 'DELETE', 'ALTER', 'CREATE TABLE']
        if any(op in sql_upper for op in destructive_ops) and not payload.allow_destructive:
            errors.append("Destructive operations not allowed")
            safe_to_execute = False
        
        # Basic confidence scoring
        confidence = 0.8
        if sql_upper.startswith('SELECT'):
            confidence = 0.85
        if 'JOIN' in sql_upper:
            confidence = 0.9
        
        # Reduce confidence for multiple statement attempts
        if sql_query.count(';') > 0:
            confidence = max(0.1, confidence - 0.4)
        
        if errors:
            confidence = max(0.1, confidence - 0.3)
        
        return {
            'errors': errors,
            'warnings': warnings,
            'safe_to_execute': safe_to_execute and len(errors) == 0,
            'confidence': confidence
        }


class CommandPayload:
    def __init__(self, intent: str, raw_nl: str, normalized: str = "", 
                 target_db: str = "", dialect: str = None,
                 allow_destructive: bool = False, session_context: Dict = None,
                 entities: Dict = None, schema_snapshot: Dict = None):
        self.intent = intent
        self.raw_nl = raw_nl
        self.normalized = normalized or raw_nl
        self.target_db = target_db
        
        # Auto-detect dialect from database type if not specified
        if dialect is None:
            self.dialect = 'mysql'  # Default fallback
        else:
            self.dialect = dialect
            
        self.allow_destructive = allow_destructive
        self.session_context = session_context or {}
        self.entities = entities or {}
        self.schema_snapshot = schema_snapshot or {}


class ReasonerOutput:
    def __init__(self, sql: str = "", intent: str = "", dialect: str = "",
                 warnings: List[str] = None, errors: List[str] = None,
                 metadata: Dict = None, explain_text: str = "",
                 confidence: float = 0.0, safe_to_execute: bool = False):
        self.sql = sql
        self.intent = intent
        self.dialect = dialect
        self.warnings = warnings or []
        self.errors = errors or []
        self.metadata = metadata or {}
        self.explain_text = explain_text
        self.confidence = confidence
        self.safe_to_execute = safe_to_execute