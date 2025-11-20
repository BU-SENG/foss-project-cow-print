#!/usr/bin/env python3

"""
Aether DB - Enhanced Streamlit Frontend

A beautiful, intuitive interface for natural language to SQL conversion
with real-time database execution and visualization.

Enhanced with better UX, real-time feedback, and improved integration.
"""
import threading
from contextlib import contextmanager
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import sys
import time # Re-added for explicit time usage in FileDatabaseManager and connect_to_database
import tempfile
import sqlite3
import re
from typing import Optional
from dotenv import load_dotenv

class ThreadSafeSQLiteConnection:
    """Thread-safe SQLite connection manager"""
    _local = threading.local()
    _lock = threading.Lock()
    
    @classmethod
    def get_connection(cls, db_file):
        if not hasattr(cls._local, 'connections'):
            cls._local.connections = {}
        
        if db_file not in cls._local.connections:
            # Removed import sqlite3 as it is imported globally
            cls._local.connections[db_file] = sqlite3.connect(
                db_file, 
                check_same_thread=False
            )
        
        return cls._local.connections[db_file]
    
    @classmethod
    # Used from contextlib import contextmanager, so no need for explicit import at top
    @contextmanager
    def connection(cls, db_file):
        conn = cls.get_connection(db_file)
        try:
            yield conn
        # Replaced bare except: with except Exception:
        except Exception:
            conn.rollback()
            raise
        finally:
            pass

    @classmethod
    def close_connection(cls, db_file):
        """Close a specific connection"""
        if hasattr(cls._local, 'connections') and db_file in cls._local.connections:
            cls._local.connections[db_file].close()
            del cls._local.connections[db_file]
# Add current directory to path to import local modules
sys.path.append(os.path.dirname(__file__))

# Load environment variables from .env
load_dotenv()
# Load environment variables from .env
# load_dotenv() # Removed redundant call

# Get the API key from environment
api_key = os.getenv("GEMINI_API_KEY")

# Safe debug check without exposing sensitive info
if api_key:
    print("Environment configuration loaded successfully ✅")
else:
    print("AI service not configured")
    MODULES_AVAILABLE = True
    GEMINI_API_VALID = False


# Import our modules
try:
    from schema_awareness import SchemaAwarenessModule
    from sqlm import GeminiReasoner, CommandPayload
    from db_executor import DatabaseExecutor
    
    # Test Gemini API securely
    import google.generativeai as genai
    
    if api_key:
        try:
            genai.configure(api_key=api_key)
            models = list(genai.list_models())
            gemini_models = [m for m in models if 'gemini' in m.name]
            print(f"✅ AI service connected successfully! Available models: {len(gemini_models)}")
            MODULES_AVAILABLE = True
            GEMINI_API_VALID = True
        # Replaced 'except Exception as e:' with 'except Exception:' as 'e' was unused
        except Exception:
            print("❌ AI service connection failed: Check API key configuration")
            MODULES_AVAILABLE = True
            GEMINI_API_VALID = False
    else:
        print("❌ AI service not configured")
        MODULES_AVAILABLE = True
        GEMINI_API_VALID = False
        
# Replaced 'except ImportError as e:' with 'except ImportError:' as 'e' was unused
except ImportError:
    print("❌ Module import error")
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

def sanitize_file_path(file_path: str) -> Optional[str]:
    """
    Sanitize file path to prevent path traversal attacks and other vulnerabilities
    """
    if not file_path or not isinstance(file_path, str):
        return None
    
    normalized_path = os.path.normpath(file_path)
    
    if '..' in normalized_path.split(os.sep):
        print(f"Security: Blocked path traversal attempt: {file_path}")
        return None
    
    try:
        abs_path = os.path.abspath(normalized_path)
        current_dir = os.path.abspath(os.getcwd())
        
        # Merge nested if conditions
        if not abs_path.startswith(current_dir):
            print(f"Security: Blocked path outside working directory: {file_path}")
            return None
        
        allowed_extensions = ['.db', '.sqlite', '.sqlite3', '.db3', '']
        file_ext = os.path.splitext(abs_path)[1].lower()
        if file_ext not in allowed_extensions:
            print(f"Security: Blocked invalid file extension: {file_ext}")
            return None
            
    # Replaced 'except Exception as e:' with 'except Exception:' as 'e' was unused
    except Exception:
        print("Security: Path validation error")
        return None
    
    return abs_path

