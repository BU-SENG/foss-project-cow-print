#!/usr/bin/env python3
"""
Aether DB - Streamlit Frontend (Optimized)
"""

from typing import Dict
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Import our modules
from schema_awareness import SchemaAwarenessModule
from sqlm import GeminiReasoner, CommandPayload
from db_executor import DatabaseExecutor

# Page configuration
st.set_page_config(
    page_title="AetherDB - Natural Language to SQL",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS (Optimized - Removed infinite animations to prevent lag)
st.markdown("""
    <style>
    .sql-editor-container {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
    
    textarea[aria-label*="edit"] {
        font-family: 'Courier New', monospace !important;
        font-size: 14px !important;
        background: #1e1e2e !important;
        color: #00ff00 !important;
        border: 2px solid #667eea !important;
    }
    
    /* Static style for primary buttons instead of infinite animation */
    button[kind="primary"] {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
        transition: transform 0.1s;
    }
    button[kind="primary"]:active {
        transform: scale(0.98);
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'connected' not in st.session_state:
    st.session_state.connected = False
if 'sam' not in st.session_state:
    st.session_state.sam = None
if 'reasoner' not in st.session_state:
    st.session_state.reasoner = None
if 'executor' not in st.session_state:
    st.session_state.executor = None
if 'query_history' not in st.session_state:
    st.session_state.query_history = []
if 'current_schema' not in st.session_state:
    st.session_state.current_schema = None
if 'generated_output' not in st.session_state:
    st.session_state.generated_output = None
if 'last_execution_result' not in st.session_state:
    st.session_state.last_execution_result = None

# --- LOGIC HANDLERS (CALLBACKS) ---
# Moving logic here prevents the "Double Rerun" lag

def handle_connect(db_type, **kwargs):
    """Callback to handle database connection"""
    try:
        sam = SchemaAwarenessModule()
        if sam.connect_database(db_type.lower(), **kwargs):
            st.session_state.sam = sam
            st.session_state.connected = True
            
            # Initialize reasoner
            with open(sam.schema_file, 'r') as f:
                schema_text = f.read()
            st.session_state.reasoner = GeminiReasoner(schema_snapshot=schema_text)
            
            # Initialize executor
            st.session_state.executor = DatabaseExecutor(sam.connection, db_type.lower())
            return True
    except Exception as e:
        st.session_state.connection_error = str(e)
        return False

def handle_generate_sql():
    """Callback for generating SQL from NL"""
    nl_query = st.session_state.input_nl_query
    dialect = st.session_state.input_dialect
    allow_destructive = st.session_state.input_destructive
    
    if not nl_query:
        return

    try:
        # Schema Handling
        if st.session_state.current_schema == "selected" and st.session_state.selected_tables:
             snapshot_file = st.session_state.sam.create_specialized_snapshot(
                st.session_state.selected_tables
            )
             with open(snapshot_file, 'r') as f:
                schema_text = f.read()
        else:
             with open(st.session_state.sam.schema_file, 'r') as f:
                schema_text = f.read()

        st.session_state.reasoner.update_schema(schema_text)

        payload = CommandPayload(
            intent="query",
            raw_nl=nl_query,
            dialect=dialect,
            allow_destructive=allow_destructive
        )

        output = st.session_state.reasoner.generate(payload)
        st.session_state.generated_output = output
        
        # Save context for refinement
        st.session_state.current_nl_query = nl_query
        st.session_state.current_dialect = dialect
        st.session_state.current_allow_destructive = allow_destructive

        # Auto-Execute Logic
        if output.confidence >= 0.90 and output.safe_to_execute and output.sql:
            is_destructive = any(keyword in output.sql.lower() for keyword in 
                                ["insert", "update", "delete", "alter", "create", "drop", "truncate"])
            
            if not (is_destructive and not allow_destructive) and not st.session_state.input_dry_run:
                _execute_sql_internal(output.sql, output.intent, is_destructive, auto=True)

    except Exception as e:
        st.error(f"Generation Error: {e}")

def handle_refinement():
    """Callback for refinement"""
    refinement = st.session_state.input_refinement
    if not refinement or not st.session_state.generated_output:
        return

    refinement_nl = f"{st.session_state.current_nl_query}. Also, {refinement}"
    payload = CommandPayload(
        intent="query",
        raw_nl=refinement_nl,
        dialect=st.session_state.current_dialect,
        allow_destructive=st.session_state.current_allow_destructive
    )
    output = st.session_state.reasoner.generate(payload)
    st.session_state.generated_output = output

def handle_manual_execution():
    """Callback for executing manually edited SQL"""
    sql = st.session_state.sql_editor
    if not sql:
        return
    
    is_destructive = any(keyword in sql.lower() for keyword in 
                        ["insert", "update", "delete", "alter", "create", "drop", "truncate"])
    
    if is_destructive and not st.session_state.current_allow_destructive:
        st.warning("Destructive operation not allowed.")
        return

    _execute_sql_internal(
        sql, 
        st.session_state.generated_output.intent if st.session_state.generated_output else "query",
        is_destructive,
        auto=False
    )

def _execute_sql_internal(sql, intent, is_destructive, auto=False):
    """Internal helper to execute and update history"""
    
    # 1. Execute the query
    exec_result = st.session_state.executor.execute_query(
        sql,
        safe_to_execute=True,
        is_destructive=is_destructive,
        dry_run=st.session_state.get('input_dry_run', False)
    )
    
    # 2. NEW: Auto-detect Schema Changes (DDL)
    # If the user ran CREATE, DROP, or ALTER, we scan the DB and update schema.txt immediately.
    if is_destructive and exec_result.status.value == 'success':
        lower_sql = sql.lower()
        if any(cmd in lower_sql for cmd in ['create table', 'drop table', 'alter table']):
            with st.spinner("🔄 Detected schema change... Updating snapshot..."):
                st.session_state.sam.generate_full_schema()
                # Reload the new schema into the Reasoner immediately
                with open(st.session_state.sam.schema_file, 'r') as f:
                    st.session_state.reasoner.update_schema(f.read())
    
    # 3. Format and display results (Standard Logic)
    formatted = st.session_state.executor.format_results_for_display(exec_result)
    
    st.session_state.last_execution_result = {
        "formatted": formatted,
        "sql": sql,
        "intent": intent
    }
    
    st.session_state.query_history.append({
        "timestamp": datetime.now().isoformat(),
        "nl_query": st.session_state.current_nl_query,
        "sql": sql,
        "intent": intent,
        "success": formatted['success'],
        "result": formatted,
        "auto_executed": auto,
        "manually_edited": not auto
    })

# --- UI FUNCTIONS ---

def display_header():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
            <div style='text-align: center; padding: 2rem 0;'>
                <h1 style='color: white; font-size: 3rem; margin-bottom: 0;'>
                    🤖 AetherDB 
                </h1>
            </div>
        """, unsafe_allow_html=True)

def sidebar_database_connection():
    st.sidebar.title("⚙️ Database Connection")
    
    if not st.session_state.connected:
        db_type = st.sidebar.selectbox("Database Type", ["MySQL", "PostgreSQL", "SQLite"])
        
        if db_type == "SQLite":
            db_file = st.sidebar.text_input("Database File Path", value="database.db")
            if st.sidebar.button("🔌 Connect", use_container_width=True):
                with st.spinner("Connecting..."):
                    if handle_connect("sqlite", database=db_file):
                        st.sidebar.success("Connected!")
                        st.rerun()
        else:
            host = st.sidebar.text_input("Host", value="localhost")
            port = st.sidebar.number_input("Port", value=3306 if db_type == "MySQL" else 5432)
            user = st.sidebar.text_input("Username")
            password = st.sidebar.text_input("Password", type="password")
            database = st.sidebar.text_input("Database Name")
            
            if st.sidebar.button("🔌 Connect", use_container_width=True):
                with st.spinner("Connecting..."):
                    conn_params = {"host": host, "port": port, "user": user, "password": password, "database": database}
                    if handle_connect(db_type, **conn_params):
                        st.sidebar.success("Connected!")
                        st.rerun()
        
        if 'connection_error' in st.session_state:
            st.sidebar.error(st.session_state.connection_error)
            del st.session_state.connection_error
            
    else:
        st.sidebar.success("✅ Database Connected")
        if st.session_state.sam and st.session_state.sam.current_metadata:
            metadata = st.session_state.sam.current_metadata
            st.sidebar.markdown(f"**DB:** {metadata.database_name} | **Tables:** {metadata.table_count}")
        
        if st.sidebar.button("🔌 Disconnect"):
            st.session_state.sam.close()
            st.session_state.connected = False
            st.rerun()

def display_available_tables():
    st.subheader("📊 Available Tables")
    if st.session_state.sam:
        tables = st.session_state.sam.get_tables()
        col1, col2 = st.columns([2, 2])
        with col1:
            table_option = st.radio(
                "Mode",
                ["🌐 All Tables", "✅ Select Specific", "📝 No Tables"],
                horizontal=True
            )
        
        selected = []
        if table_option == "✅ Select Specific":
            with col2:
                selected = st.multiselect("Select Tables", tables)
        
        # Update state
        if table_option.startswith("🌐"):
            st.session_state.current_schema = "all"
        elif table_option.startswith("📝"):
            st.session_state.current_schema = "none"
        else:
            st.session_state.current_schema = "selected"
            st.session_state.selected_tables = selected

def display_data_visualization(df: pd.DataFrame):
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) == 0:
        return
    
    st.markdown("#### 📈 Data Visualization")
    viz_col1, viz_col2, viz_col3 = st.columns(3)
    
    with viz_col1:
        chart_type = st.selectbox("Chart Type", ["Bar Chart", "Line Chart", "Scatter Plot", "Pie Chart"])
    with viz_col3:
        y_col = st.selectbox("Y-Axis (Values)", numeric_cols)
    with viz_col2:
        all_cols = df.columns.tolist()
        default_x = next((i for i, col in enumerate(all_cols) if col != y_col), 0)
        x_col = st.selectbox("X-Axis", all_cols, index=default_x)
    
    if chart_type == "Bar Chart":
        st.plotly_chart(px.bar(df, x=x_col, y=y_col), use_container_width=True)
    elif chart_type == "Line Chart":
        st.plotly_chart(px.line(df, x=x_col, y=y_col), use_container_width=True)
    elif chart_type == "Scatter Plot":
        st.plotly_chart(px.scatter(df, x=x_col, y=y_col), use_container_width=True)
    elif chart_type == "Pie Chart":
        st.plotly_chart(px.pie(df, names=x_col, values=y_col), use_container_width=True)

