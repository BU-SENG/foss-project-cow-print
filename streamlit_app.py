#!/usr/bin/env python3

"""
Aether DB - Enhanced Streamlit Frontend

A beautiful, intuitive interface for natural language to SQL conversion
with real-time database execution and visualization.

Enhanced with better UX, real-time feedback, and improved integration.
"""
import threading
from contextlib import contextmanager

class ThreadSafeSQLiteConnection:
    """Thread-safe SQLite connection manager"""
    _local = threading.local()
    _lock = threading.Lock()
    
    @classmethod
    def get_connection(cls, db_file):
        if not hasattr(cls._local, 'connections'):
            cls._local.connections = {}
        
        if db_file not in cls._local.connections:
            import sqlite3
            # Use check_same_thread=False to allow cross-thread usage
            cls._local.connections[db_file] = sqlite3.connect(
                db_file, 
                check_same_thread=False
            )
        
        return cls._local.connections[db_file]
    
    @classmethod
    @contextmanager
    def connection(cls, db_file):
        conn = cls.get_connection(db_file)
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        finally:
            pass  # Don't close the connection - keep it for the thread

    @classmethod
    def close_connection(cls, db_file):
        """Close a specific connection"""
        if hasattr(cls._local, 'connections') and db_file in cls._local.connections:
            try:
                cls._local.connections[db_file].close()
                del cls._local.connections[db_file]
            except:
                pass

    @classmethod
    def close_all(cls):
        """Close all connections"""
        if hasattr(cls._local, 'connections'):
            for db_file, conn in list(cls._local.connections.items()):
                try:
                    conn.close()
                except:
                    pass
            cls._local.connections = {}

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import sys
import time
import hashlib
import json
import tempfile
import sqlite3
import re
from typing import Optional, Dict, Any, List

# Add current directory to path to import local modules
sys.path.append(os.path.dirname(__file__))

# Load environment variables FIRST
from dotenv import load_dotenv
load_dotenv()  # This loads the .env file

# Debug: Print API key status
api_key = os.getenv("GEMINI_API_KEY")
print(f"API Key loaded: {api_key is not None}")
if api_key:
    print(f"API Key length: {len(api_key)}")
    print(f"API Key starts with: {api_key[:10]}...")

# Import our modules
try:
    from schema_awareness import SchemaAwarenessModule
    from sqlm import GeminiReasoner, CommandPayload
    from db_executor import DatabaseExecutor, ExecutionResult, ExecutionStatus
    
    # Test Gemini API immediately
    import google.generativeai as genai
    
    if api_key:
        try:
            genai.configure(api_key=api_key)
            # Test the API
            models = list(genai.list_models())
            gemini_models = [m for m in models if 'gemini' in m.name]
            print(f"✅ Gemini API connected successfully! Available models: {len(gemini_models)}")
            MODULES_AVAILABLE = True
            GEMINI_API_VALID = True
        except Exception as e:
            print(f"❌ Gemini API failed: {e}")
            MODULES_AVAILABLE = True
            GEMINI_API_VALID = False
    else:
        print("❌ No API key found")
        MODULES_AVAILABLE = True
        GEMINI_API_VALID = False
        
except ImportError as e:
    print(f"❌ Module import error: {e}")
    MODULES_AVAILABLE = False
    GEMINI_API_VALID = False


# Page configuration with enhanced settings
st.set_page_config(
    page_title="AetherDB - AI-Powered SQL Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/BU-SENG/foss-project-cow-print',
        'Report a bug': "https://github.com/BU-SENG/foss-project-cow-print/issues",
        'About': "# AetherDB\nTransform natural language into SQL with AI!"
    }
)

# Enhanced Custom CSS with modern design
st.markdown("""
<style>
    /* Main background with gradient animation */
    .main {
        background: linear-gradient(-45deg, #667eea, #764ba2, #f093fb, #f5576c);
        background-size: 400% 400%;
        animation: gradient 15s ease infinite;
    }
    
    @keyframes gradient {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    .stApp {
        background: transparent;
    }

    /* Enhanced sidebar */
    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e1e2e 0%, #2d2d44 100%);
        border-right: 1px solid #44475a;
    }

    /* Modern cards with glassmorphism effect */
    .glass-card {
        background: linear-gradient(180deg, #1e1e2e 0%, #2d2d44 100%);
        backdrop-filter: blur(5px);
        border-radius: 1rem;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid rgba(255, 255, 255, 0.2);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
    }

    .glass-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
    }

    /* Enhanced buttons */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 0.75rem;
        padding: 0.75rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }

    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
    }

    /* Success state button */
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    }

    /* Danger state button */
    .stButton>button[kind="secondary"] {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
    }

    /* Enhanced metrics */
    [data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 0.75rem;
        padding: 1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    }

    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }

    ::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%);
    }

    /* Loading animation */
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }

    .pulse {
        animation: pulse 2s infinite;
    }

    /* Code block styling */
    .stCodeBlock {
        border-radius: 0.5rem;
        border: 1px solid #e1e5e9;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 0.5rem 0.5rem 0 0;
        gap: 1rem;
        padding: 0 1rem;
    }
</style>
""", unsafe_allow_html=True)