def is_valid_sqlite_file(file_path: str) -> bool:
    """
    Validate that the file is a legitimate SQLite database file
    """
    try:
        if not os.path.isfile(file_path):
            return False
        
        file_size = os.path.getsize(file_path)
        if file_size > 100 * 1024 * 1024:
            print("Security: File too large")
            return False
        
        sqlite_header = b'SQLite format 3\x00'
        with open(file_path, 'rb') as f:
            header = f.read(16)
        
        if header == sqlite_header:
            return True
        
        print("Security: Invalid SQLite file header")
        return False
            
    # Replaced 'except Exception as e:' with 'except Exception:' as 'e' was unused
    except Exception:
        print("Security: SQLite file validation error")
        return False

def display_enhanced_header():
    """Display modern app header with import status"""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
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

def initialize_reasoner(schema_text: str) -> Optional[GeminiReasoner]:
    """Initialize the Gemini Reasoner with proper error handling"""
    try:
        return GeminiReasoner(schema_snapshot=schema_text, api_key=api_key)
    # Replaced 'except Exception as e:' with 'except Exception as _:' as 'e' was unused
    except Exception as _:
        print(f"Error initializing reasoner: {_}")
        return None

def sidebar_database_connection():
    """Clean sidebar with single SQL import option"""
    st.sidebar.title("AetherDB")
    
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
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Quick Start")
    
    sql_file = st.sidebar.file_uploader(
        "Upload SQL File", 
        type=['sql', 'txt'],
        help="Upload SQL file to create instant queryable database",
        key="main_sql_import"
    )
    
    if sql_file is not None and st.sidebar.button("Create Database & Start Querying", 
                                                   use_container_width=True, 
                                                   type="primary"):
        execute_uploaded_sql_file(sql_file, 'sqlite')
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Database Connection")
    
    if not st.session_state.connected:
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
                
                if connect_btn := st.button(
                    "Connect to SQLite", 
                    use_container_width=True,
                    type="secondary"
                ):
                    sanitized_path = sanitize_file_path(db_file)
                    if sanitized_path and os.path.exists(sanitized_path):
                        if is_valid_sqlite_file(sanitized_path):
                            connect_to_database(db_type.lower(), database=sanitized_path)
                        else:
                            st.sidebar.error("Invalid SQLite database file")
                    else:
                        st.sidebar.error("Invalid database file path or file not found")
            
            else:
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
                    # Local variable 'password' is assigned to but never used
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
        st.sidebar.success("Database Connected")
        
        db_name = "Unknown Database"
        db_type = "Unknown"
        table_count = 0
        
        if st.session_state.working_with_file_db and st.session_state.current_file_db:
            db_info = st.session_state.file_db_manager.get_current_db_info()
            if db_info:
                db_name = db_info['name']
                db_type = "SQLITE"
                table_count = len(db_info['tables'])
        
        elif (st.session_state.last_connection_type == 'sqlite' and 
              st.session_state.sam and 
              hasattr(st.session_state.sam, 'database_file')):
            db_path = st.session_state.sam.database_file
            db_name = os.path.basename(db_path)
            db_type = "SQLITE"
            try:
                conn = sqlite3.connect(db_path, check_same_thread=False)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                table_count = len(tables)
                conn.close()
            # Replaced 'except Exception:' with 'except Exception:'
            except Exception:
                table_count = 0
        
        elif (st.session_state.sam and 
              hasattr(st.session_state.sam, 'current_metadata')):
            metadata = st.session_state.sam.current_metadata
            db_name = getattr(metadata, 'database_name', 'Connected Database')
            db_type = getattr(metadata, 'database_type', 'Unknown').upper()
            table_count = getattr(metadata, 'table_count', 0)
        
        st.sidebar.markdown("""
        <div style='
            background: rgba(255,255,255,0.1); 
            padding: 1.5rem; 
            border-radius: 0.75rem;
            border: 1px solid rgba(255,255,255,0.2);
            margin: 1rem 0;
        '>
        """, unsafe_allow_html=True)
        
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
        
        st.sidebar.markdown("### Management")
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("Refresh Schema", use_container_width=True):
                refresh_schema()
        with col2:
            if st.button("Force Table Detect", use_container_width=True):
                if st.session_state.reasoner and hasattr(st.session_state.reasoner, 'get_actual_tables'):
                    st.session_state.reasoner.table_names = st.session_state.reasoner.get_actual_tables()
                    st.sidebar.success("Table detection forced!")
                st.rerun()
        
        if st.sidebar.button("Disconnect", use_container_width=True, type="secondary"):
            disconnect_database()
    
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

