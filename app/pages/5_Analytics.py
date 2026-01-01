# app/pages/5_Analytics.py
"""Analytics dashboard with caching for performance."""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from sqlalchemy import text

st.set_page_config(page_title="Analytics", page_icon="📊", layout="wide")
st.title("📊 Shelf Intel Analytics")

from core.db import get_engine

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_overview_stats():
    engine = get_engine()
    with engine.connect() as conn:
        total_products = conn.execute(text("SELECT COUNT(*) FROM raw_menu_item")).scalar()
        total_dispensaries = conn.execute(text("SELECT COUNT(*) FROM dispensary")).scalar()
        total_runs = conn.execute(text("SELECT COUNT(*) FROM scrape_run")).scalar()
    return total_products, total_dispensaries, total_runs

@st.cache_data(ttl=300)
def get_brand_data():
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text("SELECT brand, COUNT(*) as sku_count FROM raw_menu_item WHERE brand IS NOT NULL AND brand != '' GROUP BY brand ORDER BY sku_count DESC LIMIT 50"), conn)

@st.cache_data(ttl=300)
def get_category_data():
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text("SELECT category, COUNT(*) as product_count FROM raw_menu_item WHERE category IS NOT NULL AND category != '' GROUP BY category ORDER BY product_count DESC LIMIT 50"), conn)

@st.cache_data(ttl=300)
def get_store_data():
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text("SELECT d.name as store_name, d.state, COUNT(r.raw_menu_item_id) as total_products, COUNT(DISTINCT r.brand) as unique_brands FROM dispensary d LEFT JOIN raw_menu_item r ON r.dispensary_id = d.dispensary_id GROUP BY d.dispensary_id, d.name, d.state ORDER BY total_products DESC LIMIT 50"), conn)

tab1, tab2, tab3, tab4 = st.tabs(["📈 Overview", "🏷️ Brands", "📦 Categories", "🏪 Stores"])

with tab1:
    st.header("Overview")
    try:
        total_products, total_dispensaries, total_runs = get_overview_stats()
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Products", f"{total_products:,}")
        col2.metric("Dispensaries", total_dispensaries)
        col3.metric("Scrape Runs", total_runs)
    except Exception as e:
        st.error(f"Error loading stats: {e}")

with tab2:
    st.header("Brand Analysis")
    try:
        brand_df = get_brand_data()
        if not brand_df.empty:
            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(brand_df.head(25), x="sku_count", y="brand", orientation="h", title="Top 25 Brands")
                fig.update_layout(yaxis={"categoryorder":"total ascending"}, height=600)
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                fig = px.pie(brand_df.head(15), values="sku_count", names="brand", title="Brand Share")
                st.plotly_chart(fig, use_container_width=True)
            st.dataframe(brand_df, use_container_width=True)
    except Exception as e:
        st.error(f"Error loading brands: {e}")

with tab3:
    st.header("Category Breakdown")
    try:
        category_df = get_category_data()
        if not category_df.empty:
            col1, col2 = st.columns(2)
            with col1:
                fig = px.pie(category_df.head(15), values="product_count", names="category", title="Categories", hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                fig = px.bar(category_df.head(15), x="category", y="product_count", title="Products per Category")
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            
            # Simplified view
            def normalize(cat):
                cat = cat.lower() if cat else ""
                if "flower" in cat: return "Flower"
                elif "edible" in cat or "gummy" in cat: return "Edibles"
                elif "vape" in cat or "cart" in cat: return "Vapes"
                elif "pre-roll" in cat or "preroll" in cat: return "Pre-Rolls"
                elif "concentrate" in cat: return "Concentrates"
                else: return "Other"
            
            category_df["simple"] = category_df["category"].apply(normalize)
            simple = category_df.groupby("simple")["product_count"].sum().reset_index()
            fig = px.pie(simple, values="product_count", names="simple", title="Simplified")
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error loading categories: {e}")

with tab4:
    st.header("🏪 Store Comparison")
    try:
        store_df = get_store_data()
        if not store_df.empty:
            col1, col2 = st.columns(2)
            col1.metric("Total Stores", len(store_df))
            col2.metric("Avg Products/Store", f"{store_df['total_products'].mean():.0f}")
            
            fig = px.bar(store_df.head(30), x="store_name", y="total_products", title="Top 30 Stores")
            fig.update_layout(xaxis_tickangle=-45, height=500)
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(store_df, use_container_width=True)
    except Exception as e:
        st.error(f"Error loading stores: {e}")

st.divider()
st.caption(f"Data cached for 5 min. Last refresh: {datetime.now().strftime('%H:%M')}")
