# app/pages/1_Dashboard.py
"""Dashboard - Market overview with charts and insights."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import text
from core.db import get_engine

st.set_page_config(page_title="Dashboard | CannLinx", page_icon=None, layout="wide", initial_sidebar_state="collapsed")

# Import and render navigation
from app.components.nav import render_nav
render_nav()

st.title("Market Dashboard")
st.markdown("High-level market insights across Maryland dispensaries")

@st.cache_data(ttl=300)
def load_dashboard_data():
    """Load dashboard data from database."""
    engine = get_engine()
    with engine.connect() as conn:
        # High-level stats
        stats = {
            "products": conn.execute(text(
                "SELECT COUNT(DISTINCT raw_name) FROM raw_menu_item WHERE raw_name IS NOT NULL"
            )).scalar() or 0,
            "dispensaries": conn.execute(text(
                "SELECT COUNT(*) FROM dispensary"
            )).scalar() or 0,
            "brands": conn.execute(text(
                "SELECT COUNT(DISTINCT raw_brand) FROM raw_menu_item WHERE raw_brand IS NOT NULL"
            )).scalar() or 0,
            "categories": conn.execute(text(
                "SELECT COUNT(DISTINCT raw_category) FROM raw_menu_item WHERE raw_category IS NOT NULL"
            )).scalar() or 0,
        }

        # Category breakdown
        categories_df = pd.read_sql(text("""
            SELECT raw_category as category, COUNT(DISTINCT raw_name) as products
            FROM raw_menu_item
            WHERE raw_category IS NOT NULL
            GROUP BY raw_category
            ORDER BY products DESC
        """), conn)

        # Top brands
        brands_df = pd.read_sql(text("""
            SELECT raw_brand as brand, COUNT(DISTINCT raw_name) as products
            FROM raw_menu_item
            WHERE raw_brand IS NOT NULL AND raw_brand != ''
            GROUP BY raw_brand
            ORDER BY products DESC
            LIMIT 15
        """), conn)

        # Price distribution by category
        prices_df = pd.read_sql(text("""
            SELECT raw_category as category,
                   AVG(raw_price) as avg_price,
                   MIN(raw_price) as min_price,
                   MAX(raw_price) as max_price,
                   COUNT(*) as count
            FROM raw_menu_item
            WHERE raw_price IS NOT NULL AND raw_price > 0 AND raw_price < 500
            AND raw_category IS NOT NULL
            GROUP BY raw_category
            HAVING COUNT(*) > 10
            ORDER BY avg_price DESC
        """), conn)

        # Dispensary coverage by provider
        providers_df = pd.read_sql(text("""
            SELECT COALESCE(menu_provider, 'Unknown') as provider, COUNT(*) as stores
            FROM dispensary
            GROUP BY menu_provider
            ORDER BY stores DESC
        """), conn)

        # Products per store (top stores)
        stores_df = pd.read_sql(text("""
            SELECT d.name, COUNT(DISTINCT r.raw_name) as products
            FROM dispensary d
            JOIN raw_menu_item r ON d.dispensary_id = r.dispensary_id
            GROUP BY d.name
            ORDER BY products DESC
            LIMIT 10
        """), conn)

    return stats, categories_df, brands_df, prices_df, providers_df, stores_df

try:
    stats, categories_df, brands_df, prices_df, providers_df, stores_df = load_dashboard_data()

    # Key metrics row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Products Tracked", f"{stats['products']:,}")
    c2.metric("Dispensaries", f"{stats['dispensaries']:,}")
    c3.metric("Brands", f"{stats['brands']:,}")
    c4.metric("Categories", f"{stats['categories']:,}")

    st.divider()

    # Charts row 1: Category breakdown and Top Brands
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Product Mix by Category")
        if not categories_df.empty:
            fig = px.pie(categories_df, values='products', names='category',
                        hole=0.4, color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=350,
                            showlegend=True, legend=dict(orientation="h", y=-0.1))
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No category data available")

    with col2:
        st.subheader("Top Brands by Product Count")
        if not brands_df.empty:
            fig = px.bar(brands_df.head(10), x='products', y='brand', orientation='h',
                        color='products', color_continuous_scale='Blues')
            fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=350,
                            yaxis={'categoryorder': 'total ascending'},
                            showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No brand data available")

    # Charts row 2: Price Analysis and Store Coverage
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("Average Price by Category")
        if not prices_df.empty:
            fig = px.bar(prices_df, x='category', y='avg_price',
                        color='avg_price', color_continuous_scale='Greens',
                        hover_data=['min_price', 'max_price', 'count'])
            fig.update_layout(margin=dict(t=20, b=60, l=20, r=20), height=350,
                            xaxis_tickangle=-45, showlegend=False, coloraxis_showscale=False)
            fig.update_yaxes(title_text="Avg Price ($)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No price data available")

    with col4:
        st.subheader("Menu Provider Coverage")
        if not providers_df.empty:
            fig = px.pie(providers_df, values='stores', names='provider',
                        color_discrete_sequence=px.colors.qualitative.Pastel)
            fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=350)
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No provider data available")

    # Bottom section: Top stores by inventory
    st.divider()
    st.subheader("Stores with Largest Inventory")
    if not stores_df.empty:
        fig = px.bar(stores_df, x='name', y='products',
                    color='products', color_continuous_scale='Viridis')
        fig.update_layout(margin=dict(t=20, b=80, l=20, r=20), height=300,
                        xaxis_tickangle=-45, showlegend=False, coloraxis_showscale=False)
        fig.update_yaxes(title_text="Unique Products")
        fig.update_xaxes(title_text="")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No store inventory data available")

except Exception as e:
    st.error(f"Error loading dashboard: {e}")

st.divider()
st.caption("Data updated every 5 minutes | Maryland market coverage")
