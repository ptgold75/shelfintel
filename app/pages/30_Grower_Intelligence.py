# app/pages/30_Grower_Intelligence.py
"""Grower/Processor Intelligence - Market trends and distribution insights."""

import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
from components.nav import render_nav, get_section_from_params

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


@st.cache_resource
def get_engine():
    return create_engine(st.secrets["DATABASE_URL"])


@st.cache_data(ttl=300)
def get_market_overview():
    """Get high-level market stats."""
    engine = get_engine()
    with engine.connect() as conn:
        total_products = conn.execute(text(
            "SELECT COUNT(*) FROM raw_menu_item"
        )).scalar() or 0

        unique_products = conn.execute(text(
            "SELECT COUNT(DISTINCT raw_name) FROM raw_menu_item"
        )).scalar() or 0

        total_brands = conn.execute(text(
            "SELECT COUNT(DISTINCT raw_brand) FROM raw_menu_item WHERE raw_brand IS NOT NULL"
        )).scalar() or 0

        active_stores = conn.execute(text(
            "SELECT COUNT(*) FROM dispensary WHERE is_active = true"
        )).scalar() or 0

        return {
            "total_products": total_products,
            "unique_products": unique_products,
            "brands": total_brands,
            "stores": active_stores
        }


@st.cache_data(ttl=300)
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


@st.cache_data(ttl=300)
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


@st.cache_data(ttl=300)
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


@st.cache_data(ttl=300)
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
tab1, tab2, tab3, tab4 = st.tabs(["Category Analysis", "Top Strains", "Brand Distribution", "Price Benchmarks"])

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
