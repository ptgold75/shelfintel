# app/pages/20_Retail_Intelligence.py
"""Retail Intelligence Dashboard - Competitive analysis for dispensaries."""

import streamlit as st
import pandas as pd
import re
from sqlalchemy import text
from components.nav import render_nav, get_section_from_params
from core.db import get_engine


def extract_size_from_name(name: str) -> str:
    """Extract size/weight from product name for accurate comparisons."""
    if not name:
        return "unknown"
    name_lower = name.lower()

    # Grams: 3.5g, 7g, 14g, 28g, etc.
    match = re.search(r'(\d+\.?\d*)\s*(g|gram|grams|gm|grm)\b', name_lower)
    if match:
        return f"{match.group(1)}g"

    # Milligrams: 100mg, 500mg, etc.
    match = re.search(r'(\d+)\s*(mg|milligram)', name_lower)
    if match:
        return f"{match.group(1)}mg"

    # Ounces: 1oz, 0.5oz
    match = re.search(r'(\d+\.?\d*)\s*(oz|ounce)', name_lower)
    if match:
        return f"{match.group(1)}oz"

    # Fractions: 1/8, 1/4, 1/2, eighth, quarter, half
    if '1/8' in name_lower or 'eighth' in name_lower:
        return "3.5g"
    if '1/4' in name_lower or 'quarter' in name_lower:
        return "7g"
    if '1/2' in name_lower or 'half' in name_lower:
        return "14g"

    # Pack counts: 5pk, 10-pack, 3ct
    match = re.search(r'(\d+)\s*(-?)(pk|pack|ct|count)\b', name_lower)
    if match:
        return f"{match.group(1)}pk"

    return "std"

st.set_page_config(page_title="Retail Intelligence - CannLinx", layout="wide")
render_nav()

# Handle section parameter for tab navigation
section = get_section_from_params()
TAB_MAP = {"prices": 0, "gaps": 1, "category": 2}
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

st.title("Retail Intelligence")
st.caption("Competitive pricing, assortment gaps, and category optimization for dispensaries")


@st.cache_data(ttl=3600)  # Cache for 1 hour - store list rarely changes
def get_dispensaries():
    """Get list of dispensaries with products."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT d.dispensary_id, d.name, d.city, d.county, COUNT(r.raw_menu_item_id) as products
            FROM dispensary d
            LEFT JOIN raw_menu_item r ON d.dispensary_id = r.dispensary_id
            WHERE d.is_active = true
            GROUP BY d.dispensary_id, d.name, d.city, d.county
            HAVING COUNT(r.raw_menu_item_id) > 0
            ORDER BY d.name
        """))
        return [(row[0], f"{row[1]} ({row[2]})") for row in result]


@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_store_metrics(store_id: str):
    """Get all key metrics for a store in a single optimized query."""
    engine = get_engine()
    with engine.connect() as conn:
        # Combined query for all metrics
        result = conn.execute(text("""
            SELECT
                COUNT(*) as product_count,
                COUNT(DISTINCT raw_brand) FILTER (WHERE raw_brand IS NOT NULL) as brand_count,
                AVG(raw_price) FILTER (WHERE raw_price > 0 AND raw_price < 500) as avg_price,
                COUNT(DISTINCT raw_category) as cat_count
            FROM raw_menu_item
            WHERE dispensary_id = :sid
        """), {"sid": store_id}).fetchone()

        return {
            "products": result[0] or 0,
            "brands": result[1] or 0,
            "avg_price": result[2] or 0,
            "categories": result[3] or 0
        }


@st.cache_data(ttl=3600)  # Cache for 1 hour - competitors don't change often
def get_nearby_competitors(store_id: str):
    """Get competitors in same county."""
    engine = get_engine()
    with engine.connect() as conn:
        # Get store's county
        county = conn.execute(text("""
            SELECT county FROM dispensary WHERE dispensary_id = :sid
        """), {"sid": store_id}).scalar()

        if not county:
            return []

        # Get competitors
        result = conn.execute(text("""
            SELECT d.dispensary_id, d.name, d.city, COUNT(r.raw_menu_item_id) as products
            FROM dispensary d
            LEFT JOIN raw_menu_item r ON d.dispensary_id = r.dispensary_id
            WHERE d.county = :county AND d.dispensary_id <> :sid AND d.is_active = true
            GROUP BY d.dispensary_id, d.name, d.city
            ORDER BY d.name
        """), {"county": county, "sid": store_id}).fetchall()

        return result


