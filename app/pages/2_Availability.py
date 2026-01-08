# app/pages/2_Availability.py
"""Product Availability - Browse by state, store, category with size breakdowns."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
import plotly.express as px
import re
from sqlalchemy import text
from core.db import get_engine
from core.category_utils import get_normalized_category_sql

st.set_page_config(page_title="Availability | CannLinx", page_icon=None, layout="wide", initial_sidebar_state="collapsed")

# Import and render navigation
from components.nav import render_nav
render_nav()

st.title("Product Availability")

engine = get_engine()

# Size parsing functions
def parse_vape_size(name):
    """Parse vape/cart size from product name."""
    name = name.lower() if name else ""
    
    # Check for disposable/all-in-one
    if any(x in name for x in ['disposable', 'all-in-one', 'all in one', 'aio', 'rechargeable']):
        size_type = 'Disposable'
    else:
        size_type = 'Cartridge'
    
    # Parse mg/g
    if '2000' in name or '2g' in name or '2 g' in name:
        return f"{size_type} 2000mg"
    elif '1000' in name or '1g' in name or '1 g' in name or 'full gram' in name:
        return f"{size_type} 1000mg"
    elif '500' in name or '.5g' in name or '.5 g' in name or 'half gram' in name or '0.5' in name:
        return f"{size_type} 500mg"
    elif '300' in name or '.3g' in name or '.3 g' in name:
        return f"{size_type} 300mg"
    else:
        return f"{size_type} Other"

def parse_flower_size(name):
    """Parse flower size from product name."""
    name = name.lower() if name else ""
    
    if any(x in name for x in ['28g', '28 g', 'ounce', '1oz', '1 oz']):
        return '28g (1oz)'
    elif any(x in name for x in ['14g', '14 g', 'half oz', 'half ounce', '1/2 oz']):
        return '14g (1/2oz)'
    elif any(x in name for x in ['7g', '7 g', 'quarter', '1/4 oz', 'q oz']):
        return '7g (1/4oz)'
    elif any(x in name for x in ['3.5g', '3.5 g', 'eighth', '1/8', '⅛']):
        return '3.5g (1/8oz)'
    elif any(x in name for x in ['1g', '1 g', 'gram']) and '14g' not in name and '28g' not in name:
        return '1g'
    else:
        return 'Other'

def parse_preroll_size(name):
    """Parse pre-roll size from product name."""
    name = name.lower() if name else ""
    
    # Check for packs
    pack_match = re.search(r'(\d+)\s*(?:pk|pack|ct|count)', name)
    pack_size = f" ({pack_match.group(1)}pk)" if pack_match else ""
    
    if '2g' in name or '2 g' in name:
        return f'2g{pack_size}'
    elif '1.5g' in name or '1.5 g' in name:
        return f'1.5g{pack_size}'
    elif '1g' in name or '1 g' in name or 'full gram' in name:
        return f'1g{pack_size}'
    elif '.7g' in name or '0.7g' in name or '.7 g' in name:
        return f'0.7g{pack_size}'
    elif '.5g' in name or '0.5g' in name or '.5 g' in name or 'half gram' in name:
        return f'0.5g{pack_size}'
    elif '.35g' in name or '0.35g' in name:
        return f'0.35g{pack_size}'
    else:
        return f'Other{pack_size}'

# Caching functions
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

@st.cache_data(ttl=300)
def get_stores(state):
    with engine.connect() as conn:
        if state == 'All':
            df = pd.read_sql(text("""
                SELECT dispensary_id, name, COALESCE(state, 'MD') as state
                FROM dispensary
                ORDER BY name
            """), conn)
        else:
            df = pd.read_sql(text("""
                SELECT dispensary_id, name, COALESCE(state, 'MD') as state
                FROM dispensary
                WHERE COALESCE(state, 'MD') = :state
                ORDER BY name
            """), conn, params={"state": state})
    return df

@st.cache_data(ttl=300)
def get_store_summary(dispensary_id):
    cat_sql = get_normalized_category_sql()
    with engine.connect() as conn:
        # Categories (normalized)
        categories = pd.read_sql(text(f"""
            SELECT {cat_sql} as category, COUNT(*) as cnt
            FROM raw_menu_item
            WHERE dispensary_id = :disp_id
            AND scrape_run_id = (
                SELECT scrape_run_id FROM scrape_run
                WHERE dispensary_id = :disp_id AND status = 'success'
                ORDER BY started_at DESC LIMIT 1
            )
            GROUP BY {cat_sql}
            ORDER BY cnt DESC
        """), conn, params={"disp_id": dispensary_id})
        
        # Brands
        brands = pd.read_sql(text("""
            SELECT raw_brand as brand, COUNT(*) as products
            FROM raw_menu_item
            WHERE dispensary_id = :disp_id
            AND raw_brand IS NOT NULL AND raw_brand != ''
            AND scrape_run_id = (
                SELECT scrape_run_id FROM scrape_run 
                WHERE dispensary_id = :disp_id AND status = 'success'
                ORDER BY started_at DESC LIMIT 1
            )
            GROUP BY raw_brand
            ORDER BY products DESC
        """), conn, params={"disp_id": dispensary_id})
        
    return categories, brands

@st.cache_data(ttl=300)
def get_products_with_sizes(dispensary_id, category=None):
    cat_sql = get_normalized_category_sql()
    with engine.connect() as conn:
        cat_filter = f"AND ({cat_sql}) = :cat" if category and category != 'All Categories' else ""
        params = {"disp_id": dispensary_id}
        if category and category != 'All Categories':
            params["cat"] = category

        df = pd.read_sql(text(f"""
            SELECT raw_name as product, raw_brand as brand, {cat_sql} as category,
                   raw_price as price, raw_discount_price as sale_price
            FROM raw_menu_item
            WHERE dispensary_id = :disp_id
            {cat_filter}
            AND scrape_run_id = (
                SELECT scrape_run_id FROM scrape_run
                WHERE dispensary_id = :disp_id AND status = 'success'
                ORDER BY started_at DESC LIMIT 1
            )
            ORDER BY {cat_sql}, raw_brand, raw_name
        """), conn, params=params)
    
    # Parse sizes based on normalized category
    if not df.empty:
        def get_size(row):
            cat = (row['category'] or '').lower()
            name = row['product'] or ''

            if cat == 'vapes':
                return parse_vape_size(name)
            elif cat == 'flower':
                return parse_flower_size(name)
            elif cat == 'pre-rolls':
                return parse_preroll_size(name)
            else:
                return 'N/A'

        df['size'] = df.apply(get_size, axis=1)

    return df

# Sidebar filters
st.sidebar.header("🔍 Filters")

states_df = get_states()
state_options = ['All'] + states_df['state'].tolist()
default_idx = state_options.index('MD') if 'MD' in state_options else 0
selected_state = st.sidebar.selectbox("State", state_options, index=default_idx)

stores_df = get_stores(None if selected_state == 'All' else selected_state)
store_options = ['Select a store...'] + stores_df['name'].tolist()
selected_store = st.sidebar.selectbox("Dispensary", store_options)

# Main content
if selected_store == 'Select a store...':
    st.info(f"📍 **{len(stores_df)}** dispensaries in **{selected_state}**")
    st.markdown("Select a store from the sidebar to view inventory details.")
    st.dataframe(stores_df[['name', 'state']], use_container_width=True, height=400)
else:
    # Get dispensary ID
    disp_row = stores_df[stores_df['name'] == selected_store].iloc[0]
    disp_id = disp_row['dispensary_id']
    
    st.subheader(f"{selected_store}")
    
    try:
        categories_df, brands_df = get_store_summary(disp_id)
        
        if not categories_df.empty:
            # Top metrics
            total_products = categories_df['cnt'].sum()
            total_brands = len(brands_df)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Products", f"{total_products:,}")
            col2.metric("Brands Carried", total_brands)
            col3.metric("Categories", len(categories_df))
            
            st.divider()
            
            # Category pie chart and breakdown
            tab1, tab2, tab3 = st.tabs(["Category Breakdown", "Brands", "Product List"])
            
            with tab1:
                col1, col2 = st.columns(2)
                
                with col1:
                    fig = px.pie(categories_df, values='cnt', names='category', 
                                title='Inventory by Category', hole=0.4)
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.markdown("**Category Details**")
                    categories_df['pct'] = (categories_df['cnt'] / total_products * 100).round(1)
                    categories_df['pct'] = categories_df['pct'].apply(lambda x: f"{x}%")
                    st.dataframe(categories_df.rename(columns={'cnt': 'products'}), 
                               use_container_width=True, height=350)
            
            with tab2:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Top 15 brands pie
                    top_brands = brands_df.head(15)
                    fig = px.pie(top_brands, values='products', names='brand',
                                title='Top 15 Brands')
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.markdown(f"**All Brands ({len(brands_df)})**")
                    st.dataframe(brands_df, use_container_width=True, height=400)
            
            with tab3:
                # Category filter
                cat_options = ['All Categories'] + categories_df['category'].tolist()
                selected_cat = st.selectbox("Filter by Category", cat_options)
                
                products_df = get_products_with_sizes(disp_id, selected_cat)
                
                if not products_df.empty:
                    # Size breakdown for relevant categories (normalized names)
                    cat_lower = (selected_cat or '').lower()
                    show_size_chart = cat_lower in ['vapes', 'flower', 'pre-rolls']
                    
                    if show_size_chart or selected_cat == 'All Categories':
                        # Filter to sizeable categories
                        sizeable = products_df[products_df['size'] != 'N/A']
                        if not sizeable.empty:
                            st.markdown("**📏 Size Breakdown**")
                            size_counts = sizeable.groupby('size').size().reset_index(name='count')
                            size_counts = size_counts.sort_values('count', ascending=False)
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                fig = px.pie(size_counts, values='count', names='size', title='Products by Size')
                                st.plotly_chart(fig, use_container_width=True)
                            with col2:
                                st.dataframe(size_counts, use_container_width=True)
                    
                    st.markdown(f"**Products ({len(products_df)} items)**")
                    
                    # Format prices
                    products_df['price'] = products_df['price'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "")
                    products_df['sale_price'] = products_df['sale_price'].apply(lambda x: f"${x:.2f}" if pd.notna(x) and x > 0 else "")
                    
                    st.dataframe(products_df[['product', 'brand', 'category', 'size', 'price', 'sale_price']], 
                               use_container_width=True, height=400)
                else:
                    st.warning("No products found")
        else:
            st.warning("No data for this store yet. Run a scrape first.")
            
    except Exception as e:
        st.error(f"Error loading store data: {e}")

st.divider()
st.caption("Data from most recent scrape per store | Sizes parsed from product names")
