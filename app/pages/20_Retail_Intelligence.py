# app/pages/20_Retail_Intelligence.py
"""Retail Intelligence Dashboard - Competitive analysis for dispensaries."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
from sqlalchemy import text
from components.sidebar_nav import render_nav, get_section_from_params, render_state_filter, get_selected_state
from components.auth import is_authenticated
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
render_nav(require_login=False)  # Allow demo access

# Import and apply shared styles
from components.styles import get_page_styles, COLORS
st.markdown(get_page_styles(), unsafe_allow_html=True)

# Check if user is authenticated for real data vs demo
DEMO_MODE = not is_authenticated()

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
def get_dispensaries(state: str = "MD"):
    """Get list of dispensaries with products in a state."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT d.dispensary_id, d.name, d.city, d.county, COUNT(r.raw_menu_item_id) as products
            FROM dispensary d
            LEFT JOIN raw_menu_item r ON d.dispensary_id = r.dispensary_id
            WHERE d.is_active = true AND d.state = :state
            GROUP BY d.dispensary_id, d.name, d.city, d.county
            HAVING COUNT(r.raw_menu_item_id) > 0
            ORDER BY d.name
        """), {"state": state})
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


# Demo data for unauthenticated users - store-specific data
DEMO_STORES = [
    ("demo-001", "Starbuds Baltimore (Baltimore)"),
    ("demo-002", "Herbiculture (Towson)"),
    ("demo-003", "Greenhouse Wellness (Ellicott City)"),
    ("demo-004", "Gold Leaf (Annapolis)"),
    ("demo-005", "Curio Wellness (Timonium)"),
]

DEMO_STORE_DATA = {
    "demo-001": {  # Starbuds Baltimore
        "competitors": [
            ("comp-001", "Harvest Baltimore", "Baltimore", 186),
            ("comp-002", "Culta Baltimore", "Baltimore", 212),
            ("comp-003", "Health for Life", "Baltimore", 178),
        ],
        "metrics": {"products": 324, "brands": 47, "avg_price": 42.50, "categories": 12},
        "insights": [
            {"type": "assortment", "priority": "high", "title": "8 popular products you don't carry",
             "detail": "These products are carried by 3+ competitors in your county.",
             "data": [("EVERMORE", "Purple Obeah #3 3.5g", 5), ("GRASSROOTS", "Birthday Cake 3.5g", 4), ("CURIO", "Blue Dream Pre-Roll 5pk", 4)]},
            {"type": "pricing_high", "priority": "medium", "title": "5 products priced above market average",
             "detail": "You may be losing sales to competitors on these items.",
             "data": [("VERANO", "G Purps 3.5g", "3.5g", 55.00, 48.50, 6.50), ("RYTHM", "Black Afghan 3.5g", "3.5g", 52.00, 47.00, 5.00)]},
            {"type": "unique", "priority": "positive", "title": "12+ exclusive products no local competitor carries",
             "detail": "These products give you a competitive advantage - promote them!",
             "data": [("STRANE", "MAC 1 Reserve 3.5g", "Flower", 58.00), ("SELECT", "Pax Era Pod Indica", "Vapes", 45.00)]}
        ],
        "pricing_comparison": [("CURIO", "Blue Dream 3.5g", "3.5g", "Flower", 45.00, 48.00, -3.00), ("EVERMORE", "Purple Obeah #3 3.5g", "3.5g", "Flower", 52.00, 50.00, 2.00), ("GRASSROOTS", "Ray Charles 3.5g", "3.5g", "Flower", 48.00, 45.00, 3.00)],
        "assortment_gaps": [("RYTHM", "Dosidos 3.5g", "Flower", 52.00), ("VERANO", "G6 Gelato 3.5g", "Flower", 55.00), ("CRESCO", "Bio Jesus LLR Cart", "Vapes", 45.00)],
        "category_comparison": [("Flower", 145, 162), ("Vapes", 68, 75), ("Concentrates", 42, 38), ("Edibles", 35, 42), ("Pre-Rolls", 24, 28)],
    },
    "demo-002": {  # Herbiculture
        "competitors": [
            ("comp-004", "Rise Towson", "Towson", 195),
            ("comp-005", "Greenhouse Wellness", "Ellicott City", 168),
            ("comp-006", "Living Room", "Lutherville", 142),
        ],
        "metrics": {"products": 287, "brands": 42, "avg_price": 45.25, "categories": 11},
        "insights": [
            {"type": "assortment", "priority": "high", "title": "6 popular products you don't carry",
             "detail": "These products are carried by 3+ competitors in your county.",
             "data": [("RYTHM", "Dosidos 3.5g", 4), ("CRESCO", "Outer Space 3.5g", 3), ("VERANO", "Mag Landrace 3.5g", 3)]},
            {"type": "pricing_high", "priority": "medium", "title": "3 products priced above market average",
             "detail": "You may be losing sales to competitors on these items.",
             "data": [("CURIO", "Sour Jack 3.5g", "3.5g", 58.00, 52.00, 6.00)]},
            {"type": "unique", "priority": "positive", "title": "18+ exclusive products no local competitor carries",
             "detail": "These products give you a competitive advantage - promote them!",
             "data": [("GRASSROOTS", "Motor Breath 3.5g", "Flower", 52.00), ("EVERMORE", "Sunset Octane 3.5g", "Flower", 55.00)]}
        ],
        "pricing_comparison": [("RYTHM", "Black Afghan 3.5g", "3.5g", "Flower", 50.00, 52.00, -2.00), ("CURIO", "Sour Jack 3.5g", "3.5g", "Flower", 58.00, 52.00, 6.00), ("STRANE", "Grape Lime Ricky 3.5g", "3.5g", "Flower", 42.00, 40.00, 2.00)],
        "assortment_gaps": [("CRESCO", "Outer Space 3.5g", "Flower", 48.00), ("VERANO", "Mag Landrace 3.5g", "Flower", 52.00)],
        "category_comparison": [("Flower", 132, 148), ("Vapes", 58, 62), ("Concentrates", 38, 35), ("Edibles", 32, 38), ("Pre-Rolls", 27, 25)],
    },
    "demo-003": {  # Greenhouse Wellness
        "competitors": [
            ("comp-007", "Herbiculture", "Towson", 287),
            ("comp-008", "Remedy Columbia", "Columbia", 156),
            ("comp-009", "Rise Bethesda", "Bethesda", 178),
        ],
        "metrics": {"products": 412, "brands": 56, "avg_price": 44.00, "categories": 14},
        "insights": [
            {"type": "assortment", "priority": "high", "title": "4 popular products you don't carry",
             "detail": "These products are carried by 3+ competitors in your county.",
             "data": [("STRANE", "Biscotti 3.5g", 4), ("SELECT", "Elite Cart Sativa", 3)]},
            {"type": "unique", "priority": "positive", "title": "24+ exclusive products no local competitor carries",
             "detail": "These products give you a competitive advantage - promote them!",
             "data": [("EVERMORE", "Strawberry Cookies 3.5g", "Flower", 55.00), ("RYTHM", "L'Orange 3.5g", "Flower", 52.00), ("CURIO", "Blissful Wizard 3.5g", "Flower", 58.00)]}
        ],
        "pricing_comparison": [("EVERMORE", "Strawberry Cookies 3.5g", "3.5g", "Flower", 55.00, 58.00, -3.00), ("GRASSROOTS", "GSC 3.5g", "3.5g", "Flower", 48.00, 46.00, 2.00)],
        "assortment_gaps": [("STRANE", "Biscotti 3.5g", "Flower", 45.00), ("SELECT", "Elite Cart Sativa", "Vapes", 42.00)],
        "category_comparison": [("Flower", 178, 165), ("Vapes", 82, 78), ("Concentrates", 56, 52), ("Edibles", 48, 45), ("Pre-Rolls", 48, 42)],
    },
    "demo-004": {  # Gold Leaf
        "competitors": [
            ("comp-010", "Chesapeake Apothecary", "Severna Park", 134),
            ("comp-011", "Trilogy Wellness", "Ellicott City", 198),
            ("comp-012", "Oceanside Dispensary", "Glen Burnie", 167),
        ],
        "metrics": {"products": 256, "brands": 38, "avg_price": 48.50, "categories": 10},
        "insights": [
            {"type": "assortment", "priority": "high", "title": "11 popular products you don't carry",
             "detail": "These products are carried by 3+ competitors in your county.",
             "data": [("CURIO", "Blue Dream 3.5g", 5), ("RYTHM", "Animal Face 3.5g", 4), ("GRASSROOTS", "Garlic Cookies 3.5g", 4), ("VERANO", "Wedding Cake 3.5g", 3)]},
            {"type": "pricing_high", "priority": "medium", "title": "7 products priced above market average",
             "detail": "You may be losing sales to competitors on these items.",
             "data": [("EVERMORE", "Purple Obeah 3.5g", "3.5g", 60.00, 52.00, 8.00), ("STRANE", "White MAC 3.5g", "3.5g", 55.00, 48.00, 7.00), ("CRESCO", "Sugar Plum 3.5g", "3.5g", 52.00, 46.00, 6.00)]},
            {"type": "unique", "priority": "positive", "title": "8+ exclusive products no local competitor carries",
             "detail": "These products give you a competitive advantage - promote them!",
             "data": [("CULTA", "Poochie Love 3.5g", "Flower", 62.00)]}
        ],
        "pricing_comparison": [("EVERMORE", "Purple Obeah 3.5g", "3.5g", "Flower", 60.00, 52.00, 8.00), ("STRANE", "White MAC 3.5g", "3.5g", "Flower", 55.00, 48.00, 7.00), ("CRESCO", "Sugar Plum 3.5g", "3.5g", "Flower", 52.00, 46.00, 6.00), ("CURIO", "Sour Gorilla 3.5g", "3.5g", "Flower", 50.00, 52.00, -2.00)],
        "assortment_gaps": [("CURIO", "Blue Dream 3.5g", "Flower", 48.00), ("RYTHM", "Animal Face 3.5g", "Flower", 52.00), ("GRASSROOTS", "Garlic Cookies 3.5g", "Flower", 50.00), ("VERANO", "Wedding Cake 3.5g", "Flower", 55.00)],
        "category_comparison": [("Flower", 108, 142), ("Vapes", 52, 68), ("Concentrates", 35, 42), ("Edibles", 38, 45), ("Pre-Rolls", 23, 32)],
    },
    "demo-005": {  # Curio Wellness
        "competitors": [
            ("comp-013", "Blair Wellness", "Silver Spring", 145),
            ("comp-014", "Herbiculture", "Towson", 287),
            ("comp-015", "Starbuds Timonium", "Timonium", 178),
        ],
        "metrics": {"products": 378, "brands": 52, "avg_price": 46.75, "categories": 13},
        "insights": [
            {"type": "assortment", "priority": "high", "title": "5 popular products you don't carry",
             "detail": "These products are carried by 3+ competitors in your county.",
             "data": [("GRASSROOTS", "Ray Charles 3.5g", 4), ("VERANO", "Sonny G 3.5g", 3)]},
            {"type": "unique", "priority": "positive", "title": "32+ exclusive products no local competitor carries",
             "detail": "These products give you a competitive advantage - promote them!",
             "data": [("CURIO", "Blissful Wizard 3.5g", "Flower", 58.00), ("CURIO", "Blue Dream 3.5g", "Flower", 48.00), ("CURIO", "Sour Jack 3.5g", "Flower", 55.00)]}
        ],
        "pricing_comparison": [("EVERMORE", "Sunset Octane 3.5g", "3.5g", "Flower", 52.00, 55.00, -3.00), ("RYTHM", "Black Afghan 3.5g", "3.5g", "Flower", 48.00, 50.00, -2.00), ("STRANE", "OG Story 3.5g", "3.5g", "Flower", 44.00, 42.00, 2.00)],
        "assortment_gaps": [("GRASSROOTS", "Ray Charles 3.5g", "Flower", 48.00), ("VERANO", "Sonny G 3.5g", "Flower", 52.00)],
        "category_comparison": [("Flower", 162, 155), ("Vapes", 72, 68), ("Concentrates", 48, 45), ("Edibles", 52, 48), ("Pre-Rolls", 44, 38)],
    },
}

def get_retail_demo_data(store_id="demo-001"):
    """Return demo data for retail intelligence based on selected store."""
    store_data = DEMO_STORE_DATA.get(store_id, DEMO_STORE_DATA["demo-001"])
    return {
        "stores": DEMO_STORES,
        **store_data
    }


# Demo market overview data
DEMO_MARKET_OVERVIEW = {
    "total_stores": 96,
    "total_products": 32450,
    "avg_price": 44.50,
    "top_brands": [
        {"brand": "Curio", "store_count": 78, "products": 245},
        {"brand": "Evermore", "store_count": 72, "products": 198},
        {"brand": "Grassroots", "store_count": 68, "products": 176},
        {"brand": "Rythm", "store_count": 65, "products": 165},
        {"brand": "Verano", "store_count": 62, "products": 152},
        {"brand": "Strane", "store_count": 58, "products": 142},
        {"brand": "Cresco", "store_count": 54, "products": 128},
        {"brand": "Select", "store_count": 52, "products": 98},
    ],
    "category_distribution": [
        {"category": "Flower", "products": 12500, "avg_price": 48.00},
        {"category": "Vapes", "products": 6800, "avg_price": 45.00},
        {"category": "Concentrates", "products": 4200, "avg_price": 55.00},
        {"category": "Edibles", "products": 3800, "avg_price": 28.00},
        {"category": "Pre-Rolls", "products": 3100, "avg_price": 15.00},
        {"category": "Tinctures", "products": 1200, "avg_price": 42.00},
        {"category": "Topicals", "products": 850, "avg_price": 38.00},
    ],
    "price_ranges": [
        {"range": "$0-20", "count": 4500},
        {"range": "$21-40", "count": 8200},
        {"range": "$41-60", "count": 12800},
        {"range": "$61-80", "count": 4500},
        {"range": "$81+", "count": 2450},
    ]
}


if DEMO_MODE:
    st.info("**Demo Mode** - Showing sample data. [Login](/Login) to access your store's real data.")

# State and Store selector
col_state, col_store = st.columns([1, 3])

if DEMO_MODE:
    with col_state:
        st.selectbox("State", ["MD"], disabled=True)
        selected_state = "MD"

    with col_store:
        store_options = {name: id for id, name in DEMO_STORES}
        selected_store_name = st.selectbox("Select Your Store", list(store_options.keys()))
        selected_store_id = store_options[selected_store_name]

    # Get store-specific demo data based on selection
    demo_data = get_retail_demo_data(selected_store_id)
    metrics = demo_data["metrics"]
    insights = demo_data["insights"]
    competitors = demo_data["competitors"]
else:
    with col_state:
        selected_state = render_state_filter()

    dispensaries = get_dispensaries(selected_state)
    if not dispensaries:
        st.warning(f"No dispensary data available for {selected_state}")
        st.stop()

    with col_store:
        store_options = {name: id for id, name in dispensaries}
        selected_store_name = st.selectbox("Select Your Store", list(store_options.keys()))
        selected_store_id = store_options[selected_store_name]

    metrics = get_store_metrics(selected_store_id) if selected_store_id else {}
    insights = get_retail_insights(selected_store_id) if selected_store_id else []
    competitors = get_nearby_competitors(selected_store_id) if selected_store_id else []

if selected_store_id:

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

    # Market Position Charts (Demo Mode)
    if DEMO_MODE:
        st.markdown("---")
        st.subheader("Market Position")

        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            # Your store vs market average
            store_name_short = selected_store_name.split(" (")[0]
            comparison_data = pd.DataFrame({
                "Metric": ["Products", "Brands", "Avg Price ($)"],
                store_name_short: [metrics["products"], metrics["brands"], metrics["avg_price"]],
                "Market Average": [338, 45, 44.50]
            })

            fig = go.Figure()
            fig.add_trace(go.Bar(
                name=store_name_short,
                x=comparison_data["Metric"],
                y=comparison_data[store_name_short],
                marker_color='#2ecc71'
            ))
            fig.add_trace(go.Bar(
                name="Market Average",
                x=comparison_data["Metric"],
                y=comparison_data["Market Average"],
                marker_color='#3498db'
            ))
            fig.update_layout(
                title="Your Store vs Market Average",
                barmode='group',
                height=300,
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02)
            )
            st.plotly_chart(fig, use_container_width=True)

        with chart_col2:
            # Category distribution
            cat_df = pd.DataFrame(DEMO_MARKET_OVERVIEW["category_distribution"])
            fig = px.pie(
                cat_df,
                values="products",
                names="category",
                title="Market Category Distribution",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

        # Top brands and price distribution
        chart_col3, chart_col4 = st.columns(2)

        with chart_col3:
            # Top brands chart
            brands_df = pd.DataFrame(DEMO_MARKET_OVERVIEW["top_brands"])
            fig = px.bar(
                brands_df.sort_values("store_count", ascending=True),
                x="store_count",
                y="brand",
                orientation='h',
                title="Top Brands by Store Distribution",
                labels={"store_count": "Stores Carrying", "brand": ""},
                color="products",
                color_continuous_scale="Blues"
            )
            fig.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with chart_col4:
            # Price distribution chart
            price_df = pd.DataFrame(DEMO_MARKET_OVERVIEW["price_ranges"])
            fig = px.bar(
                price_df,
                x="range",
                y="count",
                title="Market Price Distribution",
                labels={"range": "Price Range", "count": "Products"},
                color="count",
                color_continuous_scale="Greens"
            )
            fig.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    # INSIGHTS SECTION
    st.markdown("---")
    st.subheader("Actionable Insights")

    # insights already loaded above (demo or real)
    if insights:
        for insight in insights:
            # Choose icon based on priority
            if insight['priority'] == 'high':
                icon = '[!]'
            elif insight['priority'] == 'positive':
                icon = '[+]'
            else:
                icon = '[-]'

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

    # competitors already loaded above (demo or real)
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

            if DEMO_MODE:
                pricing = demo_data["pricing_comparison"]
            else:
                pricing = compare_pricing(selected_store_id, selected_comp_id)

            if pricing:
                # Use competitor name in column header
                comp_col_name = selected_comp_name.split(" (")[0]  # Just store name for column
                store_name_short = selected_store_name.split(" (")[0]
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

                # Price comparison scatter plot
                if len(df) > 0:
                    fig = px.scatter(
                        df,
                        x="Your Price",
                        y=f"{comp_col_name} Price",
                        color="Difference",
                        hover_data=["Brand", "Product", "Size"],
                        color_continuous_scale=["green", "yellow", "red"],
                        color_continuous_midpoint=0,
                        title=f"Price Comparison: {store_name_short} vs {comp_col_name}"
                    )
                    # Add diagonal line (equal pricing)
                    max_price = max(df["Your Price"].max(), df[f"{comp_col_name} Price"].max()) + 5
                    fig.add_trace(go.Scatter(
                        x=[0, max_price],
                        y=[0, max_price],
                        mode='lines',
                        line=dict(color='gray', dash='dash'),
                        name='Equal Price',
                        showlegend=True
                    ))
                    fig.update_layout(height=350)
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption("Points above the line = you're priced lower. Points below = you're priced higher.")

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

            if DEMO_MODE:
                gaps = demo_data["assortment_gaps"]
            else:
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

            if DEMO_MODE:
                cat_data = demo_data["category_comparison"]
            else:
                cat_data = get_category_comparison(selected_store_id, selected_comp_id)

            if cat_data:
                comp_col_name = selected_comp_name.split(" (")[0]  # Just store name for column
                store_name_short = selected_store_name.split(" (")[0]
                df = pd.DataFrame(cat_data, columns=["Category", "Your Products", comp_col_name])
                df["Difference"] = df["Your Products"] - df[comp_col_name]

                # Plotly grouped bar chart
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    name=store_name_short,
                    y=df["Category"],
                    x=df["Your Products"],
                    orientation='h',
                    marker_color='#2ecc71'
                ))
                fig.add_trace(go.Bar(
                    name=comp_col_name,
                    y=df["Category"],
                    x=df[comp_col_name],
                    orientation='h',
                    marker_color='#e74c3c'
                ))
                fig.update_layout(
                    title="Product Count by Category",
                    barmode='group',
                    height=350,
                    xaxis_title="Products",
                    yaxis_title="",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02)
                )
                st.plotly_chart(fig, use_container_width=True)

                # Summary metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    your_total = df["Your Products"].sum()
                    st.metric("Your Total Products", your_total)
                with col2:
                    comp_total = df[comp_col_name].sum()
                    st.metric(f"{comp_col_name} Total", comp_total)
                with col3:
                    diff = your_total - comp_total
                    st.metric("Difference", f"{diff:+d}")

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