@st.cache_data(ttl=600)  # Cache for 10 minutes
def compare_pricing(store_id: str, competitor_id: str):
    """Compare product pricing between two stores with size matching."""
    engine = get_engine()
    with engine.connect() as conn:
        # Get products from both stores
        my_products = conn.execute(text("""
            SELECT UPPER(raw_brand) as brand, raw_name, raw_price, raw_category
            FROM raw_menu_item
            WHERE dispensary_id = :my_store AND raw_price > 0 AND raw_brand IS NOT NULL
        """), {"my_store": store_id}).fetchall()

        comp_products = conn.execute(text("""
            SELECT UPPER(raw_brand) as brand, raw_name, raw_price
            FROM raw_menu_item
            WHERE dispensary_id = :comp_store AND raw_price > 0 AND raw_brand IS NOT NULL
        """), {"comp_store": competitor_id}).fetchall()

        # Build competitor product lookup by brand + name + size
        # Skip "std" (unknown) sizes - can't accurately compare
        comp_lookup = {}
        for brand, name, price in comp_products:
            size = extract_size_from_name(name)
            if size == "std":  # Skip unknown sizes
                continue
            key = (brand, name, size)
            comp_lookup[key] = price

        # Match products by brand + name + size
        results = []
        seen = set()
        for brand, name, my_price, category in my_products:
            size = extract_size_from_name(name)
            if size == "std":  # Skip unknown sizes
                continue
            key = (brand, name, size)
            if key in comp_lookup and key not in seen:
                comp_price = comp_lookup[key]
                diff = my_price - comp_price
                results.append((brand, name, size, category, my_price, comp_price, diff))
                seen.add(key)

        # Sort by absolute difference descending
        results.sort(key=lambda x: abs(x[6]), reverse=True)
        return results


@st.cache_data(ttl=600)  # Cache for 10 minutes
def find_assortment_gaps(store_id: str, competitor_id: str):
    """Find products competitor has that store doesn't."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT DISTINCT
                UPPER(c.raw_brand) as brand,
                c.raw_name as product,
                c.raw_category as category,
                c.raw_price as price
            FROM raw_menu_item c
            WHERE c.dispensary_id = :comp_store
              AND c.raw_brand IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM raw_menu_item m
                  WHERE m.dispensary_id = :my_store
                    AND UPPER(m.raw_brand) = UPPER(c.raw_brand)
                    AND m.raw_name = c.raw_name
              )
            ORDER BY brand, product
            LIMIT 100
        """), {"my_store": store_id, "comp_store": competitor_id}).fetchall()

        return result


