import streamlit as st
import json
import pandas as pd
import os
from dotenv import load_dotenv

from schema_awareness import SchemaAwarenessModule
from db_executor import DatabaseExecutor

# Load env
load_dotenv()

# Admin credentials from env
ADMIN_USER = os.getenv("ADMIN_USERNAME")
ADMIN_PASS = os.getenv("ADMIN_PASSWORD")

# Session state setup
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

st.set_page_config(
    page_title="AetherDB Admin Console",
    layout="wide"
)

# ---------------- Login Function ----------------

def login_form():
    st.title("Admin Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == ADMIN_USER and password == ADMIN_PASS:
            st.session_state.authenticated = True
            st.success("Login successful")
            st.rerun()
        else:
            st.error("Invalid credentials")

# -------------- Logout Function ---------------

def logout():
    st.session_state.authenticated = False
    st.success("Logged out")
    st.rerun()

# -------------- Protected Access --------------

if not st.session_state.authenticated:
    login_form()
    st.stop()

# -------------- Sidebar Navigation --------------

st.sidebar.title("Admin Panel")
if st.sidebar.button("Logout"):
    logout()

st.sidebar.header("Navigation")
page = st.sidebar.radio(
    "Go to:",
    ["Dashboard", "DB Manager", "Schema Viewer", "Safety Controls", "Model Settings", "Logs and History"]
)

# Initialize modules
sam = SchemaAwarenessModule()

# ---------------- Pages ----------------

# Dashboard Page
if page == "Dashboard":
    st.title("AetherDB Admin Console")
    st.subheader("System Statistics")

    log_path = "query_history.csv"
    if os.path.exists(log_path):
        log_df = pd.read_csv(log_path)
        total = len(log_df)
        success = (log_df.status == "SUCCESS").sum()
        failed = (log_df.status == "FAILED").sum()
        blocked = (log_df.status == "BLOCKED").sum()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Queries", total)
        col2.metric("Success", success)
        col3.metric("Failed", failed)
        col4.metric("Blocked", blocked)

        st.subheader("Status Breakdown")
        st.bar_chart(log_df.status.value_counts())
    else:
        st.warning("No query logs found")

# DB Manager Page
elif page == "DB Manager":
    st.subheader("Database Connection")

    db_type = st.selectbox("Database Type", ["mysql", "postgresql", "sqlite"])
    st.write("Enter credentials to connect")

    if db_type == "sqlite":
        path = st.text_input("Path to SQLite file", "sample.db")
        if st.button("Connect"):
            try:
                sam.connect_database(db_type, database=path)
                st.success("Connected successfully")
            except Exception as e:
                st.error(e)
    else:
        host = st.text_input("Host")
        user = st.text_input("User")
        password = st.text_input("Password")
        database = st.text_input("Database")

        if st.button("Connect"):
            try:
                sam.connect_database(db_type, host=host, user=user, password=password, database=database)
                st.success("Connected successfully")
            except Exception as e:
                st.error(e)

    if st.button("Refresh Schema"):
        try:
            sam.scan_schema()
            st.success("Schema refreshed and auto generated")
        except Exception as e:
            st.error(e)

# Schema Viewer Page
elif page == "Schema Viewer":
    st.subheader("Schema Awareness Files")

    if os.path.exists("schema.txt"):
        with open("schema.txt") as f:
            st.code(f.read())
    else:
        st.warning("No schema file found")

    if os.path.exists("schema_metadata.json"):
        with open("schema_metadata.json") as f:
            st.json(json.load(f))
    else:
        st.warning("No metadata found")

# Safety Controls Page
elif page == "Safety Controls":
    st.subheader("Safety Rules")

    destructive = st.checkbox("Allow Destructive Operations")
    dry_run = st.checkbox("Dry Run Mode")

    st.info("Destructive statements include DROP, DELETE, UPDATE, TRUNCATE")

    if st.button("Save Safety Settings"):
        conf = {"allow_destructive": destructive, "dry_run": dry_run}
        with open("safety.json", "w") as f:
            json.dump(conf, f)
        st.success("Settings saved")

# Model Settings Page
elif page == "Model Settings":
    st.subheader("AI Model Configuration")

    model = st.text_input("Gemini Model", "models/gemini-2.5-pro")
    max_chars = st.number_input("Max Schema Prompt Characters", value=14000)

    if st.button("Save Model Settings"):
        env_data = f"GEMINI_MODEL={model}\nMAX_SCHEMA_PROMPT_CHARS={max_chars}"
        with open(".env", "a") as f:
            f.write("\n" + env_data)
        st.success("Model settings updated")

# Logs and History Page
elif page == "Logs and History":
    st.subheader("Query Logs")

    log_path = "query_history.csv"
    if os.path.exists(log_path):
        log_df = pd.read_csv(log_path)
        st.dataframe(log_df, use_container_width=True)
        st.download_button("Export CSV", data=log_df.to_csv(), file_name="query_history_export.csv")
    else:
        st.warning("No logs found")
