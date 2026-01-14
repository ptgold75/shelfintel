# app/pages/9_Product_Search.py
"""Product Search - Find products across all stores."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import text
from core.db import get_engine
from core.category_utils import get_normalized_category_sql

st.set_page_config(page_title="Product Search | CannaLinx", page_icon=None, layout="wide", initial_sidebar_state="expanded")

# Import and render navigation
from components.sidebar_nav import render_nav, get_section_from_params, render_state_filter, get_selected_state
render_nav()

# Handle section parameter for tab navigation
section = get_section_from_params()
TAB_MAP = {"prices": 0, "compare": 1}
if section and section in TAB_MAP:
    tab_index = TAB_MAP[section]
    st.markdown(f"""
    <script>
        setTimeout(function() {{
            const tabs = document.querySelectorAll('[data-baseweb="tab"]');
            if (tabs && tabs[{tab_index}]) {{ tabs[{tab_index}].click(); }}
        }}, 100);
    </script>
    """, unsafe_allow_html=True)

st.title("Product Search")

# State filter
selected_state = render_state_filter()
st.markdown(f"Find any product across all {selected_state} dispensaries")

engine = get_engine()

@st.cache_data(ttl=300)
def get_categories(state: str = "MD"):
    """Get normalized categories for filtering."""
    cat_sql = get_normalized_category_sql()
    with engine.connect() as conn:
        df = pd.read_sql(text(f"""
            SELECT DISTINCT {cat_sql} as category
            FROM raw_menu_item r
            JOIN dispensary d ON r.dispensary_id = d.dispensary_id
            WHERE r.raw_category IS NOT NULL AND d.state = :state
            ORDER BY category
        """), conn, params={"state": state})
    return ['All Categories'] + df['category'].tolist()

@st.cache_data(ttl=300)
def get_brands(state: str = "MD"):
    with engine.connect() as conn:
        df = pd.read_sql(text("""
            SELECT DISTINCT r.raw_brand as brand
            FROM raw_menu_item r
            JOIN dispensary d ON r.dispensary_id = d.dispensary_id
            WHERE r.raw_brand IS NOT NULL AND r.raw_brand != '' AND d.state = :state
            ORDER BY r.raw_brand
        """), conn, params={"state": state})
    return ['All Brands'] + df['brand'].tolist()

@st.cache_data(ttl=60)
def search_products(search_term, category, brand, min_price, max_price, state: str = "MD", limit=100):
    cat_sql = get_normalized_category_sql()
    with engine.connect() as conn:
        conditions = ["r.raw_price BETWEEN :min_price AND :max_price", "d.state = :state"]
        params = {"min_price": min_price, "max_price": max_price, "state": state, "lim": limit}

        if search_term:
            conditions.append("r.raw_name ILIKE :search")
            params["search"] = f"%{search_term}%"

        if category != 'All Categories':
            # Filter by normalized category
            conditions.append(f"({cat_sql}) = :category")
            params["category"] = category

        if brand != 'All Brands':
            conditions.append("r.raw_brand = :brand")
            params["brand"] = brand

        where_clause = " AND ".join(conditions)

        df = pd.read_sql(text(f"""
            SELECT r.raw_name as product, r.raw_brand as brand, {cat_sql} as category,
                   r.raw_price as price, r.raw_discount_price as sale_price,
                   d.name as store,
                   COALESCE(d.county, 'Unknown') as county
            FROM raw_menu_item r
            JOIN dispensary d ON d.dispensary_id = r.dispensary_id
            WHERE {where_clause}
            ORDER BY r.raw_price ASC
            LIMIT :lim
        """), conn, params=params)

    return df

# Search form
col1, col2 = st.columns([3, 1])
with col1:
    search_term = st.text_input("Search for a product", placeholder="e.g., Blue Dream, Pax Pod, 1g cart...")
with col2:
    search_button = st.button("Search", type="primary", use_container_width=True)

# Filters
filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
with filter_col1:
    categories = get_categories(selected_state)
    selected_category = st.selectbox("Category", categories)
with filter_col2:
    brands = get_brands(selected_state)
    selected_brand = st.selectbox("Brand", brands)
with filter_col3:
    min_price = st.number_input("Min Price", 0, 500, 0)
with filter_col4:
    max_price = st.number_input("Max Price", 0, 500, 200)

st.divider()

# Search results
if search_button or search_term:
    with st.spinner("Searching..."):
        results = search_products(search_term, selected_category, selected_brand, min_price, max_price, selected_state)

    if not results.empty:
        # Summary metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Results Found", len(results))
        c2.metric("Stores", results['store'].nunique())
        c3.metric("Price Range", f"${results['price'].min():.2f} - ${results['price'].max():.2f}")
        c4.metric("Avg Price", f"${results['price'].mean():.2f}")

        # Results tabs
        tab1, tab2 = st.tabs(["Price List", "Store Comparison"])

        with tab1:
            # Format display
            display_df = results.copy()
            display_df['price'] = display_df['price'].apply(lambda x: f"${x:.2f}")
            if 'sale_price' in display_df.columns:
                display_df['sale_price'] = display_df['sale_price'].apply(
                    lambda x: f"${x:.2f}" if pd.notna(x) else ""
                )

            st.dataframe(display_df, use_container_width=True, height=500, hide_index=True)

        with tab2:
            # Price comparison across stores
            if results['store'].nunique() > 1:
                store_prices = results.groupby('store').agg({
                    'price': ['min', 'mean', 'max', 'count']
                }).round(2)
                store_prices.columns = ['Min Price', 'Avg Price', 'Max Price', 'Products']
                store_prices = store_prices.sort_values('Avg Price')

                fig = px.bar(
                    store_prices.reset_index(),
                    x='store',
                    y='Avg Price',
                    color='Avg Price',
                    color_continuous_scale='RdYlGn_r',
                    hover_data=['Min Price', 'Max Price', 'Products']
                )
                fig.update_layout(height=400, xaxis_tickangle=-45, showlegend=False, coloraxis_showscale=False)
                st.plotly_chart(fig, use_container_width=True)

                st.dataframe(store_prices, use_container_width=True)
            else:
                st.info(f"Found only in: {results['store'].iloc[0]}")

            # County breakdown
            st.subheader("Availability by County")
            county_counts = results.groupby('county').size().reset_index(name='products')
            county_counts = county_counts.sort_values('products', ascending=False)

            fig2 = px.pie(county_counts, values='products', names='county', hole=0.4)
            fig2.update_layout(height=300)
            st.plotly_chart(fig2, use_container_width=True)

    else:
        st.warning("No products found matching your search criteria.")
        st.info("Try:\n- Using fewer words\n- Checking spelling\n- Removing filters")
else:
    # Show popular categories when no search
    st.subheader("Browse by Category")

    cat_sql = get_normalized_category_sql()
    with engine.connect() as conn:
        cat_counts = pd.read_sql(text(f"""
            SELECT {cat_sql} as category, COUNT(*) as products,
                   COUNT(DISTINCT r.dispensary_id) as stores
            FROM raw_menu_item r
            JOIN dispensary d ON r.dispensary_id = d.dispensary_id
            WHERE r.raw_category IS NOT NULL AND d.state = :state
            GROUP BY {cat_sql}
            ORDER BY products DESC
            LIMIT 10
        """), conn, params={"state": selected_state})

    if not cat_counts.empty:
        fig = px.bar(
            cat_counts,
            x='category',
            y='products',
            color='stores',
            labels={'products': 'Products', 'stores': 'Stores'},
            color_continuous_scale='Viridis'
        )
        fig.update_layout(height=350, xaxis_tickangle=-45, coloraxis_colorbar_title='Stores')
        st.plotly_chart(fig, use_container_width=True)

    # Popular brands
    st.subheader("Top Brands")
    with engine.connect() as conn:
        brand_counts = pd.read_sql(text("""
            SELECT r.raw_brand as brand, COUNT(*) as products,
                   COUNT(DISTINCT r.dispensary_id) as stores
            FROM raw_menu_item r
            JOIN dispensary d ON r.dispensary_id = d.dispensary_id
            WHERE r.raw_brand IS NOT NULL AND r.raw_brand != '' AND d.state = :state
            GROUP BY r.raw_brand
            ORDER BY stores DESC, products DESC
            LIMIT 15
        """), conn, params={"state": selected_state})

    if not brand_counts.empty:
        fig2 = px.bar(
            brand_counts,
            x='products',
            y='brand',
            orientation='h',
            color='stores',
            labels={'products': 'Products', 'brand': 'Brand', 'stores': 'Stores'},
            color_continuous_scale='Viridis'
        )
        fig2.update_layout(height=450, yaxis={'categoryorder': 'total ascending'}, coloraxis_colorbar_title='Stores')
        st.plotly_chart(fig2, use_container_width=True)

st.divider()
st.caption(f"Search across all tracked {selected_state} dispensary menus")
