# app/pages/15_Market_Share.py
"""Market Share Estimation - Brand revenue estimates based on state sales data."""

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

st.set_page_config(page_title="Market Share | CannLinx", page_icon=None, layout="wide", initial_sidebar_state="collapsed")

# Import and render navigation
from app.components.nav import render_nav
render_nav()

st.title("Market Share Estimation")
st.markdown("Estimated brand revenue based on Maryland state sales data and dispensary presence")

engine = get_engine()

# Maryland state sales data (November 2025)
# Source: Maryland Cannabis Administration / Marijuana Herald
STATE_SALES_DATA = {
    "total_monthly": 98_000_000,  # $98M total monthly sales
    "by_category": {
        "Flower": 54_000_000,      # $54M (55%)
        "Vapes": 18_000_000,       # ~$18M (includes cartridges/pens)
        "Concentrates": 13_000_000, # ~$13M (non-vape concentrates)
        "Edibles": 12_000_000,     # $12M (12%)
        "Pre-Rolls": 6_000_000,    # ~$6M
        "Tinctures": 2_000_000,    # ~$2M
        "Topicals": 1_500_000,     # ~$1.5M
        "Other": 1_500_000,        # ~$1.5M
    },
    "year_to_date": 1_071_000_000,  # $1.071B YTD 2025
    "data_month": "November 2025",
    "source": "Maryland Cannabis Administration"
}

@st.cache_data(ttl=300)
def get_brand_market_data():
    """Calculate brand market share based on store presence and category."""
    cat_sql = get_normalized_category_sql()

    with engine.connect() as conn:
        # Get total store count
        total_stores = conn.execute(text("""
            SELECT COUNT(DISTINCT dispensary_id)
            FROM raw_menu_item
        """)).scalar() or 1

        # Brand presence by category with store counts
        brand_data = pd.read_sql(text(f"""
            SELECT
                raw_brand as brand,
                {cat_sql} as category,
                COUNT(DISTINCT r.dispensary_id) as store_count,
                COUNT(DISTINCT raw_name) as sku_count,
                AVG(raw_price) as avg_price
            FROM raw_menu_item r
            WHERE raw_brand IS NOT NULL AND raw_brand != ''
            AND raw_category IS NOT NULL
            GROUP BY raw_brand, {cat_sql}
            HAVING COUNT(DISTINCT r.dispensary_id) >= 1
        """), conn)

        # Total SKUs per category (for market share calculation)
        category_totals = pd.read_sql(text(f"""
            SELECT
                {cat_sql} as category,
                COUNT(DISTINCT raw_brand) as brand_count,
                COUNT(DISTINCT raw_name) as total_skus,
                SUM(CASE WHEN raw_brand IS NOT NULL THEN 1 ELSE 0 END) as branded_items
            FROM raw_menu_item
            WHERE raw_category IS NOT NULL
            GROUP BY {cat_sql}
        """), conn)

        return brand_data, category_totals, total_stores

@st.cache_data(ttl=300)
def calculate_market_share(brand_data, category_totals, total_stores):
    """
    Calculate estimated market share using weighted factors:
    1. Store penetration (what % of stores carry this brand)
    2. SKU share (what % of category SKUs does brand have)
    3. Weighted by category sales
    """
    results = []

    for _, row in brand_data.iterrows():
        brand = row['brand']
        category = row['category']
        store_count = row['store_count']
        sku_count = row['sku_count']

        # Get category total
        cat_total = category_totals[category_totals['category'] == category]
        if cat_total.empty:
            continue

        total_skus = cat_total['total_skus'].values[0]

        # Calculate penetration score (0-1)
        store_penetration = store_count / total_stores

        # Calculate SKU share (0-1)
        sku_share = sku_count / total_skus if total_skus > 0 else 0

        # Combined market share estimate (weighted)
        # Store penetration is more important than SKU count
        estimated_share = (store_penetration * 0.6) + (sku_share * 0.4)

        # Get category sales from state data
        category_sales = STATE_SALES_DATA["by_category"].get(category, 0)

        # Estimate brand revenue in this category
        estimated_revenue = category_sales * estimated_share

        results.append({
            'brand': brand,
            'category': category,
            'store_count': store_count,
            'sku_count': sku_count,
            'store_penetration': store_penetration,
            'sku_share': sku_share,
            'market_share_pct': estimated_share * 100,
            'category_sales': category_sales,
            'estimated_revenue': estimated_revenue,
            'avg_price': row['avg_price']
        })

    return pd.DataFrame(results)

