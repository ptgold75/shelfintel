# app/pages/6_Competitor_Compare.py
"""Competitor Comparison Tool - Compare your store to nearby competitors."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
import plotly.express as px
import json
from sqlalchemy import text
from core.db import get_engine

st.set_page_config(page_title="Competitor Compare | CannLinx", page_icon=None, layout="wide", initial_sidebar_state="collapsed")

# Import and render navigation
from app.components.nav import render_nav
render_nav()

st.title("Competitor Comparison")
st.markdown("Compare your inventory and pricing against nearby competitors")

engine = get_engine()

@st.cache_data(ttl=300)
def get_stores_with_data():
    """Get stores that have scraped menu data."""
    with engine.connect() as conn:
        df = pd.read_sql(text("""
            SELECT DISTINCT d.dispensary_id, d.name, d.state, d.provider_metadata,
                   COUNT(DISTINCT r.raw_name) as product_count
            FROM dispensary d
            JOIN raw_menu_item r ON d.dispensary_id = r.dispensary_id
            GROUP BY d.dispensary_id, d.name, d.state, d.provider_metadata
            HAVING COUNT(DISTINCT r.raw_name) > 0
            ORDER BY d.name
        """), conn)
    return df

@st.cache_data(ttl=300)
def get_store_products(dispensary_id):
    """Get all products for a store from most recent scrape."""
    with engine.connect() as conn:
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
        """), conn, params={"disp_id": dispensary_id})
    return df

@st.cache_data(ttl=300)
def get_all_stores():
    """Get all stores with county info."""
    with engine.connect() as conn:
        df = pd.read_sql(text("""
            SELECT dispensary_id, name, state, provider_metadata
            FROM dispensary
            ORDER BY name
        """), conn)
    # Extract county from provider_metadata
    def get_county(meta):
        if meta:
            try:
                data = json.loads(meta) if isinstance(meta, str) else meta
                return data.get('county', 'Unknown')
            except:
                pass
        return 'Unknown'
    df['county'] = df['provider_metadata'].apply(get_county)
    return df

# Load stores
stores_df = get_stores_with_data()
all_stores_df = get_all_stores()

if stores_df.empty:
    st.warning("No stores with menu data available yet. Run scrapes first.")
    st.stop()

# Inline store selection
store_options = stores_df['name'].tolist()
col1, col2 = st.columns([2, 2])
with col1:
    selected_store = st.selectbox("Your Dispensary", ["Select a store..."] + store_options)

if selected_store == "Select a store...":
    st.info("Select your dispensary above to compare against competitors.")

    # Show available stores
    st.subheader("Stores with Menu Data")
    display_df = stores_df[['name', 'product_count']].rename(columns={
        'name': 'Store', 'product_count': 'Products'
    })
    st.dataframe(display_df, use_container_width=True, height=400)
    st.stop()

# Get selected store info
store_row = stores_df[stores_df['name'] == selected_store].iloc[0]
store_id = store_row['dispensary_id']
store_products = get_store_products(store_id)

# Get county for the selected store
store_info = all_stores_df[all_stores_df['dispensary_id'] == store_id].iloc[0]
store_county = store_info['county']

# Show store info inline
with col2:
    st.markdown(f"**County:** {store_county} | **Products:** {len(store_products):,}")

# Competitor selection - inline
st.divider()
comp_col1, comp_col2 = st.columns([1, 3])
with comp_col1:
    filter_method = st.radio("Find competitors by:", ["Same County", "All Stores"], horizontal=True)

# Get competitor options based on filter
if filter_method == "Same County":
    competitor_options = all_stores_df[
        (all_stores_df['county'] == store_county) &
        (all_stores_df['name'] != selected_store)
    ]['name'].tolist()
else:
    competitor_options = all_stores_df[all_stores_df['name'] != selected_store]['name'].tolist()

# Only show stores that have data
stores_with_data = set(stores_df['name'].tolist())
competitor_options = [c for c in competitor_options if c in stores_with_data]

