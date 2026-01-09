# app/pages/10_Brand_Intelligence.py
"""Brand Intelligence Dashboard - Premium layout for brand customers."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
from collections import defaultdict
from sqlalchemy import text
from components.nav import render_nav, get_section_from_params, render_state_filter, get_selected_state
from components.auth import is_authenticated
from core.db import get_engine

st.set_page_config(page_title="Brand Intelligence - CannLinx", layout="wide")
render_nav(require_login=False)  # Allow demo access

# Check if user is authenticated for real data vs demo
DEMO_MODE = not is_authenticated()

# Handle section parameter for tab navigation
section = get_section_from_params()
TAB_MAP = {"insights": 0, "distribution": 1, "coverage": 2, "competitors": 3, "roles": 4}
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


@st.cache_data(ttl=3600)  # Cache for 1 hour - brand list rarely changes
def get_brands(state: str = "MD"):
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT UPPER(r.raw_brand) as brand, COUNT(*) as cnt
            FROM raw_menu_item r
            JOIN dispensary d ON r.dispensary_id = d.dispensary_id
            WHERE r.raw_brand IS NOT NULL AND r.raw_brand <> ''
              AND d.state = :state
            GROUP BY UPPER(r.raw_brand)
            HAVING COUNT(*) >= 5
            ORDER BY cnt DESC
        """), {"state": state})
        return [row[0] for row in result]


@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_categories_for_brand(brand: str, state: str = "MD"):
    """Get list of categories for a brand in a state."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT DISTINCT r.raw_category
            FROM raw_menu_item r
            JOIN dispensary d ON r.dispensary_id = d.dispensary_id
            WHERE UPPER(r.raw_brand) = :brand AND r.raw_category IS NOT NULL
              AND d.state = :state
            ORDER BY r.raw_category
        """), {"brand": brand, "state": state})
        return [row[0] for row in result]


@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_brand_metrics(brand: str, category: str = None, state: str = "MD"):
    """Get all brand metrics in a single optimized query."""
    engine = get_engine()
    with engine.connect() as conn:
        params = {"brand": brand, "state": state}
        cat_filter = ""
        if category:
            cat_filter = "AND r.raw_category = :category"
            params["category"] = category

        # Combined query to get all metrics in one database round-trip
        result = conn.execute(text(f"""
            WITH total_stores AS (
                SELECT COUNT(DISTINCT r.dispensary_id) as cnt
                FROM raw_menu_item r
                JOIN dispensary d ON r.dispensary_id = d.dispensary_id
                WHERE d.state = :state
            ),
            brand_data AS (
                SELECT
                    COUNT(DISTINCT r.dispensary_id) as stores_carrying,
                    COUNT(DISTINCT r.raw_name) as sku_count,
                    MIN(CASE WHEN r.raw_price > 0 AND r.raw_price < 500 THEN r.raw_price END) as min_price,
                    MAX(CASE WHEN r.raw_price > 0 AND r.raw_price < 500 THEN r.raw_price END) as max_price,
                    AVG(CASE WHEN r.raw_price > 0 AND r.raw_price < 500 THEN r.raw_price END) as avg_price,
                    SUM(CASE WHEN r.raw_price > 0 AND r.raw_price < 500 THEN r.raw_price ELSE 0 END) as total_retail
                FROM raw_menu_item r
                JOIN dispensary d ON r.dispensary_id = d.dispensary_id
                WHERE UPPER(r.raw_brand) = :brand AND d.state = :state {cat_filter}
            )
            SELECT
                ts.cnt as total_stores,
                bd.stores_carrying,
                bd.sku_count,
                bd.min_price,
                bd.max_price,
                bd.avg_price,
                bd.total_retail
            FROM total_stores ts, brand_data bd
        """), params).fetchone()

        total_stores = result[0] or 1
        stores_carrying = result[1] or 0
        total_retail = result[6] or 0

        return {
            "stores_carrying": stores_carrying,
            "total_stores": total_stores,
            "coverage_pct": round(stores_carrying / total_stores * 100, 1),
            "sku_count": result[2] or 0,
            "min_price": result[3] or 0,
            "max_price": result[4] or 0,
            "avg_price": result[5] or 0,
            "total_retail": total_retail,
            "estimated_wholesale": total_retail * 0.5,
        }


@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_competitive_comparison(brand: str, state: str = "MD"):
    """Compare brand's distribution to similar brands in same categories."""
    engine = get_engine()
    with engine.connect() as conn:
        # Get brand's main categories
        categories = conn.execute(text("""
            SELECT r.raw_category, COUNT(*) as cnt
            FROM raw_menu_item r
            JOIN dispensary d ON r.dispensary_id = d.dispensary_id
            WHERE UPPER(r.raw_brand) = :brand AND d.state = :state
            GROUP BY r.raw_category ORDER BY cnt DESC LIMIT 3
        """), {"brand": brand, "state": state}).fetchall()

        if not categories:
            return None

        main_cats = [c[0] for c in categories if c[0]]
        if not main_cats:
            return None

        # Get competitor brands in same categories
        competitors = conn.execute(text("""
            SELECT UPPER(r.raw_brand) as brand, COUNT(DISTINCT r.dispensary_id) as stores
            FROM raw_menu_item r
            JOIN dispensary d ON r.dispensary_id = d.dispensary_id
            WHERE r.raw_category = ANY(:cats)
              AND r.raw_brand IS NOT NULL
              AND UPPER(r.raw_brand) <> :brand
              AND d.state = :state
            GROUP BY UPPER(r.raw_brand)
            HAVING COUNT(DISTINCT r.dispensary_id) >= 5
            ORDER BY stores DESC
            LIMIT 10
        """), {"cats": main_cats, "brand": brand, "state": state}).fetchall()

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


