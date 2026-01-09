# app/pages/7_Brand_Analytics.py
"""Brand Analytics - Market intelligence for cannabis brands."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import text
from core.db import get_engine
from core.category_utils import get_normalized_category_sql

st.set_page_config(page_title="Brand Analytics | CannLinx", page_icon=None, layout="wide", initial_sidebar_state="expanded")

# Import and render navigation
from components.sidebar_nav import render_nav
render_nav()

st.title("Brand Analytics")
st.markdown("Market intelligence and brand performance across Maryland dispensaries")

engine = get_engine()

@st.cache_data(ttl=300)
def get_brand_data():
    """Get comprehensive brand analytics."""
    with engine.connect() as conn:
        # Top brands by store presence
        brand_presence = pd.read_sql(text("""
            SELECT raw_brand as brand,
                   COUNT(DISTINCT r.dispensary_id) as store_count,
                   COUNT(DISTINCT raw_name) as product_count,
                   AVG(raw_price) as avg_price
            FROM raw_menu_item r
            WHERE raw_brand IS NOT NULL AND raw_brand != ''
            GROUP BY raw_brand
            HAVING COUNT(DISTINCT r.dispensary_id) >= 2
            ORDER BY store_count DESC, product_count DESC
        """), conn)

        # Brand category breakdown (normalized)
        cat_sql = get_normalized_category_sql()
        brand_categories = pd.read_sql(text(f"""
            SELECT raw_brand as brand, {cat_sql} as category,
                   COUNT(DISTINCT raw_name) as products
            FROM raw_menu_item
            WHERE raw_brand IS NOT NULL AND raw_brand != ''
            AND raw_category IS NOT NULL
            GROUP BY raw_brand, {cat_sql}
        """), conn)

        # Brand pricing by category (normalized)
        brand_pricing = pd.read_sql(text(f"""
            SELECT raw_brand as brand, {cat_sql} as category,
                   AVG(raw_price) as avg_price,
                   MIN(raw_price) as min_price,
                   MAX(raw_price) as max_price,
                   COUNT(*) as count
            FROM raw_menu_item
            WHERE raw_brand IS NOT NULL AND raw_brand != ''
            AND raw_price > 0 AND raw_price < 500
            GROUP BY raw_brand, {cat_sql}
            HAVING COUNT(*) >= 3
        """), conn)

        # Total stats
        total_brands = conn.execute(text(
            "SELECT COUNT(DISTINCT raw_brand) FROM raw_menu_item WHERE raw_brand IS NOT NULL"
        )).scalar() or 0

        total_stores = conn.execute(text(
            "SELECT COUNT(DISTINCT dispensary_id) FROM raw_menu_item"
        )).scalar() or 0

    return brand_presence, brand_categories, brand_pricing, total_brands, total_stores

try:
    brand_presence, brand_categories, brand_pricing, total_brands, total_stores = get_brand_data()

    # Key metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Brands", f"{total_brands:,}")
    c2.metric("Stores Tracked", f"{total_stores}")

    if not brand_presence.empty:
        top_brand = brand_presence.iloc[0]
        c3.metric("Top Brand (by reach)", top_brand['brand'], f"{int(top_brand['store_count'])} stores")
        avg_reach = brand_presence['store_count'].mean()
        c4.metric("Avg Brand Reach", f"{avg_reach:.1f} stores")

    st.divider()

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["Market Presence", "Category Analysis", "Pricing Intelligence"])

    with tab1:
        st.subheader("Brand Distribution Across Stores")

        if not brand_presence.empty:
            # Top 20 brands by store presence
            top_brands = brand_presence.head(20)

            fig = px.bar(
                top_brands,
                x='store_count',
                y='brand',
                orientation='h',
                color='product_count',
                color_continuous_scale='Viridis',
                hover_data=['avg_price', 'product_count'],
                labels={'store_count': 'Stores Carrying', 'brand': 'Brand', 'product_count': 'Products'}
            )
            fig.update_layout(
                height=600,
                yaxis={'categoryorder': 'total ascending'},
                coloraxis_colorbar_title='Products'
            )
            st.plotly_chart(fig, use_container_width=True)

            # Brand reach distribution
            st.subheader("Brand Reach Distribution")
            reach_dist = brand_presence['store_count'].value_counts().sort_index().reset_index()
            reach_dist.columns = ['stores', 'brands']

            fig2 = px.bar(
                reach_dist,
                x='stores',
                y='brands',
                labels={'stores': 'Number of Stores', 'brands': 'Number of Brands'}
            )
            fig2.update_layout(height=300)
            st.plotly_chart(fig2, use_container_width=True)

            st.caption(f"Distribution shows how many brands are in N stores (e.g., {reach_dist.iloc[-1]['brands']} brands are in {reach_dist.iloc[-1]['stores']} stores)")

        else:
            st.info("No brand data available")

    with tab2:
        st.subheader("Brand Portfolio by Category")

        if not brand_categories.empty:
            # Brand selector
            top_brand_list = brand_presence.head(30)['brand'].tolist()
            selected_brands = st.multiselect(
                "Select brands to compare",
                top_brand_list,
                default=top_brand_list[:5]
            )

            if selected_brands:
                filtered = brand_categories[brand_categories['brand'].isin(selected_brands)]

                # Stacked bar by category
                fig = px.bar(
                    filtered,
                    x='brand',
                    y='products',
                    color='category',
                    barmode='stack',
                    labels={'products': 'Product Count', 'brand': 'Brand'}
                )
                fig.update_layout(height=400, xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)

                # Category breakdown table
                pivot = filtered.pivot_table(
                    index='brand',
                    columns='category',
                    values='products',
                    fill_value=0
                )
                st.dataframe(pivot, use_container_width=True)
        else:
            st.info("No category data available")

    with tab3:
        st.subheader("Brand Pricing Analysis")

        if not brand_pricing.empty:
            # Category filter
            categories = ['All'] + sorted(brand_pricing['category'].dropna().unique().tolist())
            selected_cat = st.selectbox("Filter by category", categories)

            if selected_cat != 'All':
                pricing_filtered = brand_pricing[brand_pricing['category'] == selected_cat]
            else:
                pricing_filtered = brand_pricing.groupby('brand').agg({
                    'avg_price': 'mean',
                    'min_price': 'min',
                    'max_price': 'max',
                    'count': 'sum'
                }).reset_index()

            # Top 20 by product count
            pricing_top = pricing_filtered.nlargest(20, 'count' if 'count' in pricing_filtered.columns else 'avg_price')

            # Price comparison chart
            fig = go.Figure()

            fig.add_trace(go.Bar(
                name='Avg Price',
                x=pricing_top['brand'],
                y=pricing_top['avg_price'],
                marker_color='steelblue'
            ))

            fig.update_layout(
                height=400,
                xaxis_tickangle=-45,
                yaxis_title='Average Price ($)',
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)

            # Price range scatter
            st.subheader("Price Range by Brand")
            fig2 = go.Figure()

            for _, row in pricing_top.iterrows():
                fig2.add_trace(go.Scatter(
                    x=[row['brand'], row['brand']],
                    y=[row['min_price'], row['max_price']],
                    mode='lines+markers',
                    name=row['brand'],
                    line=dict(width=3),
                    showlegend=False
                ))
                fig2.add_trace(go.Scatter(
                    x=[row['brand']],
                    y=[row['avg_price']],
                    mode='markers',
                    marker=dict(size=10, symbol='diamond', color='red'),
                    name=f"{row['brand']} avg",
                    showlegend=False
                ))

            fig2.update_layout(
                height=400,
                xaxis_tickangle=-45,
                yaxis_title='Price ($)',
                xaxis_title='Brand'
            )
            st.plotly_chart(fig2, use_container_width=True)
            st.caption("Lines show min-max range, diamonds show average price")

        else:
            st.info("No pricing data available")

except Exception as e:
    st.error(f"Error loading brand analytics: {e}")

st.divider()
st.caption("Brand data aggregated from all tracked dispensary menus | Updated every 5 minutes")
