# app/pages/10_Brand_Intelligence.py
"""Brand Intelligence Dashboard - Premium layout for brand customers."""

import streamlit as st
import pandas as pd
import re
from collections import defaultdict
from sqlalchemy import text
from components.nav import render_nav, get_section_from_params
from core.db import get_engine

st.set_page_config(page_title="Brand Intelligence - CannLinx", layout="wide")
render_nav()

# Handle section parameter for tab navigation
section = get_section_from_params()
TAB_MAP = {"insights": 0, "distribution": 1, "coverage": 2}
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

# Custom CSS for premium layout
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
        border-radius: 8px;
        padding: 1rem 1.25rem;
        color: white;
        text-align: center;
    }
    .metric-card .value {font-size: 1.8rem; font-weight: 700; margin: 0;}
    .metric-card .label {font-size: 0.75rem; opacity: 0.9; margin: 0; text-transform: uppercase;}
    .metric-card .subtext {font-size: 0.7rem; opacity: 0.7; margin-top: 0.25rem;}

    .insight-card {
        background: #fff;
        border: 1px solid #e9ecef;
        border-left: 4px solid #dc3545;
        border-radius: 4px;
        padding: 1rem;
        margin-bottom: 0.75rem;
    }
    .insight-card.opportunity {border-left-color: #28a745;}
    .insight-card.warning {border-left-color: #ffc107;}
    .insight-card h4 {margin: 0 0 0.5rem 0; font-size: 1rem; color: #1e3a5f;}
    .insight-card p {margin: 0; font-size: 0.85rem; color: #6c757d;}

    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1e3a5f;
        margin: 1.5rem 0 0.75rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #e9ecef;
    }

    .chart-description {
        font-size: 0.8rem;
        color: #6c757d;
        font-style: italic;
        margin-bottom: 0.5rem;
    }

    .competitive-highlight {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .competitive-highlight .big-number {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1e3a5f;
    }
    .competitive-highlight .vs-number {
        font-size: 1.5rem;
        font-weight: 600;
        color: #6c757d;
    }
</style>
""", unsafe_allow_html=True)


def extract_size_from_name(name: str) -> str:
    """Extract size/weight from product name."""
    if not name:
        return "unknown"
    name_lower = name.lower()

    match = re.search(r'(\d+\.?\d*)\s*(g|gram|grams|gm|grm)\b', name_lower)
    if match:
        return f"{match.group(1)}g"
    match = re.search(r'(\d+)\s*mg\b', name_lower)
    if match:
        return f"{match.group(1)}mg"
    match = re.search(r'\[(\d+\.?\d*)\s*(g|mg)\]', name_lower)
    if match:
        return f"{match.group(1)}{match.group(2)}"
    if re.search(r'\b(1/8|eighth)\b', name_lower):
        return "3.5g"
    if re.search(r'\b(1/4|quarter)\b', name_lower):
        return "7g"
    match = re.search(r'(\d+)\s*(pk|pack|ct)\b', name_lower)
    if match:
        return f"{match.group(1)}pk"
    return "unknown"


@st.cache_data(ttl=300)
def get_brands():
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT UPPER(raw_brand) as brand, COUNT(*) as cnt
            FROM raw_menu_item
            WHERE raw_brand IS NOT NULL AND raw_brand <> ''
            GROUP BY UPPER(raw_brand)
            HAVING COUNT(*) >= 5
            ORDER BY cnt DESC
        """))
        return [row[0] for row in result]


@st.cache_data(ttl=300)
def get_categories_for_brand(brand: str):
    """Get list of categories for a brand."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT DISTINCT raw_category
            FROM raw_menu_item
            WHERE UPPER(raw_brand) = :brand AND raw_category IS NOT NULL
            ORDER BY raw_category
        """), {"brand": brand})
        return [row[0] for row in result]


