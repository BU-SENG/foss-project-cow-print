#!/usr/bin/env python3
"""
Schema Awareness Module (SAM)

This module is responsible for creating and maintaining schema snapshots of the database.
It's one of the first things that runs when a user connects to the database.

Key Responsibilities:
1. Auto-generates schema.txt when user connects their database
2. Creates specialized snapshots for specific table queries
3. Monitors and updates schema when database changes are detected
4. Provides schema versioning and change tracking
5. Handles schema introspection across different database types

Workflow:
1. User connects database → SAM scans and creates initial schema.txt
2. User requests query on specific tables → SAM creates specialized_snapshot_<id>.txt
3. Database changes detected → SAM automatically updates schema.txt
4. Specialized snapshots are temporary and deleted after use
"""

import os
import json
import sqlite3
import pymysql
import psycopg2
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib

from dotenv import load_dotenv

load_dotenv()


class DatabaseType(Enum):
    """Supported database types"""
    MYSQL = "mysql"
    POSTGRESQL = "postgres"
    SQLITE = "sqlite"


@dataclass
class SchemaMetadata:
    """Metadata about the schema snapshot"""
    database_name: str
    database_type: str
    created_at: str
    last_updated: str
    version: int
    table_count: int
    schema_hash: str
    tables: List[str]


@dataclass
class TableSchema:
    """Schema information for a single table"""
    name: str
    columns: List[Dict[str, Any]]
    primary_keys: List[str]
    foreign_keys: List[Dict[str, str]]
    indexes: List[str]
    row_count: Optional[int] = None


