# app/pages/99_Naming_Review.py
"""Naming Review Tool - Identify and standardize product naming conventions."""

import streamlit as st
import pandas as pd
import re
from collections import defaultdict
from sqlalchemy import create_engine, text
from components.nav import render_nav

st.set_page_config(page_title="Naming Review - ShelfIntel", layout="wide")
render_nav()

st.title("Product Naming Review")
st.caption("Identify products with inconsistent naming and standardize to canonical names")


@st.cache_resource
def get_engine():
    return create_engine(st.secrets["DATABASE_URL"])


def clean_name_for_grouping(name: str, brand: str = None) -> str:
    """Clean product name for grouping similar products."""
    if not name:
        return ''
    n = name.lower()

    # Remove brand from beginning
    if brand:
        brand_lower = brand.lower()
        if n.startswith(brand_lower):
            n = n[len(brand_lower):].strip()
        for var in [brand_lower.replace(' ', ''), brand_lower.replace("'", "")]:
            if n.startswith(var):
                n = n[len(var):].strip()

    # Remove common prefixes
    n = re.sub(r'^[\s\-|:]+', '', n)

    # Remove size patterns
    n = re.sub(r'\s*[-|]?\s*\d+\.?\d*\s*(g|mg|oz|gram)s?\b', '', n)
    n = re.sub(r'\s*\[\d+\.?\d*\s*(g|mg)\]', '', n)
    n = re.sub(r'\s*\(\d+\.?\d*\s*(g|mg)?\)', '', n)
    n = re.sub(r'\s*\d+\s*(pk|pack|ct)\b', '', n)
    n = re.sub(r'\s*(1/8|1/4|1/2|eighth|quarter|half)\s*(oz)?\b', '', n)

    # Remove common modifiers
    n = re.sub(r'\s*(pre-?packaged?|baby\s*buds?|smalls?|popcorn|premium)\b', '', n, flags=re.IGNORECASE)
    n = re.sub(r'\s*(indica|sativa|hybrid)\s*$', '', n, flags=re.IGNORECASE)
    n = re.sub(r'\s*-\s*(rec|med|medical|recreational)\s*$', '', n, flags=re.IGNORECASE)

    # Clean up
    n = re.sub(r'[^\w\s]', ' ', n)
    n = re.sub(r'\s+', ' ', n).strip()

    return n


def extract_size_from_name(name: str) -> str:
    """Extract size info from product name."""
    if not name:
        return ""

    # Check for gram patterns
    match = re.search(r'(\d+\.?\d*)\s*g\b', name, re.IGNORECASE)
    if match:
        return f"{match.group(1)}g"

    # Check for mg patterns
    match = re.search(r'(\d+)\s*mg\b', name, re.IGNORECASE)
    if match:
        return f"{match.group(1)}mg"

    # Check for fractions
    if re.search(r'1/8|eighth', name, re.IGNORECASE):
        return "3.5g"
    if re.search(r'1/4|quarter', name, re.IGNORECASE):
        return "7g"
    if re.search(r'1/2|half', name, re.IGNORECASE):
        return "14g"

    # Check for pack
    match = re.search(r'(\d+)\s*(pk|pack|ct)', name, re.IGNORECASE)
    if match:
        return f"{match.group(1)}pk"

    return ""


def suggest_canonical_name(variations: list, brand: str) -> str:
    """Suggest the best canonical name from variations."""
    if not variations:
        return ""

    # Score each variation
    scored = []
    for name in variations:
        score = 0
        name_lower = name.lower()

        # Prefer shorter names (usually cleaner)
        score -= len(name) * 0.1

        # Prefer names without brand prefix (brand is separate field)
        if brand.lower() not in name_lower[:len(brand)+5]:
            score += 10

        # Prefer proper case (not ALL CAPS)
        if name != name.upper():
            score += 5

        # Prefer names without size info (size should be separate)
        if not re.search(r'\d+\.?\d*\s*(g|mg|oz)\b', name, re.IGNORECASE):
            score += 5

        # Prefer names without modifiers like "Pre-Packaged"
        if 'packaged' not in name_lower and 'popcorn' not in name_lower and 'smalls' not in name_lower:
            score += 3

        # Prefer title case
        if name == name.title() or (name[0].isupper() and name[1:] != name[1:].upper()):
            score += 2

        scored.append((name, score))

    # Return highest scored
    scored.sort(key=lambda x: -x[1])
    return scored[0][0]


