#!/usr/bin/env python3
"""
Schema Awareness Module (SAM)

This module is responsible for creating and maintaining schema snapshots of the database.
Refactored for better code quality, maintainability, and linting compliance.
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
        self.output_dir = output_dir
        self.schema_file = os.path.join(output_dir, "schema.txt")
        self.metadata_file = os.path.join(output_dir, "schema_metadata.json")
        self.specialized_snapshots: Dict[str, str] = {}
        self.current_metadata: Optional[SchemaMetadata] = None
        self.connection = None
        self.db_type: Optional[DatabaseType] = None
        
        print("[SAM] Schema Awareness Module initialized.")

    def connect_database(self, db_type: str, **connection_params) -> bool:
        """Connect to a database and automatically generate initial schema.txt"""
        try:
            db_type_lower = db_type.lower()
            
            if db_type_lower == "mysql":
                self._connect_mysql(connection_params)
            elif db_type_lower in {"postgres", "postgresql"}:
                self._connect_postgres(connection_params)
            elif db_type_lower == "sqlite":
                self._connect_sqlite(connection_params)
            else:
                print(f"[SAM] ✗ Unsupported database type: {db_type}")
                return False

            # Auto-generate initial schema.txt
            # Fixed: Removed unnecessary f-string
            print("\n[SAM] Scanning database and generating schema.txt...")
            success = self.generate_full_schema()
            
            if success:
                print("[SAM] ✓ schema.txt generated successfully!\n")
            else:
                print("[SAM] ✗ Failed to generate schema.txt\n")
            
            return success
            
        except Exception as e:
            self._handle_connection_error(e, connection_params)
            return False

    def _connect_mysql(self, params):
        self.db_type = DatabaseType.MYSQL
        self.connection = pymysql.connect(
            host=params.get('host', 'localhost'),
            user=params.get('user'),
            password=params.get('password'),
            database=params.get('database'),
            port=int(params.get('port', 3306)),
            cursorclass=pymysql.cursors.DictCursor
        )
        print("[SAM] ✓ Connected to MySQL database.")

    def _connect_postgres(self, params):
        self.db_type = DatabaseType.POSTGRESQL
        self.connection = psycopg2.connect(
            host=params.get('host', 'localhost'),
            user=params.get('user'),
            password=params.get('password'),
            database=params.get('database'),
            port=int(params.get('port', 5432))
        )
        print("[SAM] ✓ Connected to PostgreSQL database.")

    def _connect_sqlite(self, params):
        self.db_type = DatabaseType.SQLITE
        self.connection = sqlite3.connect(params['database'])
        self.connection.row_factory = sqlite3.Row
        print("[SAM] ✓ Connected to SQLite database.")

    def _handle_connection_error(self, e, params):
        error_msg = str(e)
        pwd = params.get('password')
        if pwd and isinstance(pwd, str) and len(pwd) > 0:
            error_msg = error_msg.replace(pwd, "******")
        print(f"[SAM] ✗ Database connection failed: {error_msg}")

    def _get_tables(self) -> List[str]:
        """Internal method to get list of all tables"""
        if not self.connection:
            print("[SAM] Warning: No database connection.")
            return []
        
        cursor = self.connection.cursor()
        try:
            if self.db_type == DatabaseType.MYSQL:
                cursor.execute("SHOW TABLES")
                return [list(row.values())[0] for row in cursor.fetchall()]
                
            if self.db_type == DatabaseType.POSTGRESQL:
                cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                return [row[0] for row in cursor.fetchall()]
                
            if self.db_type == DatabaseType.SQLITE:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                return [row[0] for row in cursor.fetchall()]
            
            return []
            
        except Exception as e:
            print(f"[SAM] Error getting tables: {e}")
            return []
        finally:
            cursor.close()

    def get_tables(self) -> List[str]:
        """Public method to get list of all tables"""
        if not self.connection:
            print("[SAM] Warning: No database connection. Call connect_database() first.")
            return []
        try:
            return self._get_tables()
        except Exception as e:
            print(f"[SAM] Error getting tables: {e}")
            return []

    def _quote_identifier(self, identifier: str) -> str:
        """Safely quote a SQL identifier"""
        if not identifier:
            raise ValueError("Identifier cannot be empty.")
        if '\0' in identifier:
            raise ValueError("Invalid identifier: contains null byte.")
        
        if self.db_type == DatabaseType.MYSQL:
            return f"`{identifier.replace('`', '``')}`"
        if self.db_type in (DatabaseType.POSTGRESQL, DatabaseType.SQLITE):
            return f'"{identifier.replace('"', '""')}"'
            
        raise ValueError("Unsupported database type for identifier quoting")

    # Refactored: Split giant method into specific handlers
    def _get_table_schema(self, table_name: str) -> TableSchema:
        """Get detailed schema information for a specific table"""
        cursor = self.connection.cursor()
        try:
            if self.db_type == DatabaseType.MYSQL:
                return self._get_mysql_schema(cursor, table_name)
            elif self.db_type == DatabaseType.POSTGRESQL:
                return self._get_postgres_schema(cursor, table_name)
            elif self.db_type == DatabaseType.SQLITE:
                return self._get_sqlite_schema(cursor, table_name)
            return self._create_empty_schema(table_name)
        except Exception as e:
            print(f"[SAM] Error getting schema for table {table_name}: {e}")
            return self._create_empty_schema(table_name)
        finally:
            cursor.close()

    def _create_empty_schema(self, table_name: str) -> TableSchema:
        return TableSchema(table_name, [], [], [], [], None)

    def _get_mysql_schema(self, cursor, table_name):
        quoted_table = self._quote_identifier(table_name)
        
        # Columns
        cursor.execute(f"DESCRIBE {quoted_table}")
        columns = []
        primary_keys = []
        for row in cursor.fetchall():
            columns.append({
                'name': row['Field'],
                'type': row['Type'],
                'nullable': row['Null'] == 'YES',
                'default': row['Default'],
                'extra': row['Extra']
            })
            if row['Key'] == 'PRI':
                primary_keys.append(row['Field'])

        # Foreign Keys
        cursor.execute("""
            SELECT COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND REFERENCED_TABLE_NAME IS NOT NULL
        """, (table_name,))
        foreign_keys = [{
            'column': row['COLUMN_NAME'],
            'references_table': row['REFERENCED_TABLE_NAME'],
            'references_column': row['REFERENCED_COLUMN_NAME']
        } for row in cursor.fetchall()]

        # Row Count
        row_count = self._get_row_count(cursor, quoted_table)
        return TableSchema(table_name, columns, primary_keys, foreign_keys, [], row_count)

    def _get_postgres_schema(self, cursor, table_name):
        # Columns
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position
        """, (table_name,))
        columns = [{
            'name': row[0],
            'type': row[1],
            'nullable': row[2] == 'YES',
            'default': row[3]
        } for row in cursor.fetchall()]

        # Primary Keys
        cursor.execute("""
            SELECT a.attname FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = %s::regclass AND i.indisprimary
        """, (table_name,))
        primary_keys = [row[0] for row in cursor.fetchall()]

        # Foreign Keys
        cursor.execute("""
            SELECT kcu.column_name, ccu.table_name, ccu.column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = %s
        """, (table_name,))
        foreign_keys = [{
            'column': row[0],
            'references_table': row[1],
            'references_column': row[2]
        } for row in cursor.fetchall()]

        row_count = self._get_row_count(cursor, self._quote_identifier(table_name))
        return TableSchema(table_name, columns, primary_keys, foreign_keys, [], row_count)

    def _get_sqlite_schema(self, cursor, table_name):
        quoted_table = self._quote_identifier(table_name)
        
        # Columns
        cursor.execute(f"PRAGMA table_info({quoted_table})")
        columns = []
        primary_keys = []
        for row in cursor.fetchall():
            columns.append({
                'name': row[1],
                'type': row[2],
                'nullable': row[3] == 0,
                'default': row[4],
                'primary_key': row[5] == 1
            })
            if row[5] == 1:
                primary_keys.append(row[1])

        # Foreign Keys
        cursor.execute(f"PRAGMA foreign_key_list({quoted_table})")
        foreign_keys = [{
            'column': row[3],
            'references_table': row[2],
            'references_column': row[4]
        } for row in cursor.fetchall()]

        row_count = self._get_row_count(cursor, quoted_table)
        return TableSchema(table_name, columns, primary_keys, foreign_keys, [], row_count)

    def _get_row_count(self, cursor, quoted_table):
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {quoted_table}")
            result = cursor.fetchone()
            if self.db_type == DatabaseType.MYSQL:
                return list(result.values())[0]
            return result[0]
        except Exception:
            return None

    def _format_schema_text(self, tables_data: Dict[str, TableSchema], database_name: str) -> str:
        lines = [f"Database: {database_name}\n"]
        for table_name, schema in tables_data.items():
            lines.append(f"\nTable {table_name}:")
            for col in schema.columns:
                nullable = "NULL" if col['nullable'] else "NOT NULL"
                default = f"DEFAULT {col['default']}" if col.get('default') else ""
                pk = "PRIMARY KEY" if col['name'] in schema.primary_keys else ""
                lines.append(f"  - {col['name']} ({col['type']}) {nullable} {default} {pk}".strip())
            
            if schema.foreign_keys:
                lines.append("  Foreign Keys:")
                lines.extend([f"    - {fk['column']} → {fk['references_table']}.{fk['references_column']}" for fk in schema.foreign_keys])
            
            if schema.row_count is not None:
                lines.append(f"  Rows: {schema.row_count}")
        return "\n".join(lines)

    def generate_full_schema(self) -> bool:
        """Scan the entire database and generate/update schema.txt"""
        if not self.connection:
            print("[SAM] ✗ No database connection. Call connect_database() first.")
            return False
        
        try:
            tables = self._get_tables()
            if not tables:
                print("[SAM] Warning: No tables found in database")
                return False
            
            print(f"[SAM] Found {len(tables)} tables: {', '.join(tables)}")
            
            tables_data = {}
            for table in tables:
                print(f"[SAM] Scanning table: {table}...")
                tables_data[table] = self._get_table_schema(table)
            
            database_name = self._get_database_name()
            schema_text = self._format_schema_text(tables_data, database_name)
            
            self._write_schema_file(schema_text)
            self._update_metadata(database_name, tables, schema_text)
            
            return True
        except Exception as e:
            print(f"[SAM] ✗ Schema generation failed: {e}")
            return False

    def _write_schema_file(self, content):
        with open(self.schema_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[SAM] ✓ Schema written to {self.schema_file}")

    def _update_metadata(self, db_name, tables, schema_text):
        schema_hash = hashlib.md5(schema_text.encode()).hexdigest()
        now = datetime.now().isoformat()
        version = (self.current_metadata.version + 1) if self.current_metadata else 1
        
        self.current_metadata = SchemaMetadata(
            database_name=db_name,
            database_type=self.db_type.value,
            created_at=self.current_metadata.created_at if self.current_metadata else now,
            last_updated=now,
            version=version,
            table_count=len(tables),
            schema_hash=schema_hash,
            tables=tables
        )
        
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.current_metadata), f, indent=2)
        print(f"[SAM] ✓ Metadata saved (version {version})")

    def _get_database_name(self) -> str:
        cursor = self.connection.cursor()
        try:
            if self.db_type == DatabaseType.MYSQL:
                cursor.execute("SELECT DATABASE()")
                result = cursor.fetchone()
                return list(result.values())[0] if result else "unknown"
            if self.db_type == DatabaseType.POSTGRESQL:
                cursor.execute("SELECT current_database()")
                return cursor.fetchone()[0]
            return "sqlite_db" if self.db_type == DatabaseType.SQLITE else "unknown"
        except Exception:
            return "unknown"
        finally:
            cursor.close()

    def create_specialized_snapshot(self, table_names: List[str], snapshot_id: Optional[str] = None) -> Optional[str]:
        if not self.connection:
            print("[SAM] ✗ No database connection")
            return None
        
        snapshot_id = snapshot_id or f"specialized_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        snapshot_file = os.path.join(self.output_dir, f"{snapshot_id}.txt")
        
        try:
            available_tables = set(self._get_tables())
            tables_data = {}
            
            for table in table_names:
                if table in available_tables:
                    tables_data[table] = self._get_table_schema(table)
                else:
                    print(f"[SAM] Warning: Table '{table}' not found in database")
                    return None
            
            schema_text = self._format_schema_text(tables_data, self._get_database_name())
            with open(snapshot_file, 'w', encoding='utf-8') as f:
                f.write(schema_text)
            
            self.specialized_snapshots[snapshot_id] = snapshot_file
            print(f"[SAM] ✓ Specialized snapshot created: {snapshot_file}")
            print(f"[SAM]   Tables included: {', '.join(table_names)}")
            return snapshot_file
            
        except Exception as e:
            print(f"[SAM] ✗ Failed to create specialized snapshot: {e}")
            return None

    def delete_specialized_snapshot(self, snapshot_id: str) -> bool:
        if snapshot_id not in self.specialized_snapshots:
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
        """Check if the database schema has changed since last snapshot."""
        if not self.current_metadata:
            return True
        
        try:
            tables = self._get_tables()
            tables_data = {table: self._get_table_schema(table) for table in tables}
            schema_text = self._format_schema_text(tables_data, self._get_database_name())
            
            new_hash = hashlib.md5(schema_text.encode()).hexdigest()
            if changed := new_hash != self.current_metadata.schema_hash:
                print("[SAM] ⚠ Schema changes detected!")
            return changed
        except Exception as e:
            print(f"[SAM] ✗ Change detection failed: {e}")
            return False

    def auto_update_on_change(self) -> bool:
        if self.detect_schema_changes():
            print("[SAM] Updating schema.txt due to detected changes...")
            return self.generate_full_schema()
        return False

    def close(self):
        if self.connection:
            try:
                self.connection.close()
                print("[SAM] Database connection closed.")
            except Exception as e:
                print(f"[SAM] Error closing connection: {e}")
        
        for snapshot_id in list(self.specialized_snapshots.keys()):
            self.delete_specialized_snapshot(snapshot_id)


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
    
    sam = SchemaAwarenessModule(output_dir=args.output_dir)
    
    # Fixed: Merged dictionary update for CLI
    conn_params = {"database": args.database}
    if args.db_type != "sqlite":
        conn_params.update({
            "host": args.host,
            "user": args.user,
            "password": args.password
        })
        if args.port:
            conn_params["port"] = args.port
    
    if sam.connect_database(args.db_type, **conn_params):
        print("\n✓ Schema Awareness Module ready!")
        print(f"  Schema file: {sam.schema_file}")
        print(f"  Metadata file: {sam.metadata_file}")
        
        if tables := sam.get_tables():
            print("\n✓ Public get_tables() method works!")
            print(f"  Found {len(tables)} tables: {', '.join(tables)}")
            
            print("\nDemo: Creating specialized snapshot for first table...")
            sam.create_specialized_snapshot([tables[0]])
        else:
            print("\n✗ No tables found")
    
    sam.close()