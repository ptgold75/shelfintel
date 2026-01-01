# app/Home.py
"""Shelf Intel Dashboard - Home Page"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from sqlalchemy import text

st.set_page_config(page_title="Shelf Intel", page_icon="🔍", layout="wide")

st.title("🔍 Shelf Intel")
st.subheader("Cannabis Dispensary Menu Intelligence")

from core.db import get_engine

# Use summary table for fast stats
try:
    engine = get_engine()
    with engine.connect() as conn:
        # Fast query from summary table
        totals = conn.execute(text("""
            SELECT dimension, value_count 
            FROM analytics_summary 
            WHERE summary_type = 'total'
        """)).fetchall()
        
        stats = {row[0]: row[1] for row in totals}
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Products Tracked", f"{stats.get('products', 0):,}")
        col2.metric("Dispensaries", f"{stats.get('dispensaries', 0):,}")
        col3.metric("Scrape Runs", f"{stats.get('scrape_runs', 0):,}")
        
except Exception as e:
    st.warning(f"Could not load stats: {e}")
    st.info("Run the summary update script to populate dashboard stats.")

st.divider()

st.markdown("""
### Quick Links
- **📊 Analytics** - Brand and category breakdowns
- **🏪 Dispensaries** - Manage tracked stores  
- **⚙️ Admin Setup** - Configure new dispensaries

### About
Shelf Intel tracks cannabis product availability and pricing across dispensaries.
Data is scraped hourly and analyzed for demand signals.
""")
