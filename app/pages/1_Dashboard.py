# app/pages/1_Dashboard.py
"""Dashboard - Key metrics overview."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
from sqlalchemy import text
from core.db import get_engine

st.set_page_config(page_title="Dashboard | CannLinx", page_icon=None, layout="wide")
st.title("Dashboard")

@st.cache_data(ttl=300)
def load_dashboard_stats():
    """Load dashboard stats from actual tables."""
    engine = get_engine()
    with engine.connect() as conn:
        unique_skus = conn.execute(text(
            "SELECT COUNT(DISTINCT raw_name) FROM raw_menu_item WHERE raw_name IS NOT NULL"
        )).scalar() or 0

        observations = conn.execute(text(
            "SELECT COUNT(*) FROM raw_menu_item"
        )).scalar() or 0

        dispensaries = conn.execute(text(
            "SELECT COUNT(DISTINCT dispensary_id) FROM dispensary"
        )).scalar() or 0

        scrape_runs = conn.execute(text(
            "SELECT COUNT(*) FROM scrape_run"
        )).scalar() or 0

        brands = conn.execute(text(
            "SELECT COUNT(DISTINCT raw_brand) FROM raw_menu_item WHERE raw_brand IS NOT NULL"
        )).scalar() or 0

        categories = conn.execute(text(
            "SELECT COUNT(DISTINCT raw_category) FROM raw_menu_item WHERE raw_category IS NOT NULL"
        )).scalar() or 0

        return {
            "unique_skus": unique_skus,
            "observations": observations,
            "dispensaries": dispensaries,
            "scrape_runs": scrape_runs,
            "brands": brands,
            "categories": categories,
        }

try:
    stats = load_dashboard_stats()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Unique Products", f"{stats['unique_skus']:,}")
    c2.metric("Data Points", f"{stats['observations']:,}")
    c3.metric("Dispensaries", f"{stats['dispensaries']:,}")
    c4.metric("Brands", f"{stats['brands']:,}")

    st.divider()

    # Recent activity section
    st.subheader("Recent Activity")

    engine = get_engine()
    with engine.connect() as conn:
        recent_scrapes = conn.execute(text("""
            SELECT s.started_at, d.name, s.status, s.records_found
            FROM scrape_run s
            JOIN dispensary d ON s.dispensary_id = d.dispensary_id
            ORDER BY s.started_at DESC
            LIMIT 10
        """)).fetchall()

    if recent_scrapes:
        for scrape in recent_scrapes:
            status_icon = "✓" if scrape[2] == "success" else "✗" if scrape[2] == "fail" else "..."
            st.write(f"{status_icon} **{scrape[1]}** - {scrape[3] or 0} items ({scrape[0]})")
    else:
        st.info("No recent scrape activity")

except Exception as e:
    st.error(f"Error loading data: {e}")