@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_distribution_gaps(brand: str, category: str = None, state: str = "MD"):
    """Get stores with data that don't carry the brand (optionally in a category)."""
    engine = get_engine()
    with engine.connect() as conn:
        params = {"brand": brand, "state": state}
        cat_filter = ""
        if category:
            cat_filter = "AND r.raw_category = :category"
            params["category"] = category

        result = conn.execute(text(f"""
            WITH stores_with_data AS (
                SELECT DISTINCT r.dispensary_id
                FROM raw_menu_item r
                JOIN dispensary d ON r.dispensary_id = d.dispensary_id
                WHERE d.state = :state
            )
            SELECT d.name, d.city, d.county
            FROM dispensary d
            JOIN stores_with_data swd ON d.dispensary_id = swd.dispensary_id
            WHERE d.is_active = true AND d.state = :state
              AND d.dispensary_id NOT IN (
                  SELECT DISTINCT r.dispensary_id
                  FROM raw_menu_item r
                  JOIN dispensary d2 ON r.dispensary_id = d2.dispensary_id
                  WHERE UPPER(r.raw_brand) = :brand AND d2.state = :state {cat_filter}
              )
            ORDER BY d.county, d.name
        """), params).fetchall()
        return result


@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_county_coverage(brand: str, category: str = None, state: str = "MD"):
    """Get coverage by county."""
    engine = get_engine()
    with engine.connect() as conn:
        params = {"brand": brand, "state": state}
        cat_filter = ""
        if category:
            cat_filter = "AND r.raw_category = :category"
            params["category"] = category

        result = conn.execute(text(f"""
            WITH stores_with_data AS (
                SELECT DISTINCT r.dispensary_id, d.county
                FROM raw_menu_item r
                JOIN dispensary d ON r.dispensary_id = d.dispensary_id
                WHERE d.county IS NOT NULL AND d.state = :state
            ),
            brand_stores AS (
                SELECT DISTINCT r.dispensary_id, d.county
                FROM raw_menu_item r
                JOIN dispensary d ON r.dispensary_id = d.dispensary_id
                WHERE UPPER(r.raw_brand) = :brand AND d.county IS NOT NULL AND d.state = :state {cat_filter}
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


@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_pricing_issues(brand: str, category: str = None, state: str = "MD"):
    """Get products with pricing variance (same size only)."""
    engine = get_engine()
    with engine.connect() as conn:
        params = {"brand": brand, "state": state}
        cat_filter = ""
        if category:
            cat_filter = "AND r.raw_category = :category"
            params["category"] = category

        all_products = conn.execute(text(f"""
            SELECT r.raw_name, r.raw_price
            FROM raw_menu_item r
            JOIN dispensary d ON r.dispensary_id = d.dispensary_id
            WHERE UPPER(r.raw_brand) = :brand AND r.raw_price > 0 AND r.raw_price < 500
              AND d.state = :state {cat_filter}
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


# Demo data for unauthenticated users
def get_demo_data():
    """Return demo data to showcase features."""
    return {
        "brands": ["CURIO WELLNESS", "EVERMORE CANNABIS", "GRASSROOTS", "VERANO", "CULTA",
                   "STRANE", "RYTHM", "CRESCO", "SELECT", "KIVA CONFECTIONS"],
        "categories": ["Flower", "Vapes", "Concentrates", "Edibles", "Pre-Rolls"],
        "metrics": {
            "stores_carrying": 47,
            "total_stores": 96,
            "coverage_pct": 49.0,
            "sku_count": 128,
            "min_price": 25,
            "max_price": 65,
            "avg_price": 42,
            "total_retail": 5376,
            "estimated_wholesale": 2688
        },
        "competitive": {
            "avg_competitor_coverage": 52,
            "top_competitor": "EVERMORE CANNABIS",
            "top_competitor_stores": 61,
            "competitors": [
                ("EVERMORE CANNABIS", 61),
                ("GRASSROOTS", 58),
                ("VERANO", 55),
                ("CULTA", 51),
                ("STRANE", 48)
            ]
        },
        "gaps": [
            ("Green Health Docs", "Baltimore", "Baltimore City"),
            ("Remedy Columbia", "Columbia", "Howard"),
            ("Harvest of Rockville", "Rockville", "Montgomery"),
            ("The Living Room", "Ellicott City", "Howard"),
            ("Blair Wellness Center", "Silver Spring", "Montgomery"),
        ],
        "pricing_issues": [
            {"product": "Blue Dream (3.5g)", "min": 45.00, "max": 55.00, "spread": 10.00},
            {"product": "OG Kush (3.5g)", "min": 50.00, "max": 58.00, "spread": 8.00},
            {"product": "Sour Diesel (7g)", "min": 85.00, "max": 95.00, "spread": 10.00},
        ],
        "county_coverage": [
            ("Baltimore City", 18, 12),
            ("Montgomery", 14, 6),
            ("Howard", 8, 5),
            ("Anne Arundel", 10, 4),
            ("Prince George's", 7, 3),
            ("Baltimore County", 12, 8),
        ],
        # Enhanced data for charts
        "category_breakdown": {
            "Flower": 45,
            "Vapes": 28,
            "Concentrates": 12,
            "Edibles": 10,
            "Pre-Rolls": 5
        },
        "price_distribution": [
            {"range": "$0-20", "count": 8},
            {"range": "$20-35", "count": 24},
            {"range": "$35-50", "count": 52},
            {"range": "$50-65", "count": 32},
            {"range": "$65+", "count": 12}
        ],
        "market_share": {
            "CURIO WELLNESS": 12.4,
            "EVERMORE CANNABIS": 14.2,
            "GRASSROOTS": 11.8,
            "VERANO": 10.5,
            "CULTA": 9.2,
            "STRANE": 8.1,
            "Other": 33.8
        },
        "price_comparison": {
            "Your Avg": 42.00,
            "Category Avg": 45.50,
            "Market Leader": 48.00,
            "Market Low": 38.00
        },
        "weekly_velocity": [
            {"week": "Week 1", "stores": 42},
            {"week": "Week 2", "stores": 44},
            {"week": "Week 3", "stores": 43},
            {"week": "Week 4", "stores": 47}
        ],
        "store_trend": [
            {"month": "Aug", "stores": 38},
            {"month": "Sep", "stores": 41},
            {"month": "Oct", "stores": 44},
            {"month": "Nov", "stores": 45},
            {"month": "Dec", "stores": 47},
        ],
        "top_products": [
            {"product": "Blue Dream 3.5g", "stores": 42, "avg_price": 48.00},
            {"product": "OG Kush 3.5g", "stores": 38, "avg_price": 52.00},
            {"product": "Sour Diesel 3.5g", "stores": 35, "avg_price": 50.00},
            {"product": "Wedding Cake 3.5g", "stores": 32, "avg_price": 55.00},
            {"product": "Gelato 3.5g", "stores": 28, "avg_price": 54.00},
        ],
        "competitor_comparison": [
            {"brand": "CURIO WELLNESS", "stores": 47, "skus": 128, "avg_price": 42.00},
            {"brand": "EVERMORE", "stores": 61, "skus": 96, "avg_price": 48.00},
            {"brand": "GRASSROOTS", "stores": 58, "skus": 85, "avg_price": 46.00},
            {"brand": "VERANO", "stores": 55, "skus": 72, "avg_price": 50.00},
            {"brand": "CULTA", "stores": 51, "skus": 64, "avg_price": 55.00},
        ]
    }


@st.cache_data(ttl=600)
def get_category_breakdown(brand: str, state: str = "MD"):
    """Get product count by category for a brand."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT r.raw_category, COUNT(*) as cnt
            FROM raw_menu_item r
            JOIN dispensary d ON r.dispensary_id = d.dispensary_id
            WHERE UPPER(r.raw_brand) = :brand AND d.state = :state
              AND r.raw_category IS NOT NULL
            GROUP BY r.raw_category
            ORDER BY cnt DESC
        """), {"brand": brand, "state": state}).fetchall()
        return {row[0]: row[1] for row in result}


