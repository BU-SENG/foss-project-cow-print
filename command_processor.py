#!/usr/bin/env python3
"""
Command Processing Layer (CLP)

This module acts as the interactive interface for the user, fulfilling the role
of the Command Processor in the system's logical pipeline.

Workflow:
1.  Loads the full database schema from a file (e.g., schema.txt).
2.  Presents the user with available tables.
3.  Allows the user to select specific tables for their query.
4.  Creates a "specialized snapshot" of the schema containing only the
    selected tables.
5.  Prompts the user for a Natural Language (NL) query and SQL dialect.
6.  Constructs a CommandPayload and sends it to the Gemini AI Reasoning Core.
7.  Receives the ReasonerOutput and displays the generated SQL and other
    metadata to the user.
8.  Simulates notifying the Schema Awareness Module of potential changes.
"""

import os
import json
import re
from typing import Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

# This script assumes 'sqlm.py' is in the same directory.
# It imports the necessary components from the AI processing module.
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
        if not os.path.exists(schema_file):
            raise FileNotFoundError(f"Schema file not found at: {schema_file}")
        self.schema_file = schema_file
        self.full_schema_text: str = ""
        self.full_schema_dict: Dict[str, str] = {}
        self.snapshot_version = 0

        # The reasoner is initialized here and its schema can be updated later.
        # This prevents re-initializing the model for every query.
        # We pass an empty schema initially; it will be updated on the first query.
        self.reasoner = GeminiReasoner(schema_snapshot="",api_key=os.getenv("GEMINI_API_KEY"))

        self._load_and_parse_schema()
        print("Command Processor initialized successfully.")
        if self.reasoner._use_real_genai():
            print(f"Using real Gemini model: {self.reasoner.model_name}")
        else:
            print("Using mock LLM (Gemini API not available or API key missing).")


    def _load_and_parse_schema(self):
        """
        Loads the schema from the source file and parses it into a
        structured dictionary where each key is a table name.
        """
        print(f"Loading and parsing schema from '{self.schema_file}'...")
        with open(self.schema_file, "r", encoding="utf-8") as f:
            self.full_schema_text = f.read()

        # A simple regex-based parser to extract table definitions.
        # It looks for "Table <name>:" and captures everything until the next "Table" or end of file.
        table_sections = re.split(r'\n\s*Table ', self.full_schema_text)
        
        # The first element might be the "Database: ..." line, so we skip it if it is.
        start_index = 1 if table_sections[0].strip().startswith("Database:") else 0
        
        for section in table_sections[start_index:]:
            if ':' in section:
                table_name, table_def = section.split(':', 1)
                table_name = table_name.strip()
                # We reconstruct the "Table <name>:" prefix for clarity in the snapshot.
                self.full_schema_dict[table_name] = f"Table {table_name}:{table_def.strip()}"
        
        if not self.full_schema_dict:
            print("\nWarning: Could not parse any table definitions from the schema file.")
            print("Please ensure the format is 'Table <tablename>:' followed by column definitions.")
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

        Args:
            table_names (List[str]): A list of table names to include.

        Returns:
            Optional[str]: A string containing the combined schema definitions,
                           or None if any table is not found.
        """
        snapshot_parts = []
        for name in table_names:
            if name in self.full_schema_dict:
                snapshot_parts.append(self.full_schema_dict[name])
            else:
                print(f"Error: Table '{name}' not found in the loaded schema.")
                return None
        
        self.snapshot_version += 1
        # The conceptual name "specialezd_table<n>" refers to this generated snapshot.
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
            for i, table in enumerate(available_tables):
                print(f"  {i+1}. {table}")

            # Step 2: Get user table selection
            tables_input = input("\nSelect tables to query by number or name (comma-separated), or type 'exit': ").strip()
            if tables_input.lower() == 'exit':
                break
            if tables_input.lower() == 'schema':
                self.display_schema_as_json()
                continue
            if not tables_input:
                print("Error: No tables selected. Please try again.")
                continue

            selected_tables = []
            parts = [p.strip() for p in tables_input.split(',')]
            for part in parts:
                if part.isdigit() and 1 <= int(part) <= len(available_tables):
                    selected_tables.append(available_tables[int(part) - 1])
                elif part in available_tables:
                    selected_tables.append(part)
                else:
                    print(f"Warning: '{part}' is not a valid table name or number. It will be ignored.")
            
            if not selected_tables:
                print("Error: No valid tables were selected. Please try again.")
                continue
            
            print(f"Tables selected for this query: {', '.join(selected_tables)}")

            # Step 3: Create the specialized snapshot
            specialized_schema = self.create_specialized_snapshot(selected_tables)
            if specialized_schema is None:
                continue

            # Step 4: Get user NL query and dialect
            nl_query = input("Enter your Natural Language query: ").strip()
            if not nl_query:
                print("Error: Query cannot be empty.")
                continue
            
            dialect = input("Enter SQL dialect (e.g., mysql, postgres) [default: mysql]: ").strip().lower() or "mysql"

            # Step 5: Update reasoner schema and create CommandPayload
            self.reasoner.update_schema(specialized_schema)
            payload = CommandPayload(
                intent="query",  # Defaulting to 'query' as CLP focuses on NL-to-SQL
                raw_nl=nl_query,
                dialect=dialect,
                allow_destructive=False # Safety default
            )

            # Step 6: Call the Gemini Reasoner
            print("\nTranslating NL to SQL via Gemini Reasoning Core...")
            output = self.reasoner.generate(payload)

            # Step 7: Display the results
            print("\n--- CLP Received from Reasoner ---")
            print(f"Generated SQL: {output.metadata.get('pretty', output.sql)}")
            print(f"Intent: {output.intent}")
            print(f"Dialect: {output.dialect}")
            print(f"Safe to Execute: {output.safe_to_execute}")
            print(f"Confidence: {output.confidence:.2f}")
            print(f"Explanation: {output.explain_text}")
            print(f"Warnings: {output.warnings}")
            print(f"Errors: {output.errors}")
            print("----------------------------------\n")

            # Step 8: Simulate Schema Awareness Module interaction
            if output.safe_to_execute and output.intent in ["create_table", "alter", "delete", "update", "insert"]:
                print("[CLP -> Schema Awareness Module]: Notifying module of potential schema change.")
                update_confirm = input("A change was made. Do you wish to update the general snapshot? (yes/no): ").lower()
                if update_confirm == 'yes':
                    # In a real system, this would trigger a full DB scan.
                    # Here, we just simulate it by reloading from the original file.
                    self._load_and_parse_schema()
                    print("[Schema Awareness Module]: General snapshot has been updated.")
                else:
                    print("[Schema Awareness Module]: Change acknowledged. General snapshot remains unchanged.")
            
            # Per requirement, the specialized snapshot is always "deleted" after use.
            print(f"[CLP]: Specialized snapshot version {self.snapshot_version} has been deleted after use.")


if __name__ == "__main__":
    SCHEMA_FILE = "schema.txt"
    try:
        clp = CommandProcessor(schema_file=SCHEMA_FILE)
        clp.run_interactive_session()
    except FileNotFoundError as e:
        print(f"\nFatal Error: {e}")
        print("Please make sure the 'schema.txt' file exists in the same directory.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")