class SchemaAwarenessModule:
    """
    Manages database schema snapshots and keeps them synchronized with the actual database.
    """

    def __init__(self, output_dir: str = "."):
        """
        Initialize the Schema Awareness Module.

        Args:
            output_dir: Directory where schema files will be stored
        """
        self.output_dir = output_dir
        self.schema_file = os.path.join(output_dir, "schema.txt")
        self.metadata_file = os.path.join(output_dir, "schema_metadata.json")
        self.specialized_snapshots: Dict[str, str] = {}
        self.current_metadata: Optional[SchemaMetadata] = None
        self.connection = None
        self.db_type: Optional[DatabaseType] = None
        
        print("[SAM] Schema Awareness Module initialized.")

    def connect_database(self, db_type: str, **connection_params) -> bool:
        """
        Connect to a database and automatically generate initial schema.txt

        Args:
            db_type: Type of database ('mysql', 'postgres', 'sqlite')
            **connection_params: Database connection parameters
                For MySQL/Postgres: host, user, password, database, port
                For SQLite: database (file path)

        Returns:
            bool: True if connection and schema generation successful
        """
        # Extract non-sensitive info for safe logging
        target_db = connection_params.get('database', 'unknown')
        
        try:
            db_type_lower = db_type.lower()
            
            if db_type_lower == "mysql":
                self.db_type = DatabaseType.MYSQL
                self.connection = pymysql.connect(
                    host=connection_params.get('host', 'localhost'),
                    user=connection_params.get('user'),
                    password=connection_params.get('password'),
                    database=connection_params.get('database'),
                    port=int(connection_params.get('port', 3306)),
                    cursorclass=pymysql.cursors.DictCursor
                )
                print("[SAM] ✓ Connected to MySQL database.")
                
            elif db_type_lower in {"postgres", "postgresql"}:
                self.db_type = DatabaseType.POSTGRESQL
                self.connection = psycopg2.connect(
                    host=connection_params.get('host', 'localhost'),
                    user=connection_params.get('user'),
                    password=connection_params.get('password'),
                    database=connection_params.get('database'),
                    port=int(connection_params.get('port', 5432))
                )
                print("[SAM] ✓ Connected to PostgreSQL database.")
                
            elif db_type_lower == "sqlite":
                self.db_type = DatabaseType.SQLITE
                self.connection = sqlite3.connect(connection_params['database'])
                self.connection.row_factory = sqlite3.Row
                print("[SAM] ✓ Connected to SQLite database.")
                
            else:
                print(f"[SAM] ✗ Unsupported database type: {db_type}")
                return False

            # Auto-generate initial schema.txt
            print(f"\n[SAM] Scanning database and generating schema.txt...")
            success = self.generate_full_schema()
            
            if success:
                print("[SAM] ✓ schema.txt generated successfully!\n")
            else:
                print("[SAM] ✗ Failed to generate schema.txt\n")
            
            return success
            
        except Exception as e:
            # Sanitize error message to ensure no passwords are leaked
            error_msg = str(e)
            pwd = connection_params.get('password')
            
            # If password exists and is in the error message, redact it
            if pwd and isinstance(pwd, str) and len(pwd) > 0:
                error_msg = error_msg.replace(pwd, "******")
            
            print(f"[SAM] ✗ Database connection failed: {error_msg}")
            return False

    def _get_tables(self) -> List[str]:
        """
        Get list of all tables in the database (INTERNAL METHOD)
        
        Returns:
            List[str]: List of table names
        """
        if not self.connection:
            print("[SAM] Warning: No database connection.")
            return []
        
        cursor = self.connection.cursor()
        
        try:
            if self.db_type == DatabaseType.MYSQL:
                cursor.execute("SHOW TABLES")
                tables = [list(row.values())[0] for row in cursor.fetchall()]
                
            elif self.db_type == DatabaseType.POSTGRESQL:
                cursor.execute("""
                    SELECT tablename FROM pg_tables 
                    WHERE schemaname = 'public'
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
            elif self.db_type == DatabaseType.SQLITE:
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)
                tables = [row[0] for row in cursor.fetchall()]
            else:
                tables = []
                
            return tables
            
        except Exception as e:
            print(f"[SAM] Error getting tables: {e}")
            return []
            
        finally:
            cursor.close()

    def get_tables(self) -> List[str]:
        """
        PUBLIC method to get list of all tables in the database.
        This is the method that should be called by external modules.
        
        Returns:
            List[str]: List of table names, or empty list if not connected
            
        Example:
            >>> sam = SchemaAwarenessModule()
            >>> sam.connect_database("sqlite", database="sample.db")
            >>> tables = sam.get_tables()
            >>> print(tables)
            ['students', 'classes']
        """
        if not self.connection:
            print("[SAM] Warning: No database connection. Call connect_database() first.")
            return []
        
        try:
            return self._get_tables()
        except Exception as e:
            print(f"[SAM] Error getting tables: {e}")
            return []

    def _get_table_schema(self, table_name: str) -> TableSchema:
        """Get detailed schema information for a specific table"""
        cursor = self.connection.cursor()
        
        try:
            columns = []
            primary_keys = []
            foreign_keys = []
            indexes = []
            
            if self.db_type == DatabaseType.MYSQL:
                # Get columns
                cursor.execute(f"DESCRIBE `{table_name}`")
                for row in cursor.fetchall():
                    col_info = {
                        'name': row['Field'],
                        'type': row['Type'],
                        'nullable': row['Null'] == 'YES',
                        'default': row['Default'],
                        'extra': row['Extra']
                    }
                    columns.append(col_info)
                    if row['Key'] == 'PRI':
                        primary_keys.append(row['Field'])
                
                # Get foreign keys
                cursor.execute(f"""
                    SELECT COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
                    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                    WHERE TABLE_SCHEMA = DATABASE()
                    AND TABLE_NAME = '{table_name}' 
                    AND REFERENCED_TABLE_NAME IS NOT NULL
                """)
                foreign_keys.extend([{
                    'column': row['COLUMN_NAME'],
                    'references_table': row['REFERENCED_TABLE_NAME'],
                    'references_column': row['REFERENCED_COLUMN_NAME']
                } for row in cursor.fetchall()])
                
            elif self.db_type == DatabaseType.POSTGRESQL:
                # Get columns
                cursor.execute(f"""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = '{table_name}'
                    ORDER BY ordinal_position
                """)
                rows = cursor.fetchall()
                columns.extend([{
                    'name': row[0],
                    'type': row[1],
                    'nullable': row[2] == 'YES',
                    'default': row[3]
                } for row in rows])
                
                # Get primary keys
                cursor.execute(f"""
                    SELECT a.attname
                    FROM pg_index i
                    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                    WHERE i.indrelid = '{table_name}'::regclass AND i.indisprimary
                """)
                primary_keys = [row[0] for row in cursor.fetchall()]
                
                # Get foreign keys
                cursor.execute(f"""
                    SELECT
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                        AND ccu.table_schema = tc.table_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_name = '{table_name}'
                """)
                foreign_keys.extend([{
                    'column': row[0],
                    'references_table': row[1],
                    'references_column': row[2]
                } for row in cursor.fetchall()])
                
            elif self.db_type == DatabaseType.SQLITE:
                # Get columns
                cursor.execute(f"PRAGMA table_info(`{table_name}`)")
                rows = cursor.fetchall()
                for row in rows:
                    columns.append({
                        'name': row[1],
                        'type': row[2],
                        'nullable': row[3] == 0,
                        'default': row[4],
                        'primary_key': row[5] == 1
                    })
                    if row[5] == 1:
                        primary_keys.append(row[1])
                
                # Get foreign keys
                cursor.execute(f"PRAGMA foreign_key_list(`{table_name}`)")
                rows = cursor.fetchall()
                foreign_keys.extend([{
                    'column': row[3],
                    'references_table': row[2],
                    'references_column': row[4]
                } for row in rows])
            
            # Get row count
            try:
                cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                result = cursor.fetchone()
                
                if self.db_type == DatabaseType.SQLITE:
                    row_count = result[0]
                elif self.db_type == DatabaseType.MYSQL:
                    row_count = list(result.values())[0]
                else:  # PostgreSQL
                    row_count = result[0]
            except Exception as e:
                print(f"[SAM] Warning: Could not get row count for {table_name}: {e}")
                row_count = None
            
            return TableSchema(
                name=table_name,
                columns=columns,
                primary_keys=primary_keys,
                foreign_keys=foreign_keys,
                indexes=indexes,
                row_count=row_count
            )
            
        except Exception as e:
            print(f"[SAM] Error getting schema for table {table_name}: {e}")
            # Return empty schema on error
            return TableSchema(
                name=table_name,
                columns=[],
                primary_keys=[],
                foreign_keys=[],
                indexes=[],
                row_count=None
            )
            
        finally:
            cursor.close()

    def _format_schema_text(self, tables_data: Dict[str, TableSchema], database_name: str) -> str:
        """Format schema data into human-readable text format"""
        lines = [f"Database: {database_name}\n"]
        
        for table_name, table_schema in tables_data.items():
            lines.append(f"\nTable {table_name}:")
            
            # Columns
            for col in table_schema.columns:
                nullable = "NULL" if col['nullable'] else "NOT NULL"
                default = f"DEFAULT {col['default']}" if col.get('default') else ""
                pk = "PRIMARY KEY" if col['name'] in table_schema.primary_keys else ""
                
                col_line = f"  - {col['name']} ({col['type']}) {nullable} {default} {pk}".strip()
                lines.append(col_line)
            
            # Foreign Keys
            if table_schema.foreign_keys:
                lines.append("  Foreign Keys:")
                lines.extend([
                    f"    - {fk['column']} → {fk['references_table']}.{fk['references_column']}" 
                    for fk in table_schema.foreign_keys
                ])
            
            # Row count
            if table_schema.row_count is not None:
                lines.append(f"  Rows: {table_schema.row_count}")
        
        return "\n".join(lines)

    def generate_full_schema(self) -> bool:
        """
        Scan the entire database and generate/update schema.txt
        
        Returns:
            bool: True if successful
        """
        if not self.connection:
            print("[SAM] ✗ No database connection. Call connect_database() first.")
            return False
        
        try:
            # Get all tables
            tables = self._get_tables()
            
            if not tables:
                print("[SAM] Warning: No tables found in database")
                return False
            
            print(f"[SAM] Found {len(tables)} tables: {', '.join(tables)}")
            
            # Get schema for each table
            tables_data = {}
            for table in tables:
                print(f"[SAM] Scanning table: {table}...")
                tables_data[table] = self._get_table_schema(table)
            
            # Format and write schema.txt
            database_name = self._get_database_name()
            schema_text = self._format_schema_text(tables_data, database_name)
            
            with open(self.schema_file, 'w', encoding='utf-8') as f:
                f.write(schema_text)
            
            # Calculate schema hash for change detection
            schema_hash = hashlib.md5(schema_text.encode()).hexdigest()
            
            # Update or create metadata
            now = datetime.now().isoformat()
            version = self.current_metadata.version + 1 if self.current_metadata else 1
            
            self.current_metadata = SchemaMetadata(
                database_name=database_name,
                database_type=self.db_type.value,
                created_at=self.current_metadata.created_at if self.current_metadata else now,
                last_updated=now,
                version=version,
                table_count=len(tables),
                schema_hash=schema_hash,
                tables=tables
            )
            
            # Save metadata
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.current_metadata), f, indent=2)
            
            print(f"[SAM] ✓ Schema written to {self.schema_file}")
            print(f"[SAM] ✓ Metadata saved (version {version})")
            return True
            
        except Exception as e:
            print(f"[SAM] ✗ Schema generation failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _get_database_name(self) -> str:
        """Get the current database name"""
        cursor = self.connection.cursor()
        try:
            if self.db_type == DatabaseType.MYSQL:
                cursor.execute("SELECT DATABASE()")
                result = cursor.fetchone()
                return list(result.values())[0] if result else "unknown"
            elif self.db_type == DatabaseType.POSTGRESQL:
                cursor.execute("SELECT current_database()")
                result = cursor.fetchone()
                return result[0] if result else "unknown"
            elif self.db_type == DatabaseType.SQLITE:
                return "sqlite_db"
            return "unknown"
        except Exception as e:
            print(f"[SAM] Warning: Could not get database name: {e}")
            return "unknown"
        finally:
            cursor.close()

    def create_specialized_snapshot(self, table_names: List[str], snapshot_id: Optional[str] = None) -> Optional[str]:
        """
        Create a specialized snapshot containing only specified tables.
        
        Args:
            table_names: List of table names to include
            snapshot_id: Optional custom ID, auto-generated if not provided
            
        Returns:
            str: Path to the specialized snapshot file, or None if failed
        """
        if not self.connection:
            print("[SAM] ✗ No database connection")
            return None
        
        if not snapshot_id:
            snapshot_id = f"specialized_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        snapshot_file = os.path.join(self.output_dir, f"{snapshot_id}.txt")
        
        try:
            # Get schema for specified tables
            available_tables = self._get_tables()
            tables_data = {}
            
            for table in table_names:
                if table in available_tables:
                    tables_data[table] = self._get_table_schema(table)
                else:
                    print(f"[SAM] Warning: Table '{table}' not found in database")
                    return None
            
            # Format and write specialized snapshot
            database_name = self._get_database_name()
            schema_text = self._format_schema_text(tables_data, database_name)
            
            with open(snapshot_file, 'w', encoding='utf-8') as f:
                f.write(schema_text)
            
            self.specialized_snapshots[snapshot_id] = snapshot_file
            print(f"[SAM] ✓ Specialized snapshot created: {snapshot_file}")
            print(f"[SAM]   Tables included: {', '.join(table_names)}")
            
            return snapshot_file
            
        except Exception as e:
            print(f"[SAM] ✗ Failed to create specialized snapshot: {e}")
            import traceback
            traceback.print_exc()
            return None

    def delete_specialized_snapshot(self, snapshot_id: str) -> bool:
        """
        Delete a specialized snapshot file.
        
        Args:
            snapshot_id: ID of the snapshot to delete
            
        Returns:
            bool: True if successful
        """
        if snapshot_id not in self.specialized_snapshots:
            print(f"[SAM] Warning: Snapshot '{snapshot_id}' not found")
            return False
        
        try:
            snapshot_file = self.specialized_snapshots[snapshot_id]
            if os.path.exists(snapshot_file):
                os.remove(snapshot_file)
                print(f"[SAM] ✓ Deleted specialized snapshot: {snapshot_file}")
            
            del self.specialized_snapshots[snapshot_id]
            return True
            
        except Exception as e:
            print(f"[SAM] ✗ Failed to delete snapshot: {e}")
            return False

    def detect_schema_changes(self) -> bool:
        """
        Check if the database schema has changed since last snapshot.
        
        Returns:
            bool: True if changes detected
        """
        if not self.current_metadata:
            return True  # No metadata means first run
        
        try:
            # Generate temporary schema
            tables = self._get_tables()
            tables_data = {table: self._get_table_schema(table) for table in tables}
            database_name = self._get_database_name()
            schema_text = self._format_schema_text(tables_data, database_name)
            
            # Compare hashes
            new_hash = hashlib.md5(schema_text.encode()).hexdigest()
            changed = new_hash != self.current_metadata.schema_hash
            
            if changed:
                print("[SAM] ⚠ Schema changes detected!")
            
            return changed
            
        except Exception as e:
            print(f"[SAM] ✗ Change detection failed: {e}")
            return False

    def auto_update_on_change(self) -> bool:
        """
        Automatically update schema.txt if changes are detected.
        
        Returns:
            bool: True if update was performed
        """
        if self.detect_schema_changes():
            print("[SAM] Updating schema.txt due to detected changes...")
            return self.generate_full_schema()
        return False

    def close(self):
        """Close database connection and cleanup"""
        if self.connection:
            try:
                self.connection.close()
                print("[SAM] Database connection closed.")
            except Exception as e:
                print(f"[SAM] Error closing connection: {e}")
        
        # Cleanup specialized snapshots
        for snapshot_id in list(self.specialized_snapshots.keys()):
            self.delete_specialized_snapshot(snapshot_id)


# CLI for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Schema Awareness Module CLI")
    parser.add_argument("--db-type", required=True, choices=["mysql", "postgres", "sqlite"], help="Database type")
    parser.add_argument("--host", default="localhost", help="Database host")
    parser.add_argument("--user", help="Database user")
    parser.add_argument("--password", help="Database password")
    parser.add_argument("--database", required=True, help="Database name or file path (for SQLite)")
    parser.add_argument("--port", type=int, help="Database port")
    parser.add_argument("--output-dir", default=".", help="Output directory for schema files")
    
    args = parser.parse_args()
    
    # Initialize SAM
    sam = SchemaAwarenessModule(output_dir=args.output_dir)
    
    # Build connection params
    conn_params = {"database": args.database}
    if args.db_type != "sqlite":
        conn_params.update({
            "host": args.host,
            "user": args.user,
            "password": args.password
        })
        if args.port:
            conn_params["port"] = args.port
    
    # Connect and generate schema
    if sam.connect_database(args.db_type, **conn_params):
        print("\n✓ Schema Awareness Module ready!")
        print(f"  Schema file: {sam.schema_file}")
        print(f"  Metadata file: {sam.metadata_file}")
        
        # Demo: Test public get_tables() method
        tables = sam.get_tables()
        if tables:
            print(f"\n✓ Public get_tables() method works!")
            print(f"  Found {len(tables)} tables: {', '.join(tables)}")
            
            # Demo: Create specialized snapshot
            print("\nDemo: Creating specialized snapshot for first table...")
            sam.create_specialized_snapshot([tables[0]])
        else:
            print("\n✗ No tables found")
    
    sam.close()