with comp_col2:
    selected_competitors = st.multiselect(
        "Select competitors to compare",
        competitor_options,
        default=competitor_options[:3] if len(competitor_options) >= 3 else competitor_options
    )

if not selected_competitors:
    st.info("Select at least one competitor above to compare.")
    st.stop()

# Load competitor data
competitor_data = {}
for comp_name in selected_competitors:
    comp_row = all_stores_df[all_stores_df['name'] == comp_name].iloc[0]
    comp_id = comp_row['dispensary_id']
    comp_products = get_store_products(comp_id)
    if not comp_products.empty:
        competitor_data[comp_name] = comp_products

if not competitor_data:
    st.warning("Selected competitors have no menu data available.")
    st.stop()

# Main comparison view
st.subheader(f"Comparing: {selected_store}")
st.markdown(f"vs. {len(competitor_data)} competitor(s): {', '.join(competitor_data.keys())}")

# Tabs for different views
tab1, tab2, tab3 = st.tabs(["Price Comparison", "Missing Products", "Category Mix"])

with tab1:
    st.markdown("### Price Differences")
    st.markdown("Products you both carry - sorted by largest price difference")

    # Find matching products and compare prices
    your_products = store_products[['product', 'brand', 'category', 'price']].copy()
    your_products = your_products.rename(columns={'price': 'your_price'})

    all_comparisons = []

    for comp_name, comp_df in competitor_data.items():
        comp_products = comp_df[['product', 'price']].copy()
        comp_products = comp_products.rename(columns={'price': f'{comp_name[:15]}_price'})

        # Merge on product name
        merged = your_products.merge(comp_products, on='product', how='inner')
        if not merged.empty:
            merged['competitor'] = comp_name
            merged['comp_price'] = merged[f'{comp_name[:15]}_price']
            merged['price_diff'] = merged['your_price'] - merged['comp_price']
            merged['price_diff_pct'] = ((merged['your_price'] - merged['comp_price']) / merged['comp_price'] * 100).round(1)
            all_comparisons.append(merged[['product', 'brand', 'category', 'your_price', 'competitor', 'comp_price', 'price_diff', 'price_diff_pct']])

    if all_comparisons:
        comparison_df = pd.concat(all_comparisons, ignore_index=True)
        comparison_df = comparison_df.dropna(subset=['your_price', 'comp_price'])
        comparison_df = comparison_df[(comparison_df['your_price'] > 0) & (comparison_df['comp_price'] > 0)]

        if not comparison_df.empty:
            # Summary metrics
            c1, c2, c3 = st.columns(3)
            avg_diff = comparison_df['price_diff'].mean()
            higher_count = (comparison_df['price_diff'] > 0).sum()
            lower_count = (comparison_df['price_diff'] < 0).sum()

            c1.metric("Avg Price Difference", f"${avg_diff:+.2f}")
            c2.metric("You're Higher", f"{higher_count} products")
            c3.metric("You're Lower", f"{lower_count} products")

            st.markdown("---")

            # Show biggest differences (where you're higher)
            st.markdown("**Products where you're priced higher:**")
            higher_priced = comparison_df[comparison_df['price_diff'] > 2].sort_values('price_diff', ascending=False).head(10)
            if not higher_priced.empty:
                display_higher = higher_priced[['product', 'category', 'your_price', 'competitor', 'comp_price', 'price_diff']].copy()
                display_higher['your_price'] = display_higher['your_price'].apply(lambda x: f"${x:.2f}")
                display_higher['comp_price'] = display_higher['comp_price'].apply(lambda x: f"${x:.2f}")
                display_higher['price_diff'] = display_higher['price_diff'].apply(lambda x: f"+${x:.2f}")
                st.dataframe(display_higher, use_container_width=True, hide_index=True)
            else:
                st.success("No significant price gaps where you're higher!")

            st.markdown("**Products where you're priced lower:**")
            lower_priced = comparison_df[comparison_df['price_diff'] < -2].sort_values('price_diff').head(10)
            if not lower_priced.empty:
                display_lower = lower_priced[['product', 'category', 'your_price', 'competitor', 'comp_price', 'price_diff']].copy()
                display_lower['your_price'] = display_lower['your_price'].apply(lambda x: f"${x:.2f}")
                display_lower['comp_price'] = display_lower['comp_price'].apply(lambda x: f"${x:.2f}")
                display_lower['price_diff'] = display_lower['price_diff'].apply(lambda x: f"${x:.2f}")
                st.dataframe(display_lower, use_container_width=True, hide_index=True)
            else:
                st.info("No significant price advantages found.")
        else:
            st.info("No matching products with valid prices found.")
    else:
        st.info("No matching products found between stores.")

