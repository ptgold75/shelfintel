# app/pages/98_Product_Dedup.py
"""Product Deduplication Tool - Identify and analyze potential duplicate products."""

import streamlit as st
import pandas as pd
import re
from sqlalchemy import text
from components.sidebar_nav import render_nav
from core.db import get_engine

st.set_page_config(page_title="Product Deduplication - ShelfIntel", layout="wide")
render_nav()

st.title("Product Deduplication Tool")
st.caption("Identify products with same brand, category, and size but different naming conventions")


def extract_base_name(name: str) -> str:
    """Extract base product name by removing size patterns and common suffixes."""
    if not name:
        return ""

    # Work with a copy
    base = name.strip()

    # Remove common size patterns
    patterns = [
        r'\s*-?\s*\d+(\.\d+)?\s*oz\.?$',           # 1oz, 1.0 oz
        r'\s*-?\s*\d+(\.\d+)?\s*g\b',              # 1g, 3.5g
        r'\s*-?\s*\d+(\.\d+)?\s*mg\b',             # 100mg
        r'\s*-?\s*\d+(\.\d+)?\s*gram(s)?',         # 1 gram
        r'\s*-?\s*\d+/\d+\s*oz',                   # 1/8oz, 1/4oz
        r'\s*-?\s*(1/8|1/4|1/2|eighth|quarter|half)\s*(oz|ounce)?',
        r'\s*\(\d+(\.\d+)?\s*g\)',                 # (3.5g)
        r'\s*\[\d+(\.\d+)?\s*g\]',                 # [3.5g]
        r'\s*-?\s*\d+\s*pack',                     # 5 pack
        r'\s*-?\s*\d+pk\b',                        # 5pk
        r'\s*-?\s*\d+\s*ct\b',                     # 10ct
        r'\s*-?\s*pre.?packaged\s*\(\d+g?\)',      # Pre Packaged (28g)
        r'\s*-?\s*baby\s*buds.*$',                 # Baby Buds - 1/2oz
        r'\s*-?\s*smalls?\b',                      # Smalls
        r'\s*-?\s*popcorn\b',                      # Popcorn
        r'\s*-?\s*(indica|sativa|hybrid)\s*$',     # Indica/Sativa/Hybrid at end
    ]

    for pattern in patterns:
        base = re.sub(pattern, '', base, flags=re.IGNORECASE)

    # Clean up leftover punctuation
    base = re.sub(r'\s*-\s*$', '', base)  # Trailing dash
    base = re.sub(r'\s+', ' ', base)       # Multiple spaces

    return base.strip()


def extract_size(name: str) -> str:
    """Extract size info from product name."""
    if not name:
        return ""

    # Look for common size patterns
    patterns = [
        (r'(\d+(\.\d+)?)\s*oz', 'oz'),
        (r'(\d+(\.\d+)?)\s*g\b', 'g'),
        (r'(\d+(\.\d+)?)\s*mg\b', 'mg'),
        (r'(\d+(\.\d+)?)\s*gram', 'g'),
        (r'1/8\s*oz', '3.5g'),
        (r'eighth', '3.5g'),
        (r'1/4\s*oz', '7g'),
        (r'quarter', '7g'),
        (r'1/2\s*oz', '14g'),
        (r'half\s*oz', '14g'),
        (r'(\d+)\s*pack', 'pack'),
        (r'(\d+)pk\b', 'pack'),
    ]

    for pattern, unit in patterns:
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            if unit in ['oz', 'g', 'mg', 'pack']:
                return f"{match.group(1)}{unit}"
            else:
                return unit

    return ""


def normalize_for_matching(name: str, brand: str = "") -> str:
    """Create a normalized key for matching similar products."""
    if not name:
        return ""

    # Get base name
    base = extract_base_name(name)

    # Lowercase
    base = base.lower()

    # Remove brand name from the product name (if present)
    if brand:
        brand_lower = brand.lower()
        # Try various brand formats
        for variant in [brand_lower, brand_lower.replace(' ', ''), brand_lower.replace('-', ' ')]:
            base = base.replace(variant, '')

    # Remove common prefixes like "Exclusive", "Wellness", "Everyday"
    base = re.sub(r'\b(exclusive|wellness|everyday)\b', '', base, flags=re.IGNORECASE)

    # Remove common suffixes
    base = re.sub(r'\b(pre-?packed|pre-?packaged)\b', '', base, flags=re.IGNORECASE)

    # Remove special characters but keep alphanumeric
    base = re.sub(r'[^\w\s]', ' ', base)

    # Collapse whitespace
    base = re.sub(r'\s+', ' ', base).strip()

    # If the result is too short or generic, return empty (don't match)
    if len(base) < 3 or base in ['', 'flower', 'pre', 'pack', 'packaged']:
        return ""

    return base


@st.cache_data(ttl=300)
def load_product_data():
    """Load all products with their dispensary info."""
    engine = get_engine()
    query = """
        SELECT
            r.raw_menu_item_id,
            r.raw_name,
            r.raw_brand,
            r.raw_category,
            r.raw_price,
            d.name as store_name,
            d.county
        FROM raw_menu_item r
        JOIN dispensary d ON r.dispensary_id = d.dispensary_id
        WHERE r.raw_brand IS NOT NULL
          AND r.raw_brand != ''
          AND r.raw_name IS NOT NULL
    """
    df = pd.read_sql(query, engine)

    # Add normalized columns
    df['base_name'] = df['raw_name'].apply(extract_base_name)
    df['size'] = df['raw_name'].apply(extract_size)
    df['match_key'] = df.apply(lambda row: normalize_for_matching(row['raw_name'], row['raw_brand']), axis=1)

    return df


