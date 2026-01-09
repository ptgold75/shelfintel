# app/pages/8_County_Insights.py
"""County Insights - Regional market analysis for Maryland."""

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

st.set_page_config(page_title="County Insights | CannLinx", page_icon=None, layout="wide", initial_sidebar_state="expanded")

# Import and render navigation
from components.sidebar_nav import render_nav
render_nav()

st.title("County Insights")
st.markdown("Regional market analysis across Maryland counties")

engine = get_engine()

@st.cache_data(ttl=300)
def get_county_data():
    """Get comprehensive county analytics."""
    with engine.connect() as conn:
        # Stores and products by county
        county_summary = pd.read_sql(text("""
            SELECT
                COALESCE(d.provider_metadata::json->>'county', 'Unknown') as county,
                COUNT(DISTINCT d.dispensary_id) as store_count,
                COUNT(DISTINCT r.raw_name) as unique_products,
                COUNT(DISTINCT r.raw_brand) as brand_count,
                ROUND(AVG(r.raw_price)::numeric, 2) as avg_price
            FROM dispensary d
            JOIN raw_menu_item r ON d.dispensary_id = r.dispensary_id
            WHERE r.raw_price > 0 AND r.raw_price < 500
            GROUP BY d.provider_metadata::json->>'county'
            ORDER BY store_count DESC
        """), conn)

        # Category distribution by county (normalized)
        cat_sql = get_normalized_category_sql()
        county_categories = pd.read_sql(text(f"""
            SELECT
                COALESCE(d.provider_metadata::json->>'county', 'Unknown') as county,
                {cat_sql} as category,
                COUNT(*) as products
            FROM dispensary d
            JOIN raw_menu_item r ON d.dispensary_id = r.dispensary_id
            WHERE r.raw_category IS NOT NULL
            GROUP BY d.provider_metadata::json->>'county', {cat_sql}
        """), conn)

        # Top brands by county
        county_brands = pd.read_sql(text("""
            SELECT
                COALESCE(d.provider_metadata::json->>'county', 'Unknown') as county,
                r.raw_brand as brand,
                COUNT(*) as products
            FROM dispensary d
            JOIN raw_menu_item r ON d.dispensary_id = r.dispensary_id
            WHERE r.raw_brand IS NOT NULL AND r.raw_brand != ''
            GROUP BY d.provider_metadata::json->>'county', r.raw_brand
            ORDER BY products DESC
        """), conn)

        # Stores by county
        stores_by_county = pd.read_sql(text("""
            SELECT
                COALESCE(d.provider_metadata::json->>'county', 'Unknown') as county,
                d.name as store,
                COUNT(DISTINCT r.raw_name) as products
            FROM dispensary d
            JOIN raw_menu_item r ON d.dispensary_id = r.dispensary_id
            GROUP BY d.provider_metadata::json->>'county', d.name
            ORDER BY products DESC
        """), conn)

    return county_summary, county_categories, county_brands, stores_by_county

try:
    county_summary, county_categories, county_brands, stores_by_county = get_county_data()

    if county_summary.empty:
        st.warning("No county data available yet.")
        st.stop()

    # Key metrics
    total_counties = len(county_summary)
    total_stores = county_summary['store_count'].sum()
    avg_stores_per_county = county_summary['store_count'].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Counties with Data", total_counties)
    c2.metric("Total Stores", total_stores)
    c3.metric("Avg Stores/County", f"{avg_stores_per_county:.1f}")
    c4.metric("Avg Price (all)", f"${county_summary['avg_price'].mean():.2f}")

    st.divider()

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["Market Overview", "Category Distribution", "Store Details"])

    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Stores by County")
            fig = px.bar(
                county_summary.sort_values('store_count', ascending=True),
                x='store_count',
                y='county',
                orientation='h',
                color='unique_products',
                color_continuous_scale='Viridis',
                labels={'store_count': 'Number of Stores', 'county': 'County', 'unique_products': 'Products'}
            )
            fig.update_layout(height=400, coloraxis_colorbar_title='Products')
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Average Price by County")
            fig2 = px.bar(
                county_summary.sort_values('avg_price', ascending=False),
                x='county',
                y='avg_price',
                color='avg_price',
                color_continuous_scale='RdYlGn_r',
                labels={'avg_price': 'Avg Price ($)', 'county': 'County'}
            )
            fig2.update_layout(height=400, xaxis_tickangle=-45, showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig2, use_container_width=True)

        # Brand diversity
        st.subheader("Brand Diversity by County")
        fig3 = px.scatter(
            county_summary,
            x='store_count',
            y='brand_count',
            size='unique_products',
            color='avg_price',
            hover_name='county',
            labels={'store_count': 'Stores', 'brand_count': 'Unique Brands', 'unique_products': 'Products'},
            color_continuous_scale='Viridis'
        )
        fig3.update_layout(height=400)
        st.plotly_chart(fig3, use_container_width=True)
        st.caption("Bubble size = number of products | Color = average price")

        # Summary table
        st.subheader("County Summary Table")
        display_df = county_summary.copy()
        display_df['avg_price'] = display_df['avg_price'].apply(lambda x: f"${x:.2f}")
        display_df.columns = ['County', 'Stores', 'Products', 'Brands', 'Avg Price']
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Category Mix by County")

        if not county_categories.empty:
            # County selector
            counties = county_summary['county'].tolist()
            selected_counties = st.multiselect("Select counties to compare", counties, default=counties[:5])

            if selected_counties:
                filtered = county_categories[county_categories['county'].isin(selected_counties)]

                # Stacked bar chart
                fig = px.bar(
                    filtered,
                    x='county',
                    y='products',
                    color='category',
                    barmode='stack',
                    labels={'products': 'Product Count', 'county': 'County'}
                )
                fig.update_layout(height=500, xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)

                # Percentage breakdown
                st.subheader("Category Percentage by County")
                pivot = filtered.pivot_table(index='county', columns='category', values='products', fill_value=0)
                pivot_pct = pivot.div(pivot.sum(axis=1), axis=0) * 100
                pivot_pct = pivot_pct.round(1)
                st.dataframe(pivot_pct, use_container_width=True)
        else:
            st.info("No category data available")

    with tab3:
        st.subheader("Stores by County")

        if not stores_by_county.empty:
            # County filter
            county_filter = st.selectbox("Filter by county", ['All'] + county_summary['county'].tolist())

            if county_filter == 'All':
                filtered_stores = stores_by_county
            else:
                filtered_stores = stores_by_county[stores_by_county['county'] == county_filter]

            # Bar chart of stores
            fig = px.bar(
                filtered_stores.head(20),
                x='products',
                y='store',
                orientation='h',
                color='county',
                labels={'products': 'Products', 'store': 'Store'}
            )
            fig.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig, use_container_width=True)

            # Top brands in selected county
            if county_filter != 'All':
                st.subheader(f"Top Brands in {county_filter}")
                county_top_brands = county_brands[county_brands['county'] == county_filter].head(15)
                if not county_top_brands.empty:
                    fig2 = px.bar(
                        county_top_brands,
                        x='products',
                        y='brand',
                        orientation='h',
                        labels={'products': 'Products', 'brand': 'Brand'}
                    )
                    fig2.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No store data available")

except Exception as e:
    st.error(f"Error loading county insights: {e}")

st.divider()
st.caption("Regional data aggregated from all tracked dispensary menus")