@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_retail_insights(store_id: str):
    """Generate actionable insights for a dispensary."""
    engine = get_engine()
    insights = []

    with engine.connect() as conn:
        # Get store's county
        county = conn.execute(text(
            "SELECT county FROM dispensary WHERE dispensary_id = :sid"
        ), {"sid": store_id}).scalar()

        if not county:
            return insights

        # 1. Popular products you're missing - items carried by 3+ competitors in your county
        missing_popular = conn.execute(text("""
            WITH county_products AS (
                SELECT UPPER(r.raw_brand) as brand, r.raw_name, COUNT(DISTINCT r.dispensary_id) as store_count
                FROM raw_menu_item r
                JOIN dispensary d ON r.dispensary_id = d.dispensary_id
                WHERE d.county = :county AND d.dispensary_id <> :sid
                  AND r.raw_brand IS NOT NULL
                GROUP BY UPPER(r.raw_brand), r.raw_name
                HAVING COUNT(DISTINCT r.dispensary_id) >= 3
            )
            SELECT cp.brand, cp.raw_name, cp.store_count
            FROM county_products cp
            WHERE NOT EXISTS (
                SELECT 1 FROM raw_menu_item m
                WHERE m.dispensary_id = :sid
                  AND UPPER(m.raw_brand) = cp.brand
                  AND m.raw_name = cp.raw_name
            )
            ORDER BY cp.store_count DESC
            LIMIT 10
        """), {"county": county, "sid": store_id}).fetchall()

        if missing_popular:
            insights.append({
                "type": "assortment",
                "priority": "high",
                "title": f"{len(missing_popular)} popular products you don't carry",
                "detail": "These products are carried by 3+ competitors in your county.",
                "data": missing_popular
            })

        # 2. You're priced higher than average (with size matching)
        # Get your products with size info
        my_products_raw = conn.execute(text("""
            SELECT UPPER(raw_brand) as brand, raw_name, raw_price
            FROM raw_menu_item
            WHERE dispensary_id = :sid AND raw_price > 0 AND raw_brand IS NOT NULL
        """), {"sid": store_id}).fetchall()

        # Get market products for comparison
        market_products_raw = conn.execute(text("""
            SELECT UPPER(r.raw_brand) as brand, r.raw_name, r.raw_price
            FROM raw_menu_item r
            JOIN dispensary d ON r.dispensary_id = d.dispensary_id
            WHERE d.county = :county AND r.raw_price > 0 AND r.raw_brand IS NOT NULL
        """), {"county": county}).fetchall()

        # Build market averages by brand + name + size
        # Skip "std" (unknown) sizes - can't accurately compare
        from collections import defaultdict
        market_prices = defaultdict(list)
        for brand, name, price in market_products_raw:
            size = extract_size_from_name(name)
            if size == "std":  # Skip unknown sizes
                continue
            key = (brand, name, size)
            market_prices[key].append(price)

        # Calculate averages
        market_avg = {k: sum(v)/len(v) for k, v in market_prices.items()}

        # Compare your products
        priced_high = []
        seen = set()  # Avoid duplicates
        for brand, name, your_price in my_products_raw:
            size = extract_size_from_name(name)
            if size == "std":  # Skip unknown sizes
                continue
            key = (brand, name, size)
            if key in market_avg and key not in seen:
                avg_price = market_avg[key]
                diff = your_price - avg_price
                if diff > 3:  # Only show if $3+ above average
                    priced_high.append((brand, name, size, your_price, avg_price, diff))
                    seen.add(key)

        # Sort by difference descending and limit
        priced_high.sort(key=lambda x: x[5], reverse=True)
        priced_high = priced_high[:10]

        if priced_high:
            insights.append({
                "type": "pricing_high",
                "priority": "medium",
                "title": f"{len(priced_high)} products priced above market average",
                "detail": "You may be losing sales to competitors on these items (comparing same sizes only).",
                "data": priced_high
            })

        # 3. Brands your competitors carry that you don't
        missing_brands = conn.execute(text("""
            WITH my_brands AS (
                SELECT DISTINCT UPPER(raw_brand) as brand
                FROM raw_menu_item
                WHERE dispensary_id = :sid AND raw_brand IS NOT NULL
            ),
            competitor_brands AS (
                SELECT UPPER(r.raw_brand) as brand, COUNT(DISTINCT r.dispensary_id) as stores,
                       COUNT(DISTINCT r.raw_name) as products
                FROM raw_menu_item r
                JOIN dispensary d ON r.dispensary_id = d.dispensary_id
                WHERE d.county = :county AND d.dispensary_id <> :sid
                  AND r.raw_brand IS NOT NULL
                GROUP BY UPPER(r.raw_brand)
                HAVING COUNT(DISTINCT r.dispensary_id) >= 2
            )
            SELECT cb.brand, cb.stores, cb.products
            FROM competitor_brands cb
            WHERE cb.brand NOT IN (SELECT brand FROM my_brands)
            ORDER BY cb.stores DESC, cb.products DESC
            LIMIT 10
        """), {"county": county, "sid": store_id}).fetchall()

        if missing_brands:
            insights.append({
                "type": "brands",
                "priority": "medium",
                "title": f"{len(missing_brands)} brands your competitors carry that you don't",
                "detail": "Consider adding these brands to your assortment.",
                "data": missing_brands
            })

        # 4. Your unique products - items you carry that NO competitor in your county has
        unique_products = conn.execute(text("""
            WITH my_products AS (
                SELECT UPPER(raw_brand) as brand, raw_name, raw_category, raw_price
                FROM raw_menu_item
                WHERE dispensary_id = :sid AND raw_brand IS NOT NULL
            ),
            competitor_products AS (
                SELECT DISTINCT UPPER(r.raw_brand) as brand, r.raw_name
                FROM raw_menu_item r
                JOIN dispensary d ON r.dispensary_id = d.dispensary_id
                WHERE d.county = :county AND d.dispensary_id <> :sid
                  AND r.raw_brand IS NOT NULL
            )
            SELECT mp.brand, mp.raw_name, mp.raw_category, mp.raw_price
            FROM my_products mp
            WHERE NOT EXISTS (
                SELECT 1 FROM competitor_products cp
                WHERE cp.brand = mp.brand AND cp.raw_name = mp.raw_name
            )
            ORDER BY mp.brand, mp.raw_name
            LIMIT 20
        """), {"county": county, "sid": store_id}).fetchall()

        if unique_products:
            insights.append({
                "type": "unique",
                "priority": "positive",
                "title": f"{len(unique_products)}+ exclusive products no local competitor carries",
                "detail": "These products give you a competitive advantage - promote them!",
                "data": unique_products
            })

    return insights