def refresh_schema():
    """Refresh the database schema"""
    if st.session_state.sam:
        try:
            st.session_state.sam.generate_full_schema()
            st.sidebar.success("Schema refreshed successfully!")
            st.rerun()
        # Replaced 'except Exception as e:' with 'except Exception as _:' as 'e' was unused
        except Exception as _:
            st.sidebar.error(f"Failed to refresh schema: {_}")

def generate_visualizations(df: pd.DataFrame):
    """
    Dynamically generate visualization options based on the dataframe content.
    """
    if df.empty or len(df.columns) < 2:
        return

    st.markdown("---")
    st.header("🎨 Visualizations")

    # Identify column types
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'string', 'category']).columns.tolist()
    all_cols = df.columns.tolist()

    # Smart Defaults
    default_x = all_cols[0]
    default_y = numeric_cols[0] if numeric_cols else all_cols[-1]
    
    # Visualization Controls
    with st.container():
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            chart_type = st.selectbox(
                "Chart Type",
                ["Bar Chart", "Line Chart", "Scatter Plot", "Pie Chart", "Area Chart", "Histogram"],
                index=0
            )
        
        with col2:
            x_axis = st.selectbox("X Axis", all_cols, index=all_cols.index(default_x) if default_x in all_cols else 0)
            
        with col3:
            # Pie charts don't strictly need a Y axis (can count), but usually map a value
            if chart_type != "Histogram":
                y_choices = numeric_cols or all_cols
                default_y_index = y_choices.index(default_y) if default_y in y_choices else 0
                y_axis = st.selectbox("Y Axis (Value/Metric)", y_choices, index=default_y_index)
            else:
                y_axis = None

        # Color/Group by option
        use_color = st.checkbox("Group by Color (Legend)", value=False)
        if use_color:
            color_col = st.selectbox("Select Grouping Column", categorical_cols or all_cols)
        else:
            color_col = None

    # Generate Plotly Charts
    try:
        fig = None
        if chart_type == "Bar Chart":
            fig = px.bar(df, x=x_axis, y=y_axis, color=color_col, title=f"{y_axis} by {x_axis}", template="plotly_dark")
        
        elif chart_type == "Line Chart":
            fig = px.line(df, x=x_axis, y=y_axis, color=color_col, markers=True, title=f"{y_axis} over {x_axis}", template="plotly_dark")
        
        elif chart_type == "Scatter Plot":
            fig = px.scatter(df, x=x_axis, y=y_axis, color=color_col, title=f"{y_axis} vs {x_axis}", template="plotly_dark")
        
        elif chart_type == "Pie Chart":
            fig = px.pie(df, names=x_axis, values=y_axis, title=f"Distribution of {y_axis} by {x_axis}", template="plotly_dark")
            
        elif chart_type == "Area Chart":
            fig = px.area(df, x=x_axis, y=y_axis, color=color_col, title=f"{y_axis} by {x_axis}", template="plotly_dark")

        elif chart_type == "Histogram":
            fig = px.histogram(df, x=x_axis, color=color_col, title=f"Distribution of {x_axis}", template="plotly_dark")

        if fig:
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white")
            )
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.warning(f"Could not generate {chart_type} with selected data. Try changing the axes. (Error: {str(e)})")
        