@st.cache_data(ttl=600)
def get_price_distribution(brand: str, state: str = "MD"):
    """Get price distribution for a brand."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                CASE
                    WHEN r.raw_price < 20 THEN '$0-20'
                    WHEN r.raw_price < 35 THEN '$20-35'
                    WHEN r.raw_price < 50 THEN '$35-50'
                    WHEN r.raw_price < 65 THEN '$50-65'
                    ELSE '$65+'
                END as price_range,
                COUNT(*) as cnt
            FROM raw_menu_item r
            JOIN dispensary d ON r.dispensary_id = d.dispensary_id
            WHERE UPPER(r.raw_brand) = :brand AND d.state = :state
              AND r.raw_price > 0 AND r.raw_price < 500
            GROUP BY price_range
            ORDER BY MIN(r.raw_price)
        """), {"brand": brand, "state": state}).fetchall()
        return [{"range": row[0], "count": row[1]} for row in result]


@st.cache_data(ttl=600)
def get_market_share(state: str = "MD", limit: int = 6):
    """Get market share by brand (based on SKU count across stores)."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            WITH brand_counts AS (
                SELECT UPPER(r.raw_brand) as brand, COUNT(*) as cnt
                FROM raw_menu_item r
                JOIN dispensary d ON r.dispensary_id = d.dispensary_id
                WHERE r.raw_brand IS NOT NULL AND d.state = :state
                GROUP BY UPPER(r.raw_brand)
            ),
            total AS (SELECT SUM(cnt) as total FROM brand_counts)
            SELECT bc.brand, ROUND(bc.cnt * 100.0 / t.total, 1) as pct
            FROM brand_counts bc, total t
            ORDER BY bc.cnt DESC
            LIMIT :limit
        """), {"state": state, "limit": limit}).fetchall()
        shares = {row[0]: float(row[1]) for row in result}
        other = 100 - sum(shares.values())
        if other > 0:
            shares["Other"] = round(other, 1)
        return shares


