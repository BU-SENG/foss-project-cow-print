"""
AetherDB Admin Console - Main Application
Description: Entry point that integrates UI components and business logic
"""

import streamlit as st
from datetime import datetime

# Import UI components
from ui_components import setup_page_config, apply_custom_css, initialize_session_state

# Setup
setup_page_config()
apply_custom_css()
initialize_session_state()

# Header
st.markdown("""
<div class="main-header">
    <h1>AETHER DB - Admin Console</h1>
</div>
""", unsafe_allow_html=True)

# Create two columns for the layout
col1, col2 = st.columns([1, 1])

# Left column - Current Connections
with col1:
    st.markdown('<div class="section-box">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">Current Connections</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-content">', unsafe_allow_html=True)
    
    # Display connections
    for idx, conn in enumerate(st.session_state.connections):
        # Connection display
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
    
    st.markdown('</div></div>', unsafe_allow_html=True)
    
    # Add New Connection Section
    st.markdown('<div class="section-box">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">Add New Connection</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-content">', unsafe_allow_html=True)
    
    # Form for adding new connection
    db_type = st.selectbox(
        "DATABASE TYPE",
        ["MySQL", "PostgreSQL", "SQLite", "MongoDB"],
        key="db_type"
    )
    
    conn_name = st.text_input("CONNECTION NAME", placeholder="my_database", key="conn_name")
    
    col_host, col_port = st.columns([2, 1])
    with col_host:
        host = st.text_input("HOST", placeholder="localhost", key="host")
    with col_port:
        port = st.text_input("PORT", placeholder="3306", key="port")
    
    username = st.text_input("USERNAME", placeholder="root", key="username")
    password = st.text_input("PASSWORD", type="password", placeholder="••••••••", key="password")
    
    st.write("")  # Add spacing
    
    col_cancel, col_save = st.columns([1, 1])
    with col_cancel:
        if st.button("CANCEL", use_container_width=True, type="secondary"):
            st.rerun()
    with col_save:
        if st.button("SAVE CONNECTION", use_container_width=True):
            if conn_name and host:
                new_conn = {
                    "name": conn_name,
                    "type": db_type,
                    "host": f"{host}:{port}" if port else host,
                    "status": "active"
                }
                st.session_state.connections.append(new_conn)
                st.session_state.logs.insert(0, {
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "type": "info",
                    "message": f"New connection '{conn_name}' added."
                })
                st.success(f"Connection '{conn_name}' added successfully!")
                st.rerun()
            else:
                st.error("Please fill in Connection Name and Host")
    
    st.markdown('</div></div>', unsafe_allow_html=True)

# Right column - System Logs
with col2:
    st.markdown('<div class="section-box">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">System Logs</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-content"><div class="log-container">', unsafe_allow_html=True)
    
    # Display logs
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