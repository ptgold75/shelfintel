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

st.set_page_config(page_title="Analytics | CannaLinx", page_icon=None, layout="wide")
st.title("Analytics")

from core.db import get_engine

@st.cache_resource
def get_db_engine():
    return get_engine()

@st.cache_data(ttl=300)
def load_summary_data():
    """Load summary data from actual tables."""
    engine = get_db_engine()
    with engine.connect() as conn:
        # Get totals
        unique_skus = conn.execute(text(
            "SELECT COUNT(DISTINCT raw_name) FROM raw_menu_item WHERE raw_name IS NOT NULL"
        )).scalar() or 0
        observations = conn.execute(text("SELECT COUNT(*) FROM raw_menu_item")).scalar() or 0
        dispensaries = conn.execute(text("SELECT COUNT(*) FROM dispensary")).scalar() or 0
        scrape_runs = conn.execute(text("SELECT COUNT(*) FROM scrape_run")).scalar() or 0

        totals = {
            "unique_skus": unique_skus,
            "observations": observations,
            "dispensaries": dispensaries,
            "scrape_runs": scrape_runs,
        }

        # Get brand counts
        brands = pd.read_sql(text("""
            SELECT raw_brand as brand, COUNT(*) as sku_count
            FROM raw_menu_item
            WHERE raw_brand IS NOT NULL
            GROUP BY raw_brand
            ORDER BY sku_count DESC
            LIMIT 20
        """), conn)

        # Get category counts
        categories = pd.read_sql(text("""
            SELECT raw_category as category, COUNT(*) as product_count
            FROM raw_menu_item
            WHERE raw_category IS NOT NULL
            GROUP BY raw_category
            ORDER BY product_count DESC
        """), conn)

    return totals, brands, categories

@st.cache_data(ttl=300)
def load_state_data():
    engine = get_db_engine()
    with engine.connect() as conn:
        states = pd.read_sql(text("""
            SELECT
                d.state,
                COUNT(DISTINCT d.dispensary_id) as store_count,
                COUNT(DISTINCT CASE WHEN r.dispensary_id IS NOT NULL THEN d.dispensary_id END) as with_data
            FROM dispensary d
            LEFT JOIN raw_menu_item r ON r.dispensary_id = d.dispensary_id
            WHERE d.state IS NOT NULL AND d.is_active = true
            GROUP BY d.state
            ORDER BY d.state
        """), conn)
    # Calculate coverage percentage
    states['coverage_pct'] = (states['with_data'] / states['store_count'] * 100).round(1)
    return states

try:
    totals, brand_df, category_df = load_summary_data()
    state_df = load_state_data()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# Sidebar - State Filter
st.sidebar.header("Filters")
states_list = ['All States'] + sorted(state_df['state'].dropna().tolist())
selected_state = st.sidebar.selectbox("State", states_list)

tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Brands", "Categories", "Stores"])

with tab1:
    st.header("Overview")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Observations", f"{totals.get('observations', 0):,}")
    col2.metric("Unique Products", f"{totals.get('unique_skus', 0):,}")
    col3.metric("Dispensaries", f"{totals.get('dispensaries', 0):,}")
    col4.metric("Scrape Runs", f"{totals.get('scrape_runs', 0):,}")

    st.divider()
    st.subheader("Coverage by State")
    if not state_df.empty:
        # Sort by state name for display
        display_df = state_df.sort_values('state')

        # Create bar chart with dispensary count and coverage
        import plotly.graph_objects as go
        fig = go.Figure()

        # Add bars for total dispensaries
        fig.add_trace(go.Bar(
            x=display_df['state'],
            y=display_df['store_count'],
            name='Total Dispensaries',
            marker_color='#94a3b8',
            text=display_df['store_count'],
            textposition='outside',
        ))

        # Add bars for dispensaries with data (stacked appearance via overlay)
        fig.add_trace(go.Bar(
            x=display_df['state'],
            y=display_df['with_data'],
            name='With Menu Data',
            marker_color=display_df['coverage_pct'].apply(
                lambda x: '#22c55e' if x >= 70 else ('#f59e0b' if x >= 40 else '#ef4444')
            ),
            text=display_df.apply(lambda r: f"{r['coverage_pct']:.0f}%", axis=1),
            textposition='inside',
        ))

        fig.update_layout(
            title="Dispensaries and Coverage by State",
            xaxis_title="State",
            yaxis_title="Number of Dispensaries",
            barmode='overlay',
            height=500,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        fig.update_xaxes(tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

        # Summary table below chart
        st.markdown("**Coverage Summary:**")
        summary_df = display_df[['state', 'store_count', 'with_data', 'coverage_pct']].copy()
        summary_df.columns = ['State', 'Total Stores', 'With Data', 'Coverage %']
        st.dataframe(summary_df, use_container_width=True, height=300)

with tab2:
    st.header("Brand Analysis")
    if not brand_df.empty:
        fig = px.bar(brand_df.head(15), x="sku_count", y="brand", orientation="h", title="Top Brands by Product Count")
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=500)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(brand_df, use_container_width=True)
    else:
        st.info("No brand data available")

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
    else:
        st.info("No category data available")

with tab4:
    st.header("Stores by State")
    if not state_df.empty:
        st.dataframe(state_df, use_container_width=True)

        # Show stores for selected state
        if selected_state != 'All States':
            st.subheader(f"Dispensaries in {selected_state}")
            engine = get_db_engine()
            with engine.connect() as conn:
                stores = pd.read_sql(text(
                    "SELECT name, city, address FROM dispensary WHERE COALESCE(state, 'MD') = :state ORDER BY name"
                ), conn, params={"state": selected_state})
            if not stores.empty:
                st.dataframe(stores, use_container_width=True)
            else:
                st.info(f"No stores found in {selected_state}")

st.divider()
st.caption(f"Data refreshed every 5 minutes | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