def save_canonical_name(brand: str, match_key: str, canonical_name: str):
    """Save an approved canonical name to the database."""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO canonical_name (brand, match_key, canonical_name)
            VALUES (:brand, :match_key, :canonical_name)
            ON CONFLICT (brand, match_key) DO UPDATE SET
                canonical_name = EXCLUDED.canonical_name,
                created_at = NOW()
        """), {"brand": brand, "match_key": match_key, "canonical_name": canonical_name})
        conn.commit()


def get_saved_canonicals():
    """Get all saved canonical names."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT brand, match_key, canonical_name
            FROM canonical_name
        """))
        return {(row[0], row[1]): row[2] for row in result}


def get_naming_variations(category_filter: str = None, brand_filter: str = None, min_variations: int = 2):
    """Get products with naming variations (grouped by brand + name + SIZE)."""
    engine = get_engine()

    # Build category filter
    cat_clause = ""
    if category_filter and category_filter != "All":
        cat_map = {
            "Flower": "('flower', 'buds', 'indica', 'sativa', 'hybrid')",
            "Pre-Rolls": "('pre-roll', 'pre-rolls', 'preroll', 'prerolls', 'joint', 'blunt', 'infused pre-roll')",
            "Vapes": "('vape', 'vapes', 'vaporizer', 'vaporizers', 'cartridge', 'cart', 'disposable')",
            "Concentrates": "('concentrate', 'concentrates', 'wax', 'shatter', 'live resin', 'rosin', 'badder')",
            "Edibles": "('edible', 'edibles', 'gummies', 'chocolate', 'candy')",
        }
        if category_filter in cat_map:
            cat_clause = f"AND LOWER(raw_category) IN {cat_map[category_filter]}"

    brand_clause = ""
    if brand_filter and brand_filter != "All":
        brand_clause = f"AND UPPER(raw_brand) = '{brand_filter.upper()}'"

    query = f"""
        SELECT raw_brand, raw_name, raw_category, dispensary_id, raw_price
        FROM raw_menu_item
        WHERE raw_brand IS NOT NULL AND raw_brand <> ''
          AND LOWER(raw_category) NOT IN ('accessories', 'gear', 'merchandise', 'apparel')
          {cat_clause}
          {brand_clause}
    """

    with engine.connect() as conn:
        result = conn.execute(text(query))
        rows = result.fetchall()

    # Group by brand + cleaned name + SIZE (different sizes = different products)
    groups = defaultdict(list)
    for row in rows:
        brand, name, cat, disp_id, price = row
        # Strip trailing/leading spaces from name
        name = name.strip() if name else name
        size = extract_size_from_name(name) or "unknown"
        key = (brand.upper(), clean_name_for_grouping(name, brand), size)
        groups[key].append({
            'original': name,
            'category': cat,
            'store': disp_id,
            'price': price,
            'size': size
        })

    # Filter to groups with naming variations (same brand + base name + size but different full names)
    results = []
    for (brand, cleaned, size), items in groups.items():
        unique_names = list(set(item['original'] for item in items))
        if len(unique_names) >= min_variations:
            # Count occurrences of each name
            name_counts = defaultdict(int)
            for item in items:
                name_counts[item['original']] += 1

            results.append({
                'brand': brand,
                'cleaned_name': cleaned,
                'size': size,
                'total_count': len(items),
                'store_count': len(set(item['store'] for item in items)),
                'variation_count': len(unique_names),
                'variations': [(name, name_counts[name]) for name in sorted(unique_names, key=lambda x: -name_counts[x])],
                'suggested_canonical': suggest_canonical_name(unique_names, brand),
                'categories': list(set(item['category'] for item in items))
            })

    # Sort by variation count then total count
    results.sort(key=lambda x: (-x['variation_count'], -x['total_count']))
    return results


# UI
st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    category_filter = st.selectbox(
        "Category",
        ["All", "Flower", "Pre-Rolls", "Vapes", "Concentrates", "Edibles"]
    )

with col2:
    # Get top brands
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT UPPER(raw_brand), COUNT(*) as cnt
            FROM raw_menu_item
            WHERE raw_brand IS NOT NULL AND raw_brand <> ''
            GROUP BY UPPER(raw_brand)
            ORDER BY cnt DESC
            LIMIT 30
        """))
        brands = ["All"] + [row[0] for row in result]

    brand_filter = st.selectbox("Brand", brands)