@st.cache_data(ttl=600)
def get_price_vs_category(brand: str, state: str = "MD"):
    """Get brand's average price vs category average."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            WITH brand_prices AS (
                SELECT AVG(r.raw_price) as brand_avg
                FROM raw_menu_item r
                JOIN dispensary d ON r.dispensary_id = d.dispensary_id
                WHERE UPPER(r.raw_brand) = :brand AND d.state = :state
                  AND r.raw_price > 0 AND r.raw_price < 500
            ),
            brand_categories AS (
                SELECT DISTINCT r.raw_category
                FROM raw_menu_item r
                JOIN dispensary d ON r.dispensary_id = d.dispensary_id
                WHERE UPPER(r.raw_brand) = :brand AND d.state = :state
            ),
            category_prices AS (
                SELECT AVG(r.raw_price) as cat_avg,
                       MAX(r.raw_price) as cat_high,
                       MIN(r.raw_price) as cat_low
                FROM raw_menu_item r
                JOIN dispensary d ON r.dispensary_id = d.dispensary_id
                WHERE r.raw_category IN (SELECT raw_category FROM brand_categories)
                  AND d.state = :state
                  AND r.raw_price > 0 AND r.raw_price < 500
            )
            SELECT bp.brand_avg, cp.cat_avg, cp.cat_high, cp.cat_low
            FROM brand_prices bp, category_prices cp
        """), {"brand": brand, "state": state}).fetchone()
        if result:
            return {
                "Your Avg": round(result[0] or 0, 2),
                "Category Avg": round(result[1] or 0, 2),
                "Market High": round(result[2] or 0, 2),
                "Market Low": round(result[3] or 0, 2)
            }
        return None


# Page Header
st.title("Brand Intelligence")

if DEMO_MODE:
    st.info("**Demo Mode** - Showing sample data. [Login](/Login) to access your brand's real data.")

# State and Brand selector row
col_state, col_brand, col_cat = st.columns([1, 2, 1])

if DEMO_MODE:
    # Demo mode - use sample data
    demo_data = get_demo_data()
    with col_state:
        st.selectbox("State", ["MD"], disabled=True)
        selected_state = "MD"

    with col_brand:
        selected_brand = st.selectbox("Select Your Brand", demo_data["brands"], index=0)

    with col_cat:
        cat_options = ["All Categories"] + demo_data["categories"]
        selected_cat_display = st.selectbox("Filter by Category", cat_options, index=0)
        selected_category = None if selected_cat_display == "All Categories" else selected_cat_display

    metrics = demo_data["metrics"]
    competitive = demo_data["competitive"]
    gaps = demo_data["gaps"]
    pricing_issues = demo_data["pricing_issues"]

else:
    # Real data mode
    with col_state:
        selected_state = render_state_filter()

    # Brand selector
    brands = get_brands(selected_state)
    if not brands:
        st.warning(f"No brand data available for {selected_state}")
        st.stop()

    with col_brand:
        selected_brand = st.selectbox("Select Your Brand", brands, index=0)

    # Get categories for selected brand
    categories = get_categories_for_brand(selected_brand, selected_state) if selected_brand else []
    with col_cat:
        cat_options = ["All Categories"] + categories
        selected_cat_display = st.selectbox("Filter by Category", cat_options, index=0)
        selected_category = None if selected_cat_display == "All Categories" else selected_cat_display

    metrics = get_brand_metrics(selected_brand, selected_category, selected_state)
    competitive = get_competitive_comparison(selected_brand, selected_state)
    gaps = get_distribution_gaps(selected_brand, selected_category, selected_state)
    pricing_issues = get_pricing_issues(selected_brand, selected_category, selected_state)

