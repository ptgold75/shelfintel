# app/pages/2_Availability.py
"""Availability tracking with state filter."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
from sqlalchemy import text
from core.db import get_engine

st.set_page_config(page_title="Availability", page_icon="📦", layout="wide")
st.title("📦 Product Availability")

engine = get_engine()

# Get states for filter
@st.cache_data(ttl=300)
def get_states():
    with engine.connect() as conn:
        return pd.read_sql(text("SELECT DISTINCT state FROM dispensary WHERE state IS NOT NULL ORDER BY state"), conn)

states_df = get_states()
states_list = ['MD'] + [s for s in states_df['state'].tolist() if s != 'MD']  # Default to MD

selected_state = st.sidebar.selectbox("Filter by State", states_list, index=0)

st.info(f"Showing availability for **{selected_state}** dispensaries")

try:
    with engine.connect() as conn:
        # Get dispensaries in selected state
        dispensaries = pd.read_sql(text("""
            SELECT dispensary_id, name 
            FROM dispensary 
            WHERE state = :state AND is_active = true
            ORDER BY name
        """), conn, params={"state": selected_state})
    
    st.metric("Dispensaries in State", len(dispensaries))
    
    if not dispensaries.empty:
        st.subheader(f"Dispensaries in {selected_state}")
        st.dataframe(dispensaries[['name']], use_container_width=True)
        
        # Show recent activity summary
        st.subheader("Data Coverage")
        st.markdown("""
        Availability tracking requires multiple scrapes to detect changes.
        - **Appeared:** Product newly listed
        - **Disappeared:** Product no longer on menu
        """)
    else:
        st.warning(f"No dispensaries found in {selected_state}")

except Exception as e:
    st.error(f"Error: {e}")
