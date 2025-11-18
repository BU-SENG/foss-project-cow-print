#!/usr/bin/env python3
"""
Aether DB - Streamlit Frontend

A beautiful, intuitive interface for natural language to SQL conversion
with real-time database execution and visualization.
"""

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

# Custom CSS for beautiful styling
st.markdown("""
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
    .success-box {
        padding: 1.5rem;
        border-radius: 0.5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 0.75rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
    }
    .query-card {
        background: white;
        padding: 1.5rem;
        border-radius: 0.75rem;
        margin: 1rem 0;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
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


def display_header():
    """Display the app header with logo and title"""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
            <div style='text-align: center; padding: 2rem 0;'>
                <h1 style='color: white; font-size: 3rem; margin-bottom: 0;'>
                    🤖 AetherDB 
                </h1>
                <p style='color: rgba(255,255,255,0.8); font-size: 1.2rem;'>
                    Transform Natural Language into SQL with AI Magic
                </p>
            </div>
        """, unsafe_allow_html=True)


def sidebar_database_connection():
    """Sidebar for database connection"""
    st.sidebar.title("⚙️ Database Connection")
    
    if not st.session_state.connected:
        db_type = st.sidebar.selectbox(
            "Database Type",
            ["MySQL", "PostgreSQL", "SQLite"],
            help="Select your database type"
        )
        
        if db_type == "SQLite":
            db_file = st.sidebar.text_input(
                "Database File Path",
                value="database.db",
                help="Path to your SQLite database file"
            )
            
            if st.sidebar.button("🔌 Connect", use_container_width=True):
                with st.spinner("Connecting to database..."):
                    try:
                        sam = SchemaAwarenessModule()
                        if sam.connect_database(db_type.lower(), database=db_file):
                            st.session_state.sam = sam
                            st.session_state.connected = True
                            
                            # Initialize reasoner with schema
                            with open(sam.schema_file, 'r') as f:
                                schema_text = f.read()
                            st.session_state.reasoner = GeminiReasoner(schema_snapshot=schema_text)
                            
                            # Initialize executor
                            st.session_state.executor = DatabaseExecutor(
                                sam.connection,
                                db_type.lower()
                            )
                            
                            st.sidebar.success("✅ Connected successfully!")
                            st.rerun()
                    except Exception as e:
                        st.sidebar.error(f"❌ Connection failed: {str(e)}")
        
        else:  # MySQL or PostgreSQL
            host = st.sidebar.text_input("Host", value="localhost")
            port = st.sidebar.number_input(
                "Port",
                value=3306 if db_type == "MySQL" else 5432,
                min_value=1,
                max_value=65535
            )
            user = st.sidebar.text_input("Username")
            password = st.sidebar.text_input("Password", type="password")
            database = st.sidebar.text_input("Database Name")
            
            if st.sidebar.button("🔌 Connect", use_container_width=True):
                if not all([user, password, database]):
                    st.sidebar.error("❌ Please fill in all fields")
                else:
                    with st.spinner("Connecting to database..."):
                        try:
                            sam = SchemaAwarenessModule()
                            conn_params = {
                                "host": host,
                                "port": port,
                                "user": user,
                                "password": password,
                                "database": database
                            }
                            
                            if sam.connect_database(db_type.lower(), **conn_params):
                                st.session_state.sam = sam
                                st.session_state.connected = True
                                
                                # Initialize reasoner
                                with open(sam.schema_file, 'r') as f:
                                    schema_text = f.read()
                                st.session_state.reasoner = GeminiReasoner(schema_snapshot=schema_text)
                                
                                # Initialize executor
                                st.session_state.executor = DatabaseExecutor(
                                    sam.connection,
                                    db_type.lower()
                                )
                                
                                st.sidebar.success("✅ Connected successfully!")
                                st.rerun()
                        except Exception as e:
                            st.sidebar.error(f"❌ Connection failed: {str(e)}")
    
    else:
        # Show connection info
        st.sidebar.success("✅ Database Connected")
        
        if st.session_state.sam and st.session_state.sam.current_metadata:
            metadata = st.session_state.sam.current_metadata
            st.sidebar.markdown(f"""
                **Database:** {metadata.database_name}  
                **Type:** {metadata.database_type}  
                **Tables:** {metadata.table_count}  
                **Version:** {metadata.version}
            """)
        
        if st.sidebar.button("🔄 Refresh Schema", use_container_width=True):
            with st.spinner("Refreshing schema..."):
                st.session_state.sam.generate_full_schema()
                with open(st.session_state.sam.schema_file, 'r') as f:
                    schema_text = f.read()
                st.session_state.reasoner.update_schema(schema_text)
                st.sidebar.success("✅ Schema refreshed!")
        
        if st.sidebar.button("🔌 Disconnect", use_container_width=True):
            st.session_state.sam.close()
            st.session_state.connected = False
            st.session_state.sam = None
            st.session_state.reasoner = None
            st.session_state.executor = None
            st.rerun()


