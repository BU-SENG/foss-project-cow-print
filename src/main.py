import os
import sys
import streamlit as st
from dotenv import load_dotenv

# Add the src directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

def main():
    """Main entry point for the AETHER DB - AI Database System"""
    # Initialize session state FIRST
    if 'db_manager' not in st.session_state:
        from src.ai_database_query.database_manager import DatabaseManager
        st.session_state.db_manager = DatabaseManager()
    
    if 'gemini' not in st.session_state:
        from src.ai_database_query.gemini_sql_generator import GeminiSQLGenerator
        st.session_state.gemini = GeminiSQLGenerator()
    
    if 'query_history' not in st.session_state:
        st.session_state.query_history = []
    
    if 'active_db' not in st.session_state:
        st.session_state.active_db = None
    
    if 'schema_info' not in st.session_state:
        st.session_state.schema_info = {}
    
    # Load environment variables
    load_dotenv()
    
    # Set page config
    st.set_page_config(
        page_title="AETHER DB - AI Database Query System",
        page_icon="🐄",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Check if API key is configured
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key or api_key == 'your_actual_api_key_here':
        st.error("""
        🔧 **Setup Required**
        
        Please configure your Gemini API key in the `.env` file:
        
        ```env
        GEMINI_API_KEY=your_actual_gemini_api_key_here
        GEMINI_MODEL=gemini-2.0-flash-001
        DEFAULT_DIALECT=mysql
        ```
        
        Get your API key from: https://aistudio.google.com/
        """)
        return
    
    # Add cleanup on app close (theoretical - Streamlit doesn't have proper shutdown)
    if st.sidebar.button("🧹 Cleanup Temporary Files"):
        st.session_state.db_manager.cleanup_temp_files()
        st.success("Temporary files cleaned up!")
    
    # Import and run the main app
    from src.ai_database_query.app import main as ai_database_app
    ai_database_app()

if __name__ == "__main__":
    main()