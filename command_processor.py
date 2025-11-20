#!/usr/bin/env python3
"""
Command Processing Layer (CLP)

This module acts as the interactive interface for the user, fulfilling the role
of the Command Processor in the system's logical pipeline.
"""

import os
import json
import re
from typing import Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

# This script assumes 'sqlm.py' is in the same directory.
try:
    from sqlm import GeminiReasoner, CommandPayload
except ImportError:
    print("Error: 'sqlm.py' not found.")
    print("Please ensure 'sqlm.py' is in the same directory as this script.")
    exit(1)


class CommandProcessor:
    """
    Orchestrates the process of converting a user's natural language request
    into an executable SQL query by interacting with the Gemini Reasoning Core.
    """

    def __init__(self, schema_file: str):
        """
        Initializes the Command Processor.

        Args:
            schema_file (str): The path to the file containing the full
                               database schema.
        """
        # FIX: Always assign self.schema_file first so it exists on the instance
        self.schema_file = schema_file

        if not os.path.exists(schema_file):
            # Create an empty file if it doesn't exist so the code doesn't crash immediately
            # expected workflow is that SchemaAwarenessModule runs first
            print(f"Warning: Schema file not found at: {schema_file}. initializing empty.")
            self.full_schema_text = ""

        self.full_schema_text: str = ""
        self.full_schema_dict: Dict[str, str] = {}
        self.snapshot_version = 0

        # Initialize Reasoner
        # We pass an empty schema initially; it will be updated when we load the file
        self.reasoner = GeminiReasoner(schema_snapshot="", api_key=os.getenv("GEMINI_API_KEY"))

        # Only attempt to load if the file actually exists
        if os.path.exists(self.schema_file):
            self._load_and_parse_schema()
            
        print("Command Processor initialized successfully.")


    def _load_and_parse_schema(self):
        """
        Loads the schema from the source file and parses it into a
        structured dictionary where each key is a table name.
        """
        print(f"Loading and parsing schema from '{self.schema_file}'...")
        with open(self.schema_file, "r", encoding="utf-8") as f:
            self.full_schema_text = f.read()

        # Regex parser to extract table definitions.
        table_sections = re.split(r'\n\s*Table ', self.full_schema_text)
        
        start_index = 1 if table_sections[0].strip().startswith("Database:") else 0
        
        for section in table_sections[start_index:]:
            if ':' in section:
                table_name, table_def = section.split(':', 1)
                table_name = table_name.strip()
                self.full_schema_dict[table_name] = f"Table {table_name}:{table_def.strip()}"
        
        if not self.full_schema_dict:
            print("\nWarning: Could not parse any table definitions from the schema file.")
        else:
            print(f"Successfully parsed {len(self.full_schema_dict)} tables.")


    def get_available_tables(self) -> List[str]:
        """Returns a list of all table names found in the schema."""
        return list(self.full_schema_dict.keys())

    def display_schema_as_json(self):
        """Displays the entire parsed schema to the user in a readable JSON format."""
        print("\n--- Current General Schema Snapshot (JSON View) ---")
        print(json.dumps(self.full_schema_dict, indent=2))
        print("---------------------------------------------------\n")

    def create_specialized_snapshot(self, table_names: List[str]) -> Optional[str]:
        """
        Creates a schema snapshot string containing only the definitions for
        the specified tables.
        """
        snapshot_parts = []
        for name in table_names:
            if name in self.full_schema_dict:
                snapshot_parts.append(self.full_schema_dict[name])
            else:
                print(f"Error: Table '{name}' not found in the loaded schema.")
                return None
        
        self.snapshot_version += 1
        print(f"\nSuccessfully created specialized_snapshot (version {self.snapshot_version}) with {len(table_names)} tables.")
        return "\n\n".join(snapshot_parts)

    def run_interactive_session(self):
        """
        Runs the main interactive loop for the user to enter commands.
        """
        print("\n--- Gemini SQL Interactive CLP ---")
        print("Type 'exit' to quit, 'schema' to view the full schema as JSON.")

        while True:
            # Step 1: Display available tables
            print("\nAvailable Tables:")
            available_tables = self.get_available_tables()
            if not available_tables:
                print("  (No tables found. Make sure to connect a DB via Schema Awareness Module first)")
            
            for i, table in enumerate(available_tables):
                print(f"  {i+1}. {table}")

            # Step 2: Get user table selection
            print("\nOptions:")
            print("  - Type 'all' to use ALL tables")
            print("  - Type specific table numbers/names (comma-separated)")
            print("  - Press ENTER to use full database schema")
            tables_input = input("Selection: ").strip()
            
            if tables_input.lower() == 'exit':
                break
            if tables_input.lower() == 'schema':
                self.display_schema_as_json()
                continue

            # Determine which schema to use
            selected_tables = []
            schema_to_use = None
            use_full_schema = False
            
            if not tables_input:
                print("Using full database schema (database-level operations).")
                schema_to_use = self.full_schema_text
                use_full_schema = True
            elif tables_input.lower() == 'all':
                selected_tables = available_tables.copy()
                print(f"Using ALL tables: {', '.join(selected_tables)}")
                schema_to_use = self.create_specialized_snapshot(selected_tables)
                if schema_to_use is None:
                    continue
            else:
                parts = [p.strip() for p in tables_input.split(',')]
                for part in parts:
                    if part.isdigit() and 1 <= int(part) <= len(available_tables):
                        selected_tables.append(available_tables[int(part) - 1])
                    elif part in available_tables:
                        selected_tables.append(part)
                    else:
                        print(f"Warning: '{part}' is not a valid table name or number. It will be ignored.")
                
                if not selected_tables:
                    print("Error: No valid tables were selected.")
                    continue
                
                schema_to_use = self.create_specialized_snapshot(selected_tables)
                if schema_to_use is None:
                    continue

            # Step 3: Get user NL query and dialect
            # Step 3: Get user NL query and dialect
            nl_query = input("\nEnter your Natural Language query: ").strip()
            if not nl_query:
                print("Error: Query cannot be empty.")
                continue
            
            dialect = input("Enter SQL dialect (e.g., mysql, postgres) [default: mysql]: ").strip().lower() or "mysql"

            # Step 4: Update reasoner schema and create CommandPayload
            self.reasoner.update_schema(schema_to_use)
            payload = CommandPayload(
                intent="query",
                raw_nl=nl_query,
                dialect=dialect,
                allow_destructive=False
            )

            # Step 5: Call the Gemini Reasoner
            print("\nTranslating NL to SQL via Gemini Reasoning Core...")
            output = self.reasoner.generate(payload)

            # Step 6: Display the results (UPDATED)
            print("\n--- CLP Received from Reasoner ---")
            # New: Display Chain of Thought
            if output.thought_process:
                print(f"💭 Thought Process: {output.thought_process}")
                print("-" * 30)
            
            print(f"📝 Generated SQL: {output.metadata.get('pretty', output.sql)}")
            print(f"⚙️  Intent: {output.intent}")
            print(f"🗄️  Dialect: {output.dialect}")
            print(f"🛡️  Safe to Execute: {output.safe_to_execute}")
            print(f"📊 Confidence: {output.confidence:.2f}")
            print(f"💡 Explanation: {output.explain_text}")
            
            if output.warnings:
                print(f"⚠️ Warnings: {output.warnings}")
            if output.errors:
                print(f"❌ Errors: {output.errors}")
            print("----------------------------------\n")

            # Step 7: Simulate Schema Awareness Module interaction
            if output.safe_to_execute and output.intent in ["create_table", "alter", "delete", "update", "insert"]:
                print("[CLP -> Schema Awareness Module]: Notifying module of potential schema change.")
                update_confirm = input("A change was made. Do you wish to update the general snapshot? (yes/no): ").lower()
                if update_confirm == 'yes':
                    self._load_and_parse_schema()
                    print("[Schema Awareness Module]: General snapshot has been updated.")
                else:
                    print("[Schema Awareness Module]: Change acknowledged. Snapshot unchanged.")
            
            if not use_full_schema and selected_tables:
                print(f"[CLP]: Specialized snapshot version {self.snapshot_version} has been deleted after use.")


if __name__ == "__main__":
    SCHEMA_FILE = "schema.txt"
    try:
        clp = CommandProcessor(schema_file=SCHEMA_FILE)
        clp.run_interactive_session()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")