def display_available_tables():
    """Display available tables with selection"""
    st.subheader("📊 Available Tables")
    
    if st.session_state.sam:
        tables = st.session_state.sam._get_tables()
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            table_option = st.radio(
                "Table Selection Mode",
                ["🌐 All Tables (Database-level operations)", 
                 "✅ Select Specific Tables",
                 "📝 No Tables (CREATE, DROP, etc.)"],
                help="Choose which tables to include in the query context"
            )
        
        selected_tables = []
        
        if table_option == "✅ Select Specific Tables":
            with col2:
                selected_tables = st.multiselect(
                    "Select Tables",
                    tables,
                    help="Choose one or more tables for your query"
                )
        
        # Store in session state
        if table_option == "🌐 All Tables (Database-level operations)":
            st.session_state.current_schema = "all"
            st.session_state.selected_tables = tables
        elif table_option == "📝 No Tables (CREATE, DROP, etc.)":
            st.session_state.current_schema = "none"
            st.session_state.selected_tables = []
        else:
            st.session_state.current_schema = "selected"
            st.session_state.selected_tables = selected_tables
        
        # Display table info
        if tables:
            st.markdown("---")
            cols = st.columns(min(len(tables), 4))
            for idx, table in enumerate(tables):
                with cols[idx % 4]:
                    is_selected = (
                        st.session_state.current_schema == "all" or 
                        table in st.session_state.get('selected_tables', [])
                    )
                    icon = "✅" if is_selected else "⬜"
                    st.markdown(f"{icon} **{table}**")