def switch_to_main_database():
    """Switch back to main database from file database"""
    if st.session_state.working_with_file_db and st.session_state.current_file_db:
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
        # Used named expression to simplify assignment and conditional
        if not (db_name := db_name or f"imported_db_{int(time.time())}"):
            db_name = f"imported_db_{int(time.time())}"
        
        db_name = re.sub(r'[^a-zA-Z0-9_-]', '', db_name) or "imported_db"
        
        temp_dir = tempfile.gettempdir()
        temp_db_path = os.path.join(temp_dir, f"{db_name}.db")
        
        temp_db_path = sanitize_file_path(temp_db_path)
        if not temp_db_path:
            print("Security: Invalid temporary database path")
            return None
        
        try:
            conn = sqlite3.connect(temp_db_path, check_same_thread=False)
            cursor = conn.cursor()
            
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            executed_count = 0
            for statement in statements:
                if statement and statement.strip():
                    try:
                        cursor.execute(statement)
                        executed_count += 1
                    # Replaced 'except Exception as e:' with 'except Exception as _:' as 'e' was unused
                    except Exception as _:
                        if "no such table" not in str(_).lower():
                            print("Info: Could not execute statement: Schema mismatch")
            
            conn.commit()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            
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
            
        # Replaced 'except Exception:' with 'except Exception as _:'
        except Exception as _:
            print("Error creating temp database: Configuration error")
            if os.path.exists(temp_db_path):
                from contextlib import suppress
                with suppress(Exception):
                    os.remove(temp_db_path)
            return None
    
    def get_current_db_info(self):
        """Get info about current file database"""
        if self.current_file_db and self.current_file_db in self.temp_databases:
            return self.temp_databases[self.current_file_db]
        return None

    def cleanup_temp_database(self, db_name: str):
        """Clean up a temporary database file"""
        if db_name not in self.temp_databases:
            return
        
        db_info = self.temp_databases[db_name]
        try:
            ThreadSafeSQLiteConnection.close_connection(db_info['path'])
            if os.path.exists(db_info['path']):
                os.remove(db_info['path'])
        # Replaced 'except Exception:' with 'except Exception:'
        except Exception:
            print("Warning: Could not clean up temp database")
        
        del self.temp_databases[db_name]
        
        if self.current_file_db == db_name:
            self.current_file_db = None

    def cleanup_all(self):
        """Clean up all temporary databases"""
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
        'file_db_manager': FileDatabaseManager(),
        'working_with_file_db': False,
        'current_file_db': None,
        # --- NEW STATE VARIABLES ---
        'generated_sql': "",
        'query_results': None,
        'last_nl_query': ""
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def execute_uploaded_sql_file(sql_file, db_type, **conn_params):
    """Execute SQL from uploaded file and create queryable database"""
    try:
        sql_content = sql_file.getvalue().decode("utf-8")
        
        db_name = f"imported_{int(time.time())}"
        # Used named expression to simplify assignment and conditional
        if db_id := st.session_state.file_db_manager.create_temp_database_from_sql(sql_content, db_name):
            db_info = st.session_state.file_db_manager.get_current_db_info()
            
            sanitized_path = sanitize_file_path(db_info['path'])
            if not sanitized_path:
                st.sidebar.error("Security: Invalid database path")
                return
                
            if connect_to_database('sqlite', database=sanitized_path):
                st.session_state.working_with_file_db = True
                st.session_state.current_file_db = db_id
                
                st.sidebar.success("Database created from SQL file!")
                st.sidebar.info(f"Found {len(db_info['tables'])} tables")
                
                refresh_schema()
                
                if st.session_state.sam and hasattr(st.session_state.sam, 'schema_file'):
                    try:
                        with open(st.session_state.sam.schema_file, 'r') as f:
                            schema_text = f.read()
                        if st.session_state.reasoner and hasattr(st.session_state.reasoner, 'update_schema'):
                            st.session_state.reasoner.update_schema(schema_text)
                    # Replaced 'except Exception as e:' with 'except Exception:' as 'e' was unused
                    except Exception:
                        print("Warning: Could not update reasoner schema")
                
                st.session_state.active_tab = 'query'
                st.rerun()
            else:
                st.sidebar.error("Failed to connect to created database")
        else:
            st.sidebar.error("Failed to create database from SQL file")
                
    # Replaced 'except Exception as e:' with 'except Exception:' as 'e' was unused
    except Exception:
        st.sidebar.error("Failed to process SQL file")

