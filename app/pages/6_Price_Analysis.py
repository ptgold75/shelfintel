# app/pages/6_Price_Analysis.py
"""Price Analysis - Find deals, compare prices by category/size."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import text
from core.db import get_engine

st.set_page_config(page_title="Price Analysis", page_icon="💰", layout="wide")
st.title("💰 Price Analysis")

engine = get_engine()

# Sidebar - State filter
st.sidebar.header("🔍 Filters")

@st.cache_data(ttl=300)
def get_states():
    with engine.connect() as conn:
        df = pd.read_sql(text("""
            SELECT DISTINCT COALESCE(state, 'Unknown') as state
            FROM dispensary 
            WHERE state IS NOT NULL
            ORDER BY state
        """), conn)
    return ['All States'] + df['state'].tolist()

states = get_states()
selected_state = st.sidebar.selectbox("State", states, index=0)

# Min price filter (exclude promos)
min_price_filter = st.sidebar.slider("Minimum Price (exclude promos)", 1, 20, 5)

@st.cache_data(ttl=600)
def get_price_stats_by_category(state, min_price):
    with engine.connect() as conn:
        if state == 'All States':
            return pd.read_sql(text("""
                SELECT raw_category as category,
                       COUNT(*) as products,
                       ROUND(AVG(raw_price)::numeric, 2) as avg_price,
                       ROUND(MIN(raw_price)::numeric, 2) as min_price,
                       ROUND(MAX(raw_price)::numeric, 2) as max_price
                FROM raw_menu_item
                WHERE raw_price >= :min_price AND raw_price < 1000
                AND observed_at > NOW() - INTERVAL '24 hours'
                GROUP BY raw_category
                HAVING COUNT(*) > 50
                ORDER BY avg_price DESC
            """), conn, params={"min_price": min_price})
        else:
            return pd.read_sql(text("""
                SELECT r.raw_category as category,
                       COUNT(*) as products,
                       ROUND(AVG(r.raw_price)::numeric, 2) as avg_price,
                       ROUND(MIN(r.raw_price)::numeric, 2) as min_price,
                       ROUND(MAX(r.raw_price)::numeric, 2) as max_price
                FROM raw_menu_item r
                JOIN dispensary d ON d.dispensary_id = r.dispensary_id
                WHERE r.raw_price >= :min_price AND r.raw_price < 1000
                AND r.observed_at > NOW() - INTERVAL '24 hours'
                AND d.state = :state
                GROUP BY r.raw_category
                HAVING COUNT(*) > 10
                ORDER BY avg_price DESC
            """), conn, params={"min_price": min_price, "state": state})

@st.cache_data(ttl=600)
def get_cheapest_by_category(category, state, min_price, limit=20):
    with engine.connect() as conn:
        if state == 'All States':
            return pd.read_sql(text("""
                SELECT r.raw_name as product, r.raw_brand as brand, 
                       r.raw_price as price, d.name as store, d.state
                FROM raw_menu_item r
                JOIN dispensary d ON d.dispensary_id = r.dispensary_id
                WHERE r.raw_category = :cat
                AND r.raw_price >= :min_price
                AND r.observed_at > NOW() - INTERVAL '24 hours'
                ORDER BY r.raw_price ASC
                LIMIT :lim
            """), conn, params={"cat": category, "min_price": min_price, "lim": limit})
        else:
            return pd.read_sql(text("""
                SELECT r.raw_name as product, r.raw_brand as brand, 
                       r.raw_price as price, d.name as store, d.state
                FROM raw_menu_item r
                JOIN dispensary d ON d.dispensary_id = r.dispensary_id
                WHERE r.raw_category = :cat
                AND r.raw_price >= :min_price
                AND r.observed_at > NOW() - INTERVAL '24 hours'
                AND d.state = :state
                ORDER BY r.raw_price ASC
                LIMIT :lim
            """), conn, params={"cat": category, "min_price": min_price, "state": state, "lim": limit})

@st.cache_data(ttl=600)
def get_vape_price_analysis(state, min_price):
    with engine.connect() as conn:
        state_filter = "AND d.state = :state" if state != 'All States' else ""
        return pd.read_sql(text(f"""
            SELECT r.raw_name as product, r.raw_brand as brand,
                   r.raw_price as price, d.name as store, d.state,
                   CASE 
                       WHEN r.raw_name ILIKE '%2g%' OR r.raw_name ILIKE '%2000%' THEN '2000mg'
                       WHEN r.raw_name ILIKE '%1g%' OR r.raw_name ILIKE '%1000%' THEN '1000mg'
                       WHEN r.raw_name ILIKE '%.5g%' OR r.raw_name ILIKE '%500%' OR r.raw_name ILIKE '%half%' THEN '500mg'
                       WHEN r.raw_name ILIKE '%300%' THEN '300mg'
                       ELSE 'Other'
                   END as size
            FROM raw_menu_item r
            JOIN dispensary d ON d.dispensary_id = r.dispensary_id
            WHERE (r.raw_category ILIKE '%vape%' OR r.raw_category ILIKE '%cart%')
            AND r.raw_price >= :min_price AND r.raw_price < 200
            AND r.observed_at > NOW() - INTERVAL '24 hours'
            {state_filter}
            ORDER BY r.raw_price ASC
            LIMIT 500
        """), conn, params={"min_price": min_price, "state": state} if state != 'All States' else {"min_price": min_price})

@st.cache_data(ttl=600)
def get_deals(state, min_price):
    with engine.connect() as conn:
        state_filter = "AND d.state = :state" if state != 'All States' else ""
        params = {"min_price": min_price}
        if state != 'All States':
            params["state"] = state
        return pd.read_sql(text(f"""
            SELECT r.raw_name as product, r.raw_brand as brand, r.raw_category as category,
                   r.raw_price as original_price, r.raw_discount_price as sale_price,
                   ROUND((r.raw_price - r.raw_discount_price)::numeric, 2) as savings,
                   ROUND(((r.raw_price - r.raw_discount_price) / r.raw_price * 100)::numeric, 0) as pct_off,
                   d.name as store, d.state
            FROM raw_menu_item r
            JOIN dispensary d ON d.dispensary_id = r.dispensary_id
            WHERE r.raw_discount_price IS NOT NULL 
            AND r.raw_discount_price >= :min_price
            AND r.raw_discount_price < r.raw_price
            AND r.observed_at > NOW() - INTERVAL '24 hours'
            {state_filter}
            ORDER BY (r.raw_price - r.raw_discount_price) DESC
            LIMIT 50
        """), conn, params=params)

# Show selected state
st.info(f"📍 Showing prices for **{selected_state}** | Min price: **${min_price_filter}** (excludes promos)")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Category Prices", "💨 Vape Analysis", "🏷️ Best Deals", "🔍 Price Search"])

with tab1:
    st.header("Average Prices by Category")
    try:
        price_df = get_price_stats_by_category(selected_state, min_price_filter)
        if not price_df.empty:
            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(price_df.head(15), x='category', y='avg_price', 
                            title='Average Price by Category',
                            labels={'avg_price': 'Avg Price ($)'})
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.dataframe(price_df, use_container_width=True, height=400)
            
            # Cheapest in category
            st.subheader("Find Cheapest Products")
            selected_cat = st.selectbox("Select Category", price_df['category'].tolist())
            if selected_cat:
                cheapest = get_cheapest_by_category(selected_cat, selected_state, min_price_filter)
                st.dataframe(cheapest, use_container_width=True)
        else:
            st.warning("No price data found for selected filters")
    except Exception as e:
        st.error(f"Error: {e}")

with tab2:
    st.header("💨 Vape/Cartridge Price Analysis")
    try:
        vape_df = get_vape_price_analysis(selected_state, min_price_filter)
        if not vape_df.empty:
            # Group by size
            size_stats = vape_df.groupby('size').agg({
                'price': ['count', 'mean', 'min', 'max']
            }).round(2)
            size_stats.columns = ['count', 'avg_price', 'min_price', 'max_price']
            size_stats = size_stats.reset_index().sort_values('avg_price')
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Price by Size")
                fig = px.bar(size_stats, x='size', y='avg_price', title='Avg Vape Price by Size')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.dataframe(size_stats, use_container_width=True)
            
            # Cheapest vapes
            st.subheader("Cheapest Vapes")
            size_filter = st.selectbox("Filter by Size", ['All'] + size_stats['size'].tolist())
            if size_filter == 'All':
                display_df = vape_df.head(30)
            else:
                display_df = vape_df[vape_df['size'] == size_filter].head(30)
            
            st.dataframe(display_df, use_container_width=True)
        else:
            st.warning("No vape data found for selected filters")
    except Exception as e:
        st.error(f"Error: {e}")

with tab3:
    st.header("🏷️ Best Deals (On Sale)")
    try:
        deals_df = get_deals(selected_state, min_price_filter)
        if not deals_df.empty:
            st.metric("Products on Sale", len(deals_df))
            
            # Format prices
            deals_df['original_price'] = deals_df['original_price'].apply(lambda x: f"${x:.2f}")
            deals_df['sale_price'] = deals_df['sale_price'].apply(lambda x: f"${x:.2f}")
            deals_df['savings'] = deals_df['savings'].apply(lambda x: f"${x:.2f}")
            deals_df['pct_off'] = deals_df['pct_off'].apply(lambda x: f"{x:.0f}%")
            
            st.dataframe(deals_df, use_container_width=True, height=500)
        else:
            st.info("No sale items found for selected filters")
    except Exception as e:
        st.error(f"Error: {e}")

with tab4:
    st.header("🔍 Custom Price Search")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        search_term = st.text_input("Product name contains", "")
    with col2:
        min_price = st.number_input("Min Price", 0, 500, min_price_filter)
    with col3:
        max_price = st.number_input("Max Price", 0, 500, 100)
    
    if st.button("Search") and search_term:
        try:
            with engine.connect() as conn:
                state_filter = "AND d.state = :state" if selected_state != 'All States' else ""
                params = {"search": f"%{search_term}%", "min": min_price, "max": max_price}
                if selected_state != 'All States':
                    params["state"] = selected_state
                    
                results = pd.read_sql(text(f"""
                    SELECT r.raw_name as product, r.raw_brand as brand, r.raw_category as category,
                           r.raw_price as price, d.name as store, d.state
                    FROM raw_menu_item r
                    JOIN dispensary d ON d.dispensary_id = r.dispensary_id
                    WHERE r.raw_name ILIKE :search
                    AND r.raw_price BETWEEN :min AND :max
                    AND r.observed_at > NOW() - INTERVAL '24 hours'
                    {state_filter}
                    ORDER BY r.raw_price ASC
                    LIMIT 100
                """), conn, params=params)
            
            if not results.empty:
                st.success(f"Found {len(results)} products")
                st.dataframe(results, use_container_width=True)
            else:
                st.warning("No products found")
        except Exception as e:
            st.error(f"Error: {e}")

st.divider()
st.caption("Prices from last 24 hours of scrapes")