with col3:
    min_variations = st.slider("Minimum Variations", 2, 10, 2)

# Load data
with st.spinner("Analyzing product names..."):
    variations = get_naming_variations(category_filter, brand_filter, min_variations)

st.markdown("---")

if not variations:
    st.info("No naming variations found with current filters.")
else:
    # Summary stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Product Groups with Variations", len(variations))
    with col2:
        total_variations = sum(v['variation_count'] for v in variations)
        st.metric("Total Name Variations", total_variations)
    with col3:
        products_affected = sum(v['total_count'] for v in variations)
        st.metric("Products Affected", products_affected)
    with col4:
        avg_variations = total_variations / len(variations) if variations else 0
        st.metric("Avg Variations per Product", f"{avg_variations:.1f}")

    st.markdown("---")

    # Legend
    st.markdown("""
    **Legend:**
    - **Suggested Canonical** = Recommended standard name (cleanest format)
    - **Variations** = Different names found for the same product
    - **Count** = How many times each variation appears
    """)

    st.markdown("---")

    # Get already saved canonical names
    saved_canonicals = get_saved_canonicals()

    # Display groups
    for i, group in enumerate(variations[:50]):
        size_display = group['size'] if group['size'] != 'unknown' else 'No Size'

        # Check if already has canonical name saved
        canonical_key = (group['brand'], group['cleaned_name'])
        has_saved = canonical_key in saved_canonicals
        saved_name = saved_canonicals.get(canonical_key, '')

        status_icon = "✅" if has_saved else "⚠️"

        with st.expander(
            f"{status_icon} **{group['brand']}** - {group['cleaned_name']} [{size_display}] "
            f"({group['variation_count']} variations, {group['total_count']} products)",
            expanded=(i < 3 and not has_saved)
        ):
            col1, col2 = st.columns([2, 1])

            with col1:
                if has_saved:
                    st.success(f"**Approved Canonical Name:** `{saved_name}`")
                else:
                    st.markdown(f"**Suggested Canonical Name:** `{group['suggested_canonical']}`")

                st.markdown("---")
                st.markdown("**Name Variations:**")

                for name, count in group['variations'][:10]:
                    # Highlight if matches suggested canonical
                    if name == group['suggested_canonical']:
                        st.markdown(f"- **[{count}x]** ✅ `{name}`")
                    else:
                        st.markdown(f"- [{count}x] `{name}`")

                if len(group['variations']) > 10:
                    st.caption(f"... and {len(group['variations']) - 10} more variations")

            with col2:
                st.markdown(f"**Size:** {size_display}")
                st.markdown(f"**Stores:** {group['store_count']}")
                st.markdown(f"**Categories:** {', '.join(group['categories'][:3])}")

                st.markdown("---")

                # Approve button
                if not has_saved:
                    if st.button("✓ Approve Suggested", key=f"approve_{i}"):
                        save_canonical_name(group['brand'], group['cleaned_name'], group['suggested_canonical'])
                        st.success("Saved!")
                        st.rerun()
                else:
                    st.caption("Already approved")

    if len(variations) > 50:
        st.info(f"Showing first 50 of {len(variations)} groups. Use filters to narrow results.")

# Stats by brand
st.markdown("---")
st.subheader("Naming Consistency by Brand")

brand_stats = defaultdict(lambda: {'total': 0, 'with_variations': 0, 'variation_count': 0})

for group in variations:
    brand = group['brand']
    brand_stats[brand]['with_variations'] += 1
    brand_stats[brand]['variation_count'] += group['variation_count']

# Get total products per brand
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT UPPER(raw_brand), COUNT(DISTINCT raw_name) as unique_names
        FROM raw_menu_item
        WHERE raw_brand IS NOT NULL AND raw_brand <> ''
        GROUP BY UPPER(raw_brand)
    """))
    for row in result:
        brand_stats[row[0]]['total'] = row[1]

# Create dataframe
brand_df = pd.DataFrame([
    {
        'Brand': brand,
        'Total Unique Names': stats['total'],
        'Products with Variations': stats['with_variations'],
        'Total Variations': stats['variation_count'],
        'Inconsistency %': round(stats['with_variations'] / max(stats['total'], 1) * 100, 1)
    }
    for brand, stats in brand_stats.items()
    if stats['total'] > 10
]).sort_values('Total Variations', ascending=False)

if not brand_df.empty:
    st.dataframe(brand_df.head(20), use_container_width=True, hide_index=True)
