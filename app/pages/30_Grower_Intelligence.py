# app/pages/30_Grower_Intelligence.py
"""Grower/Processor Intelligence - Market trends and distribution insights."""

import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import text
from components.nav import render_nav, get_section_from_params
from core.db import get_engine

st.set_page_config(page_title="Grower Intelligence - CannLinx", layout="wide")
render_nav()

# Handle section parameter for tab navigation
section = get_section_from_params()
TAB_MAP = {"category": 0, "strains": 1, "distribution": 2, "prices": 3}
if section and section in TAB_MAP:
    tab_index = TAB_MAP[section]
    st.markdown(f"""
    <script>
        // Auto-click the appropriate tab based on section param
        setTimeout(function() {{
            const tabs = document.querySelectorAll('[data-baseweb="tab"]');
            if (tabs && tabs[{tab_index}]) {{
                tabs[{tab_index}].click();
            }}
        }}, 100);
    </script>
    """, unsafe_allow_html=True)

st.title("Grower & Processor Intelligence")
st.caption("Market trends, strain popularity, and retail distribution insights")


@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_market_overview():
    """Get high-level market stats in a single optimized query."""
    engine = get_engine()
    with engine.connect() as conn:
        # Combined query for all market overview stats
        result = conn.execute(text("""
            WITH menu_stats AS (
                SELECT
                    COUNT(*) as total_products,
                    COUNT(DISTINCT raw_name) as unique_products,
                    COUNT(DISTINCT raw_brand) FILTER (WHERE raw_brand IS NOT NULL) as total_brands
                FROM raw_menu_item
            ),
            store_stats AS (
                SELECT COUNT(*) as active_stores FROM dispensary WHERE is_active = true
            )
            SELECT
                m.total_products,
                m.unique_products,
                m.total_brands,
                s.active_stores
            FROM menu_stats m, store_stats s
        """)).fetchone()

        return {
            "total_products": result[0] or 0,
            "unique_products": result[1] or 0,
            "brands": result[2] or 0,
            "stores": result[3] or 0
        }


@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_category_distribution():
    """Get product distribution by category."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                raw_category,
                COUNT(*) as product_count,
                COUNT(DISTINCT raw_brand) as brand_count,
                AVG(raw_price) as avg_price
            FROM raw_menu_item
            WHERE raw_category IS NOT NULL
              AND raw_price > 0 AND raw_price < 500
            GROUP BY raw_category
            ORDER BY product_count DESC
            LIMIT 15
        """))
        return result.fetchall()


@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_top_strains():
    """Get most distributed strains/products."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                UPPER(raw_brand) as brand,
                raw_name,
                COUNT(DISTINCT dispensary_id) as store_count,
                AVG(raw_price) as avg_price,
                MIN(raw_price) as min_price,
                MAX(raw_price) as max_price
            FROM raw_menu_item
            WHERE raw_brand IS NOT NULL
              AND raw_price > 0 AND raw_price < 500
              AND LOWER(raw_category) IN ('flower', 'buds', 'indica', 'sativa', 'hybrid')
            GROUP BY UPPER(raw_brand), raw_name
            HAVING COUNT(DISTINCT dispensary_id) >= 3
            ORDER BY store_count DESC
            LIMIT 50
        """))
        return result.fetchall()


@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_brand_distribution():
    """Get brand distribution metrics."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                UPPER(raw_brand) as brand,
                COUNT(DISTINCT dispensary_id) as store_count,
                COUNT(DISTINCT raw_name) as sku_count,
                COUNT(*) as total_listings,
                AVG(raw_price) as avg_price
            FROM raw_menu_item
            WHERE raw_brand IS NOT NULL AND raw_brand <> ''
              AND raw_price > 0
            GROUP BY UPPER(raw_brand)
            ORDER BY store_count DESC
            LIMIT 50
        """))
        return result.fetchall()


