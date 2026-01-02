# app/pages/2_Availability.py
"""Product Availability - Browse by state, store, category."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
from sqlalchemy import text
from core.db import get_engine

st.set_page_config(page_title="Availability", page_icon="📦", layout="wide")
st.title("📦 Product Availability")

engine = get_engine()

# Get states
@st.cache_data(ttl=300)
def get_states():
    with engine.connect() as conn:
        df = pd.read_sql(text("""
            SELECT DISTINCT COALESCE(state, 'Unknown') as state, COUNT(*) as cnt
            FROM dispensary 
            GROUP BY state
            ORDER BY cnt DESC
        """), conn)
    return df

# Get stores for a state
@st.cache_data(ttl=300)
def get_stores(state):
    with engine.connect() as conn:
        if state == 'All':
            df = pd.read_sql(text("""
                SELECT dispensary_id, name, state
                FROM dispensary WHERE is_active = true
                ORDER BY name
            """), conn)
        else:
            df = pd.read_sql(text("""
                SELECT dispensary_id, name, state
                FROM dispensary 
                WHERE state = :state AND is_active = true
                ORDER BY name
            """), conn, params={"state": state})
    return df

# Get categories for a store
@st.cache_data(ttl=300)
def get_store_categories(dispensary_id):
    with engine.connect() as conn:
        df = pd.read_sql(text("""
            SELECT raw_category as category, COUNT(*) as cnt
            FROM raw_menu_item
            WHERE dispensary_id = :disp_id
            AND scrape_run_id = (
                SELECT scrape_run_id FROM scrape_run 
                WHERE dispensary_id = :disp_id AND status = 'success'
                ORDER BY started_at DESC LIMIT 1
            )
            GROUP BY raw_category
            ORDER BY cnt DESC
        """), conn, params={"disp_id": dispensary_id})
    return df

# Get products for a store/category
@st.cache_data(ttl=300)
def get_products(dispensary_id, category=None):
    with engine.connect() as conn:
        if category and category != 'All Categories':
            df = pd.read_sql(text("""
                SELECT raw_name as product, raw_brand as brand, raw_category as category,
                       raw_price as price, raw_discount_price as sale_price
                FROM raw_menu_item
                WHERE dispensary_id = :disp_id
                AND raw_category = :cat
                AND scrape_run_id = (
                    SELECT scrape_run_id FROM scrape_run 
                    WHERE dispensary_id = :disp_id AND status = 'success'
                    ORDER BY started_at DESC LIMIT 1
                )
                ORDER BY raw_brand, raw_name
            """), conn, params={"disp_id": dispensary_id, "cat": category})
        else:
            df = pd.read_sql(text("""
                SELECT raw_name as product, raw_brand as brand, raw_category as category,
                       raw_price as price, raw_discount_price as sale_price
                FROM raw_menu_item
                WHERE dispensary_id = :disp_id
                AND scrape_run_id = (
                    SELECT scrape_run_id FROM scrape_run 
                    WHERE dispensary_id = :disp_id AND status = 'success'
                    ORDER BY started_at DESC LIMIT 1
                )
                ORDER BY raw_category, raw_brand, raw_name
                LIMIT 500
            """), conn, params={"disp_id": dispensary_id})
    return df

# Sidebar filters
st.sidebar.header("🔍 Filters")

states_df = get_states()
state_options = ['All'] + states_df['state'].tolist()
selected_state = st.sidebar.selectbox("State", state_options, index=state_options.index('MD') if 'MD' in state_options else 0)

stores_df = get_stores(None if selected_state == 'All' else selected_state)
store_options = ['Select a store...'] + stores_df['name'].tolist()
selected_store = st.sidebar.selectbox("Dispensary", store_options)

# Main content
if selected_store == 'Select a store...':
    st.info(f"📍 **{len(stores_df)}** dispensaries in **{selected_state}**")
    st.dataframe(stores_df[['name', 'state']], use_container_width=True, height=400)
else:
    # Get dispensary ID
    disp_row = stores_df[stores_df['name'] == selected_store].iloc[0]
    disp_id = disp_row['dispensary_id']
    
    st.subheader(f"🏪 {selected_store}")
    
    # Get categories
    try:
        categories_df = get_store_categories(disp_id)
        
        if not categories_df.empty:
            # Category filter
            cat_options = ['All Categories'] + categories_df['category'].tolist()
            selected_cat = st.selectbox("Filter by Category", cat_options)
            
            # Show category summary
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown("**Category Breakdown**")
                st.dataframe(categories_df, use_container_width=True, height=300)
            
            with col2:
                # Show products
                products_df = get_products(disp_id, selected_cat)
                
                if not products_df.empty:
                    st.markdown(f"**Products** ({len(products_df)} items)")
                    
                    # Format prices
                    products_df['price'] = products_df['price'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "")
                    products_df['sale_price'] = products_df['sale_price'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "")
                    
                    st.dataframe(products_df, use_container_width=True, height=400)
                else:
                    st.warning("No products found")
        else:
            st.warning("No data for this store yet. Run a scrape first.")
            
    except Exception as e:
        st.error(f"Error loading store data: {e}")

st.divider()
st.caption("Data from most recent scrape per store")