def connect_to_database(db_type: str, **conn_params):
    """Database connection handler with proper thread handling and path sanitization"""
    with st.spinner("Connecting to database..."):
        try:
            if not MODULES_AVAILABLE:
                st.sidebar.error("Required modules not available")
                return False
            
            sam = SchemaAwarenessModule()
            
            if db_type == 'sqlite' and 'database' in conn_params:
                db_file = conn_params['database']
                
                if not os.path.exists(db_file):
                    st.sidebar.error(f"Database file not found: {os.path.basename(db_file)}")
                    return False
            
            if sam.connect_database(db_type, **conn_params):
                st.session_state.sam = sam
                st.session_state.connected = True
                st.session_state.last_connection_type = db_type
                
                try:
                    with open(sam.schema_file, 'r') as f:
                        schema_text = f.read()
                    
                    st.session_state.reasoner = initialize_reasoner(schema_text)
                    
                    st.session_state.executor = DatabaseExecutor(sam.connection, db_type)
                    
                    st.sidebar.success("✅ Database connected successfully!")
                    return True
                    
                # Replaced 'except Exception as e:' with 'except Exception as _:' as 'e' was unused
                except Exception as _:
                    st.sidebar.error("Error initializing AI components")
                    st.session_state.connected = True
                    st.sidebar.success("✅ Database connected (AI features limited)")
                    return True
            else:
                st.sidebar.error("❌ Database connection failed")
                return False
                
        # Replaced 'except Exception as e:' with 'except Exception as _:' as 'e' was unused
        except Exception as _:
            st.sidebar.error("❌ Connection error")
            return False
                 
def disconnect_database():
    """Enhanced database disconnection"""
    try:
        if st.session_state.connected:
            if st.session_state.working_with_file_db and st.session_state.current_file_db:
                db_name = st.session_state.current_file_db
                if hasattr(st.session_state, 'file_db_manager'):
                    st.session_state.file_db_manager.cleanup_temp_database(db_name)
            
            if st.session_state.sam:
                try:
                    st.session_state.sam.close()
                # Replaced 'except Exception as e:' with 'except Exception:' as 'e' was unused
                except Exception:
                    print("Warning: Error closing SAM")
            
            st.session_state.connected = False
            st.session_state.sam = None
            st.session_state.reasoner = None
            st.session_state.executor = None
            st.session_state.current_results = None
            st.session_state.working_with_file_db = False
            st.session_state.current_file_db = None
            st.session_state.query_results = None # Clean up results
            
            st.sidebar.success("Disconnected from database")
            time.sleep(1)
            st.rerun()
        else:
            st.sidebar.info("Not connected to any database")
            
    # Replaced 'except Exception as e:' with 'except Exception:' as 'e' was unused
    except Exception:
        st.sidebar.error("Error during disconnection")

