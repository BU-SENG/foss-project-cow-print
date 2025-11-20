import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

ADMIN_USER = os.getenv("ADMIN_USERNAME")
ADMIN_PASS = os.getenv("ADMIN_PASSWORD")

st.set_page_config(page_title="Admin Console", page_icon="🔐", layout="wide")

if "admin_logged" not in st.session_state:
    st.session_state.admin_logged = False

if not st.session_state.admin_logged:
    st.title("🔐 Admin Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if u == ADMIN_USER and p == ADMIN_PASS:
            st.session_state.admin_logged = True
            st.success("Access Granted")
        else:
            st.error("Invalid login details")
    st.stop()

st.sidebar.success("Admin Access Verified")

st.title("🛡 AetherDB System Management")

tabs = st.tabs(["👥 Users", "🔑 API Keys", "📜 Logs", "🗄 DB Connections", "📊 Costs"])

with tabs[0]:
    st.subheader("User Roles")
    st.table(pd.DataFrame({"User": ["Admin", "Dev", "Analyst", "Viewer"], "Role": ["Admin", "Developer", "Analyst", "Viewer"]}))

with tabs[1]:
    st.subheader("Manage API Keys")
    if st.button("Generate New API Key"):
        st.success("New key generated and pending activation")

with tabs[2]:
    st.subheader("Query Logs")
    st.info("Real logs integration coming soon")

with tabs[3]:
    st.subheader("Connection Overview")
    st.warning("Dynamic DB status available after backend update")

with tabs[4]:
    st.subheader("API Cost Monitoring")
    st.write("Gemini API usage tracking coming soon")
