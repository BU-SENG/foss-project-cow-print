import streamlit as st
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="AetherDB - Admin Console",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS matching the cyberpunk/terminal design
st.markdown("""
<style>
    /* Import Courier Prime for terminal look */
    @import url('https://fonts.googleapis.com/css2?family=Courier+Prime:wght@400;700&family=Share+Tech+Mono&display=swap');
    
    /* Global Styles */
    * {
        font-family: 'Courier Prime', 'Courier New', monospace;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Main container - dark background */
    .stApp {
        background: linear-gradient(135deg, #0a0e1a 0%, #151922 100%);
    }
    
    /* Remove default padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Make text visible */
    h1, h2, h3, h4, h5, h6, p, span, div, label {
        color: #00ff41 !important;
    }
    
    /* Main header with angled corners */
    .main-header {
        background: linear-gradient(135deg, #1a3a2e 0%, #0d1f1a 100%);
        border: 2px solid #00ff41;
        padding: 1rem 2rem;
        margin-bottom: 2rem;
        clip-path: polygon(0 0, calc(100% - 40px) 0, 100% 40px, 100% 100%, 0 100%);
        position: relative;
    }
    
    .main-header h1 {
        color: #00ff41 !important;
        font-weight: 700;
        font-size: 1.5rem;
        margin: 0;
        letter-spacing: 3px;
        text-transform: uppercase;
        font-family: 'Share Tech Mono', monospace;
    }
    
    /* Section containers with angled corners */
    .section-box {
        background: linear-gradient(135deg, #0f1f1a 0%, #0a1612 100%);
        border: 2px solid #00ff41;
        padding: 0;
        margin-bottom: 1.5rem;
        position: relative;
        box-shadow: 0 0 20px rgba(0, 255, 65, 0.3);
    }
    
    /* Section headers with angled design */
    .section-header {
        background: linear-gradient(90deg, #00ff41 0%, #00cc33 100%);
        color: #000000 !important;
        padding: 0.75rem 1.5rem;
        font-weight: 700;
        font-size: 1.1rem;
        letter-spacing: 2px;
        text-transform: uppercase;
        clip-path: polygon(0 0, calc(100% - 30px) 0, 100% 100%, 0 100%);
        margin-bottom: 0;
    }
    
    /* Section content */
    .section-content {
        padding: 1.5rem;
        color: #00ff41 !important;
    }
    
    /* Connection items */
    .connection-item {
        background: rgba(0, 255, 65, 0.05);
        border: 1px solid #00ff41;
        padding: 1rem;
        margin-bottom: 0.75rem;
        font-family: 'Courier Prime', monospace;
    }
    
    .connection-name {
        color: #00ff41 !important;
        font-size: 0.95rem;
    }
    
    .connection-details {
        color: #00cc33 !important;
        font-size: 0.85rem;
    }
    
    /* Log entries */
    .log-entry {
        padding: 0.5rem 0;
        border-bottom: 1px solid rgba(0, 255, 65, 0.2);
        font-size: 0.85rem;
        line-height: 1.6;
        color: #00ff41 !important;
    }
    
    .log-timestamp {
        color: #00cc33 !important;
    }
    
    .log-message {
        color: #00ff41 !important;
    }
    
    .log-error {
        color: #ff4444 !important;
    }
    
    /* Input fields */
    .stTextInput input, .stSelectbox select, .stTextInput > div > div > input {
        background: rgba(0, 0, 0, 0.5) !important;
        border: 2px solid #00ff41 !important;
        color: #00ff41 !important;
        font-family: 'Courier Prime', monospace !important;
        padding: 0.5rem !important;
        font-size: 0.9rem !important;
    }
    
    .stTextInput input::placeholder {
        color: rgba(0, 255, 65, 0.5) !important;
    }
    
    .stTextInput input:focus, .stSelectbox select:focus {
        border-color: #00ff41 !important;
        box-shadow: 0 0 10px rgba(0, 255, 65, 0.5) !important;
    }
    
    .stTextInput label, .stSelectbox label {
        color: #00ff41 !important;
        font-family: 'Courier Prime', monospace !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-size: 0.85rem !important;
        font-weight: 700 !important;
    }
    
    /* Select box options */
    .stSelectbox div[data-baseweb="select"] > div {
        background: rgba(0, 0, 0, 0.5) !important;
        border: 2px solid #00ff41 !important;
        color: #00ff41 !important;
    }
    
    /* Buttons */
    .stButton > button {
        background: #00ff41 !important;
        color: #000000 !important;
        border: none !important;
        padding: 0.6rem 2rem !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-family: 'Courier Prime', monospace !important;
        font-size: 0.85rem !important;
        transition: all 0.3s ease;
        box-shadow: 0 0 15px rgba(0, 255, 65, 0.5);
    }
    
    .stButton > button:hover {
        background: #00cc33 !important;
        box-shadow: 0 0 25px rgba(0, 255, 65, 0.7);
        transform: translateY(-2px);
    }
    
    /* Small buttons (EDIT/DELETE) */
    button[kind="secondary"] {
        background: transparent !important;
        color: #00ff41 !important;
        border: 2px solid #00ff41 !important;
        padding: 0.4rem 1rem !important;
        font-size: 0.75rem !important;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: #0a0e1a;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #00ff41;
        border-radius: 5px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #00cc33;
    }
    
    /* Log container max height */
    .log-container {
        max-height: 400px;
        overflow-y: auto;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
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

