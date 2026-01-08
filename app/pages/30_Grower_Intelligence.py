# app/pages/30_Grower_Intelligence.py
"""Grower/Processor Intelligence - Market trends and distribution insights."""

import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import text
from components.nav import render_nav, get_section_from_params, render_state_filter, get_selected_state
from components.auth import is_authenticated
from core.db import get_engine

st.set_page_config(page_title="Grower Intelligence - CannLinx", layout="wide")
render_nav(require_login=False)  # Allow demo access

# Check if user is authenticated for real data vs demo
DEMO_MODE = not is_authenticated()

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
def get_market_overview(state: str = "MD"):
    """Get high-level market stats in a single optimized query."""
    engine = get_engine()
    with engine.connect() as conn:
        # Combined query for all market overview stats
        result = conn.execute(text("""
            WITH menu_stats AS (
                SELECT
                    COUNT(*) as total_products,
                    COUNT(DISTINCT r.raw_name) as unique_products,
                    COUNT(DISTINCT r.raw_brand) FILTER (WHERE r.raw_brand IS NOT NULL) as total_brands
                FROM raw_menu_item r
                JOIN dispensary d ON r.dispensary_id = d.dispensary_id
                WHERE d.state = :state
            ),
            store_stats AS (
                SELECT COUNT(*) as active_stores FROM dispensary WHERE is_active = true AND state = :state
            )
            SELECT
                m.total_products,
                m.unique_products,
                m.total_brands,
                s.active_stores
            FROM menu_stats m, store_stats s
        """), {"state": state}).fetchone()

        return {
            "total_products": result[0] or 0,
            "unique_products": result[1] or 0,
            "brands": result[2] or 0,
            "stores": result[3] or 0
        }


@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_category_distribution(state: str = "MD"):
    """Get product distribution by category."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                r.raw_category,
                COUNT(*) as product_count,
                COUNT(DISTINCT r.raw_brand) as brand_count,
                AVG(r.raw_price) as avg_price
            FROM raw_menu_item r
            JOIN dispensary d ON r.dispensary_id = d.dispensary_id
            WHERE r.raw_category IS NOT NULL
              AND r.raw_price > 0 AND r.raw_price < 500
              AND d.state = :state
            GROUP BY r.raw_category
            ORDER BY product_count DESC
            LIMIT 15
        """), {"state": state})
        return result.fetchall()


@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_top_strains(state: str = "MD"):
    """Get most distributed strains/products."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                UPPER(r.raw_brand) as brand,
                r.raw_name,
                COUNT(DISTINCT r.dispensary_id) as store_count,
                AVG(r.raw_price) as avg_price,
                MIN(r.raw_price) as min_price,
                MAX(r.raw_price) as max_price
            FROM raw_menu_item r
            JOIN dispensary d ON r.dispensary_id = d.dispensary_id
            WHERE r.raw_brand IS NOT NULL
              AND r.raw_price > 0 AND r.raw_price < 500
              AND LOWER(r.raw_category) IN ('flower', 'buds', 'indica', 'sativa', 'hybrid')
              AND d.state = :state
            GROUP BY UPPER(r.raw_brand), r.raw_name
            HAVING COUNT(DISTINCT r.dispensary_id) >= 3
            ORDER BY store_count DESC
            LIMIT 50
        """), {"state": state})
        return result.fetchall()


@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_brand_distribution(state: str = "MD"):
    """Get brand distribution metrics."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                UPPER(r.raw_brand) as brand,
                COUNT(DISTINCT r.dispensary_id) as store_count,
                COUNT(DISTINCT r.raw_name) as sku_count,
                COUNT(*) as total_listings,
                AVG(r.raw_price) as avg_price
            FROM raw_menu_item r
            JOIN dispensary d ON r.dispensary_id = d.dispensary_id
            WHERE r.raw_brand IS NOT NULL AND r.raw_brand <> ''
              AND r.raw_price > 0
              AND d.state = :state
            GROUP BY UPPER(r.raw_brand)
            ORDER BY store_count DESC
            LIMIT 50
        """), {"state": state})
        return result.fetchall()


@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_price_trends_by_category(state: str = "MD"):
    """Get pricing data by category."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                r.raw_category,
                percentile_cont(0.25) WITHIN GROUP (ORDER BY r.raw_price) as p25,
                percentile_cont(0.50) WITHIN GROUP (ORDER BY r.raw_price) as median,
                percentile_cont(0.75) WITHIN GROUP (ORDER BY r.raw_price) as p75,
                AVG(r.raw_price) as avg_price
            FROM raw_menu_item r
            JOIN dispensary d ON r.dispensary_id = d.dispensary_id
            WHERE r.raw_category IS NOT NULL
              AND r.raw_price > 0 AND r.raw_price < 500
              AND d.state = :state
            GROUP BY r.raw_category
            HAVING COUNT(*) >= 10
            ORDER BY median DESC
        """), {"state": state})
        return result.fetchall()