@st.cache_data(ttl=300)
def get_brand_metrics(brand: str, category: str = None):
    engine = get_engine()
    with engine.connect() as conn:
        params = {"brand": brand}
        cat_filter = ""
        if category:
            cat_filter = "AND raw_category = :category"
            params["category"] = category

        # Stores with data
        total_stores_with_data = conn.execute(text("""
            SELECT COUNT(DISTINCT dispensary_id) FROM raw_menu_item
        """)).scalar() or 1

        stores_carrying = conn.execute(text(f"""
            SELECT COUNT(DISTINCT r.dispensary_id)
            FROM raw_menu_item r
            WHERE UPPER(r.raw_brand) = :brand {cat_filter}
        """), params).scalar() or 0

        sku_count = conn.execute(text(f"""
            SELECT COUNT(DISTINCT raw_name)
            FROM raw_menu_item WHERE UPPER(raw_brand) = :brand {cat_filter}
        """), params).scalar() or 0

        price_stats = conn.execute(text(f"""
            SELECT MIN(raw_price), MAX(raw_price), AVG(raw_price), SUM(raw_price)
            FROM raw_menu_item
            WHERE UPPER(raw_brand) = :brand AND raw_price > 0 AND raw_price < 500 {cat_filter}
        """), params).fetchone()

        # Total retail value (sum of all prices = proxy for market presence)
        total_retail = price_stats[3] if price_stats[3] else 0
        # Estimated wholesale (50% keystone)
        estimated_wholesale = total_retail * 0.5

        return {
            "stores_carrying": stores_carrying,
            "total_stores": total_stores_with_data,
            "coverage_pct": round(stores_carrying / total_stores_with_data * 100, 1),
            "sku_count": sku_count,
            "min_price": price_stats[0] if price_stats else 0,
            "max_price": price_stats[1] if price_stats else 0,
            "avg_price": price_stats[2] if price_stats else 0,
            "total_retail": total_retail,
            "estimated_wholesale": estimated_wholesale,
        }


@st.cache_data(ttl=300)
def get_competitive_comparison(brand: str):
    """Compare brand's distribution to similar brands in same categories."""
    engine = get_engine()
    with engine.connect() as conn:
        # Get brand's main categories
        categories = conn.execute(text("""
            SELECT raw_category, COUNT(*) as cnt
            FROM raw_menu_item WHERE UPPER(raw_brand) = :brand
            GROUP BY raw_category ORDER BY cnt DESC LIMIT 3
        """), {"brand": brand}).fetchall()

        if not categories:
            return None

        main_cats = [c[0] for c in categories if c[0]]
        if not main_cats:
            return None

        # Get competitor brands in same categories
        competitors = conn.execute(text("""
            SELECT UPPER(raw_brand) as brand, COUNT(DISTINCT dispensary_id) as stores
            FROM raw_menu_item
            WHERE raw_category = ANY(:cats)
              AND raw_brand IS NOT NULL
              AND UPPER(raw_brand) <> :brand
            GROUP BY UPPER(raw_brand)
            HAVING COUNT(DISTINCT dispensary_id) >= 5
            ORDER BY stores DESC
            LIMIT 10
        """), {"cats": main_cats, "brand": brand}).fetchall()

        if competitors:
            avg_competitor_stores = sum(c[1] for c in competitors) / len(competitors)
            top_competitor_stores = competitors[0][1] if competitors else 0
            return {
                "avg_competitor_coverage": avg_competitor_stores,
                "top_competitor": competitors[0][0] if competitors else None,
                "top_competitor_stores": top_competitor_stores,
                "competitors": competitors[:5]
            }
        return None


@st.cache_data(ttl=300)
def get_distribution_gaps(brand: str, category: str = None):
    """Get stores with data that don't carry the brand (optionally in a category)."""
    engine = get_engine()
    with engine.connect() as conn:
        params = {"brand": brand}
        cat_filter = ""
        if category:
            cat_filter = "AND raw_category = :category"
            params["category"] = category

        result = conn.execute(text(f"""
            WITH stores_with_data AS (
                SELECT DISTINCT dispensary_id FROM raw_menu_item
            )
            SELECT d.name, d.city, d.county
            FROM dispensary d
            JOIN stores_with_data swd ON d.dispensary_id = swd.dispensary_id
            WHERE d.is_active = true
              AND d.dispensary_id NOT IN (
                  SELECT DISTINCT dispensary_id FROM raw_menu_item
                  WHERE UPPER(raw_brand) = :brand {cat_filter}
              )
            ORDER BY d.county, d.name
        """), params).fetchall()
        return result