def display_enhanced_header():
    """Display modern app header with import status"""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        
        st.markdown(f"""
        <div style='text-align: center; padding: 2rem 0;'>
            <h1 style='color: white; font-size: 3.5rem; margin-bottom: 0.5rem; font-weight: 700;'>
                AetherDB
            </h1>
            <p style='color: rgba(255,255,255,0.9); font-size: 1.3rem; margin-bottom: 1rem;'>
                AI-Powered Natural Language to SQL
            </p>
            <div style='display: inline-flex; gap: 0.5rem; background: rgba(255,255,255,0.1); 
                        padding: 0.5rem 1rem; border-radius: 2rem; backdrop-filter: blur(10px);'>
                <span style='color: #10b981;'>●</span>
                <span style='color: white;'>Import SQL files or connect to databases</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
def sidebar_database_connection():
    """Clean sidebar with single SQL import option"""
    st.sidebar.title("AetherDB")
    
    # Show API key status
    if not GEMINI_API_VALID:
        st.sidebar.warning("AI Mode: Demo (Check API Key)")
        with st.sidebar.expander("API Key Help"):
            st.markdown("""
            **To enable full AI features:**
            1. Get API key from [Google AI Studio](https://aistudio.google.com/)
            2. Add to `.env` file:
            ```
            GEMINI_API_KEY=your_actual_key_here
            ```
            3. Restart the app
            """)
    
    # SINGLE SQL FILE IMPORT SECTION - Always show this
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Quick Start")
    
    sql_file = st.sidebar.file_uploader(
        "Upload SQL File", 
        type=['sql', 'txt'],
        help="Upload SQL file to create instant queryable database",
        key="main_sql_import"
    )
    
    if sql_file is not None:
        if st.sidebar.button("Create Database & Start Querying", 
                           use_container_width=True, 
                           type="primary"):
            execute_uploaded_sql_file(sql_file, 'sqlite')
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Database Connection")
    
    if not st.session_state.connected:
        # Only show traditional connection if not connected
        with st.sidebar.expander("Connect to Existing Database", expanded=False):
            db_type = st.selectbox(
                "Database Type",
                ["MySQL", "PostgreSQL", "SQLite"],
                help="Select your database type"
            )
            
            if db_type == "SQLite":
                db_file = st.text_input(
                    "Database File Path",
                    value="database.db",
                    help="Path to your SQLite database file"
                )
                
                connect_btn = st.button(
                    "Connect to SQLite", 
                    use_container_width=True,
                    type="secondary"
                )
                
                if connect_btn:
                    connect_to_database(db_type.lower(), database=db_file)
            
            else:  # MySQL or PostgreSQL
                col1, col2 = st.columns(2)
                with col1:
                    host = st.text_input("Host", value="localhost")
                    port = st.number_input(
                        "Port", 
                        value=3306 if db_type == "MySQL" else 5432,
                        min_value=1,
                        max_value=65535
                    )
                with col2:
                    user = st.text_input("Username", placeholder="Enter username")
                    password = st.text_input("Password", type="password", placeholder="Enter password")
                
                database = st.text_input("Database Name", placeholder="Enter database name")
                
                connect_btn = st.button(
                    f"Connect to {db_type}", 
                    use_container_width=True,
                    type="secondary"
                )
                
                if connect_btn:
                    if not all([user, password, database]):
                        st.sidebar.error("Please fill in all connection fields")
                    else:
                        conn_params = {
                            "host": host,
                            "port": port,
                            "user": user,
                            "password": password,
                            "database": database
                        }
                        connect_to_database(db_type.lower(), **conn_params)
    
    else:
        # CONNECTED STATE - FIXED DATABASE INFO DISPLAY
        st.sidebar.success("Database Connected")
        
        # Get database information
        db_name = "Unknown Database"
        db_type = "Unknown"
        table_count = 0
        
        # Method 1: For file databases (imported SQL files)
        if st.session_state.working_with_file_db and st.session_state.current_file_db:
            db_info = st.session_state.file_db_manager.get_current_db_info()
            if db_info:
                db_name = db_info['name']
                db_type = "SQLITE"
                table_count = len(db_info['tables'])
        
        # Method 2: For SQLite databases
        elif (st.session_state.last_connection_type == 'sqlite' and 
              st.session_state.sam and 
              hasattr(st.session_state.sam, 'database_file')):
            db_path = st.session_state.sam.database_file
            db_name = os.path.basename(db_path)
            db_type = "SQLITE"
            # Count tables for SQLite
            try:
                import sqlite3
                conn = sqlite3.connect(db_path, check_same_thread=False)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                table_count = len(tables)
                conn.close()
            except:
                table_count = 0
        
        # Method 3: For MySQL/PostgreSQL with metadata
        elif (st.session_state.sam and 
              hasattr(st.session_state.sam, 'current_metadata')):
            metadata = st.session_state.sam.current_metadata
            db_name = getattr(metadata, 'database_name', 'Connected Database')
            db_type = getattr(metadata, 'database_type', 'Unknown').upper()
            table_count = getattr(metadata, 'table_count', 0)
        
        # Method 4: Fallback - try to get from connection
        elif st.session_state.sam and hasattr(st.session_state.sam, 'connection'):
            try:
                conn = st.session_state.sam.connection
                if hasattr(conn, 'dsn'):
                    # PostgreSQL connection
                    db_name = conn.dsn.split('=')[-1] if '=' in conn.dsn else conn.dsn
                    db_type = "POSTGRESQL"
                elif hasattr(conn, 'database'):
                    # MySQL connection
                    db_name = conn.database
                    db_type = "MYSQL"
                elif hasattr(conn, 'db'):
                    # Other connection types
                    db_name = conn.db
            except:
                db_name = "Connected Database"
        
        # Method 5: Last resort - use connection type
        else:
            db_name = f"{st.session_state.last_connection_type.upper()} Database"
            db_type = st.session_state.last_connection_type.upper()
        
        # Enhanced database info display
        st.sidebar.markdown("""
        <div style='
            background: rgba(255,255,255,0.1); 
            padding: 1.5rem; 
            border-radius: 0.75rem;
            border: 1px solid rgba(255,255,255,0.2);
            margin: 1rem 0;
        '>
        """, unsafe_allow_html=True)
        
        # Database info in two columns
        info_cols = st.sidebar.columns(2)
        
        with info_cols[0]:
            st.metric(
                label="Database", 
                value=db_name,
                help="Currently connected database"
            )
            st.metric(
                label="Tables", 
                value=table_count,
                help="Number of tables in database"
            )
        
        with info_cols[1]:
            st.metric(
                label="Type", 
                value=db_type,
                help="Database type"
            )
            st.metric(
                label="Status", 
                value="Active",
                help="Connection status"
            )
        
        st.sidebar.markdown("</div>", unsafe_allow_html=True)
        
        # Show additional info for file databases
        if st.session_state.working_with_file_db and st.session_state.current_file_db:
            db_info = st.session_state.file_db_manager.get_current_db_info()
            if db_info:
                st.sidebar.markdown("---")
                st.sidebar.markdown("### Imported Database")
                st.sidebar.info(f"**{db_info['name']}**")
                st.sidebar.write(f"Tables: {len(db_info['tables'])}")
                st.sidebar.write(f"Created: {db_info['created_at'].strftime('%H:%M:%S')}")
                
                if st.sidebar.button("Switch to Main DB", use_container_width=True):
                    switch_to_main_database()
        
        # Management actions
        st.sidebar.markdown("### Management")
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("Refresh Schema", use_container_width=True):
                refresh_schema()
        with col2:
            if st.button("Force Table Detect", use_container_width=True):
                # Force the reasoner to re-detect tables
                if st.session_state.reasoner and hasattr(st.session_state.reasoner, 'get_actual_tables'):
                    st.session_state.reasoner.table_names = st.session_state.reasoner.get_actual_tables()
                    st.sidebar.success("Table detection forced!")
                st.rerun()
        
        if st.sidebar.button("Disconnect", use_container_width=True, type="secondary"):
            disconnect_database()
    
    # Quick examples (always show)
    st.sidebar.markdown("---")
    with st.sidebar.expander("Example Queries"):
        st.markdown("""
        **Try asking:**
        - "Show me all users"
        - "Count orders by status"  
        - "Find recent transactions"
        - "Average sales by region"
        - "List products with low stock"
        """)

def show_sql_import_results():
    """Display SQL import results in the main area"""
    st.subheader("SQL File Execution Results")
    
    if not hasattr(st.session_state, 'sql_import_results') or not st.session_state.sql_import_results:
        st.info("No SQL import results to display")
        return
        
    results = st.session_state.sql_import_results
    success_count = sum(1 for r in results if r['success'])
    total_count = len(results)
    
    # Summary cards
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Statements", total_count)
    with col2:
        st.metric("Successful", success_count)
    with col3:
        st.metric("Failed", total_count - success_count)
    
    # Clear results button
    if st.button("Clear Results", type="secondary"):
        del st.session_state.sql_import_results
        st.rerun()
    
    # Detailed results
    st.markdown("### Execution Details")
    for i, result in enumerate(results):
        with st.expander(f"Statement {i+1}: {'✅' if result['success'] else '❌'} {result['statement'][:50]}..."):
            st.code(result['statement'], language='sql')
            
            if result['success']:
                st.success("Execution successful")
                if hasattr(result['result'], 'data') and result['result'].data:
                    st.dataframe(pd.DataFrame(result['result'].data))
                elif hasattr(result['result'], 'rows_affected'):
                    st.info(f"Rows affected: {result['result'].rows_affected}")
            else:
                st.error(f"Execution failed: {result['error']}")

def switch_to_main_database():
    """Switch back to main database from file database"""
    if st.session_state.working_with_file_db and st.session_state.current_file_db:
        # Clean up the temporary file database
        db_name = st.session_state.current_file_db
        if hasattr(st.session_state, 'file_db_manager'):
            st.session_state.file_db_manager.cleanup_temp_database(db_name)
        
        st.session_state.working_with_file_db = False
        st.session_state.current_file_db = None
        
        st.sidebar.success("Switched back to main database")
        st.rerun()

class FileDatabaseManager:
    """Manages temporary databases created from SQL files"""
    
    def __init__(self):
        self.temp_databases = {}
        self.current_file_db = None
    
    def create_temp_database_from_sql(self, sql_content: str, db_name: str = None):
        """Create a temporary SQLite database from SQL file content"""
        import tempfile
        import sqlite3
        
        if not db_name:
            db_name = f"imported_db_{int(time.time())}"
        
        # Create temporary database file
        temp_dir = tempfile.gettempdir()
        temp_db_path = os.path.join(temp_dir, f"{db_name}.db")
        
        try:
            # Create connection with thread safety
            conn = sqlite3.connect(temp_db_path, check_same_thread=False)
            cursor = conn.cursor()
            
            # Split and execute statements
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            executed_count = 0
            for statement in statements:
                if statement and statement.strip():
                    try:
                        cursor.execute(statement)
                        executed_count += 1
                    except Exception as e:
                        # Skip statements that can't be executed (like SELECT in empty DB)
                        if "no such table" not in str(e).lower():
                            print(f"Info: Could not execute {statement[:50]}...: {e}")
            
            conn.commit()
            
            # Get the created tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            
            # Store the temp database
            self.temp_databases[db_name] = {
                'path': temp_db_path,
                'name': db_name,
                'created_at': datetime.now(),
                'tables': tables,
                'statements_executed': executed_count,
                'total_statements': len(statements)
            }
            
            self.current_file_db = db_name
            return db_name
            
        except Exception as e:
            print(f"Error creating temp database: {e}")
            # Clean up if creation failed
            if os.path.exists(temp_db_path):
                try:
                    os.remove(temp_db_path)
                except:
                    pass
            return None
    
    def get_tables_from_db(self, db_path: str):
        """Get list of tables from SQLite database"""
        import sqlite3
        try:
            conn = sqlite3.connect(db_path, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()
            return tables
        except:
            return []
    
    def connect_to_temp_db(self, db_name: str):
        """Connect to a temporary database"""
        if db_name in self.temp_databases:
            self.current_file_db = db_name
            return self.temp_databases[db_name]['path']
        return None
    
    def get_current_db_info(self):
        """Get info about current file database"""
        if self.current_file_db and self.current_file_db in self.temp_databases:
            return self.temp_databases[self.current_file_db]
        return None

    def cleanup_temp_database(self, db_name: str):
        """Clean up a temporary database file"""
        if db_name in self.temp_databases:
            db_info = self.temp_databases[db_name]
            try:
                # Close any open connections
                ThreadSafeSQLiteConnection.close_connection(db_info['path'])
                # Remove the file
                if os.path.exists(db_info['path']):
                    os.remove(db_info['path'])
            except Exception as e:
                print(f"Warning: Could not clean up temp database {db_name}: {e}")
            
            del self.temp_databases[db_name]
            
            if self.current_file_db == db_name:
                self.current_file_db = None

    def cleanup_all(self):
        """Clean up all temporary databases - ADD THIS METHOD"""
        for db_name in list(self.temp_databases.keys()):
            self.cleanup_temp_database(db_name)

def initialize_session_state():
    """Initialize all session state variables"""
    defaults = {
        'connected': False,
        'sam': None,
        'reasoner': None,
        'executor': None,
        'query_history': [],
        'current_schema': 'all',
        'selected_tables': [],
        'last_connection_type': None,
        'ai_thinking': False,
        'execution_stats': {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'total_execution_time': 0,
            'average_confidence': 0
        },
        'user_preferences': {
            'auto_refresh_schema': True,
            'show_explanations': True,
            'enable_visualizations': True,
            'theme': 'dark'
        },
        'current_results': None,
        'active_tab': 'query',
        'file_db_manager': FileDatabaseManager(),  # Add this
        'working_with_file_db': False,  # Add this
        'current_file_db': None  # Add this
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def execute_uploaded_sql_file(sql_file, db_type, **conn_params):
    """Execute SQL from uploaded file and create queryable database"""
    try:
        # Read SQL content
        sql_content = sql_file.getvalue().decode("utf-8")
        
        # Create a temporary database from the SQL file
        db_name = f"imported_{int(time.time())}"
        db_id = st.session_state.file_db_manager.create_temp_database_from_sql(sql_content, db_name)
        
        if db_id:
            # Connect to the temporary database automatically
            db_info = st.session_state.file_db_manager.get_current_db_info()
            
            if connect_to_database('sqlite', database=db_info['path']):
                st.session_state.working_with_file_db = True
                st.session_state.current_file_db = db_id
                
                st.sidebar.success(f"Database created from SQL file!")
                st.sidebar.info(f"Found {len(db_info['tables'])} tables")
                
                # IMPORTANT: Force refresh schema and update reasoner
                refresh_schema()
                
                # Update reasoner with new schema
                if st.session_state.sam and hasattr(st.session_state.sam, 'schema_file'):
                    try:
                        with open(st.session_state.sam.schema_file, 'r') as f:
                            schema_text = f.read()
                        if st.session_state.reasoner and hasattr(st.session_state.reasoner, 'update_schema'):
                            st.session_state.reasoner.update_schema(schema_text)
                    except Exception as e:
                        print(f"Warning: Could not update reasoner schema: {e}")
                
                # Auto-switch to query tab
                st.session_state.active_tab = 'query'
                st.rerun()
            else:
                st.sidebar.error("Failed to connect to created database")
        else:
            st.sidebar.error("Failed to create database from SQL file")
                
    except Exception as e:
        st.sidebar.error(f"Failed to process SQL file: {str(e)}")

def connect_to_database(db_type: str, **conn_params):
    """Database connection handler with proper thread handling"""
    with st.spinner("Connecting to database..."):
        try:
            if not MODULES_AVAILABLE:
                st.sidebar.error("Required modules not available")
                return False
            
            sam = SchemaAwarenessModule()
            
            # For SQLite, ensure we're using thread-safe approach
            if db_type == 'sqlite' and 'database' in conn_params:
                db_file = conn_params['database']
                # Ensure the connection is thread-safe
                if not os.path.exists(db_file):
                    st.sidebar.error(f"Database file not found: {db_file}")
                    return False
            
            if sam.connect_database(db_type, **conn_params):
                st.session_state.sam = sam
                st.session_state.connected = True
                st.session_state.last_connection_type = db_type
                
                # Initialize reasoner with schema
                try:
                    with open(sam.schema_file, 'r') as f:
                        schema_text = f.read()
                    
                    # Use the new initialization function
                    st.session_state.reasoner = initialize_reasoner(schema_text)
                    
                    # Initialize executor
                    st.session_state.executor = DatabaseExecutor(sam.connection, db_type)
                    
                    st.sidebar.success("✅ Database connected successfully!")
                    return True
                    
                except Exception as e:
                    st.sidebar.error(f"Error initializing AI components: {str(e)}")
                    # Still consider connected for basic operations
                    st.session_state.connected = True
                    st.sidebar.success("✅ Database connected (AI features limited)")
                    return True
            else:
                st.sidebar.error("❌ Database connection failed")
                return False
                
        except Exception as e:
            st.sidebar.error(f"❌ Connection error: {str(e)}")
            return False
                 
def disconnect_database():
    """Enhanced database disconnection"""
    try:
        if st.session_state.connected:
            # Clean up file database if we're using one
            if st.session_state.working_with_file_db and st.session_state.current_file_db:
                db_name = st.session_state.current_file_db
                if hasattr(st.session_state, 'file_db_manager'):
                    st.session_state.file_db_manager.cleanup_temp_database(db_name)
            
            # Close the schema awareness module
            if st.session_state.sam:
                try:
                    st.session_state.sam.close()
                except Exception as e:
                    print(f"Warning: Error closing SAM: {e}")
            
            # Reset session state
            st.session_state.connected = False
            st.session_state.sam = None
            st.session_state.reasoner = None
            st.session_state.executor = None
            st.session_state.current_results = None
            st.session_state.working_with_file_db = False
            st.session_state.current_file_db = None
            
            st.sidebar.success("Disconnected from database")
            time.sleep(1)
            st.rerun()
        else:
            st.sidebar.info("Not connected to any database")
            
    except Exception as e:
        st.sidebar.error(f"Error during disconnection: {str(e)}")
        
def execute_sql_file(sql_content: str, execute_all: bool, show_results: bool, stop_on_error: bool):
    """Execute SQL content from imported file"""
    try:
        # Split SQL into individual statements
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        if not statements:
            st.error("No valid SQL statements found")
            return
        
        if not execute_all and len(statements) > 1:
            # Let user choose which statement to execute
            selected_stmt = st.selectbox(
                "Select statement to execute:",
                range(len(statements)),
                format_func=lambda x: f"Statement {x+1}: {statements[x][:50]}..."
            )
            statements = [statements[selected_stmt]]
        
        # Execute statements
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, statement in enumerate(statements):
            status_text.text(f"Executing statement {i+1}/{len(statements)}...")
            progress_bar.progress((i) / len(statements))
            
            try:
                # Execute the statement
                if st.session_state.last_connection_type == 'sqlite':
                    exec_result = execute_sqlite_query_thread_safe(
                        statement, 
                        safe_to_execute=True, 
                        is_destructive=True  # Assume destructive for file imports
                    )
                else:
                    exec_result = st.session_state.executor.execute_query(
                        statement,
                        safe_to_execute=True,
                        is_destructive=True,
                        dry_run=False
                    )
                
                results.append({
                    'statement': statement,
                    'success': True,
                    'result': exec_result,
                    'error': None
                })
                
            except Exception as e:
                results.append({
                    'statement': statement,
                    'success': False,
                    'result': None,
                    'error': str(e)
                })
                
                if stop_on_error:
                    st.error(f"Stopped execution due to error in statement {i+1}")
                    break
        
        progress_bar.progress(1.0)
        status_text.text("Execution completed!")
        
        # Display results
        display_sql_import_results(results, show_results)
        
    except Exception as e:
        st.error(f"Failed to execute SQL file: {str(e)}")

def display_sql_import_results(results: List[Dict], show_results: bool):
    """Display results of SQL file execution"""
    st.markdown("### Execution Results")
    
    success_count = sum(1 for r in results if r['success'])
    total_count = len(results)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Statements", total_count)
    with col2:
        st.metric("Successful", success_count)
    with col3:
        st.metric("Failed", total_count - success_count)
    
    # Detailed results
    for i, result in enumerate(results):
        with st.expander(f"Statement {i+1}: {'✅' if result['success'] else '❌'}"):
            st.code(result['statement'], language='sql')
            
            if result['success']:
                st.success("Execution successful")
                if show_results and hasattr(result['result'], 'data') and result['result'].data:
                    st.dataframe(pd.DataFrame(result['result'].data))
                elif hasattr(result['result'], 'rows_affected'):
                    st.info(f"Rows affected: {result['result'].rows_affected}")
            else:
                st.error(f"Execution failed: {result['error']}")

def create_mock_reasoner(schema_text: str):
    """
    DEBUG: Mock Reasoner with extensive logging
    
    This is the fallback AI when Gemini API is not available.
    Extensive debug prints help understand:
    - What tables are being detected
    - How queries are being processed
    - Why certain SQL is being generated
    """
    class MockReasoner:
        def __init__(self, schema_snapshot):
            self.schema_snapshot = schema_text
            self.table_names = self.get_actual_tables()
            print(f"MockReasoner: Found tables - {self.table_names}")
            
        def get_actual_tables(self):
            """Get the actual table names from the connected database"""
            tables = []
            try:
                if st.session_state.connected and st.session_state.sam:
                    print("Attempting to get tables from database...")
                    
                    # METHOD 1: Try schema awareness module methods
                    if hasattr(st.session_state.sam, 'get_tables'):
                        tables = st.session_state.sam.get_tables()
                        print(f"Method 1 (get_tables): {tables}")
                    elif hasattr(st.session_state.sam, 'get_table_names'):
                        tables = st.session_state.sam.get_table_names()
                        print(f"Method 2 (get_table_names): {tables}")
                    elif hasattr(st.session_state.sam, 'list_tables'):
                        tables = st.session_state.sam.list_tables()
                        print(f"Method 3 (list_tables): {tables}")
                    
                    # METHOD 2: If above methods failed, try direct SQLite query
                    if not tables and st.session_state.last_connection_type == 'sqlite':
                        print("Trying direct SQLite table detection...")
                        try:
                            import sqlite3
                            # Get the database file path
                            if hasattr(st.session_state.sam, 'database_file'):
                                db_path = st.session_state.sam.database_file
                                print(f"Database path: {db_path}")
                                
                                # Direct SQL query to get tables
                                conn = sqlite3.connect(db_path, check_same_thread=False)
                                cursor = conn.cursor()
                                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
                                tables = [row[0] for row in cursor.fetchall()]
                                conn.close()
                                print(f"Direct SQLite query found: {tables}")
                        except Exception as e:
                            print(f"Direct SQLite query failed: {e}")
                    
                    # METHOD 3: Try to get from metadata
                    if not tables and hasattr(st.session_state.sam, 'current_metadata'):
                        metadata = st.session_state.sam.current_metadata
                        if hasattr(metadata, 'tables'):
                            tables = metadata.tables
                            print(f"Method 4 (metadata.tables): {tables}")
                        elif hasattr(metadata, 'table_names'):
                            tables = metadata.table_names
                            print(f"Method 5 (metadata.table_names): {tables}")
                    
                    print(f"Final table list: {tables}")
                    
            except Exception as e:
                print(f"Error getting tables: {e}")
                
            return tables
            
        def update_schema(self, schema):
            self.schema_snapshot = schema
            # Refresh table list
            self.table_names = self.get_actual_tables()
            
        def generate(self, payload):
            nl_query = payload.raw_nl.lower()
            print(f"Query: '{nl_query}', Available tables: {self.table_names}")
            
            # If we have actual tables, use them
            if self.table_names:
                # Find the most relevant table based on the query
                target_table = self.find_best_table(nl_query)
                
                if "count" in nl_query:
                    sql = f"SELECT COUNT(*) as count FROM {target_table};"
                    explanation = f"Counting records in {target_table} table"
                    
                elif any(word in nl_query for word in ['show', 'display', 'list', 'get']):
                    if 'table' in nl_query or 'tables' in nl_query:
                        # Show all tables
                        table_list = "', '".join(self.table_names)
                        sql = f"SELECT '{table_list}' as available_tables;"
                        explanation = f"Available tables: {', '.join(self.table_names)}"
                    else:
                        # Show data from specific table
                        sql = f"SELECT * FROM {target_table} LIMIT 10;"
                        explanation = f"Displaying records from {target_table} table"
                        
                elif "average" in nl_query or "avg" in nl_query:
                    sql = f"SELECT 'Average calculation' as info FROM {target_table} LIMIT 1;"
                    explanation = f"Average calculation for {target_table} table"
                    
                else:
                    # Default query
                    sql = f"SELECT * FROM {target_table} LIMIT 5;"
                    explanation = f"Querying {target_table} table"
                    
                warnings = ["Demo mode - using mock AI responses"]
                confidence = 0.9
                
            else:
                # No tables found - show a helpful message
                sql = "SELECT 'Database is connected but no tables were detected. Try refreshing the schema.' as message;"
                explanation = "The database connection is active but no tables were detected. This could be because the schema needs to be refreshed."
                warnings = ["No tables detected in database", "Try refreshing schema in sidebar", "Demo mode - using mock AI responses"]
                confidence = 0.6
            
            return type('obj', (object,), {
                'sql': sql,
                'intent': 'select',
                'dialect': payload.dialect or 'mysql',
                'warnings': warnings,
                'errors': [],
                'explain_text': explanation,
                'confidence': confidence,
                'safe_to_execute': True
            })()
            
        def find_best_table(self, query):
            """Find the best matching table based on the query content"""
            if not self.table_names:
                return "example_table"
                
            query_lower = query.lower()
            
            # Try to match table names with query keywords
            for table in self.table_names:
                table_lower = table.lower()
                
                # Direct matches
                if 'user' in query_lower and 'user' in table_lower:
                    return table
                if 'product' in query_lower and 'product' in table_lower:
                    return table
                if 'order' in query_lower and 'order' in table_lower:
                    return table
                if 'customer' in query_lower and 'customer' in table_lower:
                    return table
                if 'category' in query_lower and 'category' in table_lower:
                    return table
            
            # Return the first table as fallback
            return self.table_names[0]
    
    return MockReasoner(schema_text)

def debug_table_info():
    """Temporary debug function to see table information"""
    if st.session_state.connected:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### Debug: Table Info")
        
        # Check what tables the database has
        tables = []
        try:
            if hasattr(st.session_state.sam, 'get_tables'):
                tables = st.session_state.sam.get_tables()
            elif hasattr(st.session_state.sam, 'get_table_names'):
                tables = st.session_state.sam.get_table_names()
        except Exception as e:
            st.sidebar.write(f"Error getting tables: {e}")
        
        st.sidebar.write(f"Database tables: {tables}")
        
        # Check what tables the reasoner sees
        if st.session_state.reasoner and hasattr(st.session_state.reasoner, 'table_names'):
            st.sidebar.write(f"Reasoner tables: {st.session_state.reasoner.table_names}")

def debug_database_status():
    """Debug function to check database and table status"""
    if st.session_state.connected and st.session_state.sam:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### Debug Info")
        
        # Check schema file
        if hasattr(st.session_state.sam, 'schema_file'):
            schema_file = st.session_state.sam.schema_file
            st.sidebar.write(f"Schema file: {schema_file}")
            if schema_file and os.path.exists(schema_file):
                try:
                    with open(schema_file, 'r') as f:
                        content = f.read()
                    st.sidebar.write(f"Schema size: {len(content)} chars")
                    st.sidebar.write(f"Schema preview: {content[:200]}...")
                except Exception as e:
                    st.sidebar.write(f"Schema read error: {e}")
        
        # Check tables
        try:
            tables = []
            if hasattr(st.session_state.sam, 'get_tables'):
                tables = st.session_state.sam.get_tables()
            elif hasattr(st.session_state.sam, 'get_table_names'):
                tables = st.session_state.sam.get_table_names()
            
            st.sidebar.write(f"Database tables: {tables}")
        except Exception as e:
            st.sidebar.write(f"Table check error: {e}")
        
        # Check reasoner tables
        if st.session_state.reasoner and hasattr(st.session_state.reasoner, 'table_names'):
            st.sidebar.write(f"Reasoner tables: {st.session_state.reasoner.table_names}")

def refresh_schema():
    """Refresh database schema with better error handling"""
    with st.spinner("Refreshing schema..."):
        try:
            if not hasattr(st.session_state.sam, 'generate_full_schema'):
                st.sidebar.error("Schema generation not supported")
                return
                
            st.session_state.sam.generate_full_schema()
            
            # Check if schema file was created
            if not hasattr(st.session_state.sam, 'schema_file') or not st.session_state.sam.schema_file:
                st.sidebar.error("Schema file was not created")
                return
                
            schema_file_path = st.session_state.sam.schema_file
            if not os.path.exists(schema_file_path):
                st.sidebar.error(f"Schema file not found at: {schema_file_path}")
                return
                
            # Read schema to verify it's valid
            with open(schema_file_path, 'r') as f:
                schema_content = f.read()
                if not schema_content.strip():
                    st.sidebar.warning("Schema file is empty")
                else:
                    st.sidebar.success(f"Schema refreshed! ({len(schema_content)} chars)")
            
            # Update reasoner schema
            if hasattr(st.session_state.reasoner, 'update_schema'):
                st.session_state.reasoner.update_schema(schema_content)
                
        except Exception as e:
            st.sidebar.error(f"Schema refresh failed: {str(e)}")
        
        # Show available methods
        methods = [m for m in dir(st.session_state.sam) if not m.startswith('_') and callable(getattr(st.session_state.sam, m))]
        st.sidebar.write("Available methods:", methods[:8])

def display_schema_explorer():
    """Simple schema explorer - just show available tables"""
    st.subheader("Database Schema")
    
    if not st.session_state.sam:
        st.info("Connect to a database to view schema")
        return
    
    # Try to get tables
    tables = []
    try:
        # Try different methods to get tables
        if hasattr(st.session_state.sam, 'get_tables'):
            tables = st.session_state.sam.get_tables()
        elif hasattr(st.session_state.sam, 'get_table_names'):
            tables = st.session_state.sam.get_table_names()
        elif hasattr(st.session_state.sam, 'list_tables'):
            tables = st.session_state.sam.list_tables()
        elif hasattr(st.session_state.sam, 'tables'):
            tables = st.session_state.sam.tables
        elif hasattr(st.session_state.sam, 'current_metadata') and st.session_state.sam.current_metadata:
            metadata = st.session_state.sam.current_metadata
            if hasattr(metadata, 'tables'):
                tables = metadata.tables
            elif hasattr(metadata, 'table_names'):
                tables = metadata.table_names
    except Exception as e:
        st.error(f"Error retrieving tables: {str(e)}")
        tables = []
    
    # If no tables found
    if not tables:
        st.info("No tables found in the database")
        return
    
    # Simple table count
    st.metric("Total Tables", len(tables))
    
    # Simple table display
    st.markdown("### Available Tables")
    
    # Display tables in a clean grid
    cols = st.columns(3)
    for idx, table in enumerate(tables):
        col_idx = idx % 3
        with cols[col_idx]:
            # Simple table card
            st.markdown(f"""
            <div style='
                background: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 0.5rem;
                padding: 1rem;
                margin: 0.5rem 0;
            '>
                <div style='font-weight: 600; color: #1e293b; text-align: center;'>
                    {table}
                </div>
            </div>
            """, unsafe_allow_html=True)
                                                
def add_specialized_snapshot_support():
    """Add mock specialized snapshot support if not available"""
    if hasattr(st.session_state.sam, 'create_specialized_snapshot'):
        return  # Method already exists
    
    # Add mock method
    def create_specialized_snapshot(self, selected_tables):
        """Mock specialized snapshot that creates a filtered schema file"""
        try:
            if not hasattr(self, 'schema_file') or not self.schema_file:
                return None
                
            # Read the full schema
            with open(self.schema_file, 'r') as f:
                full_schema = f.read()
            
            # Create a specialized version (this is a simple mock)
            # In a real implementation, you would filter the schema properly
            specialized_content = f"# Specialized Schema for tables: {', '.join(selected_tables)}\n\n"
            specialized_content += f"# Filtered from full schema\n{full_schema}"
            
            # Create specialized file
            specialized_file = f"specialized_schema_{'_'.join(selected_tables)}.txt"
            with open(specialized_file, 'w') as f:
                f.write(specialized_content)
            
            return specialized_file
            
        except Exception as e:
            print(f"Mock specialized snapshot failed: {e}")
            return None
    
    # Add the method to the instance
    st.session_state.sam.create_specialized_snapshot = create_specialized_snapshot.__get__(st.session_state.sam)

def debug_schema_info():
    """
    DEBUG: Schema Information Display
    
    This debug section shows critical information about the database schema
    and connection status. Useful for troubleshooting when:
    - Tables aren't being detected properly
    - Schema file issues occur
    - Connection problems happen
    
    Displays:
    - Schema file path and existence
    - Schema file size and content preview
    - Available methods in schema module
    """
    if st.session_state.sam:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🔧 Schema Debug Info")
        
        # Show schema file info
        if hasattr(st.session_state.sam, 'schema_file'):
            schema_file = st.session_state.sam.schema_file
            st.sidebar.write(f"**Schema file:** {schema_file}")
            if schema_file and os.path.exists(schema_file):
                try:
                    with open(schema_file, 'r') as f:
                        content = f.read()
                    st.sidebar.write(f"**Schema size:** {len(content)} chars")
                    # Show first 200 chars to see if schema is populated
                    st.sidebar.write(f"**Schema preview:** {content[:200]}...")
                except Exception as e:
                    st.sidebar.write(f"**Schema read error:** {e}")
            else:
                st.sidebar.write("**Schema file:** Not found or inaccessible")
        
        # Show available methods for debugging module capabilities
        methods = [m for m in dir(st.session_state.sam) if not m.startswith('_') and callable(getattr(st.session_state.sam, m))]
        st.sidebar.write(f"**Available methods:** {methods[:8]}")  # Show first 8 methods

def debug_schema_module():
    """Debug function to see available methods in schema module"""
    if st.session_state.sam:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### Debug Info")
        
        # Show available methods
        methods = [method for method in dir(st.session_state.sam) if not method.startswith('_')]
        st.sidebar.write("Available methods:", methods[:10])  # Show first 10 methods
        
        # Show attributes
        attrs = [attr for attr in dir(st.session_state.sam) if not callable(getattr(st.session_state.sam, attr)) and not attr.startswith('_')]
        st.sidebar.write("Available attributes:", attrs[:10])

def display_query_interface():
    """Enhanced query interface with better tooltips"""
    st.subheader("Natural Language Query")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        nl_query = st.text_area(
            "Describe what you want to query:",
            placeholder="e.g., Show me all students whose grades are above 90 and enrolled in Computer Science courses...",
            height=120,
            help="Be specific about filters, sorting, and aggregations",
            key="main_query_input"
        )
    
    with col2:
        st.markdown("**Settings**")
        
        # SQL Dialect with tooltip
        dialect = st.selectbox(
            "SQL Dialect",
            ["mysql", "postgresql", "sqlite"],
            index=0,
            label_visibility="collapsed",
            help="Choose the SQL dialect for your database. MySQL for MySQL databases, PostgreSQL for PostgreSQL, SQLite for file-based databases."
        )
        
        safety_col, dry_run_col = st.columns(2)
        
        with safety_col:
            allow_destructive = st.checkbox(
                "Allow Writes",
                value=False,
                help="Enable INSERT, UPDATE, DELETE operations. When unchecked, only safe SELECT queries are allowed.",
                key="allow_destructive_check"
            )
        
        with dry_run_col:
            dry_run = st.checkbox(
                "Dry Run",
                value=False,
                help="Generate SQL without executing it. Preview the generated SQL before running it on your database.",
                key="dry_run_check"
            )
    
    if st.button("Generate & Execute SQL", type="primary", use_container_width=True):
        if nl_query.strip():
            execute_nl_query(nl_query, dialect, allow_destructive, dry_run)
        else:
            st.warning("Please enter a query description")

def show_natural_language_interface():
    """Display the natural language query interface"""
    st.subheader("Natural Language Query")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        nl_query = st.text_area(
            "Describe what you want to query:",
            placeholder="e.g., Show me all students whose grades are above 90 and enrolled in Computer Science courses...",
            height=120,
            help="Be specific about filters, sorting, and aggregations",
            key="main_query_input"
        )
    
    with col2:
        st.markdown("**Settings**")
        dialect = st.selectbox(
            "SQL Dialect",
            ["mysql", "postgresql", "sqlite"],
            index=0,
            label_visibility="collapsed",
            key="dialect_select"
        )
        
        safety_col, dry_run_col = st.columns(2)
        with safety_col:
            allow_destructive = st.checkbox(
                "Allow Writes",
                value=False,
                help="Enable INSERT, UPDATE, DELETE operations",
                key="allow_destructive_check"
            )
        with dry_run_col:
            dry_run = st.checkbox(
                "Dry Run",
                value=False,
                help="Generate SQL without executing it",
                key="dry_run_check"
            )
    
    if st.button("Generate & Execute SQL", type="primary", use_container_width=True):
        if nl_query.strip():
            execute_nl_query(nl_query, dialect, allow_destructive, dry_run)
        else:
            st.warning("Please enter a query description")

def display_sql_import_workflow():
    """Display the SQL file import workflow with database creation"""
    st.subheader("📁 SQL File Import")
    
    if not hasattr(st.session_state, 'uploaded_sql_content'):
        st.error("No SQL file content found. Please upload a file again.")
        return
    
    st.success("✅ SQL file uploaded successfully!")
    
    # Display the SQL content
    st.markdown("### SQL Content Preview")
    edited_sql = st.text_area(
        "Review and edit your SQL:",
        value=st.session_state.uploaded_sql_content,
        height=200,
        key="sql_editor"
    )
    
    # Database creation options
    st.markdown("### Database Setup")
    col1, col2 = st.columns(2)
    
    with col1:
        db_name = st.text_input(
            "Database Name:",
            value=f"imported_db_{datetime.now().strftime('%H%M%S')}",
            help="Name for the temporary database"
        )
    
    with col2:
        setup_mode = st.radio(
            "Setup Mode:",
            ["Create Database & Query", "Execute Only"],
            help="Create a queryable database or just execute the SQL"
        )
    
    # Action buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🚀 Create Database & Query", type="primary", use_container_width=True):
            if setup_mode == "Create Database & Query":
                create_file_database(edited_sql, db_name)
            else:
                # Fix: Call the function with proper parameters
                execute_sql_statements(edited_sql, "Execute All", 0, True, True)
    
    
    with col2:
        if st.button("🔍 Preview Data", use_container_width=True):
            preview_sql_data(edited_sql)
    
    with col3:
        if st.button("❌ Cancel", use_container_width=True):
            clear_sql_import_state()
            st.rerun()

def create_file_database(sql_content: str, db_name: str):
    """Create a temporary database from SQL file and connect to it"""
    try:
        with st.spinner("Creating temporary database..."):
            # Create temp database
            db_id = st.session_state.file_db_manager.create_temp_database_from_sql(sql_content, db_name)
            
            if db_id:
                # Connect to the temp database using our existing connection system
                db_info = st.session_state.file_db_manager.get_current_db_info()
                
                if connect_to_database('sqlite', database=db_info['path']):
                    st.session_state.working_with_file_db = True
                    st.session_state.current_file_db = db_id
                    
                    st.success(f"✅ Database '{db_name}' created successfully!")
                    st.info(f"📊 Found {len(db_info['tables'])} tables: {', '.join(db_info['tables'])}")
                    
                    # Auto-switch to query tab
                    st.session_state.active_tab = 'query'
                    st.session_state.show_sql_import_options = False
                    st.rerun()
                else:
                    st.error("Failed to connect to created database")
            else:
                st.error("Failed to create database from SQL file")
                
    except Exception as e:
        st.error(f"Error creating database: {str(e)}")

def preview_sql_data(sql_content: str):
    """Preview what tables and data would be created"""
    try:
        # Extract table creation statements to preview schema
        create_statements = [stmt for stmt in sql_content.split(';') 
                           if stmt.strip().upper().startswith('CREATE')]
        
        if create_statements:
            st.markdown("### 📋 Schema Preview")
            for stmt in create_statements:
                with st.expander(f"Table: {extract_table_name(stmt)}"):
                    st.code(stmt, language='sql')
        else:
            st.info("No CREATE TABLE statements found in the SQL file")
            
        # Show sample data if SELECT statements exist
        select_statements = [stmt for stmt in sql_content.split(';') 
                           if stmt.strip().upper().startswith('SELECT')]
        
        if select_statements and st.session_state.connected:
            st.markdown("### 🔍 Data Preview")
            for i, stmt in enumerate(select_statements[:3]):  # Limit to 3 selects
                try:
                    if st.session_state.last_connection_type == 'sqlite':
                        result = execute_sqlite_query_thread_safe(stmt, True, False)
                        if result.data:
                            st.write(f"**Query {i+1}:**")
                            st.dataframe(pd.DataFrame(result.data))
                except:
                    pass
                    
    except Exception as e:
        st.error(f"Error previewing data: {str(e)}")

def extract_table_name(create_statement: str) -> str:
    """Extract table name from CREATE TABLE statement"""
    import re
    match = re.search(r'CREATE TABLE (?:IF NOT EXISTS )?["`]?([^"`\s]+)["`]?', create_statement, re.IGNORECASE)
    return match.group(1) if match else "Unknown Table"

def execute_sql_statements(sql_content: str, execute_mode: str, selected_index: int, stop_on_error: bool, show_results: bool):
    """Execute the SQL statements based on selected mode"""
    try:
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        if not statements:
            st.error("No valid SQL statements found")
            return
        
        # Filter statements based on mode
        if execute_mode == "Execute Selected":
            statements = [statements[selected_index]]
        elif execute_mode == "Preview Only":
            st.info("Preview mode - no execution performed")
            st.session_state.sql_import_results = [{
                'statement': stmt,
                'success': True,
                'result': None,
                'error': None,
                'preview': True
            } for stmt in statements]
            st.session_state.show_sql_import_options = False
            st.rerun()
            return
        
        # Execute statements
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, statement in enumerate(statements):
            status_text.text(f"Executing statement {i+1}/{len(statements)}...")
            progress_bar.progress((i) / len(statements))
            
            try:
                # Execute based on database type
                if st.session_state.last_connection_type == 'sqlite':
                    exec_result = execute_sqlite_query_thread_safe(
                        statement, 
                        safe_to_execute=True, 
                        is_destructive=True
                    )
                else:
                    exec_result = st.session_state.executor.execute_query(
                        statement,
                        safe_to_execute=True,
                        is_destructive=True,
                        dry_run=False
                    )
                
                results.append({
                    'statement': statement,
                    'success': True,
                    'result': exec_result,
                    'error': None,
                    'preview': False
                })
                
            except Exception as e:
                results.append({
                    'statement': statement,
                    'success': False,
                    'result': None,
                    'error': str(e),
                    'preview': False
                })
                
                if stop_on_error:
                    st.error(f"Stopped execution due to error in statement {i+1}")
                    break
        
        progress_bar.progress(1.0)
        status_text.text("Execution completed!")
        
        # Store results and show them
        st.session_state.sql_import_results = results
        st.session_state.show_sql_import_options = False
        st.rerun()
        
    except Exception as e:
        st.error(f"Failed to execute SQL: {str(e)}")

def save_sql_to_file(sql_content: str):
    """Save SQL content to a file"""
    from datetime import datetime
    filename = f"sql_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    
    st.download_button(
        "Download SQL File",
        sql_content,
        file_name=filename,
        mime="text/sql",
        use_container_width=True
    )

def clear_sql_import_state():
    """Clear SQL import related session state"""
    keys_to_remove = ['uploaded_sql_content', 'show_sql_import_options', 'sql_import_results']
    for key in keys_to_remove:
        if key in st.session_state:
            del st.session_state[key]

def execute_nl_query(nl_query: str, dialect: str, allow_destructive: bool, dry_run: bool):
    """Enhanced query execution with better feedback"""
    # Check if reasoner is available
    if not st.session_state.reasoner:
        st.error("AI reasoner not available. Please check your connection and try again.")
        return
    
    st.session_state.ai_thinking = True
    
    # Create thinking animation
    thinking_placeholder = st.empty()
    with thinking_placeholder.container():
        st.markdown("""
        <div style='text-align: center; padding: 2rem;'>
            <div class='pulse'>AI</div>
            <h3>AI is analyzing your query...</h3>
            <p>Generating optimized SQL based on your schema</p>
        </div>
        """, unsafe_allow_html=True)
    
    try:
        # Prepare schema context
        schema_text = prepare_schema_context()
        if not schema_text:
            return
        
        # Update reasoner schema if method exists
        if hasattr(st.session_state.reasoner, 'update_schema'):
            st.session_state.reasoner.update_schema(schema_text)
        
        # Create command payload
        payload = CommandPayload(
            intent="query",
            raw_nl=nl_query,
            dialect=dialect,
            allow_destructive=allow_destructive
        )
        
        # Generate SQL
        with st.spinner("Analyzing natural language..."):
            output = st.session_state.reasoner.generate(payload)
        
        thinking_placeholder.empty()
        
        # Display results
        display_generation_results(output, nl_query, dry_run)
        
    except Exception as e:
        thinking_placeholder.empty()
        st.error(f"Query execution failed: {str(e)}")
    finally:
        st.session_state.ai_thinking = False

def prepare_schema_context() -> str:
    """Prepare appropriate schema context based on selection with proper error handling"""
    try:
        if not st.session_state.sam:
            st.error("Database connection not available")
            return ""
            
        if st.session_state.current_schema == "all":
            # Check if schema_file exists and is valid
            if not hasattr(st.session_state.sam, 'schema_file') or not st.session_state.sam.schema_file:
                st.error("Schema file path not available. Please refresh schema.")
                return ""
            
            schema_file_path = st.session_state.sam.schema_file
            if not os.path.exists(schema_file_path):
                st.error(f"Schema file not found at: {schema_file_path}")
                return ""
                
            with open(schema_file_path, 'r') as f:
                return f.read()
                
        elif st.session_state.current_schema == "none":
            return "NO_TABLES_SELECTED"
            
        else:  # selected
            if not st.session_state.selected_tables:
                st.error("Please select at least one table")
                return ""
                
            # Check if create_specialized_snapshot method exists
            if not hasattr(st.session_state.sam, 'create_specialized_snapshot'):
                st.warning("Specialized snapshots not supported. Using full schema instead.")
                # Fallback to full schema
                if hasattr(st.session_state.sam, 'schema_file') and st.session_state.sam.schema_file:
                    with open(st.session_state.sam.schema_file, 'r') as f:
                        return f.read()
                else:
                    st.error("Full schema also not available")
                    return ""
                
            # Try to create specialized snapshot
            try:
                snapshot_file = st.session_state.sam.create_specialized_snapshot(
                    st.session_state.selected_tables
                )
                
                if not snapshot_file:
                    st.warning("Specialized snapshot returned None. Using full schema instead.")
                    # Fallback to full schema
                    if hasattr(st.session_state.sam, 'schema_file') and st.session_state.sam.schema_file:
                        with open(st.session_state.sam.schema_file, 'r') as f:
                            return f.read()
                    else:
                        st.error("Full schema also not available")
                        return ""
                
                if not os.path.exists(snapshot_file):
                    st.warning(f"Specialized snapshot file not found: {snapshot_file}. Using full schema.")
                    # Fallback to full schema
                    if hasattr(st.session_state.sam, 'schema_file') and st.session_state.sam.schema_file:
                        with open(st.session_state.sam.schema_file, 'r') as f:
                            return f.read()
                    else:
                        st.error("Full schema also not available")
                        return ""
                    
                with open(snapshot_file, 'r') as f:
                    content = f.read()
                    if not content.strip():
                        st.warning("Specialized snapshot is empty. Using full schema.")
                        # Fallback to full schema
                        if hasattr(st.session_state.sam, 'schema_file') and st.session_state.sam.schema_file:
                            with open(st.session_state.sam.schema_file, 'r') as f:
                                return f.read()
                    return content
                    
            except Exception as snapshot_error:
                st.warning(f"Specialized snapshot failed: {snapshot_error}. Using full schema.")
                # Fallback to full schema
                if hasattr(st.session_state.sam, 'schema_file') and st.session_state.sam.schema_file:
                    with open(st.session_state.sam.schema_file, 'r') as f:
                        return f.read()
                else:
                    st.error("Full schema also not available")
                    return ""
                
    except Exception as e:
        st.error(f"Schema preparation failed: {str(e)}")
        return ""

def initialize_reasoner(schema_text: str):
    """Initialize reasoner with proper fallback handling"""
    try:
        if not GEMINI_API_VALID:
            st.sidebar.warning("Using demo mode - Gemini API not available")
            reasoner = create_mock_reasoner(schema_text)
            # Force table detection after initialization
            if hasattr(reasoner, 'get_actual_tables'):
                reasoner.table_names = reasoner.get_actual_tables()
            return reasoner
        
        # Try to initialize real reasoner
        if MODULES_AVAILABLE:
            return GeminiReasoner(schema_snapshot=schema_text)
        else:
            reasoner = create_mock_reasoner(schema_text)
            if hasattr(reasoner, 'get_actual_tables'):
                reasoner.table_names = reasoner.get_actual_tables()
            return reasoner
            
    except Exception as e:
        st.sidebar.error(f"Failed to initialize AI reasoner: {e}")
        reasoner = create_mock_reasoner(schema_text)
        if hasattr(reasoner, 'get_actual_tables'):
            reasoner.table_names = reasoner.get_actual_tables()
        return reasoner
     
def display_generation_results(output, nl_query: str, dry_run: bool):
    """Display enhanced generation results"""
    # Results container
    with st.container():
        st.markdown("### Generated SQL")
        
        # SQL display with copy button
        sql_col1, sql_col2 = st.columns([4, 1])
        with sql_col1:
            st.code(output.sql or "No SQL generated", language="sql")
        with sql_col2:
            if output.sql:
                st.download_button(
                    "Copy SQL",
                    output.sql,
                    file_name="generated_query.sql",
                    use_container_width=True
                )
        
        # Metadata cards
        st.markdown("### Generation Metrics")
        meta_cols = st.columns(5)
        
        with meta_cols[0]:
            intent = getattr(output, 'intent', 'unknown')
            intent_color = {
                'select': '#10b981', 'insert': '#f59e0b', 
                'update': '#f59e0b', 'delete': '#ef4444',
                'create': '#8b5cf6'
            }.get(intent, '#6b7280')
            st.markdown(f"""
            <div style='text-align: center; padding: 1rem; background: {intent_color}10; 
                        border-radius: 0.5rem; border-left: 4px solid {intent_color}'>
                <div style='font-size: 0.8rem; color: {intent_color};'>INTENT</div>
                <div style='font-size: 1.2rem; font-weight: bold; color: {intent_color};'>
                    {intent.upper()}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with meta_cols[1]:
            confidence = getattr(output, 'confidence', 0)
            confidence_color = '#10b981' if confidence > 0.7 else '#f59e0b' if confidence > 0.4 else '#ef4444'
            st.markdown(f"""
            <div style='text-align: center; padding: 1rem; background: {confidence_color}10; 
                        border-radius: 0.5rem; border-left: 4px solid {confidence_color}'>
                <div style='font-size: 0.8rem; color: {confidence_color};'>CONFIDENCE</div>
                <div style='font-size: 1.2rem; font-weight: bold; color: {confidence_color};'>
                    {confidence:.0%}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with meta_cols[2]:
            safe = getattr(output, 'safe_to_execute', False)
            safety_color = '#10b981' if safe else '#ef4444'
            safety_text = 'SAFE' if safe else 'BLOCKED'
            st.markdown(f"""
            <div style='text-align: center; padding: 1rem; background: {safety_color}10; 
                        border-radius: 0.5rem; border-left: 4px solid {safety_color}'>
                <div style='font-size: 0.8rem; color: {safety_color};'>SAFETY</div>
                <div style='font-size: 1.2rem; font-weight: bold; color: {safety_color};'>
                    {safety_text}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with meta_cols[3]:
            dialect = getattr(output, 'dialect', 'mysql')
            st.metric("Dialect", dialect.upper())
        
        with meta_cols[4]:
            warnings = len(getattr(output, 'warnings', []))
            warning_color = '#ef4444' if warnings > 0 else '#6b7280'
            st.markdown(f"""
            <div style='text-align: center; padding: 1rem; background: {warning_color}10; 
                        border-radius: 0.5rem; border-left: 4px solid {warning_color}'>
                <div style='font-size: 0.8rem; color: {warning_color};'>WARNINGS</div>
                <div style='font-size: 1.2rem; font-weight: bold; color: {warning_color};'>
                    {warnings}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Explanation and warnings
        if getattr(output, 'explain_text', None):
            st.info(f"AI Explanation: {output.explain_text}")
        
        if getattr(output, 'warnings', []):
            for warning in output.warnings:
                st.warning(f"Warning: {warning}")
        
        if getattr(output, 'errors', []):
            for error in output.errors:
                st.error(f"Error: {error}")
        
        # Execute SQL if safe and not dry run
        if output.sql and getattr(output, 'safe_to_execute', False) and not dry_run:
            execute_sql_query(output, nl_query)

def execute_sqlite_query_thread_safe(sql: str, safe_to_execute: bool, is_destructive: bool):
    """Execute SQLite query using thread-safe connection manager"""
    if not safe_to_execute:
        return type('obj', (object,), {
            'status': 'blocked',
            'rows_affected': 0,
            'data': None,
            'columns': None,
            'execution_time_ms': 0.0,
            'query_hash': 'blocked',
            'timestamp': datetime.now().isoformat(),
            'error_message': 'Query blocked due to safety concerns',
            'warnings': ['Query did not pass safety validation']
        })()
    
    from datetime import datetime
    start_time = datetime.now()
    query_hash = hashlib.md5(sql.encode()).hexdigest()[:12]
    
    try:
        # Get database file path
        if hasattr(st.session_state.sam, 'database_file'):
            db_file = st.session_state.sam.database_file
        else:
            db_file = "database.db"  # default fallback
        
        # Use thread-safe connection
        with ThreadSafeSQLiteConnection.connection(db_file) as conn:
            cursor = conn.cursor()
            
            # Execute the query
            cursor.execute(sql)
            
            # If cursor.description exists, the query returned data
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                data = [dict(zip(columns, row)) for row in rows]
                rows_affected = len(data)
            else:
                # It was a DML (INSERT, UPDATE, DELETE, etc.)
                conn.commit()
                rows_affected = cursor.rowcount
                data = None
                columns = None
            
            cursor.close()
        
        # Calculate execution time
        end_time = datetime.now()
        execution_time_ms = (end_time - start_time).total_seconds() * 1000
        
        return type('obj', (object,), {
            'status': 'success',
            'rows_affected': rows_affected,
            'data': data,
            'columns': columns,
            'execution_time_ms': execution_time_ms,
            'query_hash': query_hash,
            'timestamp': start_time.isoformat(),
            'error_message': None,
            'warnings': []
        })()
        
    except Exception as e:
        end_time = datetime.now()
        execution_time_ms = (end_time - start_time).total_seconds() * 1000
        
        return type('obj', (object,), {
            'status': 'failed',
            'rows_affected': 0,
            'data': None,
            'columns': None,
            'execution_time_ms': execution_time_ms,
            'query_hash': query_hash,
            'timestamp': start_time.isoformat(),
            'error_message': str(e),
            'warnings': ['Execution failed']
        })()

def execute_sql_query(output, nl_query: str):
    """Execute the generated SQL query with proper thread handling"""
    st.markdown("---")
    st.markdown("### Execution Results")
    
    # Determine if destructive
    intent = getattr(output, 'intent', 'select')
    is_destructive = intent in ["insert", "update", "delete", "alter", "create_table", "drop"]
    
    # Execute with progress
    with st.spinner("Executing query..."):
        try:
            # Route based on database type
            db_type = st.session_state.last_connection_type
            
            if db_type == 'sqlite':
                # Use thread-safe SQLite execution
                exec_result = execute_sqlite_query_thread_safe(
                    output.sql, 
                    output.safe_to_execute, 
                    is_destructive
                )
            else:
                # For MySQL/PostgreSQL, use the existing executor
                exec_result = st.session_state.executor.execute_query(
                    output.sql,
                    safe_to_execute=output.safe_to_execute,
                    is_destructive=is_destructive,
                    dry_run=False
                )
            
            # Format and display results
            if db_type == 'sqlite':
                # Convert our thread-safe result to match the expected format
                formatted = {
                    'success': exec_result.status == 'success',
                    'status': exec_result.status,
                    'message': 'Query executed successfully' if exec_result.status == 'success' else exec_result.error_message,
                    'execution_time': f"{exec_result.execution_time_ms:.2f}ms",
                    'rows_affected': exec_result.rows_affected,
                    'has_data': exec_result.data is not None and len(exec_result.data) > 0,
                    'data': exec_result.data,
                    'columns': exec_result.columns,
                    'warnings': exec_result.warnings,
                    'error': exec_result.error_message,
                    'timestamp': exec_result.timestamp,
                    'query_hash': exec_result.query_hash
                }
            else:
                formatted = st.session_state.executor.format_results_for_display(exec_result)
            
            st.session_state.current_results = formatted
            
            display_execution_results(formatted, output, nl_query)
            
        except Exception as e:
            st.error(f"Query execution failed: {str(e)}")

def display_execution_results(formatted: Dict, output, nl_query: str):
    """Display enhanced execution results"""
    # Status and metrics
    if formatted['success']:
        st.success(f"{formatted['message']}")
    else:
        st.error(f"{formatted['message']}")
        if formatted['error']:
            st.error(f"Error Details: {formatted['error']}")
    
    # Execution metrics
    metric_cols = st.columns(4)
    with metric_cols[0]:
        st.metric("Execution Time", formatted['execution_time'])
    with metric_cols[1]:
        st.metric("Rows Affected", formatted['rows_affected'])
    with metric_cols[2]:
        status_color = '#10b981' if formatted['success'] else '#ef4444'
        st.markdown(f"""
        <div style='text-align: center;'>
            <div style='font-size: 0.8rem; color: #6b7280;'>STATUS</div>
            <div style='font-size: 1.2rem; font-weight: bold; color: {status_color};'>
                {formatted['status'].upper()}
            </div>
        </div>
        """, unsafe_allow_html=True)
    with metric_cols[3]:
        st.metric("Timestamp", datetime.now().strftime("%H:%M:%S"))
    
    # Data display
    if formatted['success'] and formatted['has_data'] and formatted['data']:
        display_data_results(formatted)
    
    # Update statistics
    update_execution_stats(formatted, output)
    
    # Add to history
    add_to_query_history(nl_query, output, formatted)

def display_data_results(formatted: Dict):
    """Display data results with enhanced visualization"""
    st.markdown("#### Query Results")
    
    df = pd.DataFrame(formatted['data'])
    
    # Data tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Table View", "Visualization", "Statistics", "Export"])
    
    with tab1:
        st.dataframe(df, use_container_width=True, height=400)
    
    with tab2:
        if st.session_state.user_preferences['enable_visualizations']:
            display_data_visualizations(df)
        else:
            st.info("Enable visualizations in settings to see charts")
    
    with tab3:
        display_data_statistics(df)
    
    with tab4:
        display_export_options(df)

def display_data_visualizations(df: pd.DataFrame):
    """Enhanced data visualization"""
    numeric_cols = df.select_dtypes(include=['number']).columns
    
    if len(numeric_cols) == 0:
        st.info("No numeric columns available for visualization")
        return
    
    viz_col1, viz_col2 = st.columns(2)
    
    with viz_col1:
        chart_type = st.selectbox(
            "Chart Type",
            ["Bar Chart", "Line Chart", "Scatter Plot", "Pie Chart", "Histogram"],
            key="viz_type"
        )
    
    with viz_col2:
        if chart_type in ["Bar Chart", "Line Chart"]:
            x_col = st.selectbox("X-Axis", df.columns)
            y_col = st.selectbox("Y-Axis", numeric_cols)
        elif chart_type == "Scatter Plot":
            x_col = st.selectbox("X-Axis", numeric_cols)
            y_col = st.selectbox("Y-Axis", numeric_cols)
        elif chart_type == "Pie Chart":
            names_col = st.selectbox("Categories", df.columns)
            values_col = st.selectbox("Values", numeric_cols)
        else:  # Histogram
            col = st.selectbox("Column", numeric_cols)
    
    # Generate chart
    try:
        if chart_type == "Bar Chart":
            fig = px.bar(df, x=x_col, y=y_col, title=f"{y_col} by {x_col}")
        elif chart_type == "Line Chart":
            fig = px.line(df, x=x_col, y=y_col, title=f"{y_col} over {x_col}")
        elif chart_type == "Scatter Plot":
            fig = px.scatter(df, x=x_col, y=y_col, title=f"{y_col} vs {x_col}")
        elif chart_type == "Pie Chart":
            fig = px.pie(df, names=names_col, values=values_col, title=f"{values_col} by {names_col}")
        else:  # Histogram
            fig = px.histogram(df, x=col, title=f"Distribution of {col}")
        
        fig.update_layout(template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Chart generation failed: {str(e)}")

def display_data_statistics(df: pd.DataFrame):
    """Display enhanced data statistics"""
    st.markdown("#### Data Statistics")
    
    # Basic stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Rows", len(df))
    with col2:
        st.metric("Total Columns", len(df.columns))
    with col3:
        st.metric("Memory Usage", f"{df.memory_usage(deep=True).sum() / 1024:.1f} KB")
    
    # Detailed statistics for numeric columns
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0:
        st.markdown("##### Numerical Columns Statistics")
        st.dataframe(df[numeric_cols].describe(), use_container_width=True)
    
    # Data quality indicators
    st.markdown("##### Data Quality")
    quality_cols = st.columns(4)
    with quality_cols[0]:
        null_count = df.isnull().sum().sum()
        st.metric("Null Values", null_count)
    with quality_cols[1]:
        duplicate_count = df.duplicated().sum()
        st.metric("Duplicates", duplicate_count)
    with quality_cols[2]:
        complete_rows = len(df) - df.isnull().any(axis=1).sum()
        st.metric("Complete Rows", complete_rows)
    with quality_cols[3]:
        data_types = len(set(df.dtypes))
        st.metric("Data Types", data_types)

def display_export_options(df: pd.DataFrame):
    """Enhanced export options with better error handling"""
    st.markdown("#### Export Data")
    
    export_col1, export_col2, export_col3 = st.columns(3)
    
    with export_col1:
        # CSV Export (always available)
        csv = df.to_csv(index=False)
        st.download_button(
            "Download CSV",
            csv,
            file_name=f"query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with export_col2:
        # JSON Export (always available)
        json_str = df.to_json(orient='records', indent=2)
        st.download_button(
            "Download JSON",
            json_str,
            file_name=f"query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with export_col3:
        # Excel Export (with fallback)
        try:
            # import xlsxwriter for excel export
            import xlsxwriter
            
            @st.cache_data
            def convert_to_excel(df):
                import io
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='QueryResults')
                return buffer.getvalue()
            
            excel_data = convert_to_excel(df)
            st.download_button(
                "Download Excel",
                excel_data,
                file_name=f"query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.ms-excel",
                use_container_width=True
            )
            
        except ImportError:
            # Show disabled button with tooltip
            st.button(
                "Download Excel (Install xlsxwriter)",
                use_container_width=True,
                disabled=True,
                help="Install xlsxwriter package: pip install xlsxwriter"
            )
            st.caption("💡 Run: pip install xlsxwriter")
    
    # Quick copy options
    st.markdown("##### Quick Copy")
    copy_col1, copy_col2 = st.columns(2)
    
    with copy_col1:
        if st.button("Copy as Markdown", use_container_width=True):
            try:
                # Try to copy to clipboard
                st.session_state.clipboard = df.to_markdown()
                st.success("Markdown copied to clipboard!")
            except Exception as e:
                st.error(f"Could not copy to clipboard: {e}")
    
    with copy_col2:
        if st.button("Copy as JSON", use_container_width=True):
            try:
                st.session_state.clipboard = json_str
                st.success("JSON copied to clipboard!")
            except Exception as e:
                st.error(f"Could not copy to clipboard: {e}")

def update_execution_stats(formatted: Dict, output):
    """Update execution statistics"""
    st.session_state.execution_stats['total_queries'] += 1
    
    if formatted['success']:
        st.session_state.execution_stats['successful_queries'] += 1
    else:
        st.session_state.execution_stats['failed_queries'] += 1
    
    # Update average confidence
    confidence = getattr(output, 'confidence', 0)
    current_avg = st.session_state.execution_stats['average_confidence']
    total = st.session_state.execution_stats['total_queries']
    st.session_state.execution_stats['average_confidence'] = (
        (current_avg * (total - 1) + confidence) / total
    )

def add_to_query_history(nl_query: str, output, formatted: Dict):
    """Add query to history with enhanced metadata"""
    history_entry = {
        "timestamp": datetime.now().isoformat(),
        "nl_query": nl_query,
        "sql": output.sql,
        "intent": getattr(output, 'intent', 'unknown'),
        "dialect": getattr(output, 'dialect', 'mysql'),
        "confidence": getattr(output, 'confidence', 0),
        "safe_to_execute": getattr(output, 'safe_to_execute', False),
        "success": formatted['success'],
        "execution_time": formatted['execution_time'],
        "rows_affected": formatted['rows_affected'],
        "has_data": formatted.get('has_data', False),
        "data_sample": formatted.get('data', [])[:3] if formatted.get('data') else []
    }
    
    st.session_state.query_history.append(history_entry)
    
    # Keep only last 50 entries
    if len(st.session_state.query_history) > 50:
        st.session_state.query_history.pop(0)

def display_query_history():
    """Enhanced query history view"""
    st.subheader("Query History")
    
    if not st.session_state.query_history:
        st.info("No query history yet. Execute some queries to see them here!")
        return
    
    # History filters
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_intent = st.selectbox(
            "Filter by Intent",
            ["All"] + list(set(h['intent'] for h in st.session_state.query_history))
        )
    with col2:
        filter_success = st.selectbox(
            "Filter by Status",
            ["All", "Success", "Failed"]
        )
    with col3:
        search_query = st.text_input("Search queries...")
    
    # Filter history
    filtered_history = st.session_state.query_history
    if filter_intent != "All":
        filtered_history = [h for h in filtered_history if h['intent'] == filter_intent]
    if filter_success != "All":
        success_filter = filter_success == "Success"
        filtered_history = [h for h in filtered_history if h['success'] == success_filter]
    if search_query:
        filtered_history = [h for h in filtered_history if search_query.lower() in h['nl_query'].lower()]
    
    # Display history
    for idx, item in enumerate(reversed(filtered_history[-20:])):  # Show last 20
        with st.expander(
            f"Query {len(filtered_history) - idx}: {item['nl_query'][:80]}{'...' if len(item['nl_query']) > 80 else ''}",
            expanded=False
        ):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**Time:** {item['timestamp']}")
                st.markdown(f"**Intent:** `{item['intent']}`")
                st.markdown(f"**Confidence:** {item['confidence']:.0%}")
                st.markdown(f"**Status:** {'Success' if item['success'] else 'Failed'}")
                
                if item['sql']:
                    st.markdown("**Generated SQL:**")
                    st.code(item['sql'], language="sql")
            
            with col2:
                # Quick actions
                if st.button("Re-run", key=f"rerun_{idx}", use_container_width=True):
                    st.info("Re-run functionality would go here")
                
                if st.button("Copy", key=f"copy_{idx}", use_container_width=True):
                    st.session_state.clipboard = item['sql']
                    st.success("SQL copied to clipboard!")
                
                # Status indicator
                status_color = "#10b981" if item['success'] else "#ef4444"
                st.markdown(f"""
                <div style='text-align: center; padding: 0.5rem; background: {status_color}20; 
                            border-radius: 0.5rem; border: 1px solid {status_color}40;'>
                    <div style='color: {status_color}; font-weight: bold;'>
                        {item['execution_time']}
                    </div>
                    <div style='font-size: 0.8rem; color: #6b7280;'>
                        {item['rows_affected']} rows
                    </div>
                </div>
                """, unsafe_allow_html=True)

def display_analytics_dashboard():
    """Enhanced analytics dashboard"""
    st.subheader("Analytics Dashboard")
    
    if not st.session_state.execution_stats['total_queries']:
        st.info("No analytics data yet. Execute some queries to see statistics!")
        return
    
    stats = st.session_state.execution_stats
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Queries", stats['total_queries'])
    with col2:
        success_rate = (stats['successful_queries'] / stats['total_queries']) * 100
        st.metric("Success Rate", f"{success_rate:.1f}%")
    with col3:
        st.metric("Failed Queries", stats['failed_queries'])
    with col4:
        st.metric("Avg Confidence", f"{stats['average_confidence']:.0%}")
    
    # Charts
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        # Success distribution
        if stats['total_queries'] > 0:
            fig = go.Figure(data=[go.Pie(
                labels=['Successful', 'Failed'],
                values=[stats['successful_queries'], stats['failed_queries']],
                hole=0.4,
                marker_colors=['#10b981', '#ef4444']
            )])
            fig.update_layout(
                title="Query Success Distribution",
                showlegend=True,
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with chart_col2:
        # Intent distribution
        if st.session_state.query_history:
            intents = [h['intent'] for h in st.session_state.query_history]
            intent_counts = pd.Series(intents).value_counts()
            
            fig = go.Figure(data=[go.Bar(
                x=intent_counts.index,
                y=intent_counts.values,
                marker_color=['#667eea', '#764ba2', '#f093fb', '#f5576c']
            )])
            fig.update_layout(
                title="Query Intent Distribution",
                height=300,
                xaxis_title="Intent",
                yaxis_title="Count"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Recent activity timeline
    st.markdown("### Recent Activity")
    if st.session_state.query_history:
        recent_queries = st.session_state.query_history[-10:]  # Last 10 queries
        
        for query in reversed(recent_queries):
            time_ago = datetime.now() - datetime.fromisoformat(query['timestamp'])
            hours_ago = time_ago.total_seconds() / 3600
            
            if hours_ago < 1:
                time_text = f"{int(time_ago.total_seconds() / 60)} minutes ago"
            elif hours_ago < 24:
                time_text = f"{int(hours_ago)} hours ago"
            else:
                time_text = f"{int(hours_ago / 24)} days ago"
            
            status_icon = "✓" if query['success'] else "✗"
            st.markdown(f"""
            <div class='glass-card'>
                <div style='display: flex; justify-content: between; align-items: start;'>
                    <div style='flex: 1;'>
                        <strong>{status_icon} {query['nl_query'][:100]}{'...' if len(query['nl_query']) > 100 else ''}</strong>
                        <div style='font-size: 0.8rem; color: #6b7280; margin-top: 0.5rem;'>
                            {time_text} • {query['intent']} • {query['confidence']:.0%} confidence
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

def save_current_query(nl_query: str):
    """Save current query to session state"""
    st.success("Query saved! (In a real app, this would persist)")

def display_welcome_screen():
    """Clean welcome screen that matches the sidebar"""
    
    st.markdown("""
    <div style='
        text-align: center; 
        padding: 3rem 2rem; 
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 1rem;
        margin: 2rem 0;
        color: white;
    '>
        <h1 style='font-size: 3rem; margin-bottom: 1rem;'>Welcome to AetherDB</h1>
        <p style='font-size: 1.3rem; margin: 0; opacity: 0.9;'>
            Import SQL files or connect to databases to start querying with AI
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Simple instructions
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🚀 Get Started")
        st.markdown("""
        **Option 1: Import SQL File**
        - Upload SQL file in sidebar
        - Click 'Create Database & Start Querying'
        - Start asking questions immediately
        
        **Option 2: Connect to Database**  
        - Expand 'Connect to Existing Database'
        - Enter your connection details
        - Click connect
        """)
    
    with col2:
        st.markdown("### 💬 How to Query")
        st.markdown("""
        After connecting, go to the **Query** tab and:
        
        1. Describe what you want in plain English
        2. The AI generates optimized SQL
        3. Review and execute the query
        4. See results with charts and analytics
        
        **Example questions:**
        - "Show customers from California"
        - "Total sales last month"
        - "Products with highest revenue"
        """)
    
    # Call to action
    st.markdown("---")
    st.info("💡 **Ready to start?** Use the sidebar to upload a SQL file or connect to your database!")

def main():
    """Enhanced main application with optional debug features"""
    try:
        initialize_session_state()
        display_enhanced_header()
        
        # Sidebar
        sidebar_database_connection()

        debug_schema_info()

          # Temporary debug - remove after testing
        debug_database_status()

        # Temporary debug - remove after testing
        debug_table_info()

        # Main content with tabs
        if st.session_state.connected:
            tab1, tab2, tab3, tab4 = st.tabs([
                "Query", 
                "Schema", 
                "History", 
                "Analytics"
            ])
            
            with tab1:
                display_query_interface()
            
            with tab2:
                display_schema_explorer()
            
            with tab3:
                display_query_history()
            
            with tab4:
                display_analytics_dashboard()
        
        else:
            # Welcome screen for disconnected state
            display_welcome_screen()
            
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        # Don't do aggressive cleanup in main function as it can cause issues
              
if __name__ == "__main__":
    main()