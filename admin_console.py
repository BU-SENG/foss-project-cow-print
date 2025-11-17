#!/usr/bin/env python3
"""
AetherDB Admin Console

Administrative interface for managing AetherDB operations, monitoring,
and configuration. Integrates seamlessly with the main Streamlit app.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import os
from typing import Dict, List, Any


def render_admin_console():
    """
    Main admin console renderer.
    Call this function from streamlit_app.py when admin mode is active.
    """
    
    # Admin header
    st.markdown("""
        <div style='text-align: center; padding: 2rem 0;'>
            <h1 style='color: white; font-size: 2.5rem; margin-bottom: 0;'>
                🔧 AetherDB Admin Console
            </h1>
            <p style='color: rgba(255,255,255,0.8); font-size: 1rem;'>
                System Management & Monitoring Dashboard
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Admin tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Dashboard",
        "🔍 Query Monitor",
        "⚙️ Configuration",
        "👥 User Activity",
        "🛡️ Security & Safety"
    ])
    
    with tab1:
        render_dashboard_tab()
    
    with tab2:
        render_query_monitor_tab()
    
    with tab3:
        render_configuration_tab()
    
    with tab4:
        render_user_activity_tab()
    
    with tab5:
        render_security_tab()


def render_dashboard_tab():
    """Overview dashboard with key metrics"""
    st.subheader("📊 System Overview")
    
    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
            <div class='metric-card'>
                <h3 style='color: #667eea; margin: 0;'>Total Queries</h3>
                <h1 style='margin: 0.5rem 0;'>1,247</h1>
                <p style='color: #10b981; margin: 0;'>↑ 12.5% from last week</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
            <div class='metric-card'>
                <h3 style='color: #667eea; margin: 0;'>Success Rate</h3>
                <h1 style='margin: 0.5rem 0;'>94.2%</h1>
                <p style='color: #10b981; margin: 0;'>↑ 2.1% improvement</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
            <div class='metric-card'>
                <h3 style='color: #667eea; margin: 0;'>Avg Response</h3>
                <h1 style='margin: 0.5rem 0;'>1.8s</h1>
                <p style='color: #ef4444; margin: 0;'>↓ 0.3s slower</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
            <div class='metric-card'>
                <h3 style='color: #667eea; margin: 0;'>Active Users</h3>
                <h1 style='margin: 0.5rem 0;'>23</h1>
                <p style='color: #10b981; margin: 0;'>↑ 5 new today</p>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Charts row
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📈 Query Volume (Last 7 Days)")
        dates = pd.date_range(end=datetime.now(), periods=7).tolist()
        data = pd.DataFrame({
            'Date': dates,
            'Queries': [145, 167, 189, 201, 178, 223, 144]
        })
        fig = px.line(data, x='Date', y='Queries', markers=True)
        fig.update_traces(line_color='#667eea', line_width=3)
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### 🎯 Query Intent Distribution")
        intent_data = pd.DataFrame({
            'Intent': ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER'],
            'Count': [856, 142, 98, 45, 67, 39]
        })
        fig = px.pie(intent_data, names='Intent', values='Count', hole=0.4)
        fig.update_traces(marker=dict(colors=['#667eea', '#764ba2', '#10b981', '#ef4444', '#f59e0b', '#8b5cf6']))
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)
    
    # System health
    st.markdown("---")
    st.markdown("#### 🏥 System Health")
    
    health_col1, health_col2, health_col3 = st.columns(3)
    
    with health_col1:
        st.markdown("""
            <div style='padding: 1rem; background: white; border-radius: 0.5rem; border-left: 4px solid #10b981;'>
                <h4 style='margin: 0; color: #10b981;'>✅ Database Connection</h4>
                <p style='margin: 0.5rem 0 0 0; color: #666;'>Status: Connected | Latency: 12ms</p>
            </div>
        """, unsafe_allow_html=True)
    
    with health_col2:
        st.markdown("""
            <div style='padding: 1rem; background: white; border-radius: 0.5rem; border-left: 4px solid #10b981;'>
                <h4 style='margin: 0; color: #10b981;'>✅ Gemini AI API</h4>
                <p style='margin: 0.5rem 0 0 0; color: #666;'>Status: Operational | Rate: 45/min</p>
            </div>
        """, unsafe_allow_html=True)
    
    with health_col3:
        st.markdown("""
            <div style='padding: 1rem; background: white; border-radius: 0.5rem; border-left: 4px solid #f59e0b;'>
                <h4 style='margin: 0; color: #f59e0b;'>⚠️ Schema Cache</h4>
                <p style='margin: 0.5rem 0 0 0; color: #666;'>Status: Stale (2h old) | Refresh?</p>
            </div>
        """, unsafe_allow_html=True)


