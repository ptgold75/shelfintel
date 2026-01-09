# app/pages/16_Brand_Heatmap.py
"""Brand Coverage Heat Map - Geographic visualization of brand penetration."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import text
from components.sidebar_nav import render_nav, render_state_filter
from components.auth import is_authenticated
from core.db import get_engine

st.set_page_config(
    page_title="Brand Coverage Heat Map - CannLinx",
    layout="wide",
    initial_sidebar_state="expanded"
)

render_nav(require_login=False)

DEMO_MODE = not is_authenticated()

st.title("Brand Coverage Heat Map")
st.markdown("Visualize brand penetration across counties and stores")

# State filter
state = render_state_filter()

if DEMO_MODE:
    st.info("Demo Mode - Log in to see real data for your markets")

    # Demo data
    demo_brands = ["Cookies", "Cresco", "Curaleaf", "GTI", "Trulieve", "Verano"]
    selected_brand = st.selectbox("Select Brand", demo_brands)

    # Create demo county data
    demo_counties = [
        {"county": "Baltimore County", "stores": 12, "brand_stores": 8, "penetration": 67},
        {"county": "Montgomery County", "stores": 15, "brand_stores": 10, "penetration": 67},
        {"county": "Prince George's County", "stores": 10, "brand_stores": 5, "penetration": 50},
        {"county": "Anne Arundel County", "stores": 8, "brand_stores": 6, "penetration": 75},
        {"county": "Howard County", "stores": 6, "brand_stores": 4, "penetration": 67},
        {"county": "Frederick County", "stores": 5, "brand_stores": 2, "penetration": 40},
        {"county": "Harford County", "stores": 4, "brand_stores": 3, "penetration": 75},
        {"county": "Carroll County", "stores": 3, "brand_stores": 1, "penetration": 33},
        {"county": "Washington County", "stores": 3, "brand_stores": 2, "penetration": 67},
        {"county": "Cecil County", "stores": 2, "brand_stores": 1, "penetration": 50},
    ]
    df = pd.DataFrame(demo_counties)

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Stores in State", df['stores'].sum())
    with col2:
        st.metric("Stores Carrying Brand", df['brand_stores'].sum())
    with col3:
        avg_pen = round(df['brand_stores'].sum() / df['stores'].sum() * 100, 1)
        st.metric("Overall Penetration", f"{avg_pen}%")
    with col4:
        st.metric("Counties Reached", f"{len(df[df['brand_stores'] > 0])}/{len(df)}")

    st.markdown("---")

    # Heat map visualization
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("County Penetration Heat Map")

        # Create treemap as heat map alternative
        fig = px.treemap(
            df,
            path=['county'],
            values='stores',
            color='penetration',
            color_continuous_scale=['#fee2e2', '#fecaca', '#fca5a5', '#f87171', '#ef4444', '#dc2626', '#b91c1c', '#991b1b', '#7f1d1d', '#450a0a'],
            title=f"{selected_brand} Store Coverage by County"
        )
        fig.update_layout(height=500)
        fig.update_coloraxes(colorbar_title="Penetration %")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Penetration by County")

        # Bar chart sorted by penetration
        df_sorted = df.sort_values('penetration', ascending=True)

        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            y=df_sorted['county'],
            x=df_sorted['penetration'],
            orientation='h',
            marker_color=df_sorted['penetration'],
            marker_colorscale='RdYlGn',
            text=[f"{p}%" for p in df_sorted['penetration']],
            textposition='outside'
        ))
        fig2.update_layout(
            height=500,
            xaxis_title="Penetration %",
            yaxis_title="",
            showlegend=False,
            xaxis=dict(range=[0, 100])
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Detailed table
    st.subheader("County Details")

    display_df = df.copy()
    display_df['penetration'] = display_df['penetration'].apply(lambda x: f"{x}%")
    display_df.columns = ['County', 'Total Stores', 'Brand Stores', 'Penetration']
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Gap analysis
    st.subheader("Coverage Gaps")
    gaps = df[df['penetration'] < 50].sort_values('stores', ascending=False)
    if len(gaps) > 0:
        st.warning(f"**{len(gaps)} counties** have less than 50% penetration")
        for _, row in gaps.iterrows():
            opportunity = row['stores'] - row['brand_stores']
            st.markdown(f"- **{row['county']}**: {row['brand_stores']}/{row['stores']} stores ({row['penetration']}%) - **{opportunity} store opportunity**")
    else:
        st.success("Strong coverage across all counties!")

else:
    # Real data mode
    if not state:
        st.warning("Please select a state to view brand coverage data")
        st.stop()

    @st.cache_data(ttl=300)
    def get_brands_for_state(state):
        """Get top brands in the state."""
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT r.raw_brand, COUNT(DISTINCT r.dispensary_id) as store_count
                FROM raw_menu_item r
                JOIN dispensary d ON r.dispensary_id = d.dispensary_id
                WHERE d.state = :state AND d.is_active = true
                AND r.raw_brand IS NOT NULL AND r.raw_brand != ''
                GROUP BY r.raw_brand
                HAVING COUNT(DISTINCT r.dispensary_id) >= 3
                ORDER BY store_count DESC
                LIMIT 100
            """), {"state": state})
            return [row[0] for row in result]

    @st.cache_data(ttl=300)
    def get_brand_county_data(state, brand):
        """Get brand penetration by county."""
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                WITH county_totals AS (
                    SELECT county, COUNT(DISTINCT dispensary_id) as total_stores
                    FROM dispensary
                    WHERE state = :state AND is_active = true AND county IS NOT NULL
                    GROUP BY county
                ),
                brand_presence AS (
                    SELECT d.county, COUNT(DISTINCT d.dispensary_id) as brand_stores
                    FROM dispensary d
                    JOIN raw_menu_item r ON d.dispensary_id = r.dispensary_id
                    WHERE d.state = :state AND d.is_active = true
                    AND LOWER(r.raw_brand) = LOWER(:brand)
                    AND d.county IS NOT NULL
                    GROUP BY d.county
                )
                SELECT
                    ct.county,
                    ct.total_stores as stores,
                    COALESCE(bp.brand_stores, 0) as brand_stores,
                    ROUND(COALESCE(bp.brand_stores, 0)::numeric / ct.total_stores * 100, 1) as penetration
                FROM county_totals ct
                LEFT JOIN brand_presence bp ON ct.county = bp.county
                WHERE ct.total_stores > 0
                ORDER BY ct.total_stores DESC
            """), {"state": state, "brand": brand})

            rows = result.fetchall()
            return pd.DataFrame(rows, columns=['county', 'stores', 'brand_stores', 'penetration'])

    @st.cache_data(ttl=300)
    def get_brand_store_details(state, brand):
        """Get list of stores carrying the brand."""
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT d.name, d.city, d.county, d.address
                FROM dispensary d
                JOIN raw_menu_item r ON d.dispensary_id = r.dispensary_id
                WHERE d.state = :state AND d.is_active = true
                AND LOWER(r.raw_brand) = LOWER(:brand)
                ORDER BY d.county, d.name
            """), {"state": state, "brand": brand})

            rows = result.fetchall()
            return pd.DataFrame(rows, columns=['Store', 'City', 'County', 'Address'])

    # Get brands
    brands = get_brands_for_state(state)

    if not brands:
        st.warning(f"No brand data available for {state}")
        st.stop()

    selected_brand = st.selectbox("Select Brand", brands)

    # Get county data
    df = get_brand_county_data(state, selected_brand)

    if df.empty:
        st.warning(f"No coverage data for {selected_brand}")
        st.stop()

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Stores in State", int(df['stores'].sum()))
    with col2:
        st.metric("Stores Carrying Brand", int(df['brand_stores'].sum()))
    with col3:
        total_stores = df['stores'].sum()
        brand_stores = df['brand_stores'].sum()
        avg_pen = round(brand_stores / total_stores * 100, 1) if total_stores > 0 else 0
        st.metric("Overall Penetration", f"{avg_pen}%")
    with col4:
        counties_reached = len(df[df['brand_stores'] > 0])
        st.metric("Counties Reached", f"{counties_reached}/{len(df)}")

    st.markdown("---")

    # Heat map visualization
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("County Penetration Heat Map")

        # Create treemap
        fig = px.treemap(
            df[df['stores'] > 0],
            path=['county'],
            values='stores',
            color='penetration',
            color_continuous_scale='RdYlGn',
            title=f"{selected_brand} Store Coverage by County in {state}"
        )
        fig.update_layout(height=500)
        fig.update_coloraxes(colorbar_title="Penetration %")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Penetration by County")

        # Bar chart sorted by penetration
        df_sorted = df.sort_values('penetration', ascending=True).tail(15)

        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            y=df_sorted['county'],
            x=df_sorted['penetration'],
            orientation='h',
            marker_color=df_sorted['penetration'],
            marker_colorscale='RdYlGn',
            text=[f"{p}%" for p in df_sorted['penetration']],
            textposition='outside'
        ))
        fig2.update_layout(
            height=500,
            xaxis_title="Penetration %",
            yaxis_title="",
            showlegend=False,
            xaxis=dict(range=[0, 105])
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Detailed table
    st.subheader("County Details")

    display_df = df.copy()
    display_df['penetration'] = display_df['penetration'].apply(lambda x: f"{x}%")
    display_df.columns = ['County', 'Total Stores', 'Brand Stores', 'Penetration']
    st.dataframe(display_df.sort_values('Total Stores', ascending=False), use_container_width=True, hide_index=True)

    # Gap analysis
    st.subheader("Coverage Gaps - Expansion Opportunities")
    gaps = df[df['penetration'] < 50].sort_values('stores', ascending=False)

    if len(gaps) > 0:
        total_opportunity = gaps['stores'].sum() - gaps['brand_stores'].sum()
        st.warning(f"**{len(gaps)} counties** have less than 50% penetration - **{int(total_opportunity)} store opportunities**")

        gap_cols = st.columns(2)
        for i, (_, row) in enumerate(gaps.head(10).iterrows()):
            opportunity = int(row['stores'] - row['brand_stores'])
            with gap_cols[i % 2]:
                st.markdown(f"**{row['county']}**")
                st.markdown(f"{int(row['brand_stores'])}/{int(row['stores'])} stores ({row['penetration']}%)")
                st.markdown(f"*{opportunity} store opportunity*")
                st.markdown("---")
    else:
        st.success("Strong coverage across all counties!")

    # Store list
    with st.expander("View Stores Carrying This Brand"):
        store_df = get_brand_store_details(state, selected_brand)
        st.dataframe(store_df, use_container_width=True, hide_index=True)
