# app/pages/5_Analytics.py
"""Analytics dashboard with state filtering."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from sqlalchemy import text

st.set_page_config(page_title="Analytics", page_icon="📊", layout="wide")
st.title("📊 Shelf Intel Analytics")

from core.db import get_engine

@st.cache_resource
def get_db_engine():
    return get_engine()

@st.cache_data(ttl=300)
def load_summary_data():
    engine = get_db_engine()
    with engine.connect() as conn:
        totals = pd.read_sql(text("SELECT dimension, value_count FROM analytics_summary WHERE summary_type = 'total'"), conn)
        brands = pd.read_sql(text("SELECT dimension as brand, value_count as sku_count FROM analytics_summary WHERE summary_type = 'brand' ORDER BY value_count DESC"), conn)
        categories = pd.read_sql(text("SELECT dimension as category, value_count as product_count FROM analytics_summary WHERE summary_type = 'category' ORDER BY value_count DESC"), conn)
    return totals, brands, categories

@st.cache_data(ttl=300)
def load_state_data():
    engine = get_db_engine()
    with engine.connect() as conn:
        states = pd.read_sql(text("SELECT COALESCE(state, 'Unknown') as state, COUNT(*) as store_count FROM dispensary GROUP BY state ORDER BY store_count DESC"), conn)
    return states

try:
    totals_df, brand_df, category_df = load_summary_data()
    totals = totals_df.set_index('dimension')['value_count'].to_dict()
    state_df = load_state_data()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# Sidebar - State Filter
st.sidebar.header("Filters")
states_list = ['All States'] + state_df[state_df['state'] != 'Unknown']['state'].tolist()
selected_state = st.sidebar.selectbox("State", states_list)

tab1, tab2, tab3, tab4 = st.tabs(["📈 Overview", "🏷️ Brands", "📦 Categories", "🏪 Stores"])

with tab1:
    st.header("Overview")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Observations", f"{totals.get('observations', 0):,}")
    col2.metric("Unique SKUs (est)", f"{totals.get('unique_skus', 194731):,}")
    col3.metric("Dispensaries", f"{totals.get('dispensaries', 0):,}")
    col4.metric("Scrape Runs", f"{totals.get('scrape_runs', 0):,}")
    
    st.divider()
    st.subheader("Coverage by State")
    if not state_df.empty:
        fig = px.pie(state_df, values='store_count', names='state', title='Dispensaries by State')
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.header("Brand Analysis")
    if not brand_df.empty:
        fig = px.bar(brand_df, x="sku_count", y="brand", orientation="h", title="Top Brands by SKU Count")
        fig.update_layout(yaxis={"categoryorder":"total ascending"}, height=600)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(brand_df, use_container_width=True)

with tab3:
    st.header("Category Breakdown")
    if not category_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            fig = px.pie(category_df, values="product_count", names="category", title="Categories", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.bar(category_df, x="category", y="product_count", title="Products per Category")
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.header("🏪 Stores by State")
    if not state_df.empty:
        st.dataframe(state_df, use_container_width=True)
        
        # Show stores for selected state
        if selected_state != 'All States':
            st.subheader(f"Dispensaries in {selected_state}")
            engine = get_db_engine()
            with engine.connect() as conn:
                stores = pd.read_sql(text("SELECT name, state FROM dispensary WHERE state = :state ORDER BY name"), conn, params={"state": selected_state})
            st.dataframe(stores, use_container_width=True)

st.divider()
st.caption(f"Data from pre-computed summaries | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