with tab2:
    st.markdown("### Products Competitors Carry That You Don't")
    st.markdown("Potential gaps in your inventory")

    your_product_set = set(store_products['product'].str.lower().str.strip())

    missing_products = []
    for comp_name, comp_df in competitor_data.items():
        for _, row in comp_df.iterrows():
            prod_lower = str(row['product']).lower().strip()
            if prod_lower not in your_product_set:
                missing_products.append({
                    'product': row['product'],
                    'brand': row['brand'],
                    'category': row['category'],
                    'price': row['price'],
                    'carried_by': comp_name
                })

    if missing_products:
        missing_df = pd.DataFrame(missing_products)

        # Count how many competitors carry each product
        product_counts = missing_df.groupby('product').agg({
            'brand': 'first',
            'category': 'first',
            'price': 'mean',
            'carried_by': lambda x: ', '.join(x.unique())
        }).reset_index()
        product_counts['competitors'] = product_counts['carried_by'].str.count(',') + 1
        product_counts = product_counts.sort_values('competitors', ascending=False)

        # Summary
        c1, c2 = st.columns(2)
        c1.metric("Products You're Missing", f"{len(product_counts):,}")
        c2.metric("Carried by Multiple Competitors", f"{(product_counts['competitors'] > 1).sum()}")

        # Filter by category
        categories = ['All'] + sorted(product_counts['category'].dropna().unique().tolist())
        selected_cat = st.selectbox("Filter by category", categories)

        if selected_cat != 'All':
            product_counts = product_counts[product_counts['category'] == selected_cat]

        # Show top missing products
        st.markdown("**Top Missing Products** (carried by most competitors)")
        display_missing = product_counts.head(20)[['product', 'brand', 'category', 'price', 'competitors', 'carried_by']].copy()
        display_missing['price'] = display_missing['price'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "")
        st.dataframe(display_missing, use_container_width=True, hide_index=True)
    else:
        st.success("You carry all products that your competitors have!")

with tab3:
    st.markdown("### Category Mix Comparison")

    # Your category breakdown
    your_categories = store_products.groupby('category').size().reset_index(name='count')
    your_categories['store'] = selected_store

    # Competitor category breakdowns
    all_cat_data = [your_categories]
    for comp_name, comp_df in competitor_data.items():
        comp_categories = comp_df.groupby('category').size().reset_index(name='count')
        comp_categories['store'] = comp_name
        all_cat_data.append(comp_categories)

    combined_cats = pd.concat(all_cat_data, ignore_index=True)

    if not combined_cats.empty:
        fig = px.bar(combined_cats, x='category', y='count', color='store',
                    barmode='group', title='Product Count by Category')
        fig.update_layout(xaxis_tickangle=-45, height=400)
        st.plotly_chart(fig, use_container_width=True)

        # Category percentages
        st.markdown("**Category Distribution (%)**")
        pivot_df = combined_cats.pivot(index='category', columns='store', values='count').fillna(0)
        for col in pivot_df.columns:
            pivot_df[col] = (pivot_df[col] / pivot_df[col].sum() * 100).round(1)
        st.dataframe(pivot_df, use_container_width=True)

st.divider()
st.caption("Comparison based on most recent menu data | Update frequency: daily")
