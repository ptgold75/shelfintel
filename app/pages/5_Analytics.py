# app/pages/5_Analytics.py
"""Analytics dashboard - optimized for large datasets."""

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

@st.cache_data(ttl=600)
def get_overview_stats():
    engine = get_engine()
    with engine.connect() as conn:
        total_products = conn.execute(text("""
            SELECT reltuples::bigint FROM pg_class WHERE relname = 'raw_menu_item'
        """)).scalar() or 0
        total_dispensaries = conn.execute(text("""
            SELECT reltuples::bigint FROM pg_class WHERE relname = 'dispensary'
        """)).scalar() or 0
        total_runs = conn.execute(text("""
            SELECT reltuples::bigint FROM pg_class WHERE relname = 'scrape_run'
        """)).scalar() or 0
    return int(total_products), int(total_dispensaries), int(total_runs)

@st.cache_data(ttl=600)
def get_brand_data():
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text("""
            SELECT raw_brand as brand, COUNT(*) as sku_count 
            FROM raw_menu_item 
            WHERE raw_brand IS NOT NULL AND raw_brand != '' 
            GROUP BY raw_brand 
            ORDER BY sku_count DESC 
            LIMIT 30
        """), conn)

@st.cache_data(ttl=600)
def get_category_data():
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text("""
            SELECT raw_category as category, COUNT(*) as product_count 
            FROM raw_menu_item 
            WHERE raw_category IS NOT NULL AND raw_category != '' 
            GROUP BY raw_category 
            ORDER BY product_count DESC 
            LIMIT 30
        """), conn)

@st.cache_data(ttl=600)
def get_store_data():
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text("""
            SELECT d.name as store_name, COUNT(r.raw_menu_item_id) as total_products
            FROM dispensary d
            LEFT JOIN raw_menu_item r ON r.dispensary_id = d.dispensary_id
            GROUP BY d.dispensary_id, d.name
            ORDER BY total_products DESC
            LIMIT 30
        """), conn)

tab1, tab2, tab3, tab4 = st.tabs(["📈 Overview", "🏷️ Brands", "📦 Categories", "🏪 Stores"])

with tab1:
    st.header("Overview")
    try:
        total_products, total_dispensaries, total_runs = get_overview_stats()
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Products (approx)", f"{total_products:,}")
        col2.metric("Dispensaries", total_dispensaries)
        col3.metric("Scrape Runs", total_runs)
        st.info("Product count is approximate for performance. Data refreshes every 10 minutes.")
    except Exception as e:
        st.error(f"Error: {e}")

with tab2:
    st.header("Brand Analysis")
    try:
        brand_df = get_brand_data()
        if not brand_df.empty:
            fig = px.bar(brand_df, x="sku_count", y="brand", orientation="h", title="Top 30 Brands by SKU Count")
            fig.update_layout(yaxis={"categoryorder":"total ascending"}, height=700)
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(brand_df, use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")

with tab3:
    st.header("Category Breakdown")
    try:
        category_df = get_category_data()
        if not category_df.empty:
            col1, col2 = st.columns(2)
            with col1:
                fig = px.pie(category_df.head(15), values="product_count", names="category", title="Top 15 Categories")
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                fig = px.bar(category_df, x="category", y="product_count", title="Products per Category")
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")

with tab4:
    st.header("🏪 Top Stores")
    try:
        store_df = get_store_data()
        if not store_df.empty:
            fig = px.bar(store_df, x="store_name", y="total_products", title="Top 30 Stores by Product Count")
            fig.update_layout(xaxis_tickangle=-45, height=500)
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(store_df, use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")

st.divider()
st.caption(f"Cached for 10 min | {datetime.now().strftime('%H:%M')}")