def display_sql_editor_and_execution():
    """Display SQL editor with refinement and execution controls"""
    if st.session_state.generated_sql:
        st.subheader("📝 SQL Editor")
        
        # Refinement Section (Collapsible)
        with st.expander("✨ AI Refinement (Optional)"):
            refine_instruction = st.text_input("How should the SQL be modified?", placeholder="e.g., Filter by date > 2023")
            if st.button("Refine Code") and st.session_state.generated_sql and refine_instruction:
                with st.spinner("Refining..."):
                    # Heuristic prompt construction for refinement
                    refine_prompt = f"Existing SQL: {st.session_state.generated_sql}\n\nModification request: {refine_instruction}\n\nReturn only the updated SQL."
                    payload = CommandPayload(
                        intent="query",
                        raw_nl=refine_prompt,
                        dialect=st.session_state.last_connection_type or "sqlite"
                    )
                    output = st.session_state.reasoner.generate(payload)
                    st.session_state.generated_sql = output.sql
                    st.rerun()

        # The SQL Editor
        # We use a key to sync this widget with session state, but we also want to allow manual edits.
        sql_query = st.text_area(
            "SQL Query", 
            value=st.session_state.generated_sql, 
            height=150,
            key="sql_editor_widget"
        )
        
        # Sync manual edits back to session state
        st.session_state.generated_sql = sql_query

        # Execution
        col_exec1, col_exec2, col_exec3 = st.columns([1, 1, 3])
        with col_exec1:
            execute_btn = st.button("🚀 Run Query", type="primary", use_container_width=True)
        with col_exec2:
            allow_destructive = st.checkbox("Allow Changes", value=False, help="Enable INSERT/UPDATE/DELETE")

        if execute_btn:
            with st.spinner("Executing..."):
                try:
                    is_destructive = not sql_query.strip().lower().startswith("select")
                    if is_destructive and not allow_destructive:
                        st.warning("Destructive operations (INSERT/UPDATE/DELETE) are disabled. Enable 'Allow Changes' to proceed.")
                    else:
                        result = st.session_state.executor.execute_query(
                            sql_query,
                            safe_to_execute=True,
                            is_destructive=is_destructive and allow_destructive
                        )
                    st.session_state.query_results = st.session_state.executor.format_results_for_display(result)
                except Exception as e:
                    st.error(f"Execution error: {e}")

def display_query_results():
    """Display query results and visualization"""
    if st.session_state.query_results:
        formatted = st.session_state.query_results
        
        st.markdown("---")
        st.subheader("📊 Results")
        
        if formatted['success']:
            st.success(formatted['message'])
            if formatted['has_data']:
                df = pd.DataFrame(formatted['data'])
                st.dataframe(df, use_container_width=True)
                
                # Visualization (Updates here won't lose state because query_results is in session_state)
                generate_visualizations(df)
                
                # Download
                csv = df.to_csv(index=False)
                st.download_button("📥 Download CSV", csv, "results.csv", "text/csv")
        else:
            st.error(formatted['message'])
            if formatted.get('error'):
                st.code(formatted['error'])

def display_query_interface():
    """Display the main query interface"""
    st.header("🔍 Natural Language Query")
    
    # Initialize session state for this page if not present
    if "generated_sql" not in st.session_state:
        st.session_state.generated_sql = ""
    if "query_results" not in st.session_state:
        st.session_state.query_results = None
    if "last_nl_query" not in st.session_state:
        st.session_state.last_nl_query = ""

    # 1. NL Input
    nl_query = st.text_area(
        "Enter your question:", 
        value=st.session_state.last_nl_query,
        placeholder="e.g., Show me top 10 users...", 
        height=70
    )
    
    col_gen1, col_gen2 = st.columns([1, 4])
    with col_gen1:
        generate_btn = st.button("🤖 Generate SQL", type="primary", use_container_width=True)
    
    # Logic: Generate SQL
    if generate_btn and nl_query:
        st.session_state.last_nl_query = nl_query
        with st.spinner("Translating to SQL..."):
            try:
                payload = CommandPayload(
                    intent="select",
                    raw_nl=nl_query,
                    dialect=st.session_state.last_connection_type or "sqlite",
                )
                output = st.session_state.reasoner.generate(payload)
                st.session_state.generated_sql = output.sql or "-- No SQL generated"
                # Clear previous results when new SQL is generated
                st.session_state.query_results = None 
                st.rerun()
            except Exception as e:
                st.error(f"Generation failed: {e}")

    # 2. SQL Editor & Refinement
    display_sql_editor_and_execution()

    # 3. Results & Visualization (Persistent)
    display_query_results()

