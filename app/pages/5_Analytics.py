# app/pages/5_Analytics.py
"""Analytics dashboard for Shelf Intel data."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from sqlalchemy import text
import json

st.set_page_config(page_title="Analytics", page_icon="📊", layout="wide")
st.title("📊 Shelf Intel Analytics")

# Database connection
from core.db import get_engine

engine = get_engine()

# Sidebar filters
st.sidebar.header("Filters")

# Date range filter
date_range = st.sidebar.selectbox(
    "Time Period",
    ["Last 24 hours", "Last 7 days", "Last 30 days", "All time"],
    index=1
)

date_map = {
    "Last 24 hours": 1,
    "Last 7 days": 7,
    "Last 30 days": 30,
    "All time": 9999
}
days_back = date_map[date_range]
cutoff_date = datetime.now() - timedelta(days=days_back)

# Tab layout
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Overview", 
    "🏷️ Brands", 
    "📦 Categories", 
    "👻 Disappeared Products",
    "🏪 Store Comparison"
])

# ============ TAB 1: OVERVIEW ============
with tab1:
    st.header("Overview")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with engine.connect() as conn:
        # Total products
        total_products = conn.execute(text("SELECT COUNT(*) FROM raw_menu_item")).scalar()
        
        # Total dispensaries
        total_dispensaries = conn.execute(text("SELECT COUNT(*) FROM dispensary")).scalar()
        
        # Total scrape runs
        total_runs = conn.execute(text("SELECT COUNT(*) FROM scrape_run")).scalar()
        
        # Currently listed items
        try:
            currently_listed = conn.execute(text(
                "SELECT COUNT(*) FROM menu_item_state WHERE currently_listed = true"
            )).scalar() or 0
        except:
            currently_listed = "N/A"
    
    col1.metric("Total Products Scraped", f"{total_products:,}")
    col2.metric("Dispensaries", total_dispensaries)
    col3.metric("Scrape Runs", total_runs)
    col4.metric("Currently Listed", f"{currently_listed:,}" if isinstance(currently_listed, int) else currently_listed)
    
    st.divider()
    
    # Scrape activity over time
    st.subheader("Scrape Activity")
    
    with engine.connect() as conn:
        scrape_df = pd.read_sql(text("""
            SELECT DATE(scraped_at) as date, COUNT(*) as items, COUNT(DISTINCT dispensary_id) as stores
            FROM raw_menu_item
            WHERE scraped_at > :cutoff
            GROUP BY DATE(scraped_at)
            ORDER BY date
        """), conn, params={"cutoff": cutoff_date})
    
    if not scrape_df.empty:
        fig = px.bar(scrape_df, x='date', y='items', title='Products Scraped by Day')
        st.plotly_chart(fig, use_container_width=True)


# ============ TAB 2: BRANDS ============
with tab2:
    st.header("Brand Analysis")
    
    with engine.connect() as conn:
        brand_df = pd.read_sql(text("""
            SELECT brand, COUNT(*) as sku_count
            FROM raw_menu_item
            WHERE brand IS NOT NULL AND brand != ''
            GROUP BY brand
            ORDER BY sku_count DESC
            LIMIT 50
        """), conn)
    
    if not brand_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Top 25 Brands by SKU Count")
            fig = px.bar(
                brand_df.head(25), 
                x='sku_count', 
                y='brand', 
                orientation='h',
                title='SKUs per Brand'
            )
            fig.update_layout(yaxis={'categoryorder':'total ascending'}, height=600)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Brand Market Share (Top 20)")
            top_20 = brand_df.head(20)
            fig = px.pie(top_20, values='sku_count', names='brand', title='Brand Distribution')
            st.plotly_chart(fig, use_container_width=True)
        
        # Brand table
        st.subheader("All Brands")
        st.dataframe(brand_df, use_container_width=True, height=400)
    else:
        st.info("No brand data available")


# ============ TAB 3: CATEGORIES ============
with tab3:
    st.header("Category Breakdown")
    
    with engine.connect() as conn:
        category_df = pd.read_sql(text("""
            SELECT category, COUNT(*) as product_count
            FROM raw_menu_item
            WHERE category IS NOT NULL AND category != ''
            GROUP BY category
            ORDER BY product_count DESC
        """), conn)
    
    if not category_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Products by Category")
            fig = px.pie(
                category_df.head(15), 
                values='product_count', 
                names='category',
                title='Category Distribution',
                hole=0.4
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Category Counts")
            fig = px.bar(
                category_df.head(20),
                x='category',
                y='product_count',
                title='Products per Category'
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        
        # Normalized categories (group similar)
        st.subheader("Simplified Category View")
        
        def normalize_category(cat):
            cat = cat.lower() if cat else ''
            if 'flower' in cat or 'bud' in cat:
                return 'Flower'
            elif 'edible' in cat or 'gummy' in cat or 'chocolate' in cat or 'candy' in cat:
                return 'Edibles'
            elif 'vape' in cat or 'cart' in cat or 'pen' in cat:
                return 'Vapes'
            elif 'pre-roll' in cat or 'preroll' in cat or 'joint' in cat:
                return 'Pre-Rolls'
            elif 'concentrate' in cat or 'wax' in cat or 'shatter' in cat or 'dab' in cat or 'extract' in cat:
                return 'Concentrates'
            elif 'tincture' in cat or 'oil' in cat or 'rso' in cat:
                return 'Tinctures/Oils'
            elif 'topical' in cat or 'cream' in cat or 'lotion' in cat:
                return 'Topicals'
            elif 'accessory' in cat or 'gear' in cat or 'pipe' in cat or 'bong' in cat:
                return 'Accessories'
            else:
                return 'Other'
        
        category_df['simplified'] = category_df['category'].apply(normalize_category)
        simplified = category_df.groupby('simplified')['product_count'].sum().reset_index()
        simplified = simplified.sort_values('product_count', ascending=False)
        
        fig = px.pie(simplified, values='product_count', names='simplified', title='Simplified Category Breakdown')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No category data available")


# ============ TAB 4: DISAPPEARED PRODUCTS ============
with tab4:
    st.header("👻 Disappeared Products")
    
    st.markdown("""
    Products that were listed but have not been seen in recent scrapes.
    This could indicate: out of stock, discontinued, or delisted products.
    """)
    
    # Filter for days missing
    days_missing = st.slider("Missing for at least X days", 1, 30, 3)
    missing_cutoff = datetime.now() - timedelta(days=days_missing)
    
    with engine.connect() as conn:
        try:
            disappeared_df = pd.read_sql(text("""
                SELECT 
                    mis.canonical_name as product_name,
                    mis.canonical_brand as brand,
                    d.name as dispensary,
                    mis.first_seen_at,
                    mis.last_seen_at,
                    mis.last_missing_at,
                    EXTRACT(DAY FROM NOW() - mis.last_seen_at) as days_missing
                FROM menu_item_state mis
                JOIN dispensary d ON d.dispensary_id = mis.dispensary_id
                WHERE mis.currently_listed = false
                AND mis.last_seen_at < :cutoff
                ORDER BY mis.last_seen_at DESC
                LIMIT 500
            """), conn, params={"cutoff": missing_cutoff})
            
            if not disappeared_df.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Disappeared Products", len(disappeared_df))
                
                with col2:
                    avg_days = disappeared_df['days_missing'].mean()
                    st.metric("Avg Days Missing", f"{avg_days:.1f}")
                
                # By brand
                st.subheader("Disappeared by Brand")
                by_brand = disappeared_df.groupby('brand').size().reset_index(name='count')
                by_brand = by_brand.sort_values('count', ascending=False).head(20)
                
                fig = px.bar(by_brand, x='brand', y='count', title='Disappeared Products by Brand')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
                
                # Table
                st.subheader("Disappeared Products List")
                st.dataframe(disappeared_df, use_container_width=True, height=400)
            else:
                st.success("No products have disappeared for that time period!")
                
        except Exception as e:
            st.warning(f"Availability tracking not fully set up yet. Error: {e}")
            st.info("Run more scrapes to build up appeared/disappeared data.")


# ============ TAB 5: STORE COMPARISON ============
with tab5:
    st.header("🏪 Store Comparison")
    
    with engine.connect() as conn:
        store_df = pd.read_sql(text("""
            SELECT 
                d.name as store_name,
                d.state,
                COUNT(DISTINCT r.raw_menu_item_id) as total_products,
                COUNT(DISTINCT r.brand) as unique_brands,
                COUNT(DISTINCT r.category) as unique_categories,
                AVG(r.price) as avg_price
            FROM dispensary d
            LEFT JOIN raw_menu_item r ON r.dispensary_id = d.dispensary_id
            GROUP BY d.dispensary_id, d.name, d.state
            ORDER BY total_products DESC
        """), conn)
    
    if not store_df.empty:
        # Metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Stores", len(store_df))
        col2.metric("Avg Products/Store", f"{store_df['total_products'].mean():.0f}")
        col3.metric("Avg Price", f"${store_df['avg_price'].mean():.2f}" if store_df['avg_price'].notna().any() else "N/A")
        
        # Top stores by product count
        st.subheader("Stores by Product Count")
        fig = px.bar(
            store_df.head(30),
            x='store_name',
            y='total_products',
            title='Top 30 Stores by Product Count'
        )
        fig.update_layout(xaxis_tickangle=-45, height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        # Scatter: products vs brands
        st.subheader("Products vs Unique Brands")
        fig = px.scatter(
            store_df,
            x='unique_brands',
            y='total_products',
            hover_name='store_name',
            title='Store Diversity: Products vs Unique Brands',
            size='total_products',
            color='state'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Full table
        st.subheader("All Stores")
        st.dataframe(store_df, use_container_width=True, height=400)
    else:
        st.info("No store data available")


# Footer
st.divider()
st.caption(f"Data as of {datetime.now().strftime('%Y-%m-%d %H:%M')}")
