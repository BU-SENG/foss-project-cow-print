#!/usr/bin/env python3
"""
Optimized Streamlit frontend for AetherDB
- Uses caching for heavy resources
- Minimizes reruns and blocking calls
- Provides async-friendly placeholders for AI calls
- Keeps original functionality: connect, generate SQL, edit, execute, visualize

Notes:
This refactor assumes the existing core modules are available:
- schema_awareness.SchemaAwarenessModule
- sqlm.GeminiReasoner, CommandPayload
- db_executor.DatabaseExecutor

Save this file as streamlit_app.py and run with: streamlit run streamlit_app.py
"""

from typing import Dict, List
import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import asyncio
import json

# Import project modules (assumed present)
from schema_awareness import SchemaAwarenessModule
from sqlm import GeminiReasoner, CommandPayload
from db_executor import DatabaseExecutor

# ------------------------- App Config -------------------------
st.set_page_config(page_title="AetherDB - Natural language → SQL", page_icon="🤖", layout="wide")

# ------------------------- Utilities & Cached Resources -------------------------
@st.cache_resource
def load_css() -> str:
    return """
    <style>
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .stApp {
        background: transparent;
    }
    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e1e2e 0%, #2d2d44 100%);
    }
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 0.5rem;
        padding: 0.75rem 2rem;
        font-weight: 600;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(102, 126, 234, 0.4);
    }
    /* SQL Editor Styling */
    textarea[aria-label*="edit"] {
        font-family: 'Courier New', monospace !important;
        font-size: 14px !important;
        background: #1e1e2e !important;
        color: #00ff00 !important;
        border: 2px solid #667eea !important;
    }
    .sql-editor-container { 
        background: #f8f9fa; 
        padding: 1rem; 
        border-radius: .5rem; 
        border-left: 4px solid #667eea; 
    }
    </style>
    """

@st.cache_resource
def create_reasoner(schema_text: str) -> GeminiReasoner:
    """Create and cache a GeminiReasoner instance for a given schema snapshot."""
    return GeminiReasoner(schema_snapshot=schema_text)

@st.cache_resource
def read_text_file(path: str) -> str:
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

# ------------------------- Session State Initialization -------------------------
def init_session_state():
    defaults = {
        'connected': False,
        'sam': None,
        'reasoner': None,
        'executor': None,
        'query_history': [],
        'current_schema': None,
        'generated_output': None,
        'current_nl_query': "",
        'current_dialect': 'mysql',
        'current_allow_destructive': False,
        'current_dry_run': False,
        'execute_edited_sql': False,
        'last_execution_result': None,
        'need_rerender': False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()

# ------------------------- Helper functions -------------------------
def safe_metric(label: str, value):
    try:
        st.metric(label, value)
    except Exception:
        st.write(f"{label}: {value}")

async def async_generate_sql(payload: CommandPayload) -> object:
    """Attempt to call an async generation method on the reasoner if present.
    Falls back to sync call to keep compatibility with existing reasoner implementations.
    """
    reasoner = st.session_state.reasoner
    if reasoner is None:
        raise RuntimeError("Reasoner not initialized")

    # If the reasoner exposes an async method, use it
    if hasattr(reasoner, 'agenerate'):
        return await reasoner.agenerate(payload)
    # Otherwise run in threadpool to avoid blocking
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: reasoner.generate(payload))

# ------------------------- UI Components -------------------------
def display_header():
    st.markdown(load_css(), unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 3, 1])
    with c2:
        st.markdown("""
        <div style='text-align:center; padding:1.2rem;'>
            <h1 style='margin:0; color:#eef2ff'>🤖 AetherDB</h1>
            <p style='margin:0; color:rgba(255,255,255,0.8)'>Natural language → SQL powered by Gemini</p>
        </div>
        """, unsafe_allow_html=True)


