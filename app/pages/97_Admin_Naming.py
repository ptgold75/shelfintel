# app/pages/97_Admin_Naming.py
"""Admin Naming Convention Tool - Track product name variations and verify normalization."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
from sqlalchemy import text
from core.db import get_engine
from core.category_utils import get_normalized_category_sql
from core.product_normalizer import (
    normalize_product, extract_base_name, extract_size,
    extract_form_factor, normalize_brand
)

st.set_page_config(page_title="Admin: Naming | CannLinx", page_icon=None, layout="wide", initial_sidebar_state="collapsed")

# Import and render navigation
from app.components.nav import render_nav
render_nav()

st.title("Naming Convention Verification")
st.markdown("Track product name variations across stores and verify normalization accuracy")

engine = get_engine()

@st.cache_data(ttl=300)
def get_name_variations():
    """Get products grouped by normalized base name to identify variations."""
    cat_sql = get_normalized_category_sql()

    with engine.connect() as conn:
        # Get all products with variations in naming
        df = pd.read_sql(text(f"""
            WITH base_names AS (
                SELECT
                    raw_brand,
                    raw_name,
                    raw_category,
                    raw_price,
                    {cat_sql} as norm_category,
                    d.name as store_name,
                    -- Simple base name extraction (remove size patterns)
                    REGEXP_REPLACE(
                        REGEXP_REPLACE(
                            REGEXP_REPLACE(raw_name, '\\s*[-|]\\s*\\d+\\.?\\d*\\s*(g|mg|gram)s?\\s*$', '', 'i'),
                            '\\s*\\[\\d+\\.?\\d*\\s*(g|mg)\\]', '', 'i'
                        ),
                        '\\s*\\d+\\.?\\d*\\s*(g|mg|gram)s?\\s*$', '', 'i'
                    ) as base_name_sql
                FROM raw_menu_item r
                JOIN dispensary d ON r.dispensary_id = d.dispensary_id
                WHERE raw_name IS NOT NULL
            )
            SELECT
                raw_brand as brand,
                base_name_sql as base_name,
                norm_category as category,
                COUNT(*) as variation_count,
                COUNT(DISTINCT raw_name) as unique_names,
                COUNT(DISTINCT store_name) as store_count,
                STRING_AGG(DISTINCT raw_name, ' | ' ORDER BY raw_name) as all_names,
                AVG(raw_price) as avg_price
            FROM base_names
            WHERE raw_brand IS NOT NULL AND raw_brand != ''
            AND LENGTH(base_name_sql) > 3
            GROUP BY raw_brand, base_name_sql, norm_category
            HAVING COUNT(DISTINCT raw_name) > 1
            ORDER BY COUNT(DISTINCT raw_name) DESC
            LIMIT 500
        """), conn)

        return df

@st.cache_data(ttl=300)
def get_brand_name_variations(brand: str):
    """Get all product name variations for a specific brand."""
    with engine.connect() as conn:
        df = pd.read_sql(text("""
            SELECT
                r.raw_name,
                r.raw_category,
                r.raw_price,
                d.name as store_name,
                COUNT(*) as occurrences
            FROM raw_menu_item r
            JOIN dispensary d ON r.dispensary_id = d.dispensary_id
            WHERE r.raw_brand = :brand
            GROUP BY r.raw_name, r.raw_category, r.raw_price, d.name
            ORDER BY r.raw_name
        """), conn, params={'brand': brand})
        return df

@st.cache_data(ttl=300)
def search_products(query: str):
    """Search for products matching a query."""
    with engine.connect() as conn:
        df = pd.read_sql(text("""
            SELECT
                r.raw_brand as brand,
                r.raw_name as name,
                r.raw_category as category,
                r.raw_price as price,
                d.name as store,
                COUNT(*) OVER (PARTITION BY r.raw_name, r.raw_brand) as stores_with_product
            FROM raw_menu_item r
            JOIN dispensary d ON r.dispensary_id = d.dispensary_id
            WHERE LOWER(r.raw_name) LIKE LOWER(:query)
               OR LOWER(r.raw_brand) LIKE LOWER(:query)
            ORDER BY r.raw_brand, r.raw_name
            LIMIT 500
        """), conn, params={'query': f'%{query}%'})
        return df

@st.cache_data(ttl=300)
def get_normalization_sample():
    """Get sample of products with their normalized forms for verification."""
    cat_sql = get_normalized_category_sql()

    with engine.connect() as conn:
        df = pd.read_sql(text(f"""
            SELECT DISTINCT
                r.raw_brand as brand,
                r.raw_name as original_name,
                r.raw_category as category,
                {cat_sql} as norm_category,
                r.raw_price as price,
                d.name as store
            FROM raw_menu_item r
            JOIN dispensary d ON r.dispensary_id = d.dispensary_id
            WHERE r.raw_brand IS NOT NULL AND r.raw_brand != ''
            ORDER BY r.raw_brand, r.raw_name
            LIMIT 1000
        """), conn)
        return df

# Tabs for different views
tab1, tab2, tab3, tab4 = st.tabs([
    "Name Variations",
    "Brand Explorer",
    "Product Search",
    "Normalization Preview"
])

with tab1:
    st.subheader("Product Name Variations")
    st.markdown("Products with multiple name variations that may need normalization review")

    variations_df = get_name_variations()

    if not variations_df.empty:
        # Summary metrics
        c1, c2, c3 = st.columns(3)
        c1.metric("Product Groups with Variations", len(variations_df))
        c2.metric("Total Unique Names", variations_df['unique_names'].sum())
        c3.metric("Avg Names per Product", f"{variations_df['unique_names'].mean():.1f}")

        # Filter controls
        col1, col2 = st.columns(2)
        with col1:
            min_variations = st.slider("Min Variations", 2, 10, 2)
        with col2:
            category_filter = st.selectbox(
                "Category Filter",
                ["All"] + sorted(variations_df['category'].dropna().unique().tolist())
            )

        # Apply filters
        filtered = variations_df[variations_df['unique_names'] >= min_variations]
        if category_filter != "All":
            filtered = filtered[filtered['category'] == category_filter]

        # Display table with expandable details
        for _, row in filtered.head(50).iterrows():
            with st.expander(f"**{row['brand']}** - {row['base_name']} ({row['unique_names']} variations)"):
                st.markdown(f"**Category:** {row['category']}")
                st.markdown(f"**Found in:** {row['store_count']} stores")
                st.markdown(f"**Avg Price:** ${row['avg_price']:.2f}" if row['avg_price'] else "")
                st.markdown("**Name Variations:**")
                names = row['all_names'].split(' | ')
                for name in names[:20]:
                    # Apply normalization to show results
                    normalized = normalize_product(name, row['brand'], row['category'])
                    st.markdown(f"- `{name}`")
                    st.caption(f"  → Base: {normalized.base_name} | Size: {normalized.size_display} | Form: {normalized.form_factor}")
    else:
        st.info("No name variations found")

with tab2:
    st.subheader("Brand Explorer")
    st.markdown("View all products for a specific brand")

    # Get brand list
    with engine.connect() as conn:
        brands = pd.read_sql(text("""
            SELECT DISTINCT raw_brand as brand, COUNT(*) as products
            FROM raw_menu_item
            WHERE raw_brand IS NOT NULL AND raw_brand != ''
            AND raw_brand NOT IN ('ADD TO CART', 'SALE', 'None', 'null')
            GROUP BY raw_brand
            HAVING COUNT(*) > 10
            ORDER BY COUNT(*) DESC
        """), conn)

    if not brands.empty:
        brand_options = brands['brand'].tolist()
        selected_brand = st.selectbox("Select Brand", brand_options)

        if selected_brand:
            brand_products = get_brand_name_variations(selected_brand)

            if not brand_products.empty:
                st.markdown(f"**{len(brand_products)} product variations found for {selected_brand}**")

                # Group by normalized base name
                st.markdown("### Grouped by Base Product")

                # Apply normalization to each product
                for _, row in brand_products.iterrows():
                    normalized = normalize_product(row['raw_name'], selected_brand, row['raw_category'])
                    brand_products.loc[_, 'base_name'] = normalized.base_name
                    brand_products.loc[_, 'size'] = normalized.size_display
                    brand_products.loc[_, 'form'] = normalized.form_factor

                # Group view
                grouped = brand_products.groupby(['base_name', 'raw_category']).agg({
                    'raw_name': 'count',
                    'size': lambda x: ', '.join(x.unique()),
                    'form': 'first',
                    'store_name': lambda x: len(x.unique())
                }).reset_index()
                grouped.columns = ['Base Name', 'Category', 'Variations', 'Sizes Available', 'Form', 'Stores']

                st.dataframe(grouped.sort_values('Variations', ascending=False), use_container_width=True, hide_index=True)

                # Detail view
                st.markdown("### All Products")
                display_df = brand_products[['raw_name', 'raw_category', 'raw_price', 'store_name', 'base_name', 'size', 'form']]
                display_df.columns = ['Original Name', 'Category', 'Price', 'Store', 'Base Name', 'Size', 'Form']
                st.dataframe(display_df, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Product Search")
    st.markdown("Search for specific products across all stores")

    search_query = st.text_input("Search by product name or brand", placeholder="e.g., Blue Dream")

    if search_query and len(search_query) >= 3:
        results = search_products(search_query)

        if not results.empty:
            st.markdown(f"**Found {len(results)} results**")

            # Apply normalization
            for idx, row in results.iterrows():
                normalized = normalize_product(row['name'], row['brand'], row['category'])
                results.loc[idx, 'base_name'] = normalized.base_name
                results.loc[idx, 'size'] = normalized.size_display
                results.loc[idx, 'form'] = normalized.form_factor
                results.loc[idx, 'norm_key'] = normalized.normalized_key

            # Summary by normalized key
            st.markdown("### Grouped by Normalized Product")
            summary = results.groupby(['norm_key']).agg({
                'name': 'first',
                'brand': 'first',
                'category': 'first',
                'base_name': 'first',
                'size': 'first',
                'form': 'first',
                'price': ['mean', 'min', 'max'],
                'store': 'nunique'
            }).reset_index()
            summary.columns = ['Key', 'Sample Name', 'Brand', 'Category', 'Base Name', 'Size', 'Form', 'Avg Price', 'Min Price', 'Max Price', 'Stores']
            st.dataframe(summary, use_container_width=True, hide_index=True)

            # Full results
            st.markdown("### All Results")
            st.dataframe(results[['brand', 'name', 'category', 'price', 'store', 'base_name', 'size', 'form']],
                        use_container_width=True, hide_index=True)
        else:
            st.info("No results found")
    elif search_query:
        st.caption("Enter at least 3 characters to search")

with tab4:
    st.subheader("Normalization Preview")
    st.markdown("Preview how products are normalized by our system")

    # Manual test input
    st.markdown("### Test Normalization")
    col1, col2, col3 = st.columns(3)
    with col1:
        test_name = st.text_input("Product Name", "Pineapple Express 3.5g")
    with col2:
        test_brand = st.text_input("Brand", "Curio")
    with col3:
        test_category = st.text_input("Category", "Flower")

    if test_name:
        result = normalize_product(test_name, test_brand, test_category)
        st.markdown("**Normalization Result:**")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Base Name", result.base_name)
        col2.metric("Size", result.size_display)
        col3.metric("Form Factor", result.form_factor)
        col4.metric("Pack Count", result.pack_count)

        st.code(f"Normalized Key: {result.normalized_key}")

    st.divider()

    # Sample from database
    st.markdown("### Sample Products with Normalization")
    sample_df = get_normalization_sample()

    if not sample_df.empty:
        # Apply normalization
        preview_data = []
        for _, row in sample_df.head(100).iterrows():
            normalized = normalize_product(row['original_name'], row['brand'], row['category'])
            preview_data.append({
                'Brand': row['brand'],
                'Original Name': row['original_name'],
                'Category': row['category'],
                'Base Name': normalized.base_name,
                'Size': normalized.size_display,
                'Form': normalized.form_factor,
                'Key': normalized.normalized_key[:60] + '...' if len(normalized.normalized_key) > 60 else normalized.normalized_key
            })

        preview_df = pd.DataFrame(preview_data)
        st.dataframe(preview_df, use_container_width=True, hide_index=True, height=500)

st.divider()
st.caption("Naming Convention Tool | Use this to verify product grouping accuracy")
