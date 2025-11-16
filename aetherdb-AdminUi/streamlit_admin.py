"""
AetherDB Admin Console - UI Components (Purple Gradient Theme)
Author: [Your Name]
Description: Contains page configuration, CSS styling, and session state initialization
"""

import streamlit as st

def setup_page_config():
    """Configure Streamlit page settings"""
    st.set_page_config(
        page_title="AetherDB - Admin Console",
        page_icon="🗄️",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

def apply_custom_css():
    """Apply custom CSS styling for purple gradient theme"""
    st.markdown("""
    <style>
        /* Import Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Poppins:wght@400;500;600;700&display=swap');
        
        /* Global Styles */
        * {
            font-family: 'Inter', 'Poppins', sans-serif;
        }
        
        /* Hide Streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Main container - Purple gradient background */
        .stApp {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
            background-attachment: fixed;
        }
        
        /* Remove default padding */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1400px;
        }
        
        /* Make text visible */
        h1, h2, h3, h4, h5, h6 {
            color: #ffffff !important;
        }
        
        p, span, div, label {
            color: #f0f0f0 !important;
        }
        
        /* Main header */
        .main-header {
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.9) 0%, rgba(118, 75, 162, 0.9) 100%);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            padding: 1.5rem 2rem;
            border-radius: 20px;
            margin-bottom: 2rem;
            box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
        }
        
        .main-header h1 {
            color: #ffffff !important;
            font-weight: 700;
            font-size: 2rem;
            margin: 0;
            letter-spacing: 1px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
        }
        
        /* Section containers */
        .section-box {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            padding: 0;
            margin-bottom: 1.5rem;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        
        /* Section headers */
        .section-header {
            background: linear-gradient(90deg, rgba(102, 126, 234, 0.8) 0%, rgba(118, 75, 162, 0.8) 100%);
            color: #ffffff !important;
            padding: 1rem 1.5rem;
            font-weight: 600;
            font-size: 1.1rem;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        /* Section content */
        .section-content {
            padding: 1.5rem;
            color: #ffffff !important;
        }
        
        /* Connection items */
        .connection-item {
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(5px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            padding: 1rem;
            margin-bottom: 0.75rem;
            border-radius: 10px;
            transition: all 0.3s ease;
        }
        
        .connection-item:hover {
            background: rgba(255, 255, 255, 0.2);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        
        .connection-name {
            color: #ffffff !important;
            font-size: 0.95rem;
            font-weight: 500;
        }
        
        /* Log entries */
        .log-entry {
            padding: 0.75rem;
            margin-bottom: 0.5rem;
            border-radius: 8px;
            font-size: 0.85rem;
            line-height: 1.6;
            color: #ffffff !important;
            background: rgba(255, 255, 255, 0.05);
            border-left: 3px solid rgba(102, 126, 234, 0.5);
        }
        
        .log-timestamp {
            color: #e0e0ff !important;
            font-weight: 600;
        }
        
        .log-message {
            color: #f0f0f0 !important;
        }
        
        .log-error {
            color: #ff6b6b !important;
            background: rgba(255, 107, 107, 0.1);
            border-left-color: #ff6b6b;
        }
        
        /* Input fields */
        .stTextInput input, .stSelectbox select, .stTextInput > div > div > input {
            background: rgba(255, 255, 255, 0.15) !important;
            backdrop-filter: blur(5px) !important;
            border: 1px solid rgba(255, 255, 255, 0.3) !important;
            border-radius: 10px !important;
            color: #ffffff !important;
            padding: 0.75rem !important;
            font-size: 0.9rem !important;
        }
        
        .stTextInput input::placeholder {
            color: rgba(255, 255, 255, 0.5) !important;
        }
        
        .stTextInput input:focus, .stSelectbox select:focus {
            border-color: rgba(240, 147, 251, 0.8) !important;
            box-shadow: 0 0 0 3px rgba(240, 147, 251, 0.2) !important;
            background: rgba(255, 255, 255, 0.2) !important;
        }
        
        .stTextInput label, .stSelectbox label {
            color: #ffffff !important;
            font-weight: 600 !important;
            font-size: 0.85rem !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.5rem !important;
        }
        
        /* Select box dropdown */
        .stSelectbox div[data-baseweb="select"] > div {
            background: rgba(255, 255, 255, 0.15) !important;
            border: 1px solid rgba(255, 255, 255, 0.3) !important;
            color: #ffffff !important;
        }
        
        /* Buttons */
        .stButton > button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 10px !important;
            padding: 0.75rem 2rem !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 0.85rem !important;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        
        .stButton > button:hover {
            background: linear-gradient(135deg, #764ba2 0%, #667eea 100%) !important;
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
            transform: translateY(-2px);
        }
        
        /* Secondary buttons (EDIT/DELETE) */
        button[kind="secondary"] {
            background: rgba(255, 255, 255, 0.2) !important;
            color: #ffffff !important;
            border: 1px solid rgba(255, 255, 255, 0.4) !important;
            padding: 0.5rem 1rem !important;
            font-size: 0.75rem !important;
        }
        
        button[kind="secondary"]:hover {
            background: rgba(255, 255, 255, 0.3) !important;
            border-color: rgba(255, 255, 255, 0.6) !important;
        }
        
        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 12px;
            height: 12px;
        }
        
        ::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px;
            border: 2px solid rgba(255, 255, 255, 0.1);
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: linear-gradient(135deg, #764ba2 0%, #f093fb 100%);
        }
        
        /* Log container with scrolling */
        .log-container {
            max-height: 450px;
            overflow-y: auto;
            padding-right: 0.5rem;
        }
        
        /* Info/Success messages */
        .stSuccess {
            background: rgba(72, 187, 120, 0.2) !important;
            color: #ffffff !important;
            border-left: 4px solid #48bb78;
        }
        
        .stError {
            background: rgba(255, 107, 107, 0.2) !important;
            color: #ffffff !important;
            border-left: 4px solid #ff6b6b;
        }
        
        .stInfo {
            background: rgba(102, 126, 234, 0.2) !important;
            color: #ffffff !important;
            border-left: 4px solid #667eea;
        }
        
        /* Glass morphism effect */
        .glass-effect {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 15px;
        }
    </style>
    """, unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state with default data"""
    if 'connections' not in st.session_state:
        st.session_state.connections = [
            {
                "name": "studentdb",
                "type": "MySQL",
                "host": "localhost:3306",
                "status": "active"
            },
            {
                "name": "analytics_db",
                "type": "PostgreSQL",
                "host": "10.0.1.5:5432",
                "status": "active"
            },
            {
                "name": "local_test.db",
                "type": "SQLite",
                "host": "",
                "status": "active"
            }
        ]

    if 'logs' not in st.session_state:
        st.session_state.logs = [
            {"time": "2025-11-02 17:55:01", "type": "info", "message": "AetherDB service started."},
            {"time": "2025-11-02 17:55:04", "type": "info", "message": "Scanned schema for 'studentdb'."},
            {"time": "2025-11-02 17:56:10", "type": "info", "message": "User 'admin' executed query."},
            {"time": "2025-11-02 17:56:15", "type": "error", "message": "Connection to 'analytics_db' failed."}
        ]