def display_query_interface():
    """Main query interface"""
    st.subheader("💬 Natural Language Query")
    
    # Query input
    col1, col2 = st.columns([3, 1])
    
    with col1:
        nl_query = st.text_area(
            "Enter your question in plain English",
            placeholder="e.g., Show me all students whose surname starts with 'A'\n     Count how many classes exist\n     Create a new table called courses with columns id, name, credits",
            height=120,
            help="Type your question naturally - the AI will convert it to SQL"
        )
    
    with col2:
        dialect = st.selectbox(
            "SQL Dialect",
            ["mysql", "postgresql", "sqlite"],
            index=0
        )
        
        allow_destructive = st.checkbox(
            "Allow Destructive Operations",
            value=False,
            help="Enable INSERT, UPDATE, DELETE, DROP operations"
        )
        
        dry_run = st.checkbox(
            "Dry Run (Preview Only)",
            value=False,
            help="Generate SQL without executing it"
        )
    
    # Execute button
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        execute_btn = st.button("🚀 Generate & Execute SQL", use_container_width=True)
    with col2:
        if st.button("🗑️ Clear History", use_container_width=True):
            st.session_state.query_history = []
            if st.session_state.executor:
                st.session_state.executor.clear_history()
            st.rerun()
    
    if execute_btn and nl_query:
        with st.spinner("🤖 AI is thinking..."):
            try:
                # Prepare schema based on selection
                if st.session_state.current_schema == "all":
                    with open(st.session_state.sam.schema_file, 'r') as f:
                        schema_text = f.read()
                elif st.session_state.current_schema == "none":
                    with open(st.session_state.sam.schema_file, 'r') as f:
                        schema_text = f.read()
                else:  # selected
                    if not st.session_state.selected_tables:
                        st.error("❌ Please select at least one table")
                        return
                    # Create specialized snapshot
                    snapshot_file = st.session_state.sam.create_specialized_snapshot(
                        st.session_state.selected_tables
                    )
                    with open(snapshot_file, 'r') as f:
                        schema_text = f.read()
                
                # Update reasoner schema
                st.session_state.reasoner.update_schema(schema_text)
                
                # Create command payload
                payload = CommandPayload(
                    intent="query",
                    raw_nl=nl_query,
                    dialect=dialect,
                    allow_destructive=allow_destructive
                )
                
                # Generate SQL
                output = st.session_state.reasoner.generate(payload)
                
                # Display generated SQL
                st.markdown("### 📝 Generated SQL")
                st.code(output.sql or "No SQL generated", language="sql")
                
                # Display metadata
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Intent", output.intent.upper())
                with col2:
                    st.metric("Confidence", f"{output.confidence:.0%}")
                with col3:
                    st.metric("Safety", "✅ Safe" if output.safe_to_execute else "⚠️ Blocked")
                with col4:
                    st.metric("Dialect", output.dialect.upper())
                
                # Display explanation
                if output.explain_text:
                    st.info(f"💡 **Explanation:** {output.explain_text}")
                
                # Display warnings
                if output.warnings:
                    for warning in output.warnings:
                        st.warning(f"⚠️ {warning}")
                
                # Display errors
                if output.errors:
                    for error in output.errors:
                        st.error(f"❌ {error}")
                
                # Execute SQL if safe
                if output.sql and output.safe_to_execute:
                    st.markdown("---")
                    st.markdown("### 🎯 Execution Results")
                    
                    # Determine if destructive
                    is_destructive = output.intent in ["insert", "update", "delete", "alter", "create_table", "drop"]
                    
                    # Execute
                    exec_result = st.session_state.executor.execute_query(
                        output.sql,
                        safe_to_execute=output.safe_to_execute,
                        is_destructive=is_destructive,
                        dry_run=dry_run
                    )
                    
                    # Format and display results
                    formatted = st.session_state.executor.format_results_for_display(exec_result)
                    
                    # ---------------------------------------------------------
                    # NEW IMPROVED DISPLAY LOGIC
                    # ---------------------------------------------------------
                    
                    if formatted['success']:
                        st.success(f"✅ {formatted['message']}")
                    else:
                        st.error(f"❌ Execution Failed")
                        st.error(f"Error Details: {formatted['error']}")

                    # Stats Bar
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Execution Time", formatted['execution_time'])
                    with col2:
                        st.metric("Rows Affected/Returned", formatted['rows_affected'])
                    with col3:
                        st.metric("Status", formatted['status'].upper())
                    
                    # Show Data (Success Case)
                    if formatted['success']:
                        if formatted['has_data'] and formatted['data']:
                            st.markdown("#### 📊 Query Output")
                            df = pd.DataFrame(formatted['data'])
                            st.dataframe(df, use_container_width=True, height=400)
                            
                            # Download button
                            csv = df.to_csv(index=False)
                            st.download_button(
                                label="📥 Download Results as CSV",
                                data=csv,
                                file_name=f"query_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv"
                            )
                            
                            # Visualization
                            numeric_cols = df.select_dtypes(include=['number']).columns
                            if len(numeric_cols) > 0:
                                st.markdown("#### 📈 Data Visualization")
                                viz_col1, viz_col2 = st.columns(2)
                                
                                with viz_col1:
                                    chart_type = st.selectbox(
                                        "Chart Type",
                                        ["Bar Chart", "Line Chart", "Scatter Plot", "Pie Chart"]
                                    )
                                
                                with viz_col2:
                                    y_col = st.selectbox("Y-Axis", numeric_cols)
                                
                                # Generate chart
                                if chart_type == "Bar Chart" and len(df.columns) >= 2:
                                    fig = px.bar(df, x=df.columns[0], y=y_col)
                                    st.plotly_chart(fig, use_container_width=True)
                                elif chart_type == "Line Chart" and len(df.columns) >= 2:
                                    fig = px.line(df, x=df.columns[0], y=y_col)
                                    st.plotly_chart(fig, use_container_width=True)
                                elif chart_type == "Scatter Plot" and len(numeric_cols) >= 2:
                                    x_col = st.selectbox("X-Axis", numeric_cols)
                                    fig = px.scatter(df, x=x_col, y=y_col)
                                    st.plotly_chart(fig, use_container_width=True)
                                elif chart_type == "Pie Chart" and len(df.columns) >= 2:
                                    fig = px.pie(df, names=df.columns[0], values=y_col)
                                    st.plotly_chart(fig, use_container_width=True)

                        elif formatted['columns']: 
                            # Query worked (SELECT/SHOW) but returned 0 rows
                            st.warning("⚠️ Query executed successfully, but returned 0 results (Empty Set).")
                        else:
                            # Query worked (INSERT/UPDATE) and has no return columns
                            st.info(f"ℹ️ Operation completed. {formatted['rows_affected']} rows were affected.")

                    # Failure Case
                    else:
                         if formatted.get('warnings'):
                             st.warning(f"Warnings: {formatted['warnings']}")
                
                # Add to history
                st.session_state.query_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "nl_query": nl_query,
                    "sql": output.sql,
                    "intent": output.intent,
                    "success": output.safe_to_execute,
                    "result": formatted if output.safe_to_execute else None
                })
                
            except Exception as e:
                st.error(f"❌ An error occurred: {str(e)}")


