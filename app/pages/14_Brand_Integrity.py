# app/pages/14_Brand_Integrity.py
"""Brand Integrity - Product image quality audit for manufacturers."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
import json
from sqlalchemy import text
from core.db import get_engine
from core.category_utils import get_normalized_category_sql

st.set_page_config(page_title="Brand Integrity | CannLinx", page_icon=None, layout="wide", initial_sidebar_state="expanded")

# Import and render navigation
from components.sidebar_nav import render_nav
render_nav()

st.title("Brand Integrity Audit")
st.markdown("Review product images across dispensaries to ensure brand consistency and quality")

engine = get_engine()

@st.cache_data(ttl=300)
def get_brands():
    """Get all brands with product counts."""
    with engine.connect() as conn:
        df = pd.read_sql(text("""
            SELECT raw_brand as brand, COUNT(DISTINCT raw_name) as products,
                   COUNT(DISTINCT sr.dispensary_id) as stores
            FROM raw_menu_item r
            JOIN scrape_run sr ON r.scrape_run_id = sr.scrape_run_id
            WHERE r.raw_brand IS NOT NULL AND r.raw_brand != ''
            AND sr.status = 'success'
            AND sr.started_at > NOW() - INTERVAL '7 days'
            GROUP BY raw_brand
            HAVING COUNT(*) > 5
            ORDER BY COUNT(*) DESC
        """), conn)
    return df

@st.cache_data(ttl=300)
def get_brand_products(brand, category=None):
    """Get products for a brand."""
    cat_sql = get_normalized_category_sql()
    with engine.connect() as conn:
        cat_filter = f"AND ({cat_sql}) = :cat" if category and category != "All Categories" else ""
        params = {"brand": brand}
        if category and category != "All Categories":
            params["cat"] = category

        df = pd.read_sql(text(f"""
            SELECT DISTINCT raw_name as product, {cat_sql} as category
            FROM raw_menu_item r
            JOIN scrape_run sr ON r.scrape_run_id = sr.scrape_run_id
            WHERE r.raw_brand = :brand
            AND sr.status = 'success'
            AND sr.started_at > NOW() - INTERVAL '7 days'
            {cat_filter}
            ORDER BY raw_name
        """), conn, params=params)
    return df

@st.cache_data(ttl=300)
def get_brand_categories(brand):
    """Get categories for a brand."""
    cat_sql = get_normalized_category_sql()
    with engine.connect() as conn:
        df = pd.read_sql(text(f"""
            SELECT DISTINCT {cat_sql} as category
            FROM raw_menu_item r
            JOIN scrape_run sr ON r.scrape_run_id = sr.scrape_run_id
            WHERE r.raw_brand = :brand
            AND sr.status = 'success'
            ORDER BY category
        """), conn, params={"brand": brand})
    return df

@st.cache_data(ttl=300)
def get_product_images(brand, product_name):
    """Get all images for a product across dispensaries."""
    with engine.connect() as conn:
        df = pd.read_sql(text("""
            SELECT d.name as dispensary, r.raw_json, r.raw_price as price
            FROM raw_menu_item r
            JOIN scrape_run sr ON r.scrape_run_id = sr.scrape_run_id
            JOIN dispensary d ON sr.dispensary_id = d.dispensary_id
            WHERE r.raw_brand = :brand
            AND r.raw_name = :product
            AND sr.status = 'success'
            AND sr.started_at > NOW() - INTERVAL '7 days'
            ORDER BY d.name
        """), conn, params={"brand": brand, "product": product_name})

    # Extract images from raw_json
    results = []
    for _, row in df.iterrows():
        images = []
        if row['raw_json']:
            try:
                data = json.loads(row['raw_json']) if isinstance(row['raw_json'], str) else row['raw_json']
                # Try different image field names
                if 'images' in data and data['images']:
                    images = data['images'] if isinstance(data['images'], list) else [data['images']]
                elif 'Image' in data and data['Image']:
                    images = [data['Image']]
                elif 'image' in data and data['image']:
                    images = [data['image']]
                elif 'photoUrl' in data and data['photoUrl']:
                    images = [data['photoUrl']]
            except:
                pass

        results.append({
            'dispensary': row['dispensary'],
            'price': row['price'],
            'images': images
        })

    return results

# Sidebar: Brand Selection
brands_df = get_brands()

if brands_df.empty:
    st.warning("No brand data available. Run scrapes first.")
    st.stop()

st.sidebar.header("Select Brand")
brand_options = brands_df['brand'].tolist()
selected_brand = st.sidebar.selectbox(
    "Brand",
    brand_options,
    index=0 if brand_options else None
)

if not selected_brand:
    st.info("Select a brand from the sidebar to begin.")
    st.stop()

# Brand info
brand_info = brands_df[brands_df['brand'] == selected_brand].iloc[0]
st.markdown(f"### {selected_brand}")
col1, col2 = st.columns(2)
col1.metric("Products", brand_info['products'])
col2.metric("Stores Carrying", brand_info['stores'])

st.divider()

# Category filter
categories_df = get_brand_categories(selected_brand)
category_options = ["All Categories"] + categories_df['category'].dropna().tolist()
selected_category = st.selectbox("Filter by Category", category_options)

# Product selector
products_df = get_brand_products(selected_brand, selected_category)

if products_df.empty:
    st.info("No products found for this brand/category combination.")
    st.stop()

# Product search/filter
search_term = st.text_input("Search products", placeholder="Type to filter...")
if search_term:
    products_df = products_df[products_df['product'].str.contains(search_term, case=False, na=False)]

st.markdown(f"**{len(products_df)} products found**")

# Product selector
product_options = products_df['product'].tolist()
selected_product = st.selectbox("Select SKU to audit", product_options)

if not selected_product:
    st.stop()

st.divider()

# Display images for selected product
st.subheader(f"Image Audit: {selected_product}")

product_images = get_product_images(selected_brand, selected_product)

if not product_images:
    st.warning("No image data found for this product.")
    st.stop()

# Count dispensaries with/without images
with_images = sum(1 for p in product_images if p['images'])
without_images = len(product_images) - with_images

col1, col2, col3 = st.columns(3)
col1.metric("Dispensaries Carrying", len(product_images))
col2.metric("With Product Images", with_images)
col3.metric("Missing Images", without_images, delta=f"-{without_images}" if without_images > 0 else None, delta_color="inverse")

st.markdown("---")

# Display images in grid (6 wide)
st.markdown("**Product Images by Dispensary:**")

# Filter options
show_missing = st.checkbox("Show dispensaries without images", value=True)

# Create grid
cols_per_row = 6
image_items = []

for item in product_images:
    if item['images']:
        for img in item['images'][:1]:  # Just first image
            image_items.append({
                'dispensary': item['dispensary'],
                'image': img,
                'price': item['price'],
                'has_image': True
            })
    elif show_missing:
        image_items.append({
            'dispensary': item['dispensary'],
            'image': None,
            'price': item['price'],
            'has_image': False
        })

if not image_items:
    st.info("No images to display.")
    st.stop()

# Display in grid
for i in range(0, len(image_items), cols_per_row):
    cols = st.columns(cols_per_row)
    for j, col in enumerate(cols):
        idx = i + j
        if idx < len(image_items):
            item = image_items[idx]
            with col:
                st.caption(f"**{item['dispensary'][:20]}**")
                if item['has_image']:
                    try:
                        st.image(item['image'], width="stretch")
                    except:
                        st.markdown("*Image load error*")
                else:
                    st.markdown("""
                    <div style="
                        background: #f8d7da;
                        border: 2px dashed #dc3545;
                        border-radius: 8px;
                        padding: 40px 10px;
                        text-align: center;
                        color: #721c24;
                        font-size: 0.8rem;
                    ">No Image</div>
                    """, unsafe_allow_html=True)
                if item['price']:
                    st.caption(f"${item['price']:.2f}")

st.divider()

# Summary table
st.subheader("Detailed Listing")
summary_data = []
for item in product_images:
    summary_data.append({
        'Dispensary': item['dispensary'],
        'Has Image': 'Yes' if item['images'] else 'No',
        'Price': f"${item['price']:.2f}" if item['price'] else '',
        'Image URL': item['images'][0][:50] + '...' if item['images'] else ''
    })

summary_df = pd.DataFrame(summary_data)
st.dataframe(summary_df, width="stretch", height=300)

st.divider()

# Value proposition
st.markdown("""
### Why Brand Integrity Matters

As a manufacturer, ensuring consistent product presentation across all retail partners is crucial for:

- **Brand Recognition** - Customers should see the same professional images everywhere
- **Quality Perception** - Poor images can hurt perceived product quality
- **Compliance** - Ensure retailers are using approved marketing materials
- **Sales Performance** - Products with quality images typically sell better

**This tool helps you:**
1. Identify dispensaries using low-quality or incorrect product images
2. Track which retailers are missing product images entirely
3. Audit pricing consistency across your distribution network
4. Provide data for conversations with retail partners about brand standards
""")

st.caption("Images sourced from dispensary menu systems | Data refreshes daily")