def display_schema_explorer():
    """Display schema exploration interface"""
    st.header("📋 Database Schema")
    
    if st.session_state.sam:
        tables = st.session_state.sam.get_tables()
        
        if tables:
            st.success(f"Found {len(tables)} tables")
            
            for table in tables:
                with st.expander(f"📊 Table: {table}"):
                    try:
                        schema = st.session_state.sam._get_table_schema(table)
                        
                        st.markdown("**Columns:**")
                        col_data = [
                            {
                                "Name": col['name'],
                                "Type": col['type'],
                                "Nullable": "Yes" if col['nullable'] else "No",
                                "Default": col.get('default', 'None')
                            }
                            for col in schema.columns
                        ]
                        
                        if col_data:
                            st.table(pd.DataFrame(col_data))
                        
                        if schema.primary_keys:
                            st.markdown("**Primary Keys:** " + ", ".join(schema.primary_keys))
                        
                        if schema.foreign_keys:
                            st.markdown("**Foreign Keys:**")
                            for fk in schema.foreign_keys:
                                # Local variable 'fk' is assigned to but never used
                                st.write(f"- {fk['column']} → {fk['references_table']}.{fk['references_column']}")
                        
                        if schema.row_count is not None:
                            st.metric("Row Count", schema.row_count)
                    
                    # Replaced 'except Exception as e:' with 'except Exception as _:' as 'e' was unused
                    except Exception as _:
                        st.error(f"Error loading schema: {_}")
        else:
            st.warning("No tables found in database")
    else:
        st.info("Connect to a database to view schema")

def display_query_history():
    """Display query execution history"""
    st.header("📜 Query History")
    
    if st.session_state.executor:
        history = st.session_state.executor.get_execution_history(limit=20)
        
        if history:
            for i, entry in enumerate(reversed(history)):
                with st.expander(f"Query {len(history) - i} - {entry['status']} - {entry['timestamp']}"):
                    # --- FIX START --- 
                    # Use .get() to handle missing key and format the ms value
                    exec_time_ms = entry.get('execution_time_ms', 0)
                    st.markdown(f"**Execution Time:** {exec_time_ms:.2f}ms")
                    # --- FIX END ---
                    
                    st.markdown("**Rows Affected:** " + str(entry['rows_affected']))
                    
                    if entry.get('error'):
                        st.error(entry['error'])
                    
                    if entry.get('warnings'):
                        st.warning(", ".join(entry['warnings']))
        else:
            st.info("No query history yet")
    else:
        st.info("Connect to a database to view history")
        
def display_query_performance_charts(history):
    """Display query performance charts from execution history"""
    try:
        df = pd.DataFrame(history)
        
        if 'execution_time_ms' in df.columns:
            fig = px.line(
                df,
                x=df.index,
                y='execution_time_ms',
                title='Query Execution Time Trend',
                labels={'execution_time_ms': 'Time (ms)', 'index': 'Query Number'}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        if 'status' in df.columns:
            status_counts = df['status'].value_counts()
            fig2 = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title='Query Status Distribution'
            )
            st.plotly_chart(fig2, use_container_width=True)
    except Exception:
        st.error("Error displaying performance charts")

def display_analytics_dashboard():
    """Display analytics dashboard with performance metrics"""
    st.header("📈 Analytics Dashboard")
    
    if st.session_state.executor:
        # --- FIX START ---
        # We use a large number (10000) instead of None to avoid the TypeError
        history = st.session_state.executor.get_execution_history(limit=10000)
        
        total_executions = len(history)
        
        # Count blocked queries
        blocked = len([entry for entry in history if entry.get('status') == 'blocked'])
        
        stats = {
            'total_executions': total_executions,
            'blocked': blocked
        }
        # --- FIX END ---
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Total Queries", stats.get('total_executions', 0))
        
        with col2:
            st.metric("Blocked Queries", stats.get('blocked', 0))
        
        if stats.get('total_executions', 0) > 0:
            st.markdown("### 📊 Query Performance")
            
            if history:
                display_query_performance_charts(history)
    else:
        st.info("Connect to a database to view analytics")
        
