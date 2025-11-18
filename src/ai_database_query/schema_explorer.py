# schema_explorer.py
import streamlit as st
import pandas as pd
from typing import Dict, Any

class SchemaExplorer:
    @staticmethod
    def display_schema(schema_info: Dict[str, Any]):
        """Display database schema in an organized way"""
        if not schema_info or 'tables' not in schema_info:
            st.warning("No schema information available")
            return
        
        st.subheader("📊 Database Schema")
        
        # Create tabs for different views
        tab1, tab2, tab3 = st.tabs(["Tables", "Relationships", "JSON View"])
        
        with tab1:
            for table_name, table_info in schema_info['tables'].items():
                with st.expander(f"📋 {table_name}"):
                    # Display columns
                    cols_data = []
                    for col in table_info['columns']:
                        cols_data.append({
                            'Column Name': col['name'],
                            'Data Type': col['type'],
                            'Nullable': 'Yes' if col['nullable'] else 'No',
                            'Primary Key': 'Yes' if col.get('primary_key') else 'No'
                        })
                    
                    if cols_data:
                        st.dataframe(pd.DataFrame(cols_data), use_container_width=True)
                    
                    # Display primary keys
                    if table_info.get('primary_key'):
                        st.write(f"**Primary Key:** {', '.join(table_info['primary_key'])}")
        
        with tab2:
            if schema_info.get('relationships'):
                rel_data = []
                for rel in schema_info['relationships']:
                    rel_data.append({
                        'From Table': rel['from_table'],
                        'From Column': ', '.join(rel['from_column']),
                        'To Table': rel['to_table'],
                        'To Column': ', '.join(rel['to_column'])
                    })
                st.dataframe(pd.DataFrame(rel_data), use_container_width=True)
            else:
                st.info("No foreign key relationships found")
        
        with tab3:
            st.json(schema_info)