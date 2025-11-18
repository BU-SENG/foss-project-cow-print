import sqlalchemy as sa
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
import streamlit as st
from typing import Dict, List, Optional, Any
import json
import os
import tempfile
import shutil
import subprocess
import sys

class DatabaseManager:
    def __init__(self):
        self.connections = {}
        self.active_connection = None
        self.temp_files = []  # Track temporary files for cleanup
        
    def create_connection_string(self, db_type: str, host: str, port: str, 
                               database: str, username: str, password: str) -> str:
        """Create connection string based on database type"""
        if db_type == "postgresql":
            return f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}"
        elif db_type == "mysql":
            return f"mysql+mysqlconnector://{username}:{password}@{host}:{port}/{database}"
        elif db_type == "sqlite":
            # SQLite connection - database should be the file path
            if not database:
                database = ":memory:"
            elif not database.endswith('.db'):
                database += '.db'
            return f"sqlite:///{database}"
        elif db_type == "mssql":
            return f"mssql+pyodbc://{username}:{password}@{host}:{port}/{database}?driver=ODBC+Driver+17+for+SQL+Server"
        elif db_type == "oracle":
            return f"oracle+cx_oracle://{username}:{password}@{host}:{port}/{database}"
        elif db_type == "sqlite_memory":
            return "sqlite:///:memory:"
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
    
    def connect_database(self, connection_name: str, db_type: str, host: str, port: str,
                        database: str, username: str, password: str) -> bool:
        """Establish database connection"""
        try:
            connection_string = self.create_connection_string(
                db_type, host, port, database, username, password
            )
            
            # Create engine with better error handling
            engine = create_engine(connection_string, pool_pre_ping=True)
            
            # Test connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self.connections[connection_name] = {
                'engine': engine,
                'type': db_type,
                'database': database,
                'host': host,
                'port': port
            }
            self.active_connection = connection_name
            return True
            
        except ImportError as e:
            st.error(f"Database driver missing: {str(e)}")
            return False
        except Exception as e:
            st.error(f"Connection failed: {str(e)}")
            return False
    
    def import_database_file(self, file_path: str, connection_name: str, db_type: str = None) -> bool:
        """Import an external database file with enhanced support"""
        try:
            if not os.path.exists(file_path):
                st.error(f"File not found: {file_path}")
                return False
            
            # Auto-detect database type from file extension
            if not db_type or db_type == "auto_detect":
                file_ext = os.path.splitext(file_path)[1].lower()
                db_type_map = {
                    '.db': 'sqlite',
                    '.sqlite': 'sqlite', 
                    '.sqlite3': 'sqlite',
                    '.sql': 'sql_dump',  # SQL dump files
                    '.csv': 'csv',       # CSV files
                    '.json': 'json',     # JSON files
                    '.xlsx': 'excel',    # Excel files
                    '.xls': 'excel',     # Excel files (old format)
                    '.mdb': 'access',
                    '.accdb': 'access'
                }
                db_type = db_type_map.get(file_ext, 'sqlite')
            
            if db_type == 'sqlite':
                # For SQLite, we can use the file directly
                return self.connect_database(
                    connection_name, db_type, "", "", file_path, "", ""
                )
            
            elif db_type == 'sql_dump':
                # For SQL dump files, import into a new SQLite database
                return self._import_sql_dump(file_path, connection_name)
            
            elif db_type == 'csv':
                # For CSV files, import into SQLite
                return self._import_csv_file(file_path, connection_name)
            
            elif db_type == 'json':
                # For JSON files, import into SQLite
                return self._import_json_file(file_path, connection_name)
            
            elif db_type == 'excel':
                # For Excel files, import into SQLite
                return self._import_excel_file(file_path, connection_name)
            
            else:
                st.error(f"File import not supported for {db_type} files")
                return False
                
        except Exception as e:
            st.error(f"Import failed: {str(e)}")
            return False
    
    def _import_sql_dump(self, file_path: str, connection_name: str) -> bool:
        """Import SQL dump file into a new SQLite database"""
        try:
            # Create a temporary SQLite database
            temp_db_path = f"temp_import_{connection_name}.db"
            self.temp_files.append(temp_db_path)  # Track for cleanup
            
            # Connect to new SQLite database
            success = self.connect_database(
                connection_name, "sqlite", "", "", temp_db_path, "", ""
            )
            
            if not success:
                return False
            
            # Read SQL file
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                sql_content = f.read()
            
            # Split into individual statements
            statements = self._split_sql_statements(sql_content)
            
            # Execute statements
            engine = self.connections[connection_name]['engine']
            with engine.connect() as conn:
                for statement in statements:
                    if statement.strip() and not statement.strip().startswith('--'):
                        try:
                            conn.execute(text(statement))
                        except Exception as e:
                            st.warning(f"Could not execute: {statement[:100]}... Error: {e}")
                conn.commit()
            
            st.success(f"✅ SQL dump imported successfully with {len(statements)} statements")
            return True
            
        except Exception as e:
            st.error(f"SQL import failed: {str(e)}")
            return False
    
    def _split_sql_statements(self, sql_content: str) -> List[str]:
        """Split SQL content into individual statements"""
        # Remove comments and split by semicolons
        lines = sql_content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Remove inline comments
            if '--' in line:
                line = line.split('--')[0]
            cleaned_lines.append(line.strip())
        
        # Join and split by semicolons
        full_sql = ' '.join(cleaned_lines)
        statements = [stmt.strip() for stmt in full_sql.split(';') if stmt.strip()]
        
        return statements
    
    def _import_csv_file(self, file_path: str, connection_name: str) -> bool:
        """Import CSV file into a new SQLite database"""
        try:
            import pandas as pd
            
            # Read CSV file with automatic encoding detection
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                st.error("Could not read CSV file with any supported encoding")
                return False
            
            # Create a temporary SQLite database
            temp_db_path = f"temp_import_{connection_name}.db"
            self.temp_files.append(temp_db_path)  # Track for cleanup
            
            # Connect to new SQLite database
            success = self.connect_database(
                connection_name, "sqlite", "", "", temp_db_path, "", ""
            )
            
            if success:
                # Get table name from filename
                table_name = os.path.splitext(os.path.basename(file_path))[0]
                table_name = ''.join(c for c in table_name if c.isalnum() or c == '_')
                
                if not table_name:
                    table_name = "imported_data"
                
                # Clean column names
                df.columns = [''.join(c for c in str(col) if c.isalnum() or c == '_') for col in df.columns]
                
                # Import data
                engine = self.connections[connection_name]['engine']
                df.to_sql(table_name, engine, index=False, if_exists='replace')
                
                st.success(f"✅ CSV imported as table '{table_name}' with {len(df)} rows and {len(df.columns)} columns")
                return True
            
            return False
            
        except Exception as e:
            st.error(f"CSV import failed: {str(e)}")
            return False
    
    def _import_json_file(self, file_path: str, connection_name: str) -> bool:
        """Import JSON file into a new SQLite database"""
        try:
            import pandas as pd
            import json
            
            # Read JSON file
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert to DataFrame (handle different JSON structures)
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                # If it's a dict with arrays, use the first array
                for key, value in data.items():
                    if isinstance(value, list):
                        df = pd.DataFrame(value)
                        break
                else:
                    # Single object
                    df = pd.DataFrame([data])
            else:
                st.error("Unsupported JSON structure")
                return False
            
            # Create a temporary SQLite database
            temp_db_path = f"temp_import_{connection_name}.db"
            self.temp_files.append(temp_db_path)  # Track for cleanup
            
            # Connect to new SQLite database
            success = self.connect_database(
                connection_name, "sqlite", "", "", temp_db_path, "", ""
            )
            
            if success:
                # Get table name from filename
                table_name = os.path.splitext(os.path.basename(file_path))[0]
                table_name = ''.join(c for c in table_name if c.isalnum() or c == '_')
                
                if not table_name:
                    table_name = "imported_data"
                
                # Clean column names
                df.columns = [''.join(c for c in str(col) if c.isalnum() or c == '_') for col in df.columns]
                
                # Import data
                engine = self.connections[connection_name]['engine']
                df.to_sql(table_name, engine, index=False, if_exists='replace')
                
                st.success(f"✅ JSON imported as table '{table_name}' with {len(df)} rows and {len(df.columns)} columns")
                return True
            
            return False
            
        except Exception as e:
            st.error(f"JSON import failed: {str(e)}")
            return False
    
    def _import_excel_file(self, file_path: str, connection_name: str) -> bool:
        """Import Excel file into a new SQLite database"""
        try:
            import pandas as pd
            
            # Read Excel file
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names
            
            # Create a temporary SQLite database
            temp_db_path = f"temp_import_{connection_name}.db"
            self.temp_files.append(temp_db_path)  # Track for cleanup
            
            # Connect to new SQLite database
            success = self.connect_database(
                connection_name, "sqlite", "", "", temp_db_path, "", ""
            )
            
            if not success:
                return False
            
            engine = self.connections[connection_name]['engine']
            imported_sheets = []
            
            # Import each sheet as a separate table
            for sheet_name in sheet_names:
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    
                    # Clean table name
                    table_name = ''.join(c for c in sheet_name if c.isalnum() or c == '_')
                    if not table_name:
                        table_name = f"sheet_{len(imported_sheets) + 1}"
                    
                    # Clean column names
                    df.columns = [''.join(c for c in str(col) if c.isalnum() or c == '_') for col in df.columns]
                    
                    # Import data
                    df.to_sql(table_name, engine, index=False, if_exists='replace')
                    imported_sheets.append((table_name, len(df)))
                    
                except Exception as e:
                    st.warning(f"Could not import sheet '{sheet_name}': {e}")
            
            if imported_sheets:
                sheet_info = ", ".join([f"'{name}' ({rows} rows)" for name, rows in imported_sheets])
                st.success(f"✅ Excel file imported with sheets: {sheet_info}")
                return True
            else:
                st.error("No sheets could be imported from the Excel file")
                return False
            
        except Exception as e:
            st.error(f"Excel import failed: {str(e)}")
            return False
    
    def get_schema_info(self, connection_name: str) -> Dict[str, Any]:
        """Get database schema information"""
        if connection_name not in self.connections:
            return {}
        
        engine = self.connections[connection_name]['engine']
        
        try:
            inspector = inspect(engine)
            schema_info = {
                'tables': {},
                'relationships': [],
                'database_type': self.connections[connection_name]['type']
            }
            
            # Get all tables
            tables = inspector.get_table_names()
            
            for table_name in tables:
                # Get columns
                columns = inspector.get_columns(table_name)
                # Get primary keys
                try:
                    primary_keys = inspector.get_pk_constraint(table_name)
                except:
                    primary_keys = {'constrained_columns': []}
                # Get foreign keys
                try:
                    foreign_keys = inspector.get_foreign_keys(table_name)
                except:
                    foreign_keys = []
                
                schema_info['tables'][table_name] = {
                    'columns': [
                        {
                            'name': col['name'],
                            'type': str(col['type']),
                            'nullable': col['nullable'],
                            'primary_key': col['name'] in primary_keys.get('constrained_columns', [])
                        }
                        for col in columns
                    ],
                    'primary_key': primary_keys.get('constrained_columns', []),
                    'foreign_keys': foreign_keys
                }
                
                # Extract relationships
                for fk in foreign_keys:
                    schema_info['relationships'].append({
                        'from_table': table_name,
                        'from_column': fk['constrained_columns'],
                        'to_table': fk['referred_table'],
                        'to_column': fk['referred_columns']
                    })
            
            return schema_info
            
        except Exception as e:
            st.error(f"Error fetching schema: {str(e)}")
            return {}
    
    def execute_query(self, connection_name: str, query: str, limit: int = 1000) -> Dict[str, Any]:
        """Execute SQL query and return results"""
        if connection_name not in self.connections:
            return {'error': 'No active connection'}
        
        try:
            engine = self.connections[connection_name]['engine']
            
            # Clean the query - remove trailing semicolons and whitespace
            query = query.strip().rstrip(';')
            
            # Add LIMIT clause if it's a SELECT query and doesn't have one
            query_upper = query.upper().strip()
            if (query_upper.startswith('SELECT') and 
                'LIMIT' not in query_upper and 
                not query_upper.startswith('SELECT COUNT')):
                query += f" LIMIT {limit}"
            
            with engine.connect() as conn:
                result = conn.execute(text(query))
                
                if result.returns_rows:
                    df = pd.DataFrame(result.fetchall(), columns=result.keys())
                    return {
                        'success': True,
                        'data': df,
                        'row_count': len(df),
                        'columns': list(df.columns)
                    }
                else:
                    return {
                        'success': True,
                        'data': None,
                        'message': f"Query executed successfully. Rows affected: {result.rowcount}",
                        'row_count': result.rowcount
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_connection_info(self, connection_name: str) -> Dict[str, str]:
        """Get information about a connection"""
        if connection_name in self.connections:
            conn_info = self.connections[connection_name]
            return {
                'type': conn_info['type'],
                'database': conn_info['database'],
                'host': conn_info.get('host', ''),
                'port': conn_info.get('port', '')
            }
        return {}
    
    def get_all_connections(self) -> Dict[str, Dict]:
        """Get all active connections"""
        return self.connections
    
    def disconnect(self, connection_name: str) -> bool:
        """Disconnect from a database"""
        if connection_name in self.connections:
            # Dispose of the engine
            try:
                self.connections[connection_name]['engine'].dispose()
            except:
                pass
            
            # Remove from connections
            del self.connections[connection_name]
            
            # Update active connection
            if self.active_connection == connection_name:
                self.active_connection = None
                if self.connections:
                    self.active_connection = next(iter(self.connections.keys()))
            
            return True
        return False
    
    def cleanup_temp_files(self):
        """Clean up temporary files created during imports"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except:
                pass
        self.temp_files.clear()