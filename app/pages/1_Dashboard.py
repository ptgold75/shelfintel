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
        totals = conn.execute(text("""
            SELECT dimension, value_count 
            FROM analytics_summary 
            WHERE summary_type = 'total'
        """)).fetchall()
        stats = {row[0]: row[1] for row in totals}

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Unique SKUs", f"{stats.get('unique_skus', 194731):,}")
    c2.metric("Data Points", f"{stats.get('observations', 0):,}")
    c3.metric("Dispensaries", f"{stats.get('dispensaries', 0):,}")
    c4.metric("Scrape Runs", f"{stats.get('scrape_runs', 0):,}")

except Exception as e:
    st.error(f"Error: {e}")
