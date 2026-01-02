# app/Home.py
"""CannaLinx - Home Page"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from sqlalchemy import text
from core.db import get_engine
from pathlib import Path

st.set_page_config(page_title="CannaLinx", page_icon="🔍", layout="wide")

# Banner - use absolute path
banner_path = Path(__file__).parent / "static" / "cannalinx_banner.png"
if banner_path.exists():
    st.image(str(banner_path), use_container_width=True)
else:
    st.title("🔍 CannaLinx")
    st.subheader("Shelf Space Intelligence for Cannabis")

st.divider()

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
    c1.metric("Unique SKUs", f"{stats.get('unique_skus', 0):,}")
    c2.metric("Data Points", f"{stats.get('observations', 0):,}")
    c3.metric("Dispensaries", f"{stats.get('dispensaries', 0):,}")
    c4.metric("Scrape Runs", f"{stats.get('scrape_runs', 0):,}")

except Exception as e:
    st.warning(f"Could not load stats: {e}")

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### 📊 What We Track
    - **Product availability** across dispensaries
    - **Price changes** over time
    - **Brand distribution** by region
    - **Category trends** (Flower, Vapes, Edibles)
    """)

with col2:
    st.markdown("""
    ### 🎯 Use Cases
    - **Manufacturers:** Track where your products are stocked
    - **Wholesalers:** Identify pricing opportunities  
    - **Retailers:** Competitive intelligence
    - **Investors:** Market demand signals
    """)