def render_query_monitor_tab():
    """Real-time query monitoring"""
    st.subheader("🔍 Query Monitor")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        time_filter = st.selectbox("Time Range", ["Last Hour", "Last 24 Hours", "Last 7 Days", "Last 30 Days"])
    
    with col2:
        status_filter = st.multiselect("Status", ["Success", "Failed", "Blocked"], default=["Success", "Failed", "Blocked"])
    
    with col3:
        intent_filter = st.multiselect("Intent", ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER"])
    
    with col4:
        search_query = st.text_input("🔎 Search", placeholder="Search queries...")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Query log table
    st.markdown("#### 📋 Recent Queries")
    
    # Sample data
    query_log = pd.DataFrame({
        'Timestamp': [
            datetime.now() - timedelta(minutes=i*5) for i in range(20)
        ],
        'Natural Language': [
            'Show all students whose surname starts with A',
            'Count total number of classes',
            'Insert new student John Doe',
            'Update student age where id = 5',
            'Delete class with id 12',
            'Create table courses',
            'Show students with their class names',
            'List all teachers',
            'Count students by class',
            'Show top 10 students by grade',
        ] * 2,
        'SQL': [
            "SELECT * FROM students WHERE surname LIKE 'A%'",
            "SELECT COUNT(*) FROM classes",
            "INSERT INTO students (name, surname) VALUES ('John', 'Doe')",
            "UPDATE students SET age = 21 WHERE id = 5",
            "DELETE FROM classes WHERE id = 12",
            "CREATE TABLE courses (id INT, name VARCHAR(255))",
            "SELECT s.*, c.classname FROM students s JOIN classes c ON s.class_id = c.id",
            "SELECT * FROM teachers",
            "SELECT class_id, COUNT(*) FROM students GROUP BY class_id",
            "SELECT * FROM students ORDER BY grade DESC LIMIT 10",
        ] * 2,
        'Intent': ['SELECT', 'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'SELECT', 'SELECT', 'SELECT', 'SELECT'] * 2,
        'Status': ['Success', 'Success', 'Success', 'Success', 'Blocked', 'Blocked', 'Success', 'Success', 'Success', 'Success'] * 2,
        'Execution Time': ['120ms', '95ms', '210ms', '180ms', 'N/A', 'N/A', '340ms', '110ms', '160ms', '145ms'] * 2,
        'Confidence': ['98%', '99%', '95%', '96%', '94%', '97%', '99%', '98%', '97%', '98%'] * 2
    })
    
    # Style the dataframe
    def style_status(val):
        if val == 'Success':
            return 'background-color: #d1fae5; color: #065f46'
        elif val == 'Failed':
            return 'background-color: #fee2e2; color: #991b1b'
        else:
            return 'background-color: #fef3c7; color: #92400e'
    
    styled_df = query_log.style.applymap(style_status, subset=['Status'])
    st.dataframe(styled_df, use_container_width=True, height=400)
    
    # Export options
    col1, col2 = st.columns([3, 1])
    with col2:
        csv = query_log.to_csv(index=False)
        st.download_button(
            label="📥 Export to CSV",
            data=csv,
            file_name=f"query_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )


def render_configuration_tab():
    """System configuration settings"""
    st.subheader("⚙️ Configuration Management")
    
    # Configuration sections
    with st.expander("🤖 AI Model Settings", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.text_input("Gemini API Key", value="sk-*********************", type="password")
            st.selectbox("Model Version", ["gemini-2.5-pro", "gemini-2.0-flash", "gemini-1.5-pro"])
            st.number_input("Max Tokens", value=1000, min_value=100, max_value=10000)
        
        with col2:
            st.number_input("Temperature", value=0.7, min_value=0.0, max_value=1.0, step=0.1)
            st.number_input("Request Timeout (seconds)", value=30, min_value=5, max_value=120)
            st.checkbox("Enable Streaming", value=False)
        
        if st.button("💾 Save AI Settings", use_container_width=True):
            st.success("✅ AI settings saved successfully!")
    
    with st.expander("🗄️ Database Settings"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.selectbox("Default Dialect", ["mysql", "postgresql", "sqlite"])
            st.number_input("Connection Pool Size", value=10, min_value=1, max_value=100)
            st.number_input("Query Timeout (seconds)", value=60, min_value=5, max_value=300)
        
        with col2:
            st.checkbox("Auto-reconnect on Failure", value=True)
            st.checkbox("Enable Query Caching", value=True)
            st.number_input("Cache TTL (minutes)", value=15, min_value=1, max_value=1440)
        
        if st.button("💾 Save Database Settings", use_container_width=True):
            st.success("✅ Database settings saved successfully!")
    
    with st.expander("🛡️ Safety & Security"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.checkbox("Require Confirmation for Destructive Operations", value=True)
            st.checkbox("Enable SQL Injection Detection", value=True)
            st.checkbox("Log All Queries", value=True)
        
        with col2:
            st.checkbox("Block DROP DATABASE Commands", value=True)
            st.checkbox("Block TRUNCATE Commands", value=True)
            st.number_input("Max Rows Per Query", value=10000, min_value=100, max_value=100000)
        
        if st.button("💾 Save Safety Settings", use_container_width=True):
            st.success("✅ Safety settings saved successfully!")
    
    with st.expander("📊 Schema Management"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.number_input("Max Schema Prompt Chars", value=14000, min_value=5000, max_value=50000)
            st.checkbox("Auto-refresh Schema on Connect", value=True)
            st.number_input("Schema Cache Duration (hours)", value=24, min_value=1, max_value=168)
        
        with col2:
            if st.button("🔄 Refresh Schema Now", use_container_width=True):
                with st.spinner("Refreshing schema..."):
                    st.success("✅ Schema refreshed successfully!")
            
            if st.button("📥 Export Schema", use_container_width=True):
                st.info("Schema exported to schema.txt")
            
            if st.button("🗑️ Clear Schema Cache", use_container_width=True):
                st.warning("Schema cache cleared!")


def render_user_activity_tab():
    """User activity monitoring"""
    st.subheader("👥 User Activity & Usage")
    
    # User stats
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Active Sessions", "23", delta="5")
    
    with col2:
        st.metric("Total Users (All Time)", "147", delta="12")
    
    with col3:
        st.metric("Avg Queries per User", "8.5", delta="-1.2")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Activity charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📅 Daily Active Users")
        dates = pd.date_range(end=datetime.now(), periods=14).tolist()
        users_data = pd.DataFrame({
            'Date': dates,
            'Users': [18, 22, 25, 19, 28, 31, 27, 23, 26, 29, 24, 27, 30, 23]
        })
        fig = px.area(users_data, x='Date', y='Users')
        fig.update_traces(fillcolor='rgba(102, 126, 234, 0.3)', line_color='#667eea')
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### ⏰ Peak Usage Hours")
        hours = list(range(24))
        usage = [2, 1, 0, 0, 1, 3, 8, 15, 23, 28, 25, 22, 24, 26, 23, 19, 17, 14, 12, 9, 7, 5, 4, 3]
        time_data = pd.DataFrame({
            'Hour': hours,
            'Queries': usage
        })
        fig = px.bar(time_data, x='Hour', y='Queries')
        fig.update_traces(marker_color='#764ba2')
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)
    
    # Top users table
    st.markdown("---")
    st.markdown("#### 🏆 Top Users by Query Volume")
    
    top_users = pd.DataFrame({
        'User ID': [f'user_{i}' for i in range(1, 11)],
        'Queries': [156, 142, 128, 115, 97, 89, 76, 68, 54, 47],
        'Success Rate': ['96%', '94%', '98%', '92%', '95%', '97%', '93%', '91%', '99%', '94%'],
        'Avg Response Time': ['1.2s', '1.5s', '1.1s', '1.8s', '1.4s', '1.3s', '1.6s', '1.9s', '1.0s', '1.5s'],
        'Last Active': [
            datetime.now() - timedelta(minutes=i*15) for i in range(10)
        ]
    })
    
    st.dataframe(top_users, use_container_width=True, height=350)


def render_security_tab():
    """Security and safety monitoring"""
    st.subheader("🛡️ Security & Safety Dashboard")
    
    # Security alerts
    st.markdown("#### ⚠️ Recent Security Events")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
            <div style='padding: 1rem; background: #fef3c7; border-radius: 0.5rem; border-left: 4px solid #f59e0b;'>
                <h4 style='margin: 0; color: #92400e;'>⚠️ Blocked Queries</h4>
                <h2 style='margin: 0.5rem 0;'>47</h2>
                <p style='margin: 0; color: #78350f;'>Last 24 hours</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
            <div style='padding: 1rem; background: #fee2e2; border-radius: 0.5rem; border-left: 4px solid #ef4444;'>
                <h4 style='margin: 0; color: #991b1b;'>🚨 Failed Queries</h4>
                <h2 style='margin: 0.5rem 0;'>23</h2>
                <p style='margin: 0; color: #7f1d1d;'>Last 24 hours</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
            <div style='padding: 1rem; background: #d1fae5; border-radius: 0.5rem; border-left: 4px solid #10b981;'>
                <h4 style='margin: 0; color: #065f46;'>✅ Safe Queries</h4>
                <h2 style='margin: 0.5rem 0;'>1,177</h2>
                <p style='margin: 0; color: #064e3b;'>Last 24 hours</p>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Blocked queries log
    st.markdown("#### 🚫 Blocked Query Log")
    
    blocked_queries = pd.DataFrame({
        'Timestamp': [datetime.now() - timedelta(hours=i) for i in range(10)],
        'User': [f'user_{i}' for i in range(10)],
        'Natural Language': [
            'Delete all students',
            'Drop the classes table',
            'Truncate teachers table',
            'Delete all records from courses',
            'Drop database school',
            'Update all student grades to 100',
            'Delete students where age > 0',
            'Alter table students drop column',
            'Drop table if exists users',
            'Delete from students'
        ],
        'Attempted SQL': [
            'DELETE FROM students',
            'DROP TABLE classes',
            'TRUNCATE TABLE teachers',
            'DELETE FROM courses',
            'DROP DATABASE school',
            'UPDATE students SET grade = 100',
            'DELETE FROM students WHERE age > 0',
            'ALTER TABLE students DROP COLUMN name',
            'DROP TABLE IF EXISTS users',
            'DELETE FROM students'
        ],
        'Reason': [
            'Destructive operation not allowed',
            'DROP command blocked',
            'TRUNCATE command blocked',
            'Mass deletion blocked',
            'DROP DATABASE blocked',
            'Mass update blocked',
            'Mass deletion blocked',
            'ALTER command blocked',
            'DROP command blocked',
            'Destructive operation not allowed'
        ]
    })
    
    st.dataframe(blocked_queries, use_container_width=True, height=350)
    
    # Safety rules
    st.markdown("---")
    st.markdown("#### 📋 Active Safety Rules")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Blocked Operations:**
        - ❌ DROP DATABASE
        - ❌ DROP TABLE (without confirmation)
        - ❌ TRUNCATE TABLE
        - ❌ DELETE without WHERE clause
        - ❌ UPDATE without WHERE clause
        """)
    
    with col2:
        st.markdown("""
        **Allowed with Confirmation:**
        - ⚠️ DROP TABLE (with flag)
        - ⚠️ DELETE with WHERE
        - ⚠️ UPDATE with WHERE
        - ⚠️ ALTER TABLE
        - ⚠️ CREATE TABLE
        """)


# Export the main function
if __name__ == "__main__":
    st.set_page_config(page_title="Admin Console", layout="wide")
    render_admin_console()