@st.cache_data(ttl=300)
def get_county_coverage(brand: str, category: str = None):
    """Get coverage by county."""
    engine = get_engine()
    with engine.connect() as conn:
        params = {"brand": brand}
        cat_filter = ""
        if category:
            cat_filter = "AND r.raw_category = :category"
            params["category"] = category

        result = conn.execute(text(f"""
            WITH stores_with_data AS (
                SELECT DISTINCT r.dispensary_id, d.county
                FROM raw_menu_item r
                JOIN dispensary d ON r.dispensary_id = d.dispensary_id
                WHERE d.county IS NOT NULL
            ),
            brand_stores AS (
                SELECT DISTINCT r.dispensary_id, d.county
                FROM raw_menu_item r
                JOIN dispensary d ON r.dispensary_id = d.dispensary_id
                WHERE UPPER(r.raw_brand) = :brand AND d.county IS NOT NULL {cat_filter}
            )
            SELECT
                swd.county,
                COUNT(DISTINCT swd.dispensary_id) as total_stores,
                COUNT(DISTINCT bs.dispensary_id) as carrying
            FROM stores_with_data swd
            LEFT JOIN brand_stores bs ON swd.dispensary_id = bs.dispensary_id
            GROUP BY swd.county
            ORDER BY total_stores DESC
        """), params).fetchall()
        return result


@st.cache_data(ttl=300)
def get_pricing_issues(brand: str, category: str = None):
    """Get products with pricing variance (same size only)."""
    engine = get_engine()
    with engine.connect() as conn:
        params = {"brand": brand}
        cat_filter = ""
        if category:
            cat_filter = "AND raw_category = :category"
            params["category"] = category

        all_products = conn.execute(text(f"""
            SELECT raw_name, raw_price
            FROM raw_menu_item
            WHERE UPPER(raw_brand) = :brand AND raw_price > 0 AND raw_price < 500 {cat_filter}
        """), params).fetchall()

        price_by_product_size = defaultdict(list)
        for name, price in all_products:
            size = extract_size_from_name(name)
            base_name = re.sub(r'\s*[-|]?\s*\d+\.?\d*\s*(g|gram|grams|gm|grm|mg|oz)\b', '', name, flags=re.IGNORECASE)
            base_name = re.sub(r'\s*\[\d+\.?\d*\s*(g|mg)\]', '', base_name)
            base_name = base_name.strip()
            key = (base_name, size)
            price_by_product_size[key].append(price)

        issues = []
        for (base_name, size), prices in price_by_product_size.items():
            if len(prices) >= 2 and size != "unknown":
                spread = max(prices) - min(prices)
                if spread > 5:
                    issues.append({
                        "product": f"{base_name} ({size})",
                        "min": min(prices),
                        "max": max(prices),
                        "spread": spread
                    })

        issues.sort(key=lambda x: -x["spread"])
        return issues[:10]


# Page Header
st.title("Brand Intelligence")

# Brand selector
brands = get_brands()
if not brands:
    st.warning("No brand data available")
    st.stop()

col_brand, col_cat = st.columns([2, 1])
with col_brand:
    selected_brand = st.selectbox("Select Your Brand", brands, index=0)

# Get categories for selected brand
categories = get_categories_for_brand(selected_brand) if selected_brand else []
with col_cat:
    cat_options = ["All Categories"] + categories
    selected_cat_display = st.selectbox("Filter by Category", cat_options, index=0)
    selected_category = None if selected_cat_display == "All Categories" else selected_cat_display

