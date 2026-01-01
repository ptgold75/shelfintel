# app/pages/5_Analytics.py
"""Analytics dashboard - reads from pre-computed summaries."""

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

# Single connection for all queries
@st.cache_resource
def get_db_engine():
    return get_engine()

@st.cache_data(ttl=300)
def load_all_data():
    """Load all data in one connection."""
    engine = get_db_engine()
    with engine.connect() as conn:
        totals = pd.read_sql(text("""
            SELECT dimension, value_count 
            FROM analytics_summary 
            WHERE summary_type = 'total'
        """), conn)
        
        brands = pd.read_sql(text("""
            SELECT dimension as brand, value_count as sku_count
            FROM analytics_summary
            WHERE summary_type = 'brand'
            ORDER BY value_count DESC
            LIMIT 30
        """), conn)
        
        categories = pd.read_sql(text("""
            SELECT dimension as category, value_count as product_count
            FROM analytics_summary
            WHERE summary_type = 'category'
            ORDER BY value_count DESC
            LIMIT 30
        """), conn)
        
        stores = pd.read_sql(text("""
            SELECT dimension as store_name, value_count as total_products
            FROM analytics_summary
            WHERE summary_type = 'store'
            ORDER BY value_count DESC
            LIMIT 30
        """), conn)
    
    return totals, brands, categories, stores

try:
    totals_df, brand_df, category_df, store_df = load_all_data()
    totals = totals_df.set_index('dimension')['value_count'].to_dict()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

tab1, tab2, tab3, tab4 = st.tabs(["📈 Overview", "🏷️ Brands", "📦 Categories", "🏪 Stores"])

with tab1:
    st.header("Overview")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Products", f"{totals.get('products', 0):,}")
    col2.metric("Dispensaries", f"{totals.get('dispensaries', 0):,}")
    col3.metric("Scrape Runs", f"{totals.get('scrape_runs', 0):,}")

with tab2:
    st.header("Brand Analysis")
    if not brand_df.empty:
        fig = px.bar(brand_df, x="sku_count", y="brand", orientation="h", title="Top 30 Brands by SKU Count")
        fig.update_layout(yaxis={"categoryorder":"total ascending"}, height=700)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(brand_df, use_container_width=True)

with tab3:
    st.header("Category Breakdown")
    if not category_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            fig = px.pie(category_df.head(15), values="product_count", names="category", title="Top 15 Categories", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.bar(category_df, x="category", y="product_count", title="Products per Category")
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.header("🏪 Top Stores")
    if not store_df.empty:
        st.metric("Stores Tracked", len(store_df))
        fig = px.bar(store_df, x="store_name", y="total_products", title="Top 30 Stores by Product Count")
        fig.update_layout(xaxis_tickangle=-45, height=500)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(store_df, use_container_width=True)

st.divider()
st.caption(f"Data from pre-computed summaries | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