def display_query_interface():
    st.subheader("💬 Natural Language Query")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.text_area("Enter your question", key="input_nl_query", height=100)
    with col2:
        st.selectbox("Dialect", ["mysql", "postgresql", "sqlite"], key="input_dialect")
        st.checkbox("Allow Destructive", key="input_destructive")
        st.checkbox("Dry Run", key="input_dry_run")
    
    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        # CALLS THE CALLBACK - No st.rerun() needed
        st.button("🚀 Generate SQL", on_click=handle_generate_sql, use_container_width=True)
    with col_btn2:
         if st.button("🗑️ Clear History"):
            st.session_state.query_history = []
            st.session_state.executor.clear_history()

    # --- RESULT DISPLAY AREA ---
    
    # 1. Generated Output
    if st.session_state.generated_output:
        out = st.session_state.generated_output
        st.markdown("---")
        
        # Metrics row
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Intent", out.intent.upper())
        m2.metric("Confidence", f"{out.confidence:.0%}")
        m3.metric("Safety", "✅ Safe" if out.safe_to_execute else "⚠️ Blocked")
        m4.metric("Dialect", out.dialect.upper())
        
        if out.thought_process:
            with st.expander("💭 AI Thought Process", expanded=False):
                st.info(out.thought_process)
        
        # Editor Area
        st.markdown("#### ✏️ Review & Edit")
        e_col1, e_col2 = st.columns([3, 1])
        
        with e_col1:
            st.text_area("SQL Editor", value=out.sql or "", key="sql_editor", height=150)
        
        with e_col2:
            st.text_input("Refine with AI", key="input_refinement", placeholder="e.g. add limit 5")
            st.button("🔄 Refine", on_click=handle_refinement, use_container_width=True)
            st.markdown("---")
            # CALLS THE CALLBACK - No st.rerun() needed
            st.button("▶️ Execute SQL", type="primary", on_click=handle_manual_execution, use_container_width=True)

    # 2. Execution Results (Displayed immediately after callback updates state)
    if st.session_state.last_execution_result:
        st.markdown("---")
        st.markdown("### 🎯 Execution Results")
        res = st.session_state.last_execution_result
        display_execution_results(res['formatted'])

