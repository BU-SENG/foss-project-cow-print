import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import json
import tempfile
import os

def main():
    """Main Streamlit application for AI Database Query System"""
    
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sql-box {
        background-color: #272822;
        color: #f8f8f2;
        padding: 1rem;
        border-radius: 0.5rem;
        font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
        margin: 0.5rem 0;
    }
    .success-box {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #c3e6cb;
    }
    .connection-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #dee2e6;
        margin-bottom: 0.5rem;
    }
    .file-info {
        background-color: #e7f3ff;
        padding: 0.5rem;
        border-radius: 0.25rem;
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # App header
    st.markdown("""
    <div style="text-align: center;">
        <h1 class="main-header"> AETHER DB - AI Database Query System</h1>
        <p>Query your databases using natural language with AI-powered SQL generation</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.title("AETHER DB")
        st.markdown("---")
        
        # Database Connection Section
        st.subheader("Database Connection")
        
        # Connection Method Selection
        connection_method = st.radio(
            "Connection Method:",
            ["Connect to Server", "Import Database File"],
            horizontal=True
        )
        
        with st.expander("Database Connection", expanded=True):
            connection_name = st.text_input("Connection Name", value="My Database")
            
            if connection_method == "Connect to Server":
                db_type = st.selectbox("Database Type", 
                    ["sqlite", "mysql", "postgresql", "mssql", "oracle"])
                
                if db_type == "sqlite":
                    database = st.text_input("Database File", value="demo_company.db", 
                                           help="Path to SQLite database file")
                    host = st.text_input("Host", value="", disabled=True)
                    port = st.text_input("Port", value="", disabled=True)
                    username = st.text_input("Username", value="", disabled=True)
                    password = st.text_input("Password", type="password", disabled=True)
                else:
                    host = st.text_input("Host", value="localhost")
                    port = st.text_input("Port", value={
                        "mysql": "3306", 
                        "postgresql": "5432",
                        "mssql": "1433",
                        "oracle": "1521"
                    }.get(db_type, "3306"))
                    database = st.text_input("Database Name", value="test_company")
                    username = st.text_input("Username", value="root")
                    password = st.text_input("Password", type="password")
                
                if st.button("Connect to Server", type="primary", key="connect_server"):
                    with st.spinner("Connecting to database..."):
                        success = st.session_state.db_manager.connect_database(
                            connection_name, db_type, host, port, database, username, password
                        )
                        if success:
                            st.session_state.active_db = connection_name
                            schema_info = st.session_state.db_manager.get_schema_info(connection_name)
                            st.session_state.schema_info = schema_info
                            st.session_state.gemini.update_schema(schema_info)
                            st.success(f"Connected to {database}!")
                            st.rerun()
            
            else:  # Import Database File
                st.info("""
                **Supported file types:**
                - **SQLite**: .db, .sqlite, .sqlite3 (direct connection)
                - **Data Files**: .csv, .json, .xlsx, .xls (import into SQLite)
                - **SQL Dumps**: .sql (import into SQLite)
                """)
                
                uploaded_file = st.file_uploader(
                    "Choose database or data file", 
                    type=['db', 'sqlite', 'sqlite3', 'csv', 'json', 'sql', 'xlsx', 'xls'],
                    help="Upload database files or data files to import"
                )
                
                if uploaded_file is not None:
                    file_ext = os.path.splitext(uploaded_file.name)[1].lower()
                    file_size = len(uploaded_file.getvalue()) / 1024 / 1024  # Size in MB
                    
                    # Show file info
                    st.markdown(f"""
                    <div class="file-info">
                        <strong>File:</strong> {uploaded_file.name}<br>
                        <strong>Size:</strong> {file_size:.2f} MB<br>
                        <strong>Type:</strong> {file_ext.upper()} file
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Show appropriate message based on file type
                    if file_ext in ['.csv', '.json', '.xlsx', '.xls']:
                        st.info(f"📊 {uploaded_file.name} will be imported into a new SQLite database")
                        if file_ext == '.csv':
                            st.caption("CSV files will be imported as a single table")
                        elif file_ext == '.json':
                            st.caption("JSON files will be imported as a single table")
                        elif file_ext in ['.xlsx', '.xls']:
                            st.caption("Excel files will import each sheet as a separate table")
                    elif file_ext == '.sql':
                        st.info("🗃️ SQL dump will be imported into a new SQLite database")
                        st.caption("SQL files will be executed to create the database structure")
                    else:
                        st.info(f"🗄️ {uploaded_file.name} will be connected directly")
                        st.caption("SQLite database files are used directly")
                    
                    # Warn about large files
                    if file_size > 50:  # 50MB
                        st.warning("⚠️ Large file detected. Import may take a while.")
                    elif file_size > 10:  # 10MB
                        st.info("⏳ Medium file size - import may take a few seconds")
                    
                    if st.button("Import File", type="primary", key="import_file"):
                        with st.spinner("Importing file..."):
                            # Save uploaded file temporarily
                            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                                tmp_file.write(uploaded_file.getvalue())
                                temp_path = tmp_file.name
                            
                            success = st.session_state.db_manager.import_database_file(
                                temp_path, connection_name
                            )
                            
                            if success:
                                st.session_state.active_db = connection_name
                                schema_info = st.session_state.db_manager.get_schema_info(connection_name)
                                st.session_state.schema_info = schema_info
                                st.session_state.gemini.update_schema(schema_info)
                                
                                # Show import summary
                                table_count = len(schema_info.get('tables', {}))
                                if table_count > 0:
                                    table_names = list(schema_info['tables'].keys())
                                    st.success(f"✅ {uploaded_file.name} imported successfully!")
                                    st.info(f"📊 Found {table_count} tables: {', '.join(table_names)}")
                                else:
                                    st.success(f"✅ {uploaded_file.name} imported successfully!")
                                
                                # Clean up temp file
                                try:
                                    os.unlink(temp_path)
                                except:
                                    pass
                                st.rerun()
                            else:
                                # Clean up temp file on failure
                                try:
                                    os.unlink(temp_path)
                                except:
                                    pass
        
        # Active Connections Management
        if st.session_state.db_manager.connections:
            st.subheader("ACTIVE CONNECTIONS")
            
            for conn_name in st.session_state.db_manager.connections.keys():
                conn_info = st.session_state.db_manager.get_connection_info(conn_name)
                db_type = conn_info.get('type', 'Unknown')
                db_name = conn_info.get('database', 'Unknown')
                
                # Create a nice display name
                if db_type == 'sqlite':
                    if db_name.endswith('.db'):
                        display_name = f"📁 {db_name}"
                    else:
                        display_name = f"📁 {db_name}.db"
                else:
                    display_name = f"🖥️ {db_name} ({db_type})"
                
                # Connection card
                col1, col2 = st.columns([3, 1])
                with col1:
                    is_active = " 🟢" if st.session_state.active_db == conn_name else ""
                    if st.button(f"{display_name}{is_active}", key=f"select_{conn_name}", use_container_width=True):
                        st.session_state.active_db = conn_name
                        schema_info = st.session_state.db_manager.get_schema_info(conn_name)
                        st.session_state.schema_info = schema_info
                        st.session_state.gemini.update_schema(schema_info)
                        st.rerun()
                with col2:
                    if st.button("❌", key=f"disconnect_{conn_name}", help=f"Disconnect from {conn_name}"):
                        st.session_state.db_manager.disconnect(conn_name)
                        st.success(f"Disconnected from {conn_name}")
                        st.rerun()
        
        # AI Settings
        st.markdown("---")
        st.subheader("🤖 AI Settings")
        allow_destructive = st.checkbox("Allow Destructive Operations", value=False, 
                                       help="Allow DELETE, DROP, ALTER operations")
        confidence_threshold = st.slider("Confidence Threshold", 0.1, 1.0, 0.8, 
                                        help="Minimum confidence for auto-execution")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Refresh Schema", use_container_width=True):
                if st.session_state.active_db:
                    schema_info = st.session_state.db_manager.get_schema_info(st.session_state.active_db)
                    st.session_state.schema_info = schema_info
                    st.session_state.gemini.update_schema(schema_info)
                    st.success("Schema refreshed!")
                else:
                    st.warning("No active database connection")
        
        with col2:
            if st.button("🧹 Cleanup Temp Files", use_container_width=True):
                st.session_state.db_manager.cleanup_temp_files()
                st.success("Temporary files cleaned up!")
    
    # Main Content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("CHAT")
        
        # Active database info
        if st.session_state.active_db:
            conn_info = st.session_state.db_manager.get_connection_info(st.session_state.active_db)
            db_type = conn_info.get('type', 'Unknown')
            db_name = conn_info.get('database', 'Unknown')
            
            if db_type == 'sqlite':
                # Extract just the filename for display
                display_name = os.path.basename(db_name)
                if not display_name:
                    display_name = "Memory Database"
                icon = "📁"
            else:
                display_name = f"{db_name} ({db_type})"
                icon = "🖥️"
            
            st.markdown(f"**ACTIVE DB:** {icon} {display_name}")
            
            # Show connection details in expander
            with st.expander("Connection Details"):
                st.write(f"**Type:** {db_type}")
                st.write(f"**Database:** {db_name}")
                if db_type != 'sqlite':
                    st.write(f"**Host:** {conn_info.get('host', 'N/A')}")
                    st.write(f"**Port:** {conn_info.get('port', 'N/A')}")
                
                # Show table count
                if st.session_state.schema_info and st.session_state.schema_info.get('tables'):
                    table_count = len(st.session_state.schema_info['tables'])
                    st.write(f"**Tables:** {table_count}")
        else:
            st.warning("⚠️ No active database connection. Connect to a database in the sidebar.")
            st.info("💡 You can:")
            st.write("-  Connect to a database server (MySQL, PostgreSQL, etc.)")
            st.write("-  Import a SQLite database file")
            st.write("-  Upload data files (CSV, JSON, Excel) to create a database")
        
        # Query input
        natural_language_query = st.text_area(
            "Enter your question in natural language:",
            placeholder="e.g., Show me all customers from London who made purchases last month\nOr: List the top 5 products by sales\nOr: Find employees in the Engineering department",
            height=100,
            help="Ask questions about your data in plain English"
        )
        
        col1_1, col1_2, col1_3 = st.columns([1, 1, 1])
        with col1_1:
            generate_sql = st.button("Generate SQL", type="primary", use_container_width=True,
                                   help="Generate SQL without executing")
        with col1_2:
            execute_direct = st.button("Generate & Execute", use_container_width=True,
                                     help="Generate SQL and execute if safe and confident")
        with col1_3:
            clear_chat = st.button("Clear", use_container_width=True,
                                 help="Clear the current query")
        
        if clear_chat:
            natural_language_query = ""
            st.rerun()
        
        # SQL Generation and Execution
        if generate_sql or execute_direct:
            if not natural_language_query:
                st.warning("Please enter a natural language query")
            elif not st.session_state.active_db:
                st.warning("Please connect to a database first")
            else:
                with st.spinner("🧠 Generating SQL..."):
                    # Create command payload
                    from .gemini_sql_generator import CommandPayload
                    
                    # Auto-detect dialect based on database type
                    conn_info = st.session_state.db_manager.get_connection_info(st.session_state.active_db)
                    db_type = conn_info.get('type', 'mysql')
                    dialect_map = {
                        'mysql': 'mysql',
                        'postgresql': 'postgresql', 
                        'sqlite': 'sqlite',
                        'mssql': 'mssql',
                        'oracle': 'oracle'
                    }
                    dialect = dialect_map.get(db_type, 'mysql')
                    
                    payload = CommandPayload(
                        intent="query",
                        raw_nl=natural_language_query,
                        dialect=dialect,
                        allow_destructive=allow_destructive,
                        schema_snapshot=st.session_state.schema_info
                    )
                    
                    # Generate SQL
                    result = st.session_state.gemini.generate_sql(payload)
                    
                    # Display SQL
                    st.markdown("**Generated SQL:**")
                    st.markdown(f'<div class="sql-box">{result.sql}</div>', unsafe_allow_html=True)
                    
                    # Display confidence and safety
                    col_conf, col_safe, col_action = st.columns(3)
                    with col_conf:
                        confidence_color = "🟢" if result.confidence >= 0.8 else "🟡" if result.confidence >= 0.6 else "🔴"
                        st.metric("Confidence", f"{confidence_color} {result.confidence:.2f}")
                    with col_safe:
                        status = "✅ Safe" if result.safe_to_execute else "⚠️ Unsafe"
                        st.metric("Execution Status", status)
                    with col_action:
                        can_auto_execute = (result.safe_to_execute and 
                                          result.confidence >= confidence_threshold and
                                          not result.errors)
                        status = "✅ Auto" if can_auto_execute else "⏸️ Review"
                        st.metric("Action", status)
                    
                    # Show warnings/errors
                    if result.warnings:
                        for warning in result.warnings:
                            st.warning(warning)
                    if result.errors:
                        for error in result.errors:
                            st.error(error)
                    
                    # Execute if requested and conditions are met
                    if execute_direct:
                        if not result.safe_to_execute:
                            st.error("❌ Cannot execute: Query is not safe")
                        elif result.confidence < confidence_threshold:
                            st.warning(f"⚠️ Confidence ({result.confidence:.2f}) below threshold ({confidence_threshold})")
                        elif result.errors:
                            st.error("❌ Cannot execute due to errors")
                        else:
                            with st.spinner("Executing query..."):
                                execution_result = st.session_state.db_manager.execute_query(
                                    st.session_state.active_db, result.sql
                                )
                                
                                if execution_result['success']:
                                    st.success("✅ Query executed successfully!")
                                    
                                    # Display results
                                    if execution_result['data'] is not None:
                                        st.subheader("📊 Results")
                                        
                                        # Show data preview
                                        st.dataframe(execution_result['data'], use_container_width=True)
                                        
                                        # Show metrics
                                        col_metrics1, col_metrics2, col_metrics3 = st.columns(3)
                                        with col_metrics1:
                                            st.metric("Rows Returned", execution_result['row_count'])
                                        with col_metrics2:
                                            st.metric("Columns", len(execution_result['columns']))
                                        with col_metrics3:
                                            st.metric("Data Type", "Tabular")
                                        
                                        # Add to history
                                        st.session_state.query_history.append({
                                            'timestamp': datetime.now(),
                                            'natural_language': natural_language_query,
                                            'sql': result.sql,
                                            'row_count': execution_result['row_count'],
                                            'confidence': result.confidence,
                                            'columns': execution_result['columns']
                                        })
                                else:
                                    st.error(f"❌ Execution failed: {execution_result['error']}")
    
    with col2:
        st.subheader("📊 Schema Explorer")
        if st.session_state.schema_info and st.session_state.schema_info.get('tables'):
            from .schema_explorer import SchemaExplorer
            SchemaExplorer.display_schema(st.session_state.schema_info)
        else:
            st.info("Connect to a database to view schema")
            st.caption("The schema explorer shows tables, columns, and relationships")
    
    # Additional Tabs
    if st.session_state.query_history:
        tab1, tab2, tab3 = st.tabs(["📜 Query History", "📈 Analytics", "💾 Export"])
        
        with tab1:
            st.subheader("Query History")
            st.caption(f"Showing last {min(10, len(st.session_state.query_history))} of {len(st.session_state.query_history)} queries")
            
            for i, history_item in enumerate(reversed(st.session_state.query_history[-10:])):
                with st.expander(f"Query {len(st.session_state.query_history) - i} - {history_item['timestamp'].strftime('%H:%M:%S')}"):
                    st.write(f"**Question:** {history_item['natural_language']}")
                    st.code(history_item['sql'], language='sql')
                    
                    col_hist1, col_hist2, col_hist3 = st.columns(3)
                    with col_hist1:
                        st.write(f"**Rows:** {history_item['row_count']}")
                    with col_hist2:
                        st.write(f"**Confidence:** {history_item['confidence']:.2f}")
                    with col_hist3:
                        st.write(f"**Columns:** {len(history_item.get('columns', []))}")
                    
                    # Re-execute button
                    if st.button(f"Re-execute", key=f"re_exec_{i}"):
                        execution_result = st.session_state.db_manager.execute_query(
                            st.session_state.active_db, history_item['sql']
                        )
                        if execution_result['success'] and execution_result['data'] is not None:
                            st.dataframe(execution_result['data'], use_container_width=True)
        
        with tab2:
            st.subheader("Analytics")
            
            # Basic metrics
            col_anal1, col_anal2, col_anal3, col_anal4 = st.columns(4)
            total_queries = len(st.session_state.query_history)
            avg_confidence = sum(h['confidence'] for h in st.session_state.query_history) / total_queries
            total_rows = sum(h['row_count'] for h in st.session_state.query_history)
            success_rate = sum(1 for h in st.session_state.query_history if h['confidence'] >= 0.7) / total_queries
            
            with col_anal1:
                st.metric("Total Queries", total_queries)
            with col_anal2:
                st.metric("Avg Confidence", f"{avg_confidence:.2f}")
            with col_anal3:
                st.metric("Total Rows", total_rows)
            with col_anal4:
                st.metric("Success Rate", f"{success_rate:.1%}")
            
            # Confidence distribution chart
            if total_queries > 1:
                confidences = [h['confidence'] for h in st.session_state.query_history]
                fig = px.histogram(x=confidences, nbins=10, 
                                 title="Confidence Distribution",
                                 labels={'x': 'Confidence', 'y': 'Number of Queries'})
                st.plotly_chart(fig, use_container_width=True)
        
        with tab3:
            st.subheader("Export Data")
            st.info("Export your query results and history")
            
            if st.session_state.query_history:
                # Export query history
                history_df = pd.DataFrame(st.session_state.query_history)
                
                col_exp1, col_exp2 = st.columns(2)
                with col_exp1:
                    if st.button("Export Query History CSV"):
                        csv = history_df.to_csv(index=False)
                        st.download_button(
                            label="Download CSV",
                            data=csv,
                            file_name="query_history.csv",
                            mime="text/csv"
                        )
                with col_exp2:
                    if st.button("Export Query History JSON"):
                        json_str = history_df.to_json(orient='records', indent=2)
                        st.download_button(
                            label="Download JSON",
                            data=json_str,
                            file_name="query_history.json",
                            mime="application/json"
                        )
            else:
                st.info("No query history to export")
                
    else:
        st.info("Execute some queries to see history and analytics")
        
        # Quick start examples
        st.subheader("💡 Quick Start Examples")
        examples = [
            "Show me all employees",
            "List customers from London", 
            "Find the top 5 products by sales",
            "Show employees and their departments",
            "Calculate total sales by month"
        ]
        
        for example in examples:
            if st.button(f"\"{example}\"", key=f"example_{example}", use_container_width=True):
                # This would need to be handled by setting the query input
                st.info(f"Try typing: {example}")

# This ensures the main function runs when the module is executed directly
if __name__ == "__main__":
    main()