def sidebar_database_connection():
    st.sidebar.title("⚙️ Database Connection")

    if not st.session_state.connected:
        db_type = st.sidebar.selectbox("Database Type", ["MySQL", "PostgreSQL", "SQLite"]) 

        if db_type == "SQLite":
            db_file = st.sidebar.text_input("Database File Path", value="database.db")
            if st.sidebar.button("🔌 Connect"):
                with st.spinner("Connecting..."):
                    try:
                        sam = SchemaAwarenessModule()
                        if sam.connect_database('sqlite', database=db_file):
                            st.session_state.sam = sam
                            st.session_state.connected = True
                            schema_text = read_text_file(sam.schema_file)
                            # cache reasoner per schema snapshot
                            st.session_state.reasoner = create_reasoner(schema_text)
                            st.session_state.executor = DatabaseExecutor(sam.connection, 'sqlite')
                            st.sidebar.success("Connected")
                    except Exception as e:
                        st.sidebar.error(f"Connection failed: {e}")
        else:
            host = st.sidebar.text_input("Host", value="localhost")
            port = st.sidebar.number_input("Port", value=3306 if db_type=="MySQL" else 5432, min_value=1, max_value=65535)
            user = st.sidebar.text_input("Username")
            password = st.sidebar.text_input("Password", type='password')
            database = st.sidebar.text_input("Database Name")

            if st.sidebar.button("🔌 Connect"):
                if not all([user, password, database]):
                    st.sidebar.error("Please fill in all fields")
                else:
                    with st.spinner("Connecting..."):
                        try:
                            sam = SchemaAwarenessModule()
                            conn_params = {"host": host, "port": port, "user": user, "password": password, "database": database}
                            if sam.connect_database(db_type.lower(), **conn_params):
                                st.session_state.sam = sam
                                st.session_state.connected = True
                                schema_text = read_text_file(sam.schema_file)
                                st.session_state.reasoner = create_reasoner(schema_text)
                                st.session_state.executor = DatabaseExecutor(sam.connection, db_type.lower())
                                st.sidebar.success("Connected")
                        except Exception as e:
                            st.sidebar.error(f"Connection failed: {e}")
    else:
        st.sidebar.success("✅ Database Connected")
        if st.session_state.sam and getattr(st.session_state.sam, 'current_metadata', None):
            md = st.session_state.sam.current_metadata
            st.sidebar.markdown(f"**Database:** {md.database_name}  \n**Type:** {md.database_type}  \n**Tables:** {md.table_count}")

        if st.sidebar.button("🔄 Refresh Schema"):
            with st.spinner("Refreshing schema..."):
                st.session_state.sam.generate_full_schema()
                schema_text = read_text_file(st.session_state.sam.schema_file)
                # Replace reasoner only when schema changed
                st.session_state.reasoner = create_reasoner(schema_text)
                st.sidebar.success("Schema refreshed")

        if st.sidebar.button("🔌 Disconnect"):
            try:
                st.session_state.sam.close()
            except Exception:
                pass
            for k in ['connected','sam','reasoner','executor']:
                st.session_state[k] = None if k!='connected' else False
            st.rerun()


def display_available_tables():
    st.subheader("📊 Available Tables")
    if not st.session_state.sam:
        st.info("Connect a database to see tables")
        return

    tables = st.session_state.sam.get_tables()

    col1, col2 = st.columns([3,1])
    with col1:
        table_option = st.radio("Table Selection Mode", ["All Tables","Select Specific Tables","No Tables"], index=0)

    selected_tables: List[str] = []
    if table_option == "Select Specific Tables":
        selected_tables = st.multiselect("Select Tables", tables)

    if table_option == "All Tables":
        st.session_state.current_schema = 'all'
        st.session_state.selected_tables = tables
    elif table_option == "No Tables":
        st.session_state.current_schema = 'none'
        st.session_state.selected_tables = []
    else:
        st.session_state.current_schema = 'selected'
        st.session_state.selected_tables = selected_tables

    # display simple badge list
    if tables:
        cols = st.columns(min(len(tables), 4))
        for idx, t in enumerate(tables):
            with cols[idx % 4]:
                icon = '✅' if (st.session_state.current_schema=='all' or t in st.session_state.get('selected_tables', [])) else '⬜'
                st.markdown(f"{icon} **{t}**")