if selected_brand:
    # Show active filter
    if selected_category:
        st.info(f"Filtered by category: **{selected_category}**")

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

    # Load chart data
    if DEMO_MODE:
        category_data = demo_data.get("category_breakdown", {})
        price_dist = demo_data.get("price_distribution", [])
        market_share = demo_data.get("market_share", {})
        price_comparison = demo_data.get("price_comparison", {})
    else:
        category_data = get_category_breakdown(selected_brand, selected_state)
        price_dist = get_price_distribution(selected_brand, selected_state)
        market_share = get_market_share(selected_state)
        price_comparison = get_price_vs_category(selected_brand, selected_state)

    # Charts Section - Visual Analysis
    st.markdown("---")
    st.markdown('<p class="section-header">Market Analysis</p>', unsafe_allow_html=True)

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("**Your Product Mix by Category**")
        if category_data:
            cat_df = pd.DataFrame(list(category_data.items()), columns=["Category", "Products"])
            fig = px.pie(
                cat_df,
                values="Products",
                names="Category",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig.update_layout(height=280, margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No category data available")

    with chart_col2:
        st.markdown("**Market Share (All Brands)**")
        if market_share:
            share_df = pd.DataFrame(list(market_share.items()), columns=["Brand", "Share"])
            # Highlight your brand
            colors = ['#1e3a5f' if b == selected_brand else '#94a3b8' for b in share_df["Brand"]]
            fig = px.bar(
                share_df,
                x="Brand",
                y="Share",
                color="Brand",
                color_discrete_sequence=colors
            )
            fig.update_layout(
                height=280,
                showlegend=False,
                xaxis_tickangle=-45,
                margin=dict(t=20, b=60, l=40, r=20)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No market share data available")

    # Additional charts row
    chart_col3, chart_col4 = st.columns(2)

    with chart_col3:
        st.markdown("**Price Distribution**")
        if price_dist:
            price_df = pd.DataFrame(price_dist)
            fig = px.bar(
                price_df,
                x="range",
                y="count",
                color="count",
                color_continuous_scale="Blues",
                labels={"range": "Price Range", "count": "SKUs"}
            )
            fig.update_layout(height=280, showlegend=False, margin=dict(t=20, b=40, l=40, r=20))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No pricing data available")

    with chart_col4:
        # Store trend chart (demo mode only shows this nicely)
        if DEMO_MODE:
            st.markdown("**Store Distribution Trend**")
            trend_df = pd.DataFrame(demo_data.get("store_trend", []))
            if not trend_df.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=trend_df["month"],
                    y=trend_df["stores"],
                    mode='lines+markers',
                    line=dict(color='#1e3a5f', width=3),
                    marker=dict(size=10),
                    fill='tozeroy',
                    fillcolor='rgba(30, 58, 95, 0.1)'
                ))
                fig.update_layout(
                    height=280,
                    margin=dict(t=20, b=40, l=40, r=20),
                    xaxis_title="",
                    yaxis_title="Stores"
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown("**Top Products by Distribution**")
            # For real mode, could add top products query here
            st.info("Login for product-level analytics")

    # Price Positioning
    if price_comparison:
        st.markdown("---")
        st.markdown('<p class="section-header">Price Positioning</p>', unsafe_allow_html=True)

        price_cols = st.columns(4)
        price_labels = [
            ("Your Avg", "Your average price", "#1e3a5f"),
            ("Category Avg", "Category average", "#6c757d"),
            ("Market High", "Highest in category", "#dc3545"),
            ("Market Low", "Lowest in category", "#28a745")
        ]

        for i, (key, label, color) in enumerate(price_labels):
            if key in price_comparison:
                with price_cols[i]:
                    val = price_comparison[key]
                    st.markdown(f"""
                    <div style="text-align:center; padding:0.75rem; background:#f8f9fa; border-radius:6px;">
                        <p style="margin:0; font-size:1.5rem; font-weight:700; color:{color};">${val:.2f}</p>
                        <p style="margin:0; font-size:0.75rem; color:#6c757d;">{label}</p>
                    </div>
                    """, unsafe_allow_html=True)

        # Price insight
        your_avg = price_comparison.get("Your Avg", 0)
        cat_avg = price_comparison.get("Category Avg", 0)
        if your_avg and cat_avg:
            diff = ((your_avg - cat_avg) / cat_avg) * 100
            if diff < -5:
                st.success(f"Your products are priced **{abs(diff):.1f}% below** the category average - competitive positioning for value-conscious buyers.")
            elif diff > 5:
                st.warning(f"Your products are priced **{diff:.1f}% above** the category average - premium positioning that may limit distribution.")
            else:
                st.info(f"Your products are priced **at market** (within 5% of category average).")

    # Tabs for detailed analysis
    st.markdown("---")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Actionable Insights", "Store Distribution", "County Coverage", "Competitor Deep-Dive", "Role-Based Insights"])

    with tab1:
        st.markdown('<p class="section-header">Actionable Insights</p>', unsafe_allow_html=True)

        # Distribution Gaps - use pre-loaded data
        if gaps:
            st.markdown(f"""
            <div class="insight-card">
                <h4>{len(gaps)} Stores Don't Carry Your Products</h4>
                <p>These stores have menu data but don't stock your brand. Priority sales targets.</p>
            </div>
            """, unsafe_allow_html=True)

            with st.expander(f"View {len(gaps)} target stores"):
                df = pd.DataFrame(gaps, columns=["Store", "City", "County"])
                st.dataframe(df, use_container_width=True, hide_index=True, height=300)

        # Pricing Issues - use pre-loaded data
        if pricing_issues:
            st.markdown(f"""
            <div class="insight-card warning">
                <h4>{len(pricing_issues)} Products with Price Variance</h4>
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
                <h4>No Critical Issues Found</h4>
                <p>Your brand has strong distribution and consistent pricing across the market.</p>
            </div>
            """, unsafe_allow_html=True)

    with tab2:
        st.markdown('<p class="section-header">Store Distribution</p>', unsafe_allow_html=True)
        st.markdown('<p class="chart-description">Stores currently stocking your products vs. stores that could be carrying them.</p>', unsafe_allow_html=True)

        if DEMO_MODE:
            # Demo data for carrying stores
            carrying = [
                ("Starbuds Baltimore", "Baltimore", "Baltimore City", 24),
                ("Herbiculture", "Towson", "Baltimore County", 18),
                ("Greenhouse Wellness", "Ellicott City", "Howard", 16),
                ("Curio Wellness", "Timonium", "Baltimore County", 14),
                ("Gold Leaf", "Annapolis", "Anne Arundel", 12),
            ]
        else:
            # Get carrying/not carrying from database
            engine = get_engine()
            with engine.connect() as conn:
                carrying = conn.execute(text("""
                    SELECT d.name, d.city, d.county, COUNT(DISTINCT r.raw_name) as products
                    FROM dispensary d
                    JOIN raw_menu_item r ON d.dispensary_id = r.dispensary_id
                    WHERE UPPER(r.raw_brand) = :brand AND d.is_active = true AND d.state = :state
                    GROUP BY d.dispensary_id, d.name, d.city, d.county
                    ORDER BY products DESC
                """), {"brand": selected_brand, "state": selected_state}).fetchall()

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

        # Top products chart (demo mode)
        if DEMO_MODE and demo_data.get("top_products"):
            st.markdown("---")
            st.markdown("**Top Products by Store Distribution**")
            top_prods = pd.DataFrame(demo_data["top_products"])
            fig = px.bar(
                top_prods.sort_values("stores", ascending=True),
                x="stores",
                y="product",
                orientation='h',
                color="avg_price",
                color_continuous_scale="Greens",
                labels={"stores": "Stores Carrying", "product": "", "avg_price": "Avg Price"}
            )
            fig.update_layout(height=280, margin=dict(t=10, b=40, l=10, r=20))
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.markdown('<p class="section-header">Coverage by County</p>', unsafe_allow_html=True)
        st.markdown('<p class="chart-description">Shows what percentage of stores in each county carry your products. Low percentages indicate expansion opportunities.</p>', unsafe_allow_html=True)

        if DEMO_MODE:
            county_data = get_demo_data()["county_coverage"]
        else:
            county_data = get_county_coverage(selected_brand, selected_category, selected_state)

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
                # Create horizontal bar chart with Plotly
                chart_df = df.head(15).copy()
                fig = px.bar(
                    chart_df.sort_values("Coverage %", ascending=True),
                    x="Coverage %",
                    y="County",
                    orientation='h',
                    color="Coverage %",
                    color_continuous_scale=["#dc3545", "#ffc107", "#28a745"]
                )
                fig.update_layout(height=350, showlegend=False, margin=dict(t=10, b=40, l=10, r=20))
                st.plotly_chart(fig, use_container_width=True)

    with tab4:
        st.markdown('<p class="section-header">Competitor Deep-Dive</p>', unsafe_allow_html=True)
        st.markdown('<p class="chart-description">Compare your brand head-to-head against competitors in your categories.</p>', unsafe_allow_html=True)

        if competitive and competitive.get("competitors"):
            # Competitor comparison chart
            comp_data = []
            comp_data.append({"Brand": selected_brand, "Stores": metrics["stores_carrying"], "Type": "You"})
            for comp_name, comp_stores in competitive["competitors"][:5]:
                comp_data.append({"Brand": comp_name[:20], "Stores": comp_stores, "Type": "Competitor"})

            comp_df = pd.DataFrame(comp_data)

            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown("**Distribution Reach Comparison**")
                # Color your brand differently
                colors = ['#1e3a5f' if t == "You" else '#94a3b8' for t in comp_df["Type"]]
                fig = px.bar(
                    comp_df.sort_values("Stores", ascending=True),
                    x="Stores",
                    y="Brand",
                    orientation='h',
                    color="Type",
                    color_discrete_map={"You": "#1e3a5f", "Competitor": "#94a3b8"}
                )
                fig.update_layout(height=300, showlegend=False, margin=dict(t=10, b=40, l=10, r=20))
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.markdown("**Your Position**")
                your_rank = 1
                for comp_name, comp_stores in competitive["competitors"]:
                    if comp_stores > metrics["stores_carrying"]:
                        your_rank += 1

                st.markdown(f"""
                <div style="background:#f8f9fa; padding:1rem; border-radius:8px; text-align:center;">
                    <p style="margin:0; font-size:2.5rem; font-weight:700; color:#1e3a5f;">#{your_rank}</p>
                    <p style="margin:0; font-size:0.85rem; color:#6c757d;">in your category</p>
                </div>
                """, unsafe_allow_html=True)

                gap_to_leader = competitive["top_competitor_stores"] - metrics["stores_carrying"]
                if gap_to_leader > 0:
                    st.markdown(f"""
                    <div style="margin-top:1rem; padding:0.75rem; background:#fff3cd; border-radius:6px;">
                        <p style="margin:0; font-size:0.85rem;"><strong>{gap_to_leader} stores</strong> behind category leader ({competitive['top_competitor'][:15]})</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="margin-top:1rem; padding:0.75rem; background:#d4edda; border-radius:6px;">
                        <p style="margin:0; font-size:0.85rem;"><strong>You're the category leader!</strong></p>
                    </div>
                    """, unsafe_allow_html=True)

            # Competitive insights
            st.markdown("---")
            st.markdown("**Competitive Insights**")

            insight_cols = st.columns(3)
            with insight_cols[0]:
                st.markdown("""
                <div style="background:#e3f2fd; padding:1rem; border-radius:8px;">
                    <p style="margin:0 0 0.5rem 0; font-weight:600; color:#1565c0;">Distribution Gap</p>
                    <p style="margin:0; font-size:0.85rem; color:#424242;">Focus sales efforts on counties where competitors have presence but you don't.</p>
                </div>
                """, unsafe_allow_html=True)

            with insight_cols[1]:
                st.markdown("""
                <div style="background:#fce4ec; padding:1rem; border-radius:8px;">
                    <p style="margin:0 0 0.5rem 0; font-weight:600; color:#c2185b;">Price Position</p>
                    <p style="margin:0; font-size:0.85rem; color:#424242;">Evaluate if your pricing allows retailers to maintain healthy margins vs. competitors.</p>
                </div>
                """, unsafe_allow_html=True)

            with insight_cols[2]:
                st.markdown("""
                <div style="background:#e8f5e9; padding:1rem; border-radius:8px;">
                    <p style="margin:0 0 0.5rem 0; font-weight:600; color:#2e7d32;">SKU Strategy</p>
                    <p style="margin:0; font-size:0.85rem; color:#424242;">Compare your SKU count to competitors - too few limits shelf presence, too many confuses buyers.</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Competitor data not available for this selection.")

    with tab5:
        st.markdown('<p class="section-header">Role-Based Insights</p>', unsafe_allow_html=True)
        st.markdown('<p class="chart-description">Tailored analysis based on your business role in the cannabis industry.</p>', unsafe_allow_html=True)

        role = st.radio(
            "Select your role for customized insights:",
            ["Brand / Manufacturer", "Dispensary / Retailer", "Investor / Analyst"],
            horizontal=True
        )

        st.markdown("---")

        if role == "Brand / Manufacturer":
            st.markdown("### Insights for Brands & Manufacturers")

            insight_data = [
                {
                    "title": "Distribution Expansion Priority",
                    "metric": f"{len(gaps)} stores" if gaps else "0 stores",
                    "insight": "Stores actively selling in your categories but not carrying your products. These are warm leads - they already buy similar products.",
                    "action": "Export the gap list and prioritize by county population density.",
                    "type": "opportunity"
                },
                {
                    "title": "Pricing Consistency",
                    "metric": f"{len(pricing_issues)} issues" if pricing_issues else "No issues",
                    "insight": "Products with >$5 price variance across retailers may indicate MAP violations or unauthorized discounting.",
                    "action": "Review retailer agreements and communicate pricing expectations.",
                    "type": "warning" if pricing_issues else "success"
                },
                {
                    "title": "Market Coverage Rate",
                    "metric": f"{metrics['coverage_pct']}%",
                    "insight": f"You're in {metrics['stores_carrying']} of {metrics['total_stores']} active dispensaries. " +
                              ("Strong coverage - focus on deepening SKU penetration." if metrics['coverage_pct'] > 60 else "Growth opportunity - prioritize new store placements."),
                    "action": "Target 70%+ coverage for market leadership.",
                    "type": "success" if metrics['coverage_pct'] > 50 else "warning"
                }
            ]

            for item in insight_data:
                border_color = "#28a745" if item["type"] == "success" else "#ffc107" if item["type"] == "warning" else "#17a2b8"
                st.markdown(f"""
                <div style="background:#fff; border:1px solid #e9ecef; border-left:4px solid {border_color}; border-radius:4px; padding:1rem; margin-bottom:1rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                        <h4 style="margin:0; color:#1e3a5f;">{item['title']}</h4>
                        <span style="background:{border_color}; color:white; padding:0.25rem 0.75rem; border-radius:12px; font-size:0.8rem; font-weight:600;">{item['metric']}</span>
                    </div>
                    <p style="margin:0 0 0.5rem 0; font-size:0.9rem; color:#495057;">{item['insight']}</p>
                    <p style="margin:0; font-size:0.8rem; color:#6c757d;"><strong>Action:</strong> {item['action']}</p>
                </div>
                """, unsafe_allow_html=True)

        elif role == "Dispensary / Retailer":
            st.markdown("### Insights for Dispensaries & Retailers")

            # For retailers viewing brand data
            retailer_insights = [
                {
                    "title": "Brand Popularity Score",
                    "metric": f"{metrics['stores_carrying']}/{metrics['total_stores']} stores",
                    "insight": f"This brand is carried by {metrics['coverage_pct']}% of dispensaries. " +
                              ("High demand - customers expect to find it." if metrics['coverage_pct'] > 50 else "Niche brand - can differentiate your store if you carry it."),
                    "action": "Stock popular brands to meet customer expectations, add niche brands for differentiation.",
                    "type": "info"
                },
                {
                    "title": "Price Competitiveness",
                    "metric": f"${metrics['avg_price']:.0f} avg",
                    "insight": f"Market average is ${metrics['avg_price']:.0f}. Pricing below attracts price-sensitive customers; pricing above positions as premium.",
                    "action": "Compare your shelf price to the market range shown above.",
                    "type": "info"
                },
                {
                    "title": "SKU Depth Opportunity",
                    "metric": f"{metrics['sku_count']} SKUs available",
                    "insight": "This brand offers multiple products. Carrying variety can increase basket size and customer satisfaction.",
                    "action": "Review which SKUs perform best and ensure adequate inventory depth.",
                    "type": "opportunity"
                }
            ]

            for item in retailer_insights:
                border_color = "#17a2b8" if item["type"] == "info" else "#28a745"
                st.markdown(f"""
                <div style="background:#fff; border:1px solid #e9ecef; border-left:4px solid {border_color}; border-radius:4px; padding:1rem; margin-bottom:1rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                        <h4 style="margin:0; color:#1e3a5f;">{item['title']}</h4>
                        <span style="background:{border_color}; color:white; padding:0.25rem 0.75rem; border-radius:12px; font-size:0.8rem; font-weight:600;">{item['metric']}</span>
                    </div>
                    <p style="margin:0 0 0.5rem 0; font-size:0.9rem; color:#495057;">{item['insight']}</p>
                    <p style="margin:0; font-size:0.8rem; color:#6c757d;"><strong>Action:</strong> {item['action']}</p>
                </div>
                """, unsafe_allow_html=True)

            # What retailers should stock
            st.markdown("---")
            st.markdown("**Should You Carry This Brand?**")
            score = 0
            reasons = []
            if metrics['coverage_pct'] > 50:
                score += 2
                reasons.append("High market penetration - customers expect it")
            elif metrics['coverage_pct'] > 30:
                score += 1
                reasons.append("Moderate market presence")
            if metrics['sku_count'] > 50:
                score += 1
                reasons.append("Wide product selection available")
            if not pricing_issues:
                score += 1
                reasons.append("Consistent pricing across market")

            rec_color = "#28a745" if score >= 3 else "#ffc107" if score >= 2 else "#6c757d"
            rec_text = "Recommended" if score >= 3 else "Consider" if score >= 2 else "Optional"

            st.markdown(f"""
            <div style="background:#f8f9fa; padding:1rem; border-radius:8px; border-left:4px solid {rec_color};">
                <p style="margin:0 0 0.5rem 0; font-size:1.2rem; font-weight:600; color:{rec_color};">{rec_text}</p>
                <ul style="margin:0; padding-left:1.5rem; color:#495057;">
                    {''.join(f'<li>{r}</li>' for r in reasons)}
                </ul>
            </div>
            """, unsafe_allow_html=True)

        else:  # Investor / Analyst
            st.markdown("### Insights for Investors & Analysts")

            investor_insights = [
                {
                    "title": "Market Penetration",
                    "metric": f"{metrics['coverage_pct']}%",
                    "insight": f"Brand reaches {metrics['coverage_pct']}% of tracked dispensaries. " +
                              ("Strong distribution moat." if metrics['coverage_pct'] > 60 else "Growth runway available." if metrics['coverage_pct'] > 30 else "Early stage or niche positioning."),
                    "benchmark": "Top brands typically achieve 60-80% coverage."
                },
                {
                    "title": "Estimated Retail Footprint",
                    "metric": f"${metrics['total_retail']:,.0f}",
                    "insight": "Total retail value of products currently on shelves across all stores. Indicates brand's shelf presence investment by retailers.",
                    "benchmark": "Compare quarter-over-quarter for growth trends."
                },
                {
                    "title": "SKU Portfolio",
                    "metric": f"{metrics['sku_count']} products",
                    "insight": f"Active SKU count indicates product line breadth. " +
                              ("Diversified portfolio reduces single-product risk." if metrics['sku_count'] > 50 else "Focused portfolio - monitor for category concentration risk."),
                    "benchmark": "Leading brands typically maintain 75-150 active SKUs."
                }
            ]

            for item in investor_insights:
                st.markdown(f"""
                <div style="background:#fff; border:1px solid #e9ecef; border-radius:8px; padding:1rem; margin-bottom:1rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
                        <h4 style="margin:0; color:#1e3a5f;">{item['title']}</h4>
                        <span style="background:#1e3a5f; color:white; padding:0.25rem 0.75rem; border-radius:12px; font-size:0.9rem; font-weight:600;">{item['metric']}</span>
                    </div>
                    <p style="margin:0 0 0.5rem 0; font-size:0.9rem; color:#495057;">{item['insight']}</p>
                    <p style="margin:0; font-size:0.8rem; color:#6c757d; font-style:italic;">Benchmark: {item['benchmark']}</p>
                </div>
                """, unsafe_allow_html=True)

            # Competitive landscape summary
            if competitive:
                st.markdown("---")
                st.markdown("**Competitive Landscape Summary**")

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"""
                    <div style="background:#f8f9fa; padding:1rem; border-radius:8px;">
                        <p style="margin:0; font-size:0.8rem; color:#6c757d;">CATEGORY LEADER</p>
                        <p style="margin:0.25rem 0; font-size:1.1rem; font-weight:600; color:#1e3a5f;">{competitive['top_competitor']}</p>
                        <p style="margin:0; font-size:0.85rem; color:#495057;">{competitive['top_competitor_stores']} stores ({competitive['top_competitor_stores']/metrics['total_stores']*100:.0f}% coverage)</p>
                    </div>
                    """, unsafe_allow_html=True)

                with col2:
                    st.markdown(f"""
                    <div style="background:#f8f9fa; padding:1rem; border-radius:8px;">
                        <p style="margin:0; font-size:0.8rem; color:#6c757d;">CATEGORY AVERAGE</p>
                        <p style="margin:0.25rem 0; font-size:1.1rem; font-weight:600; color:#1e3a5f;">{competitive['avg_competitor_coverage']:.0f} stores</p>
                        <p style="margin:0; font-size:0.85rem; color:#495057;">Average distribution for top competitors</p>
                    </div>
                    """, unsafe_allow_html=True)

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