def display_welcome_screen():
    """Display welcome screen when not connected"""
    st.markdown("""
    <div style='text-align: center; padding: 3rem 0;'>
        <h2 style='color: white;'>Welcome to AetherDB! 🚀</h2>
        <p style='color: rgba(255,255,255,0.8); font-size: 1.2rem;'>
            Get started by connecting to a database or uploading a SQL file
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        ### Quick Start Guide
        
        1. **Upload SQL File** 📁
           - Click "Upload SQL File" in the sidebar
           - Select your .sql file
           - Click "Create Database & Start Querying"
        
        2. **Connect to Database** 🔌
           - Expand "Connect to Existing Database"
           - Choose your database type
           - Enter connection details
           - Click "Connect"
        
        3. **Start Querying** 💬
           - Type natural language questions
           - AI will generate SQL
           - Execute and view results
        
        ### Features
        
        ✅ Natural language to SQL translation  
        ✅ Support for MySQL, PostgreSQL, SQLite  
        ✅ Schema exploration and visualization  
        ✅ Query history and analytics  
        ✅ Safe execution with validation  
        """)

def debug_database_status():
    """Debug function to show current database connection status"""
    if st.session_state.get('connected'):
        with st.expander("🔍 Debug: Database Status", expanded=False):
            st.write("**Connection Status:**", "✅ Connected")
            st.write("**DB Type:**", st.session_state.get('last_connection_type', 'Unknown'))
            st.write("**SAM Available:**", st.session_state.sam is not None)
            st.write("**Reasoner Available:**", st.session_state.reasoner is not None)
            st.write("**Executor Available:**", st.session_state.executor is not None)
            st.write("**Working with File DB:**", st.session_state.get('working_with_file_db', False))
            
            if st.session_state.sam:
                tables = st.session_state.sam.get_tables()
                st.write("**Tables Found:**", len(tables))
                if tables:
                    st.write("**Table Names:**", ", ".join(tables))

def debug_table_info():
    """Debug function to show table information"""
    if st.session_state.get('connected') and st.session_state.sam:
        with st.expander("🔍 Debug: Table Information", expanded=False):
            tables = st.session_state.sam.get_tables()
            st.write(f"**Total Tables:** {len(tables)}")
            
            for table in tables:
                try:
                    schema = st.session_state.sam._get_table_schema(table)
                    st.write(f"**{table}:** {len(schema.columns)} columns, {schema.row_count} rows")
                # Replaced 'except Exception as e:' with 'except Exception as _:' as 'e' was unused
                except Exception as _:
                    st.write(f"**{table}:** Error loading - {_}")

def debug_schema_info():
    """Debug function to show schema file information"""
    if st.session_state.get('connected') and st.session_state.sam:
        with st.expander("🔍 Debug: Schema File", expanded=False):
            schema_file = st.session_state.sam.schema_file
            st.write("**Schema File Path:**", schema_file)
            st.write("**File Exists:**", os.path.exists(schema_file))
            
            if os.path.exists(schema_file):
                try:
                    with open(schema_file, 'r') as f:
                        content = f.read()
                    st.write("**File Size:**", len(content), "characters")
                    st.text_area("**Schema Content (first 1000 chars):**", content[:1000], height=200)
                # Replaced 'except Exception as e:' with 'except Exception as _:' as 'e' was unused
                except Exception as _:
                    st.error(f"Error reading schema file: {_}")

def main():
    """Enhanced main application with optional debug features"""
    try:
        initialize_session_state()
        display_enhanced_header()
        
        sidebar_database_connection()

        #Admin Console Access
        st.sidebar.markdown("---")
        st.sidebar.write(" 🔐 Admin Console")
        if st.sidebar.button("Open Admin Console"):
            st.switch_page("pages/admin_console.py")

        # Debug sections (remove in production)
        if st.session_state.get('connected'):
            debug_schema_info()
            debug_database_status()
            debug_table_info()

        if st.session_state.connected:
            tab1, tab2, tab3, tab4 = st.tabs([
                "🔍 Query", 
                "📋 Schema", 
                "📜 History", 
                "📈 Analytics"
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
            display_welcome_screen()
            
    # Replaced 'except Exception as e:' with 'except Exception as _:' as 'e' was unused
    except Exception as _:
        st.error(f"Application error: {_}")
        import traceback
        st.code(traceback.format_exc())
              
if __name__ == "__main__":
    main()