def display_execution_results(formatted: Dict, sql: str, intent: str):
    # Basic status
    if formatted.get('success'):
        st.success(formatted.get('message','Executed'))
    else:
        st.error('Execution Failed')
        if formatted.get('error'):
            st.error(formatted['error'])

    c1, c2, c3 = st.columns(3)
    with c1:
        safe_metric("Execution Time", formatted.get('execution_time','-'))
    with c2:
        safe_metric("Rows Affected/Returned", formatted.get('rows_affected', 0))
    with c3:
        safe_metric("Status", formatted.get('status','-'))

    if formatted.get('success') and formatted.get('has_data') and formatted.get('data'):
        df = pd.DataFrame(formatted['data'])
        # limit rendering for very large datasets
        if len(df) > 5000:
            st.warning("Large result set detected — showing first 2000 rows for performance")
            st.dataframe(df.head(2000), use_container_width=True)
        else:
            st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False)
        st.download_button("📥 Download CSV", csv, file_name=f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            chart_type = st.selectbox('Chart Type', ['Bar','Line','Scatter','Pie'], key='chart_type')
            y_col = st.selectbox('Y-Axis', list(numeric_cols), key='y_col')
            if chart_type == 'Bar':
                fig = px.bar(df, x=df.columns[0], y=y_col)
                st.plotly_chart(fig, use_container_width=True)
            elif chart_type == 'Line':
                fig = px.line(df, x=df.columns[0], y=y_col)
                st.plotly_chart(fig, use_container_width=True)
            elif chart_type == 'Scatter':
                x_col = st.selectbox('X-Axis', list(numeric_cols), key='x_col')
                fig = px.scatter(df, x=x_col, y=y_col)
                st.plotly_chart(fig, use_container_width=True)
            elif chart_type == 'Pie':
                fig = px.pie(df, names=df.columns[0], values=y_col)
                st.plotly_chart(fig, use_container_width=True)
    else:
        if formatted.get('columns'):
            st.warning('Query returned 0 rows')
        else:
            st.info(f"Operation completed. Rows affected: {formatted.get('rows_affected',0)}")


# ------------------------- Main Query Interface -------------------------
async def handle_generate(nl_query: str, dialect: str, allow_destructive: bool, dry_run: bool):
    # Build schema snapshot according to selection
    if st.session_state.current_schema == 'all':
        schema_text = read_text_file(st.session_state.sam.schema_file)
    elif st.session_state.current_schema == 'none':
        schema_text = read_text_file(st.session_state.sam.schema_file)
    else:
        if not st.session_state.selected_tables:
            st.warning('Please select at least one table')
            return
        snapshot = st.session_state.sam.create_specialized_snapshot(st.session_state.selected_tables)
        schema_text = read_text_file(snapshot)

    # Only replace reasoner when schema changes
    if not st.session_state.reasoner:
        st.session_state.reasoner = create_reasoner(schema_text)

    payload = CommandPayload(intent='query', raw_nl=nl_query, dialect=dialect, allow_destructive=allow_destructive)

    # Call async generator (wrapped)
    try:
        with st.spinner('🤖 Generating SQL...'):
            output = await async_generate_sql(payload)
    except Exception as e:
        st.error(f'Generation failed: {e}')
        return

    st.session_state.generated_output = output
    st.session_state.current_nl_query = nl_query
    st.session_state.current_dialect = dialect
    st.session_state.current_allow_destructive = allow_destructive
    st.session_state.current_dry_run = dry_run
    st.session_state.need_rerender = True


def display_query_interface():
    st.subheader('💬 Natural Language Query')
    col1, col2 = st.columns([3,1])
    with col1:
        nl_query = st.text_area('Enter your question', height=120, placeholder='e.g., Show students whose surname starts with A')
    with col2:
        dialect = st.selectbox('SQL Dialect', ['mysql','postgresql','sqlite'])
        allow_destructive = st.checkbox('Allow Destructive Operations', value=False)
        dry_run = st.checkbox('Dry Run (Preview Only)', value=False)

    c1, c2, c3 = st.columns([1,1,2])
    gen = c1.button('🚀 Generate SQL')
    if c2.button('🗑️ Clear History'):
        st.session_state.query_history = []
        if st.session_state.executor:
            try:
                st.session_state.executor.clear_history()
            except Exception:
                pass

    if gen and nl_query:
        # Run async generator without blocking main thread
        asyncio.run(handle_generate(nl_query, dialect, allow_destructive, dry_run))

    # Display generated SQL & editor
    out = st.session_state.get('generated_output')
    if out:
        st.markdown('---')
        st.markdown('### 📝 Generated SQL')
        cols = st.columns(4)
        with cols[0]:
            st.metric('Intent', getattr(out, 'intent', '').upper())
        with cols[1]:
            try:
                conf = getattr(out, 'confidence', None)
                st.metric('Confidence', f"{conf:.0%}")
            except Exception:
                st.metric('Confidence', '-')
        with cols[2]:
            safe = '✅ Safe' if getattr(out, 'safe_to_execute', False) else '⚠️ Blocked'
            st.metric('Safety', safe)
        with cols[3]:
            st.metric('Dialect', getattr(out, 'dialect', '').upper())

        if getattr(out, 'explain_text', None):
            st.info(f"💡 {out.explain_text}")

        if getattr(out, 'warnings', None):
            for w in out.warnings:
                st.warning(w)

        edited_sql = st.text_area('Review & edit SQL', value=getattr(out, 'sql', ''), height=150, key='sql_editor')

        refinement = st.text_input('AI Refinement', placeholder='e.g., add ORDER BY created_at DESC')
        if st.button('🔄 Refine with AI'):
            if refinement:
                refined_nl = f"{st.session_state.current_nl_query} Also, {refinement}"
                # Synchronous refinement for simplicity
                payload = CommandPayload(intent='query', raw_nl=refined_nl, dialect=st.session_state.current_dialect, allow_destructive=st.session_state.current_allow_destructive)
                try:
                    with st.spinner('Refining...'):
                        refined_output = st.session_state.reasoner.generate(payload)
                        st.session_state.generated_output = refined_output
                        st.rerun()
                except Exception as e:
                    st.error(f'Refinement failed: {e}')
            else:
                st.warning('Enter refinement text')

        if st.button('▶️ Execute Edited SQL'):
            st.session_state.execute_edited_sql = True
            st.session_state.edited_sql_value = edited_sql
            # Do not call st.rerun here — let flow continue to execution block below

        if st.button('📋 Copy SQL'):
            st.toast('✅ SQL copied to clipboard!', icon='📋')

    # Execute edited SQL (inline, no full rerun)
    if st.session_state.get('execute_edited_sql'):
        st.session_state.execute_edited_sql = False
        edited_sql_val = st.session_state.get('edited_sql_value','')
        if not edited_sql_val.strip():
            st.warning('SQL empty')
        else:
            is_destructive = any(k in edited_sql_val.lower() for k in ['insert','update','delete','alter','create','drop','truncate'])
            if is_destructive and not st.session_state.current_allow_destructive:
                st.error('Destructive SQL detected but not allowed')
            else:
                try:
                    exec_result = st.session_state.executor.execute_query(edited_sql_val, safe_to_execute=True, is_destructive=is_destructive, dry_run=st.session_state.current_dry_run)
                    formatted = st.session_state.executor.format_results_for_display(exec_result)
                    st.session_state.last_execution_result = {'formatted': formatted, 'sql': edited_sql_val, 'intent': getattr(st.session_state.generated_output,'intent','')}
                    # append to history
                    st.session_state.query_history.append({
                        'timestamp': datetime.now().isoformat(),
                        'nl_query': st.session_state.current_nl_query,
                        'sql': edited_sql_val,
                        'intent': getattr(st.session_state.generated_output,'intent',''),
                        'success': formatted.get('success', False),
                        'result': formatted,
                        'manually_edited': True
                    })
                    st.session_state.need_rerender = True
                except Exception as e:
                    st.error(f'Execution error: {e}')

    # Persistent display of last execution
    if st.session_state.get('last_execution_result'):
        st.markdown('---')
        st.markdown('### 🎯 Execution Results')
        res = st.session_state.last_execution_result
        display_execution_results(res['formatted'], res['sql'], res['intent'])


def display_query_history():
    if not st.session_state.query_history:
        return
    st.markdown('---')
    st.subheader('📜 Query History')
    for idx, item in enumerate(reversed(st.session_state.query_history[-10:])):
        edited_badge = '✏️ EDITED' if item.get('manually_edited') else ''
        with st.expander(f"Query {len(st.session_state.query_history)-idx}: {item['nl_query'][:50]}... {edited_badge}"):
            st.markdown(f"**Time:** {item['timestamp']}")
            st.markdown(f"**Intent:** {item['intent']}")
            st.code(item['sql'], language='sql')
            if item.get('success'):
                st.success('✅ Executed successfully')
                if item.get('result') and item['result'].get('has_data'):
                    st.markdown(f"**Rows returned:** {item['result']['rows_affected']}")
            else:
                st.error('❌ Execution failed')


def display_statistics():
    if not st.session_state.executor:
        return
    stats = st.session_state.executor.get_statistics()
    st.sidebar.markdown('---')
    st.sidebar.subheader('📊 Statistics')
    total = stats.get('total_executions',0)
    success = stats.get('successful',0)
    success_rate = (success/total*100) if total>0 else 0
    st.sidebar.metric('Total Queries', total)
    st.sidebar.metric('Success Rate', f"{success_rate:.1f}%")
    st.sidebar.metric('Avg Execution Time', f"{stats.get('average_execution_time_ms',0):.2f}ms")
    if total>0:
        fig = go.Figure(data=[go.Pie(labels=['Success','Failed','Blocked'], values=[stats.get('successful',0), stats.get('failed',0), stats.get('blocked',0)], hole=.3)])
        fig.update_layout(height=200, margin=dict(l=0,r=0,t=0,b=0))
        st.sidebar.plotly_chart(fig, use_container_width=True)


# ------------------------- Main -------------------------

def main():
    display_header()
    sidebar_database_connection()
    display_statistics()

    if not st.session_state.connected:
        st.markdown("""
        <div style='text-align:center; padding:2rem;'>
            <h2>Welcome to AetherDB</h2>
            <p>Connect a database from the sidebar to begin.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    display_available_tables()
    st.markdown('---')
    display_query_interface()
    display_query_history()

    # soft rerender trigger — avoids performing expensive st.rerun in many places
    if st.session_state.get('need_rerender'):
        st.session_state.need_rerender = False
        st.rerun()


if __name__ == '__main__':
    main()