@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_price_trends_by_category():
    """Get pricing data by category."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                raw_category,
                percentile_cont(0.25) WITHIN GROUP (ORDER BY raw_price) as p25,
                percentile_cont(0.50) WITHIN GROUP (ORDER BY raw_price) as median,
                percentile_cont(0.75) WITHIN GROUP (ORDER BY raw_price) as p75,
                AVG(raw_price) as avg_price
            FROM raw_menu_item
            WHERE raw_category IS NOT NULL
              AND raw_price > 0 AND raw_price < 500
            GROUP BY raw_category
            HAVING COUNT(*) >= 10
            ORDER BY median DESC
        """))
        return result.fetchall()


# Market Overview
overview = get_market_overview()

st.markdown("---")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Product Listings", f"{overview['total_products']:,}")
with col2:
    st.metric("Unique Products", f"{overview['unique_products']:,}")
with col3:
    st.metric("Brands Tracked", overview['brands'])
with col4:
    st.metric("Active Dispensaries", overview['stores'])

# Tabs
st.markdown("---")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Category Analysis", "Top Strains", "Brand Distribution", "Price Benchmarks", "Size Distribution"])

with tab1:
    st.subheader("Category Distribution")
    st.caption("Product volume and pricing by category")

    cat_data = get_category_distribution()
    if cat_data:
        df = pd.DataFrame(cat_data, columns=["Category", "Products", "Brands", "Avg Price"])
        df["Avg Price"] = df["Avg Price"].round(2)

        col1, col2 = st.columns([2, 1])

        with col1:
            # Horizontal bar chart with clear labels
            fig = px.bar(
                df.sort_values("Products", ascending=True),
                x="Products",
                y="Category",
                orientation="h",
                title="Products by Category",
                labels={"Products": "Number of Products", "Category": "Category"}
            )
            fig.update_layout(
                xaxis_title="Number of Products",
                yaxis_title="",
                showlegend=False,
                height=450
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.dataframe(df, use_container_width=True, hide_index=True)

with tab2:
    st.subheader("Most Distributed Flower Products")
    st.caption("Strains available at the most stores")

    strains = get_top_strains()
    if strains:
        df = pd.DataFrame(strains, columns=["Brand", "Product", "Stores", "Avg Price", "Min", "Max"])
        df["Avg Price"] = df["Avg Price"].round(2)
        df["Min"] = df["Min"].round(2)
        df["Max"] = df["Max"].round(2)
        df["Price Range"] = df.apply(lambda r: f"${r['Min']:.0f}-${r['Max']:.0f}", axis=1)

        # Top 20 table
        st.dataframe(
            df[["Brand", "Product", "Stores", "Avg Price", "Price Range"]].head(30),
            use_container_width=True,
            hide_index=True,
            height=500
        )

        # Summary
        st.markdown("---")
        st.markdown(f"**Insights:**")
        top_brand = df.groupby("Brand")["Stores"].mean().idxmax()
        st.markdown(f"- Most distributed brand: **{top_brand}**")
        avg_distribution = df["Stores"].mean()
        st.markdown(f"- Average distribution: **{avg_distribution:.1f} stores** per product")

with tab3:
    st.subheader("Brand Distribution Rankings")
    st.caption("Which brands have the widest retail presence")

    brands = get_brand_distribution()
    if brands:
        df = pd.DataFrame(brands, columns=["Brand", "Stores", "SKUs", "Total Listings", "Avg Price"])
        df["Avg Price"] = df["Avg Price"].round(2)

        # Distribution efficiency = listings per store
        df["Listings/Store"] = (df["Total Listings"] / df["Stores"]).round(1)

        st.dataframe(df, use_container_width=True, hide_index=True, height=500)

        # Top 20 visualization
        st.markdown("---")
        top_brands = df.head(20).sort_values("Stores", ascending=True)
        fig = px.bar(
            top_brands,
            x="Stores",
            y="Brand",
            orientation="h",
            title="Store Coverage - Top 20 Brands",
            labels={"Stores": "Number of Stores Carrying Brand", "Brand": ""}
        )
        fig.update_layout(
            xaxis_title="Number of Stores",
            yaxis_title="",
            showlegend=False,
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("Price Benchmarks by Category")
    st.caption("Understand market pricing for each category")

    prices = get_price_trends_by_category()
    if prices:
        df = pd.DataFrame(prices, columns=["Category", "25th %ile", "Median", "75th %ile", "Average"])
        df = df.round(2)

        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("---")
        # Melt the dataframe for grouped bar chart
        price_cols = ["25th %ile", "Median", "75th %ile"]
        df_melted = df.melt(id_vars=["Category"], value_vars=price_cols, var_name="Percentile", value_name="Price")

        fig = px.bar(
            df_melted,
            x="Price",
            y="Category",
            color="Percentile",
            orientation="h",
            barmode="group",
            title="Price Distribution by Category",
            labels={"Price": "Price ($)", "Category": ""}
        )
        fig.update_layout(
            xaxis_title="Price ($)",
            yaxis_title="",
            legend_title="Percentile",
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)

with tab5:
    st.subheader("Size Distribution by Category")
    st.caption("Product counts by unit size at store, county, and state levels")

    import re

    def extract_size(name: str) -> str:
        """Extract size from product name."""
        if not name:
            return "Unknown"
        name_lower = name.lower()

        # Grams
        match = re.search(r'(\d+\.?\d*)\s*(g|gram|grams)\b', name_lower)
        if match:
            val = float(match.group(1))
            if val <= 1.5:
                return "1g"
            elif val <= 4:
                return "3.5g"
            elif val <= 8:
                return "7g"
            elif val <= 16:
                return "14g"
            else:
                return "28g"

        # Fractions
        if '1/8' in name_lower or 'eighth' in name_lower:
            return "3.5g"
        if '1/4' in name_lower or 'quarter' in name_lower:
            return "7g"
        if '1/2' in name_lower or 'half' in name_lower:
            return "14g"
        if '1oz' in name_lower or 'ounce' in name_lower:
            return "28g"

        return "Unknown"

    # Get size distribution data
    @st.cache_data(ttl=600)  # Cache for 10 minutes
    def get_size_distribution(level: str, filter_id: str = None):
        """Get product counts by category and size."""
        engine = get_engine()
        with engine.connect() as conn:
            if level == "state":
                result = conn.execute(text("""
                    SELECT raw_category, raw_name, COUNT(*) as cnt
                    FROM raw_menu_item
                    WHERE raw_category ILIKE '%flower%' OR raw_category ILIKE '%bud%'
                       OR raw_category ILIKE '%pre-roll%' OR raw_category ILIKE '%preroll%'
                    GROUP BY raw_category, raw_name
                """)).fetchall()
            elif level == "county":
                result = conn.execute(text("""
                    SELECT r.raw_category, r.raw_name, COUNT(*) as cnt
                    FROM raw_menu_item r
                    JOIN dispensary d ON r.dispensary_id = d.dispensary_id
                    WHERE d.county = :county
                      AND (r.raw_category ILIKE '%flower%' OR r.raw_category ILIKE '%bud%'
                           OR r.raw_category ILIKE '%pre-roll%' OR r.raw_category ILIKE '%preroll%')
                    GROUP BY r.raw_category, r.raw_name
                """), {"county": filter_id}).fetchall()
            else:  # store
                result = conn.execute(text("""
                    SELECT raw_category, raw_name, COUNT(*) as cnt
                    FROM raw_menu_item
                    WHERE dispensary_id = :store_id
                      AND (raw_category ILIKE '%flower%' OR raw_category ILIKE '%bud%'
                           OR raw_category ILIKE '%pre-roll%' OR raw_category ILIKE '%preroll%')
                    GROUP BY raw_category, raw_name
                """), {"store_id": filter_id}).fetchall()

            # Aggregate by size
            from collections import defaultdict
            size_counts = defaultdict(lambda: defaultdict(int))
            for cat, name, cnt in result:
                size = extract_size(name)
                cat_norm = "Flower" if "flower" in cat.lower() or "bud" in cat.lower() else "Pre-Rolls"
                size_counts[cat_norm][size] += cnt

            return dict(size_counts)

    @st.cache_data(ttl=600)  # Cache for 10 minutes
    def get_counties():
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT county FROM dispensary
                WHERE county IS NOT NULL ORDER BY county
            """)).fetchall()
            return [r[0] for r in result]

    @st.cache_data(ttl=600)  # Cache for 10 minutes
    def get_stores():
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT dispensary_id, name, city FROM dispensary
                WHERE is_active = true ORDER BY name
            """)).fetchall()
            return [(r[0], f"{r[1]} ({r[2]})") for r in result]

    # Level selector
    col1, col2 = st.columns([1, 2])
    with col1:
        level = st.selectbox("View Level", ["State (All MD)", "By County", "By Store"])

    filter_id = None
    if level == "By County":
        counties = get_counties()
        with col2:
            selected_county = st.selectbox("Select County", counties)
            filter_id = selected_county
        level_key = "county"
    elif level == "By Store":
        stores = get_stores()
        with col2:
            store_options = {name: sid for sid, name in stores}
            selected_store = st.selectbox("Select Store", list(store_options.keys()))
            filter_id = store_options[selected_store]
        level_key = "store"
    else:
        level_key = "state"

    # Get and display data
    size_data = get_size_distribution(level_key, filter_id)

    if size_data:
        # Flower sizes
        st.markdown("#### Flower by Size")
        if "Flower" in size_data:
            flower_sizes = size_data["Flower"]
            size_order = ["1g", "3.5g", "7g", "14g", "28g", "Unknown"]
            df_flower = pd.DataFrame([
                {"Size": s, "Products": flower_sizes.get(s, 0)}
                for s in size_order if flower_sizes.get(s, 0) > 0
            ])

            if not df_flower.empty:
                col1, col2 = st.columns([2, 1])
                with col1:
                    fig = px.bar(df_flower, x="Size", y="Products",
                                 title="Flower Products by Size",
                                 color="Size",
                                 color_discrete_sequence=px.colors.qualitative.Set2)
                    fig.update_layout(showlegend=False, height=350)
                    st.plotly_chart(fig, use_container_width=True)
                with col2:
                    st.dataframe(df_flower, hide_index=True, use_container_width=True)

                    total = df_flower["Products"].sum()
                    known = total - flower_sizes.get("Unknown", 0)
                    st.metric("Total Flower", f"{total:,}")
                    st.metric("Known Sizes", f"{known:,} ({100*known/total:.0f}%)" if total > 0 else "0")
        else:
            st.info("No flower data available for this selection")

        # Pre-roll sizes (could expand this)
        st.markdown("#### Pre-Rolls by Size")
        if "Pre-Rolls" in size_data:
            preroll_sizes = size_data["Pre-Rolls"]
            df_preroll = pd.DataFrame([
                {"Size": s, "Products": c}
                for s, c in sorted(preroll_sizes.items(), key=lambda x: -x[1])
            ])
            if not df_preroll.empty:
                st.dataframe(df_preroll.head(10), hide_index=True, use_container_width=True)
        else:
            st.info("No pre-roll data available for this selection")
    else:
        st.warning("No data available for this selection")

# Value proposition
st.markdown("---")
st.markdown("""
**What Grower Intelligence Helps You Do:**

| Use Case | Benefit |
|----------|---------|
| **Strain Planning** | See which strains have best retail distribution |
| **Brand Benchmarking** | Compare your distribution to competitors |
| **Price Positioning** | Set wholesale prices based on retail market data |
| **Category Trends** | Identify growing/declining product categories |
| **Retail Partners** | Find stores that carry similar brands |
""")