def find_duplicates(df, brand_filter=None, category_filter=None, min_variations=2):
    """Find potential duplicate products.

    Only groups products with the SAME size as potential duplicates.
    Different sizes = different SKUs, not duplicates.
    """
    filtered = df.copy()

    if brand_filter and brand_filter != "All":
        filtered = filtered[filtered['raw_brand'].str.upper() == brand_filter.upper()]

    if category_filter and category_filter != "All":
        filtered = filtered[filtered['raw_category'].str.lower() == category_filter.lower()]

    # Group by brand + match_key + size to find similar products with SAME size
    # Different sizes are NOT duplicates
    groups = filtered.groupby(['raw_brand', 'match_key', 'size']).agg({
        'raw_name': lambda x: list(set(x)),
        'raw_price': lambda x: list(set(x.dropna())),
        'store_name': lambda x: list(set(x)),
        'raw_menu_item_id': 'count',
        'raw_category': 'first'
    }).reset_index()

    groups.columns = ['brand', 'match_key', 'size', 'name_variations', 'prices', 'stores', 'count', 'category']

    # Filter by minimum variations
    groups['variation_count'] = groups['name_variations'].apply(len)
    groups = groups[groups['variation_count'] >= min_variations]

    # Sort by variation count descending
    groups = groups.sort_values('variation_count', ascending=False)

    return groups


# Load data
with st.spinner("Loading product data..."):
    df = load_product_data()

# Filters
col1, col2, col3 = st.columns(3)

with col1:
    brands = ["All"] + sorted(df['raw_brand'].dropna().unique().tolist())
    brand_filter = st.selectbox("Filter by Brand", brands, index=0)

with col2:
    categories = ["All"] + sorted(df['raw_category'].dropna().unique().tolist())
    category_filter = st.selectbox("Filter by Category", categories, index=0)

with col3:
    min_variations = st.slider("Minimum Name Variations", 2, 10, 2)

# Find duplicates
duplicates = find_duplicates(df, brand_filter, category_filter, min_variations)

st.markdown("---")

if len(duplicates) == 0:
    st.info("No potential duplicates found with current filters.")
else:
    st.subheader(f"Found {len(duplicates)} Product Groups with Multiple Names")

    # Summary stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Product Groups", len(duplicates))
    with col2:
        total_variations = duplicates['variation_count'].sum()
        st.metric("Total Name Variations", total_variations)
    with col3:
        avg_variations = duplicates['variation_count'].mean()
        st.metric("Avg Variations per Group", f"{avg_variations:.1f}")

    st.markdown("---")

    # Display each group
    for idx, row in duplicates.head(50).iterrows():
        size_label = row['size'] if row['size'] else "no size"
        with st.expander(f"**{row['brand']}** - {row['match_key'][:40]} ({size_label}) - {row['variation_count']} names", expanded=False):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown("**Name Variations (same product, same size):**")
                for name in sorted(row['name_variations']):
                    st.markdown(f"- {name}")

            with col2:
                st.markdown(f"**Category:** {row['category']}")
                st.markdown(f"**Size:** {row['size'] or 'Not detected'}")

                prices = [p for p in row['prices'] if p and p > 0]
                if prices:
                    st.markdown(f"**Price Range:** ${min(prices):.2f} - ${max(prices):.2f}")

                st.markdown(f"**Stores:** {len(row['stores'])}")
                st.markdown(f"**Total SKUs:** {row['count']}")

    if len(duplicates) > 50:
        st.info(f"Showing first 50 of {len(duplicates)} groups. Apply filters to narrow results.")

# Detailed view tab
st.markdown("---")
st.subheader("Detailed Product View")

# Let user select a specific brand to see all products
if brand_filter and brand_filter != "All":
    brand_products = df[df['raw_brand'].str.upper() == brand_filter.upper()].copy()

    # Group by base_name
    product_summary = brand_products.groupby('base_name').agg({
        'raw_name': lambda x: list(set(x)),
        'raw_price': ['min', 'max', 'mean'],
        'store_name': lambda x: len(set(x)),
        'raw_category': 'first'
    }).reset_index()

    product_summary.columns = ['Base Name', 'All Names', 'Min Price', 'Max Price', 'Avg Price', 'Store Count', 'Category']
    product_summary['Variation Count'] = product_summary['All Names'].apply(len)
    product_summary = product_summary.sort_values('Variation Count', ascending=False)

    st.dataframe(
        product_summary[['Base Name', 'Category', 'Variation Count', 'Store Count', 'Min Price', 'Max Price']],
        use_container_width=True,
        height=400
    )

    # Show raw names for selected product
    if st.checkbox("Show all name variations for selected brand"):
        for _, row in product_summary.head(20).iterrows():
            if row['Variation Count'] > 1:
                with st.expander(f"{row['Base Name']} ({row['Variation Count']} names)"):
                    for name in sorted(row['All Names']):
                        st.text(name)