def display_execution_results(formatted):
    if formatted['success']:
        st.success(f"✅ {formatted['message']}")
    else:
        st.error(f"❌ {formatted.get('error', 'Unknown Error')}")

    if formatted.get('has_data') and formatted.get('data'):
        df = pd.DataFrame(formatted['data'])
        st.dataframe(df, use_container_width=True, height=300) # Reduced height for performance
        display_data_visualization(df)
    elif formatted.get('columns'):
        st.warning("Query returned empty set.")

def display_statistics():
    if not st.session_state.executor: return
    
    # Calculate stats lightly
    hist = st.session_state.executor.execution_history
    total = len(hist)
    success = len([h for h in hist if h.status.value == 'success'])
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Statistics")
    st.sidebar.metric("Total Queries", total)
    if total > 0:
        st.sidebar.metric("Success Rate", f"{(success/total)*100:.1f}%")

    # Only render chart if there is data, to save render time
    if total > 0:
        failed = len([h for h in hist if h.status.value == 'failed'])
        blocked = len([h for h in hist if h.status.value == 'blocked'])
        fig = go.Figure(data=[go.Pie(labels=['Success', 'Fail', 'Block'], values=[success, failed, blocked], hole=.4)])
        fig.update_layout(height=150, margin=dict(t=0, b=0, l=0, r=0), showlegend=False)
        st.sidebar.plotly_chart(fig, use_container_width=True)

def main():
    display_header()
    sidebar_database_connection()

    # ================== ADMIN CONSOLE ACCESS ==================
    st.sidebar.markdown("---")
    st.sidebar.write("🔐 For administrators")
    if st.sidebar.button("Open Admin Console"):
        st.switch_page("pages/admin_console.py")
    
    if st.session_state.connected:
        display_statistics()
        display_available_tables()
        st.markdown("---")
        display_query_interface()
        
        # History at bottom
        if st.session_state.query_history:
            st.markdown("---")
            with st.expander("📜 Query History"):
                for item in reversed(st.session_state.query_history[-5:]):
                    st.text(f"{item['timestamp']} | {item['nl_query']}")
                    st.code(item['sql'], language='sql')
    else:
        st.info("👈 Please connect to a database in the sidebar to begin.")

if __name__ == "__main__":
    main()