def display_query_history():
    """Display query history"""
    if not st.session_state.query_history:
        return
    
    st.markdown("---")
    st.subheader("📜 Query History")
    
    for idx, item in enumerate(reversed(st.session_state.query_history[-5:])):
        with st.expander(f"Query {len(st.session_state.query_history) - idx}: {item['nl_query'][:50]}..."):
            st.markdown(f"**Time:** {item['timestamp']}")
            st.markdown(f"**Intent:** {item['intent']}")
            st.code(item['sql'], language="sql")
            if item['success']:
                st.success("✅ Executed successfully")
            else:
                st.error("❌ Execution blocked or failed")


def display_statistics():
    """Display execution statistics"""
    if st.session_state.executor:
        stats = st.session_state.executor.get_statistics()
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("📊 Statistics")
        
        # Get values safely with .get() defaults
        total = stats.get('total_executions', 0)
        success = stats.get('successful', 0)
        
        # Calculate success rate manually to avoid KeyError
        if total > 0:
            success_rate = (success / total) * 100
        else:
            success_rate = 0
        
        st.sidebar.metric("Total Queries", total)
        st.sidebar.metric("Success Rate", f"{success_rate:.1f}%")
        st.sidebar.metric("Avg Execution Time", f"{stats.get('average_execution_time_ms', 0):.2f}ms")
        
        # Success pie chart
        if total > 0:
            fig = go.Figure(data=[go.Pie(
                labels=['Success', 'Failed', 'Blocked'],
                values=[
                    stats.get('successful', 0), 
                    stats.get('failed', 0), 
                    stats.get('blocked', 0)
                ],
                hole=.3,
                marker_colors=['#10b981', '#ef4444', '#f59e0b']
            )])
            fig.update_layout(
                showlegend=True,
                height=200,
                margin=dict(l=0, r=0, t=0, b=0)
            )
            st.sidebar.plotly_chart(fig, use_container_width=True)


def main():
    """Main application"""
    display_header()
    
    # Sidebar
    sidebar_database_connection()
    display_statistics()
    
    # Main content
    if not st.session_state.connected:
        # Welcome screen
        st.markdown("""
            <div style='text-align: center; padding: 4rem 2rem; background: white; border-radius: 1rem; margin: 2rem 0;'>
                <h2 style='color: #667eea; margin-bottom: 1rem;'>Welcome to AetherDB 👋</h2>
                <p style='font-size: 1.1rem; color: #666; max-width: 600px; margin: 0 auto;'>
                    Connect your database using the sidebar to get started. Once connected, you can:
                </p>
                <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 2rem; margin-top: 2rem; max-width: 800px; margin-left: auto; margin-right: auto;'>
                    <div style='padding: 1.5rem; background: #f8f9fa; border-radius: 0.5rem;'>
                        <div style='font-size: 2rem; margin-bottom: 0.5rem;'>💬</div>
                        <strong>Natural Language Queries</strong>
                        <p style='font-size: 0.9rem; color: #666; margin-top: 0.5rem;'>
                            Ask questions in plain English
                        </p>
                    </div>
                    <div style='padding: 1.5rem; background: #f8f9fa; border-radius: 0.5rem;'>
                        <div style='font-size: 2rem; margin-bottom: 0.5rem;'>🤖</div>
                        <strong>AI-Powered SQL</strong>
                        <p style='font-size: 0.9rem; color: #666; margin-top: 0.5rem;'>
                            Get optimized SQL instantly
                        </p>
                    </div>
                    <div style='padding: 1.5rem; background: #f8f9fa; border-radius: 0.5rem;'>
                        <div style='font-size: 2rem; margin-bottom: 0.5rem;'>📊</div>
                        <strong>Visual Results</strong>
                        <p style='font-size: 0.9rem; color: #666; margin-top: 0.5rem;'>
                            See data in beautiful charts
                        </p>
                    </div>
                    <div style='padding: 1.5rem; background: #f8f9fa; border-radius: 0.5rem;'>
                        <div style='font-size: 2rem; margin-bottom: 0.5rem;'>🛡️</div>
                        <strong>Safe Execution</strong>
                        <p style='font-size: 0.9rem; color: #666; margin-top: 0.5rem;'>
                            Built-in safety checks
                        </p>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    else:
        # Main interface
        display_available_tables()
        st.markdown("---")
        display_query_interface()
        display_query_history()


if __name__ == "__main__":
    main()