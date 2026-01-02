# app/pages/1_Dashboard.py
"""Dashboard - uses pre-computed summaries."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
from sqlalchemy import text
from core.db import get_engine

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.title("📊 Dashboard")

try:
    engine = get_engine()
    with engine.connect() as conn:
        # Use summary table (fast)
        totals = conn.execute(text("""
            SELECT dimension, value_count 
            FROM analytics_summary 
            WHERE summary_type = 'total'
        """)).fetchall()
        stats = {row[0]: row[1] for row in totals}

    c1, c2, c3 = st.columns(3)
    c1.metric("Dispensaries", f"{stats.get('dispensaries', 0):,}")
    c2.metric("Scrape Runs", f"{stats.get('scrape_runs', 0):,}")
    c3.metric("Products", f"{stats.get('products', 0):,}")

except Exception as e:
    st.error(f"Error: {e}")
    st.info("Make sure analytics summaries have been populated.")
