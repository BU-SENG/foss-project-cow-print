"""
AetherDB Admin Console - Business Logic
Author: [Person 2 Name]
Description: Contains UI rendering, connection management, and user interactions

INSTRUCTIONS FOR PERSON 2:
1. Create a new file: aetherdb_ui/business_logic.py
2. Copy this entire code into that file
3. Save the file
4. Test by running: python -m streamlit run aetherdb_ui/app.py
5. Push to your branch: git checkout -b person2/business-logic
6. Commit: git add aetherdb_ui/business_logic.py
7. Push: git push -u origin person2/business-logic
"""""""""

import streamlit as st
from datetime import datetime

def render_header():
    """Render the main header"""
    st.markdown("""
    <div class="main-header">
        <h1>AETHER DB</h1>
    </div>
    """, unsafe_allow_html=True)

def render_connection_item(idx, conn):
    """Render a single connection item with edit/delete buttons
    
    Args:
        idx (int): Index of the connection in the list
        conn (dict): Connection details dictionary
    """
    host_display = f" - {conn['host']}" if conn['host'] else ""
    st.markdown(f"""
    <div class="connection-item">
        <div class="connection-name">{conn['name']} ({conn['type']}){host_display}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Action buttons
    col_edit, col_del, col_space = st.columns([1, 1, 3])
    with col_edit:
        if st.button("EDIT", key=f"edit_{idx}", type="secondary"):
            st.info(f"Edit {conn['name']}")
    with col_del:
        if st.button("DELETE", key=f"del_{idx}", type="secondary"):
            st.session_state.connections = [c for i, c in enumerate(st.session_state.connections) if i != idx]
            st.rerun()

def render_current_connections():
    """Render the current connections section with all active database connections"""
    st.markdown('<div class="section-box">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">CURRENT CONNECTIONS</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-content">', unsafe_allow_html=True)
    
    # Display each connection
    for idx, conn in enumerate(st.session_state.connections):
        render_connection_item(idx, conn)
    
    st.markdown('</div></div>', unsafe_allow_html=True)

def render_add_connection_form():
    """Render the add new connection form with all input fields and buttons"""
    st.markdown('<div class="section-box">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">ADD NEW CONNECTION</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-content">', unsafe_allow_html=True)
    
    # Database type selector
    db_type = st.selectbox(
        "DATABASE TYPE",
        ["MySQL", "PostgreSQL", "SQLite", "MongoDB"],
        key="db_type"
    )
    
    # Connection name input
    conn_name = st.text_input("CONNECTION NAME", placeholder="my_database", key="conn_name")
    
    # Host and Port inputs
    col_host, col_port = st.columns([2, 1])
    with col_host:
        host = st.text_input("HOST", placeholder="localhost", key="host")
    with col_port:
        port = st.text_input("PORT", placeholder="3306", key="port")
    
    # Credentials inputs
    username = st.text_input("USERNAME", placeholder="root", key="username")
    password = st.text_input("PASSWORD", type="password", placeholder="••••••••", key="password")
    
    st.write("")  # Add spacing
    
    # Action buttons - Cancel and Save
    col_cancel, col_save = st.columns([1, 1])
    with col_cancel:
        if st.button("CANCEL", use_container_width=True, type="secondary"):
            st.rerun()
    with col_save:
        if st.button("SAVE CONNECTION", use_container_width=True):
            handle_save_connection(conn_name, db_type, host, port, username, password)
    
    st.markdown('</div></div>', unsafe_allow_html=True)

def handle_save_connection(conn_name, db_type, host, port, username, password):
    """Handle saving a new connection to the session state
    
    Args:
        conn_name (str): Name of the database connection
        db_type (str): Type of database (MySQL, PostgreSQL, etc.)
        host (str): Database host address
        port (str): Database port number
        username (str): Database username
        password (str): Database password
    """
    if conn_name and host:
        # Create new connection object
        new_conn = {
            "name": conn_name,
            "type": db_type,
            "host": f"{host}:{port}" if port else host,
            "status": "active"
        }
        
        # Add to connections list
        st.session_state.connections.append(new_conn)
        
        # Add log entry
        st.session_state.logs.insert(0, {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": "info",
            "message": f"New connection '{conn_name}' added."
        })
        
        # Show success message
        st.success(f"Connection '{conn_name}' added successfully!")
        st.rerun()
    else:
        # Show error if required fields are missing
        st.error("Please fill in Connection Name and Host")

def render_system_logs():
    """Render the system logs section showing all logged events"""
    st.markdown('<div class="section-box">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">SYSTEM LOGS</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-content"><div class="log-container">', unsafe_allow_html=True)
    
    # Display each log entry
    for log in st.session_state.logs:
        log_class = "log-error" if log['type'] == "error" else "log-message"
        error_tag = " [ERROR]" if log['type'] == "error" else ""
        st.markdown(f"""
        <div class="log-entry">
            <span class="log-timestamp">[{log['time']}]</span>
            <span class="{log_class}">{error_tag} {log['message']}</span>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div></div></div>', unsafe_allow_html=True)

def render_main_interface():
    """Main function that renders the complete admin console interface
    
    This function orchestrates all the UI components:
    - Header
    - Two-column layout
    - Current connections (left column)
    - Add connection form (left column)
    - System logs (right column)
    """
    # Render header
    render_header()
    
    # Create two-column layout
    col1, col2 = st.columns([1, 1])
    
    # Left column - Connections and form
    with col1:
        render_current_connections()
        render_add_connection_form()
    
    # Right column - System logs
    with col2:
        render_system_logs()


# TESTING INSTRUCTIONS:
# =====================
# After creating this file, test it by:
# 1. Make sure Person 1 has created ui_components.py
# 2. Update app.py to import both files (see integration guide)
# 3. Run: python -m streamlit run aetherdb_ui/app.py
# 4. Test all buttons and form inputs
# 5. Verify connections can be added and deleted
# 6. Check that logs update correctly

# GIT WORKFLOW:
# =============
# git checkout -b person2/business-logic
# git add aetherdb_ui/business_logic.py
# git commit -m "Add business logic for AetherDB admin console
# 
# - Implement connection management
# - Add form handling and validation
# - Create log rendering system
# - Add EDIT/DELETE functionality for connections"
# git push -u origin person2/business-logic