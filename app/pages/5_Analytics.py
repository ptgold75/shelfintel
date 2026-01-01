# app/pages/5_Analytics.py
"""Analytics - focuses on availability tracking."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from sqlalchemy import text

st.set_page_config(page_title="Analytics", page_icon="📊", layout="wide")
st.title("📊 Shelf Intel Analytics")

from core.db import get_engine

tab1, tab2, tab3 = st.tabs(["📈 Overview", "👻 Availability Changes", "🏪 Stores"])

with tab1:
    st.header("Overview")
    try:
        engine = get_engine()
        with engine.connect() as conn:
            # Fast queries on smaller tables
            dispensaries = conn.execute(text("SELECT COUNT(*) FROM dispensary")).scalar()
            scrape_runs = conn.execute(text("SELECT COUNT(*) FROM scrape_run")).scalar()
            
            # Estimate products from pg_class (instant)
            products = conn.execute(text(
                "SELECT reltuples::bigint FROM pg_class WHERE relname = 'raw_menu_item'"
            )).scalar() or 0
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Products (approx)", f"{int(products):,}")
        col2.metric("Dispensaries", dispensaries)
        col3.metric("Scrape Runs", scrape_runs)
        
    except Exception as e:
        st.error(f"Error: {e}")

with tab2:
    st.header("👻 Availability Tracking")
    st.markdown("Track products appearing and disappearing from menus.")
    
    try:
        engine = get_engine()
        with engine.connect() as conn:
            # Recent events (smaller table, should be fast)
            events_df = pd.read_sql(text("""
                SELECT 
                    e.event_type,
                    e.event_at,
                    d.name as store
                FROM menu_item_event e
                JOIN dispensary d ON d.dispensary_id = e.dispensary_id
                ORDER BY e.event_at DESC
                LIMIT 100
            """), conn)
        
        if not events_df.empty:
            # Summary
            appeared = len(events_df[events_df['event_type'] == 'appeared'])
            disappeared = len(events_df[events_df['event_type'] == 'disappeared'])
            
            col1, col2 = st.columns(2)
            col1.metric("Recent Appearances", appeared)
            col2.metric("Recent Disappearances", disappeared)
            
            st.subheader("Recent Events")
            st.dataframe(events_df, use_container_width=True)
        else:
            st.info("No availability events yet. Run multiple scrapes to track changes.")
            
    except Exception as e:
        st.warning(f"Availability tracking: {e}")
        st.info("Run more scrapes to build availability data.")

with tab3:
    st.header("🏪 Dispensaries")
    try:
        engine = get_engine()
        with engine.connect() as conn:
            stores_df = pd.read_sql(text("""
                SELECT name, state, menu_provider, is_active
                FROM dispensary
                ORDER BY name
                LIMIT 50
            """), conn)
        
        if not stores_df.empty:
            active = len(stores_df[stores_df['is_active'] == True])
            st.metric("Active Stores", active)
            st.dataframe(stores_df, use_container_width=True)
            
    except Exception as e:
        st.error(f"Error: {e}")

st.divider()
st.caption("For full analytics with brand/category breakdowns, run locally: streamlit run app/Home.py")