if selected_brand:
    metrics = get_brand_metrics(selected_brand, selected_category)
    competitive = get_competitive_comparison(selected_brand)

    # Show active filter
    if selected_category:
        st.info(f"📁 Filtered by category: **{selected_category}**")

    # Key Metrics - Premium Cards
    st.markdown("---")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <p class="value">{metrics['stores_carrying']}</p>
            <p class="label">Stores Carrying</p>
            <p class="subtext">of {metrics['total_stores']} tracked</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <p class="value">{metrics['coverage_pct']}%</p>
            <p class="label">Market Coverage</p>
            <p class="subtext">of stores with data</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <p class="value">{metrics['sku_count']}</p>
            <p class="label">Active SKUs</p>
            <p class="subtext">unique products</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        avg_price = metrics['avg_price'] or 0
        min_price = metrics['min_price'] or 0
        max_price = metrics['max_price'] or 0
        st.markdown(f"""
        <div class="metric-card">
            <p class="value">${avg_price:.0f}</p>
            <p class="label">Avg Retail Price</p>
            <p class="subtext">${min_price:.0f} - ${max_price:.0f} range</p>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        wholesale_val = metrics['estimated_wholesale'] or 0
        if wholesale_val >= 1000:
            wholesale_display = f"${wholesale_val/1000:.1f}K"
        else:
            wholesale_display = f"${wholesale_val:.0f}"
        st.markdown(f"""
        <div class="metric-card">
            <p class="value">{wholesale_display}</p>
            <p class="label">Est. Wholesale Value</p>
            <p class="subtext">50% of retail listings</p>
        </div>
        """, unsafe_allow_html=True)

    # Competitive Comparison Highlight
    if competitive:
        st.markdown("---")
        col1, col2 = st.columns([2, 1])

        with col1:
            gap = competitive['avg_competitor_coverage'] - metrics['stores_carrying']
            gap_pct = (gap / max(metrics['stores_carrying'], 1)) * 100

            if gap > 0:
                st.markdown(f"""
                <div class="competitive-highlight">
                    <p style="margin:0; color:#6c757d; font-size:0.85rem;">COMPETITIVE GAP ANALYSIS</p>
                    <p style="margin:0.5rem 0;">
                        <span class="big-number">{metrics['stores_carrying']}</span>
                        <span style="color:#6c757d; font-size:1rem;"> stores carry your products</span>
                    </p>
                    <p style="margin:0;">
                        <span class="vs-number">{competitive['avg_competitor_coverage']:.0f}</span>
                        <span style="color:#6c757d;"> avg stores for competitors in your categories</span>
                    </p>
                    <p style="margin-top:0.75rem; color:#dc3545; font-weight:600;">
                        You're missing ~{gap:.0f} potential stores ({gap_pct:.0f}% opportunity)
                    </p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="competitive-highlight">
                    <p style="margin:0; color:#6c757d; font-size:0.85rem;">COMPETITIVE POSITION</p>
                    <p style="margin:0.5rem 0;">
                        <span class="big-number">{metrics['stores_carrying']}</span>
                        <span style="color:#6c757d; font-size:1rem;"> stores carry your products</span>
                    </p>
                    <p style="margin-top:0.75rem; color:#28a745; font-weight:600;">
                        You're ahead of the average competitor ({competitive['avg_competitor_coverage']:.0f} stores)
                    </p>
                </div>
                """, unsafe_allow_html=True)

        with col2:
            st.markdown("**Top Competitors**")
            for comp in competitive['competitors'][:5]:
                pct = (comp[1] / metrics['total_stores']) * 100
                st.caption(f"{comp[0]}: {comp[1]} stores ({pct:.0f}%)")

    # Tabs for detailed analysis
    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["Actionable Insights", "Store Distribution", "County Coverage"])

    with tab1:
        st.markdown('<p class="section-header">Actionable Insights</p>', unsafe_allow_html=True)

        # Distribution Gaps
        gaps = get_distribution_gaps(selected_brand, selected_category)
        if gaps:
            st.markdown(f"""
            <div class="insight-card">
                <h4>🎯 {len(gaps)} Stores Don't Carry Your Products</h4>
                <p>These stores have menu data but don't stock your brand. Priority sales targets.</p>
            </div>
            """, unsafe_allow_html=True)

            with st.expander(f"View {len(gaps)} target stores"):
                df = pd.DataFrame(gaps, columns=["Store", "City", "County"])
                st.dataframe(df, use_container_width=True, hide_index=True, height=300)

        # Pricing Issues
        pricing_issues = get_pricing_issues(selected_brand, selected_category)
        if pricing_issues:
            st.markdown(f"""
            <div class="insight-card warning">
                <h4>💰 {len(pricing_issues)} Products with Price Variance</h4>
                <p>Same-size products priced differently across stores. May indicate MAP violations.</p>
            </div>
            """, unsafe_allow_html=True)

            with st.expander(f"View {len(pricing_issues)} pricing issues"):
                df = pd.DataFrame(pricing_issues)
                df.columns = ["Product (Size)", "Min Price", "Max Price", "Spread"]
                df["Min Price"] = df["Min Price"].apply(lambda x: f"${x:.2f}")
                df["Max Price"] = df["Max Price"].apply(lambda x: f"${x:.2f}")
                df["Spread"] = df["Spread"].apply(lambda x: f"${x:.2f}")
                st.dataframe(df, use_container_width=True, hide_index=True)

        # No critical issues
        if not gaps and not pricing_issues:
            st.markdown("""
            <div class="insight-card opportunity">
                <h4>✅ No Critical Issues Found</h4>
                <p>Your brand has strong distribution and consistent pricing across the market.</p>
            </div>
            """, unsafe_allow_html=True)

    with tab2:
        st.markdown('<p class="section-header">Store Distribution</p>', unsafe_allow_html=True)
        st.markdown('<p class="chart-description">Stores currently stocking your products vs. stores that could be carrying them.</p>', unsafe_allow_html=True)

        # Get carrying/not carrying
        engine = get_engine()
        with engine.connect() as conn:
            carrying = conn.execute(text("""
                SELECT d.name, d.city, d.county, COUNT(DISTINCT r.raw_name) as products
                FROM dispensary d
                JOIN raw_menu_item r ON d.dispensary_id = r.dispensary_id
                WHERE UPPER(r.raw_brand) = :brand AND d.is_active = true
                GROUP BY d.dispensary_id, d.name, d.city, d.county
                ORDER BY products DESC
            """), {"brand": selected_brand}).fetchall()

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**Currently Carrying ({len(carrying)} stores)**")
            if carrying:
                df = pd.DataFrame(carrying, columns=["Store", "City", "County", "Products"])
                st.dataframe(df, use_container_width=True, hide_index=True, height=350)

        with col2:
            st.markdown(f"**Not Carrying - Sales Targets ({len(gaps)} stores)**")
            if gaps:
                df = pd.DataFrame(gaps, columns=["Store", "City", "County"])
                st.dataframe(df, use_container_width=True, hide_index=True, height=350)

    with tab3:
        st.markdown('<p class="section-header">Coverage by County</p>', unsafe_allow_html=True)
        st.markdown('<p class="chart-description">Shows what percentage of stores in each county carry your products. Low percentages indicate expansion opportunities.</p>', unsafe_allow_html=True)

        county_data = get_county_coverage(selected_brand, selected_category)

        if county_data:
            df = pd.DataFrame(county_data, columns=["County", "Total Stores", "Carrying"])
            df["Not Carrying"] = df["Total Stores"] - df["Carrying"]
            df["Coverage %"] = (df["Carrying"] / df["Total Stores"] * 100).round(0).astype(int)
            df["Gap"] = df["Total Stores"] - df["Carrying"]

            # Sort by gap (biggest opportunities first)
            df = df.sort_values("Gap", ascending=False)

            col1, col2 = st.columns([1, 1])

            with col1:
                st.markdown("**Coverage Table** - Sorted by opportunity size")
                display_df = df[["County", "Carrying", "Total Stores", "Coverage %", "Gap"]].copy()
                display_df["Coverage %"] = display_df["Coverage %"].apply(lambda x: f"{x}%")
                st.dataframe(display_df, use_container_width=True, hide_index=True, height=350)

            with col2:
                st.markdown("**Coverage by County** - Higher % = better penetration")
                # Create horizontal bar chart data
                chart_df = df[["County", "Coverage %"]].set_index("County").head(15)
                st.bar_chart(chart_df, horizontal=True, height=350)

    # Value Proposition Footer
    st.markdown("---")
    st.markdown("""
    **Ready to grow your distribution?** CannLinx provides daily updates on:
    - Real-time store coverage tracking
    - Competitive intelligence alerts
    - Pricing compliance monitoring
    - Custom sales target lists

    [Contact us](mailto:support@cannlinx.com) for a demo.
    """)