try:
    brand_data, category_totals, total_stores = get_brand_market_data()
    market_share_df = calculate_market_share(brand_data, category_totals, total_stores)

    # Key metrics row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("State Monthly Sales", f"${STATE_SALES_DATA['total_monthly']/1_000_000:.0f}M")
    c2.metric("YTD 2025 Sales", f"${STATE_SALES_DATA['year_to_date']/1_000_000_000:.2f}B")
    c3.metric("Stores Tracked", f"{total_stores}")
    c4.metric("Data Month", STATE_SALES_DATA['data_month'])

    st.divider()

    # Category sales breakdown
    st.subheader("State Sales by Category")

    cat_sales = pd.DataFrame([
        {"Category": k, "Sales ($M)": v/1_000_000}
        for k, v in STATE_SALES_DATA["by_category"].items()
    ]).sort_values("Sales ($M)", ascending=False)

    col1, col2 = st.columns([2, 1])

    with col1:
        fig = px.bar(
            cat_sales,
            x='Category',
            y='Sales ($M)',
            color='Sales ($M)',
            color_continuous_scale='Greens'
        )
        fig.update_layout(height=350, showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.dataframe(
            cat_sales.style.format({"Sales ($M)": "${:.1f}M"}),
            use_container_width=True,
            hide_index=True
        )

    st.divider()

    # Brand market share tabs
    tab1, tab2, tab3 = st.tabs(["Top Brands by Revenue", "Category Leaders", "Brand Deep Dive"])

    with tab1:
        st.subheader("Estimated Brand Revenue (Monthly)")
        st.caption("Based on store penetration and SKU presence weighted against state category sales")

        # Aggregate by brand across all categories
        brand_totals = market_share_df.groupby('brand').agg({
            'estimated_revenue': 'sum',
            'store_count': 'max',
            'sku_count': 'sum',
            'category': 'count'
        }).reset_index()
        brand_totals.columns = ['brand', 'estimated_revenue', 'max_stores', 'total_skus', 'categories']
        brand_totals = brand_totals.sort_values('estimated_revenue', ascending=False)

        # Top 25 brands
        top_brands = brand_totals.head(25)

        fig = px.bar(
            top_brands,
            x='estimated_revenue',
            y='brand',
            orientation='h',
            color='max_stores',
            color_continuous_scale='Blues',
            labels={'estimated_revenue': 'Estimated Monthly Revenue ($)', 'brand': 'Brand', 'max_stores': 'Stores'}
        )
        fig.update_layout(
            height=700,
            yaxis={'categoryorder': 'total ascending'},
            xaxis_tickformat='$,.0f'
        )
        st.plotly_chart(fig, use_container_width=True)

        # Revenue table
        display_df = top_brands.copy()
        display_df['estimated_revenue'] = display_df['estimated_revenue'].apply(lambda x: f"${x:,.0f}")
        display_df.columns = ['Brand', 'Est. Monthly Revenue', 'Store Reach', 'Total SKUs', 'Categories']
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Top Brands by Category")

        # Category selector
        categories = sorted(market_share_df['category'].dropna().unique().tolist())
        selected_cat = st.selectbox("Select Category", categories, index=0 if 'Flower' not in categories else categories.index('Flower'))

        cat_data = market_share_df[market_share_df['category'] == selected_cat].sort_values('estimated_revenue', ascending=False)

        if not cat_data.empty:
            col1, col2, col3 = st.columns(3)
            col1.metric(f"{selected_cat} State Sales", f"${STATE_SALES_DATA['by_category'].get(selected_cat, 0)/1_000_000:.1f}M")
            col2.metric("Brands in Category", f"{len(cat_data)}")
            col3.metric("Top Brand Revenue", f"${cat_data.iloc[0]['estimated_revenue']:,.0f}")

            # Top 15 in category
            top_in_cat = cat_data.head(15)

            fig = px.bar(
                top_in_cat,
                x='brand',
                y='estimated_revenue',
                color='store_count',
                color_continuous_scale='Viridis',
                labels={'estimated_revenue': 'Est. Revenue ($)', 'brand': 'Brand', 'store_count': 'Stores'}
            )
            fig.update_layout(
                height=400,
                xaxis_tickangle=-45,
                yaxis_tickformat='$,.0f'
            )
            st.plotly_chart(fig, use_container_width=True)

            # Market share pie
            fig2 = px.pie(
                top_in_cat.head(10),
                values='market_share_pct',
                names='brand',
                title=f"Top 10 {selected_cat} Market Share"
            )
            fig2.update_layout(height=400)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info(f"No data available for {selected_cat}")

    with tab3:
        st.subheader("Brand Deep Dive")

        # Brand selector
        all_brands = sorted(market_share_df['brand'].unique().tolist())
        selected_brand = st.selectbox("Select Brand", all_brands)

        brand_detail = market_share_df[market_share_df['brand'] == selected_brand]

        if not brand_detail.empty:
            total_rev = brand_detail['estimated_revenue'].sum()
            total_stores = brand_detail['store_count'].max()
            total_skus = brand_detail['sku_count'].sum()

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Est. Monthly Revenue", f"${total_rev:,.0f}")
            col2.metric("Store Reach", f"{total_stores}")
            col3.metric("Total SKUs", f"{total_skus}")
            col4.metric("Categories", f"{len(brand_detail)}")

            # Revenue by category
            fig = px.pie(
                brand_detail,
                values='estimated_revenue',
                names='category',
                title=f"{selected_brand} Revenue by Category"
            )
            st.plotly_chart(fig, use_container_width=True)

            # Detail table
            detail_display = brand_detail[['category', 'store_count', 'sku_count', 'market_share_pct', 'estimated_revenue']].copy()
            detail_display['market_share_pct'] = detail_display['market_share_pct'].apply(lambda x: f"{x:.1f}%")
            detail_display['estimated_revenue'] = detail_display['estimated_revenue'].apply(lambda x: f"${x:,.0f}")
            detail_display.columns = ['Category', 'Stores', 'SKUs', 'Category Share', 'Est. Revenue']
            st.dataframe(detail_display, use_container_width=True, hide_index=True)
        else:
            st.info(f"No data available for {selected_brand}")

except Exception as e:
    st.error(f"Error loading market share data: {e}")
    import traceback
    st.code(traceback.format_exc())

st.divider()

# Methodology note
with st.expander("Methodology"):
    st.markdown("""
    ### Market Share Estimation Model

    This model estimates brand revenue using publicly available state sales data combined with
    dispensary menu intelligence:

    **Data Sources:**
    - State-level category sales from Maryland Cannabis Administration
    - Brand presence across tracked dispensaries
    - SKU counts by brand and category

    **Calculation:**
    1. **Store Penetration (60% weight):** What percentage of dispensaries carry this brand
    2. **SKU Share (40% weight):** What percentage of category SKUs belong to this brand
    3. **Revenue Estimate:** Category sales × Combined market share score

    **Limitations:**
    - Actual sales velocity varies by product and location
    - Premium brands may have higher revenue per SKU
    - Not all dispensaries are tracked
    - Estimates are directional, not precise

    **Updates:** Data refreshes every 5 minutes based on menu scrapes
    """)

st.caption(f"State sales data: {STATE_SALES_DATA['source']} ({STATE_SALES_DATA['data_month']}) | Brand data from {total_stores} tracked dispensaries")