# Demo data for unauthenticated users
def get_grower_demo_data():
    """Return demo data for grower intelligence."""
    return {
        "overview": {
            "total_products": 48532,
            "unique_products": 8724,
            "brands": 187,
            "stores": 96
        },
        "categories": [
            ("Flower", 18542, 89, 45.50),
            ("Vapes", 12361, 67, 42.25),
            ("Concentrates", 8234, 45, 55.00),
            ("Edibles", 5892, 52, 28.50),
            ("Pre-Rolls", 3503, 41, 15.00),
        ],
        "strains": [
            ("CURIO", "Blue Dream 3.5g", 47, 45.00, 42.00, 55.00),
            ("EVERMORE", "Purple Obeah #3 3.5g", 44, 52.00, 48.00, 58.00),
            ("GRASSROOTS", "Birthday Cake 3.5g", 42, 48.00, 45.00, 52.00),
            ("RYTHM", "Dosidos 3.5g", 38, 50.00, 47.00, 55.00),
            ("VERANO", "G Purps 3.5g", 35, 52.00, 48.00, 58.00),
        ],
        "brands": [
            ("CURIO", 47, 128, 1842, 42.50),
            ("EVERMORE", 44, 96, 1634, 48.25),
            ("GRASSROOTS", 42, 85, 1521, 46.00),
            ("RYTHM", 38, 72, 1298, 50.00),
            ("VERANO", 35, 64, 1156, 52.25),
        ],
        "prices": [
            ("Flower", 35.00, 45.00, 55.00, 45.50),
            ("Vapes", 28.00, 40.00, 52.00, 42.25),
            ("Concentrates", 35.00, 50.00, 72.00, 55.00),
            ("Edibles", 18.00, 25.00, 38.00, 28.50),
            ("Pre-Rolls", 10.00, 14.00, 22.00, 15.00),
        ]
    }


if DEMO_MODE:
    st.info("**Demo Mode** - Showing sample data. [Login](/Login) to access real market data.")
    demo_data = get_grower_demo_data()
    st.selectbox("🗺️ State", ["MD"], disabled=True)
    selected_state = "MD"
    overview = demo_data["overview"]
else:
    # State filter
    selected_state = render_state_filter()
    # Market Overview
    overview = get_market_overview(selected_state)

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

    if DEMO_MODE:
        cat_data = demo_data["categories"]
    else:
        cat_data = get_category_distribution(selected_state)
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

    if DEMO_MODE:
        strains = demo_data["strains"]
    else:
        strains = get_top_strains(selected_state)
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

    if DEMO_MODE:
        brands = demo_data["brands"]
    else:
        brands = get_brand_distribution(selected_state)
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

    if DEMO_MODE:
        prices = demo_data["prices"]
    else:
        prices = get_price_trends_by_category(selected_state)
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
    def get_size_distribution(level: str, filter_id: str = None, state: str = "MD"):
        """Get product counts by category and size."""
        engine = get_engine()
        with engine.connect() as conn:
            if level == "state":
                result = conn.execute(text("""
                    SELECT r.raw_category, r.raw_name, COUNT(*) as cnt
                    FROM raw_menu_item r
                    JOIN dispensary d ON r.dispensary_id = d.dispensary_id
                    WHERE d.state = :state
                      AND (r.raw_category ILIKE '%flower%' OR r.raw_category ILIKE '%bud%'
                           OR r.raw_category ILIKE '%pre-roll%' OR r.raw_category ILIKE '%preroll%')
                    GROUP BY r.raw_category, r.raw_name
                """), {"state": state}).fetchall()
            elif level == "county":
                result = conn.execute(text("""
                    SELECT r.raw_category, r.raw_name, COUNT(*) as cnt
                    FROM raw_menu_item r
                    JOIN dispensary d ON r.dispensary_id = d.dispensary_id
                    WHERE d.county = :county AND d.state = :state
                      AND (r.raw_category ILIKE '%flower%' OR r.raw_category ILIKE '%bud%'
                           OR r.raw_category ILIKE '%pre-roll%' OR r.raw_category ILIKE '%preroll%')
                    GROUP BY r.raw_category, r.raw_name
                """), {"county": filter_id, "state": state}).fetchall()
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
    def get_counties(state: str = "MD"):
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT county FROM dispensary
                WHERE county IS NOT NULL AND state = :state ORDER BY county
            """), {"state": state}).fetchall()
            return [r[0] for r in result]

    @st.cache_data(ttl=600)  # Cache for 10 minutes
    def get_stores(state: str = "MD"):
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT dispensary_id, name, city FROM dispensary
                WHERE is_active = true AND state = :state ORDER BY name
            """), {"state": state}).fetchall()
            return [(r[0], f"{r[1]} ({r[2]})") for r in result]

    # Level selector
    col1, col2 = st.columns([1, 2])
    with col1:
        level = st.selectbox("View Level", [f"State (All {selected_state})", "By County", "By Store"])

    filter_id = None
    if level == "By County":
        counties = get_counties(selected_state)
        with col2:
            selected_county = st.selectbox("Select County", counties)
            filter_id = selected_county
        level_key = "county"
    elif level == "By Store":
        stores = get_stores(selected_state)
        with col2:
            store_options = {name: sid for sid, name in stores}
            selected_store = st.selectbox("Select Store", list(store_options.keys()))
            filter_id = store_options[selected_store]
        level_key = "store"
    else:
        level_key = "state"

    # Get and display data
    size_data = get_size_distribution(level_key, filter_id, selected_state)

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