@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_category_comparison(store_id: str, competitor_id: str):
    """Compare category mix between stores."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            WITH my_cats AS (
                SELECT raw_category, COUNT(*) as cnt
                FROM raw_menu_item WHERE dispensary_id = :my_store
                GROUP BY raw_category
            ),
            comp_cats AS (
                SELECT raw_category, COUNT(*) as cnt
                FROM raw_menu_item WHERE dispensary_id = :comp_store
                GROUP BY raw_category
            )
            SELECT
                COALESCE(m.raw_category, c.raw_category) as category,
                COALESCE(m.cnt, 0) as my_count,
                COALESCE(c.cnt, 0) as comp_count
            FROM my_cats m
            FULL OUTER JOIN comp_cats c ON m.raw_category = c.raw_category
            ORDER BY COALESCE(m.cnt, 0) + COALESCE(c.cnt, 0) DESC
        """), {"my_store": store_id, "comp_store": competitor_id}).fetchall()

        return result


# Store selector
dispensaries = get_dispensaries()
if not dispensaries:
    st.warning("No dispensary data available")
    st.stop()

store_options = {name: id for id, name in dispensaries}
selected_store_name = st.selectbox("Select Your Store", list(store_options.keys()))
selected_store_id = store_options[selected_store_name]

if selected_store_id:
    metrics = get_store_metrics(selected_store_id)

    # Key Metrics
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Products", metrics["products"])
    with col2:
        st.metric("Brands", metrics["brands"])
    with col3:
        st.metric("Avg Price", f"${metrics['avg_price']:.2f}" if metrics["avg_price"] else "N/A")
    with col4:
        st.metric("Categories", metrics["categories"])

    # INSIGHTS SECTION
    st.markdown("---")
    st.subheader("Actionable Insights")

    insights = get_retail_insights(selected_store_id)

    if insights:
        for insight in insights:
            # Choose icon based on priority
            if insight['priority'] == 'high':
                icon = '🔴'
            elif insight['priority'] == 'positive':
                icon = '🟢'
            else:
                icon = '🟡'

            with st.expander(f"{icon} {insight['title']}", expanded=True):
                st.caption(insight["detail"])

                if insight["type"] == "assortment":
                    df = pd.DataFrame(insight["data"], columns=["Brand", "Product", "Competitors Carrying"])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    st.markdown("**Action:** Consider adding these popular products to your menu")

                elif insight["type"] == "pricing_high":
                    df = pd.DataFrame(insight["data"], columns=["Brand", "Product", "Size", "Your Price", "Market Avg", "Difference"])
                    df["Your Price"] = df["Your Price"].apply(lambda x: f"${x:.2f}")
                    df["Market Avg"] = df["Market Avg"].apply(lambda x: f"${x:.2f}")
                    df["Difference"] = df["Difference"].apply(lambda x: f"+${x:.2f}")
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    st.markdown("**Action:** Review pricing on these items to stay competitive")

                elif insight["type"] == "brands":
                    df = pd.DataFrame(insight["data"], columns=["Brand", "Competitor Stores", "Products Available"])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    st.markdown("**Action:** Reach out to these brands for distribution")

                elif insight["type"] == "unique":
                    df = pd.DataFrame(insight["data"], columns=["Brand", "Product", "Category", "Price"])
                    df["Price"] = df["Price"].apply(lambda x: f"${x:.2f}" if x else "N/A")
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    st.markdown("**Action:** Highlight these exclusive products in marketing and promotions")
    else:
        st.success("Your store looks well-positioned in the market!")

    # Competitor selection
    st.markdown("---")
    st.subheader("Detailed Competitive Analysis")

    competitors = get_nearby_competitors(selected_store_id)

    if competitors:
        # Build options with city for clarity
        comp_options = {}
        comp_display_names = {}
        for row in competitors:
            disp_id, name, city, products = row
            display_name = f"{name} ({city})" if city else name
            comp_options[display_name] = disp_id
            comp_display_names[disp_id] = display_name

        selected_comp_name = st.selectbox("Compare with Competitor", list(comp_options.keys()))
        selected_comp_id = comp_options[selected_comp_name]

        # Show clear comparison header
        st.markdown(f"**Comparing:** {selected_store_name} **vs** {selected_comp_name}")

        # Tabs for analysis
        tab1, tab2, tab3 = st.tabs(["Price Comparison", "Assortment Gaps", "Category Mix"])

        with tab1:
            st.subheader(f"Price Comparison vs {selected_comp_name}")
            st.caption("Products you both carry - see where you're higher or lower")

            pricing = compare_pricing(selected_store_id, selected_comp_id)

            if pricing:
                # Use competitor name in column header
                comp_col_name = selected_comp_name.split(" (")[0]  # Just store name for column
                df = pd.DataFrame(pricing, columns=["Brand", "Product", "Size", "Category", "Your Price", f"{comp_col_name} Price", "Difference"])

                # Summary stats
                col1, col2, col3 = st.columns(3)
                with col1:
                    higher = len(df[df["Difference"] > 0])
                    st.metric("You're Higher", f"{higher} products")
                with col2:
                    lower = len(df[df["Difference"] < 0])
                    st.metric("You're Lower", f"{lower} products")
                with col3:
                    avg_diff = df["Difference"].mean()
                    st.metric("Avg Difference", f"${avg_diff:+.2f}")

                st.markdown("---")

                # Filter
                show_filter = st.radio("Show", ["All", "You're Higher", "You're Lower"], horizontal=True)

                if show_filter == "You're Higher":
                    df = df[df["Difference"] > 0]
                elif show_filter == "You're Lower":
                    df = df[df["Difference"] < 0]

                st.dataframe(
                    df.style.applymap(
                        lambda x: "color: red" if isinstance(x, (int, float)) and x > 0
                        else "color: green" if isinstance(x, (int, float)) and x < 0
                        else "",
                        subset=["Difference"]
                    ),
                    use_container_width=True,
                    hide_index=True,
                    height=400
                )
            else:
                st.info("No overlapping products found")

        with tab2:
            st.subheader(f"Assortment Gaps vs {selected_comp_name}")
            st.caption(f"Products that {selected_comp_name} carries that you don't")

            gaps = find_assortment_gaps(selected_store_id, selected_comp_id)

            if gaps:
                df = pd.DataFrame(gaps, columns=["Brand", "Product", "Category", "Price"])
                st.metric("Products You're Missing", len(df))

                # Group by brand
                brand_filter = st.selectbox("Filter by Brand", ["All"] + sorted(df["Brand"].unique().tolist()))

                if brand_filter != "All":
                    df = df[df["Brand"] == brand_filter]

                st.dataframe(df, use_container_width=True, hide_index=True, height=400)
            else:
                st.success("No assortment gaps found!")

        with tab3:
            st.subheader(f"Category Mix: You vs {selected_comp_name}")

            cat_data = get_category_comparison(selected_store_id, selected_comp_id)

            if cat_data:
                comp_col_name = selected_comp_name.split(" (")[0]  # Just store name for column
                df = pd.DataFrame(cat_data, columns=["Category", "Your Products", comp_col_name])
                df["Difference"] = df["Your Products"] - df[comp_col_name]

                # Horizontal bar chart comparison
                st.bar_chart(
                    df.set_index("Category")[["Your Products", comp_col_name]],
                    horizontal=True
                )

                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No category data available")
    else:
        st.info("No competitors found in your county")

# Value proposition
st.markdown("---")
st.markdown("""
**What Retail Intelligence Helps You Do:**

| Use Case | Benefit |
|----------|---------|
| **Price Positioning** | Know if you're priced too high or leaving money on table |
| **Assortment Gaps** | Find popular products you're missing |
| **Category Optimization** | Balance your product mix vs competition |
| **Competitive Response** | React quickly to competitor changes |
""")
