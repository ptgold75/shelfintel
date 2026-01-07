# app/pages/4_Competitive_Intel.py
"""Competitive Intelligence - Compare your dispensary to competitors."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
from sqlalchemy import text
from core.db import get_engine
from collections import defaultdict
import math

st.set_page_config(page_title="Competitive Intelligence | CannaLinx", page_icon="🎯", layout="wide")

st.markdown("""
<style>
    .block-container {padding-top: 1rem;}
    .metric-card {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
        border-left: 4px solid #1a5f2a;
    }
    .metric-value {font-size: 1.6rem; font-weight: bold; color: #1a5f2a; margin: 0;}
    .metric-label {font-size: 0.8rem; color: #666; margin: 0;}
    .gap-item {
        background: #fff8e1;
        border-radius: 6px;
        padding: 0.8rem;
        margin: 0.3rem 0;
        border-left: 3px solid #ffc107;
    }
    .price-below {color: #28a745; font-weight: bold;}
    .price-above {color: #dc3545; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

st.title("🎯 Competitive Intelligence")

# Cached data loading functions
@st.cache_data(ttl=600)
def load_dispensaries():
    """Load dispensary list with location data."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, name, county, lat, lng
                FROM dispensaries
                ORDER BY name
            """)).fetchall()
            return [{"id": r[0], "name": r[1], "county": r[2], "lat": r[3], "lng": r[4]} for r in result]
    except:
        return []

@st.cache_data(ttl=300)
def load_products_for_dispensary(disp_id):
    """Load current products for a dispensary."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT p.name, p.brand, p.category, po.price, po.discount_price
                FROM products p
                JOIN product_observations po ON p.id = po.product_id
                WHERE po.dispensary_id = :disp_id
                AND po.scraped_at >= NOW() - INTERVAL '7 days'
                ORDER BY p.category, p.brand, p.name
            """), {"disp_id": disp_id}).fetchall()
            return [{"name": r[0], "brand": r[1], "category": r[2], "price": float(r[3]) if r[3] else 0, "discount": float(r[4]) if r[4] else None} for r in result]
    except:
        return []

@st.cache_data(ttl=300)
def load_products_for_dispensaries(disp_ids):
    """Load products for multiple dispensaries."""
    if not disp_ids:
        return []
    try:
        engine = get_engine()
        with engine.connect() as conn:
            placeholders = ','.join([f':id{i}' for i in range(len(disp_ids))])
            params = {f'id{i}': did for i, did in enumerate(disp_ids)}
            result = conn.execute(text(f"""
                SELECT p.name, p.brand, p.category, po.price, d.name as dispensary
                FROM products p
                JOIN product_observations po ON p.id = po.product_id
                JOIN dispensaries d ON po.dispensary_id = d.id
                WHERE po.dispensary_id IN ({placeholders})
                AND po.scraped_at >= NOW() - INTERVAL '7 days'
            """), params).fetchall()
            return [{"name": r[0], "brand": r[1], "category": r[2], "price": float(r[3]) if r[3] else 0, "dispensary": r[4]} for r in result]
    except Exception as e:
        return []

def haversine_distance(lat1, lng1, lat2, lng2):
    """Calculate distance in miles between two points."""
    if not all([lat1, lng1, lat2, lng2]):
        return float('inf')
    R = 3959  # Earth's radius in miles
    lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
    dlat, dlng = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def find_competitors(my_disp, all_disps, comparison_type, radius_miles=None):
    """Find competitor dispensaries based on comparison type."""
    competitors = []
    for d in all_disps:
        if d["id"] == my_disp["id"]:
            continue
        if comparison_type == "state":
            competitors.append(d)
        elif comparison_type == "county":
            if d["county"] == my_disp["county"]:
                competitors.append(d)
        elif comparison_type == "radius" and radius_miles:
            dist = haversine_distance(my_disp["lat"], my_disp["lng"], d["lat"], d["lng"])
            if dist <= radius_miles:
                competitors.append(d)
    return competitors

def analyze_gaps(my_products, comp_products):
    """Find product and brand gaps."""
    my_keys = {(p["brand"], p["name"]) for p in my_products}
    my_brands = {p["brand"] for p in my_products if p["brand"]}

    product_gaps = defaultdict(lambda: {"brand": "", "category": "", "carriers": [], "prices": []})
    brand_gaps = defaultdict(set)

    for p in comp_products:
        key = (p["brand"], p["name"])
        if key not in my_keys:
            product_gaps[key]["brand"] = p["brand"]
            product_gaps[key]["category"] = p["category"]
            product_gaps[key]["carriers"].append(p["dispensary"])
            if p["price"]:
                product_gaps[key]["prices"].append(p["price"])

        if p["brand"] and p["brand"] not in my_brands:
            brand_gaps[p["brand"]].add(p["dispensary"])

    # Sort by popularity
    sorted_gaps = sorted(product_gaps.items(), key=lambda x: -len(set(x[1]["carriers"])))
    sorted_brands = sorted(brand_gaps.items(), key=lambda x: -len(x[1]))

    return sorted_gaps[:50], sorted_brands[:30]

def analyze_prices(my_products, comp_products):
    """Compare prices between my products and competitors."""
    comp_prices = defaultdict(list)
    for p in comp_products:
        if p["price"]:
            comp_prices[(p["brand"], p["name"])].append(p["price"])

    comparisons = []
    for p in my_products:
        if not p["price"]:
            continue
        key = (p["brand"], p["name"])
        if key in comp_prices:
            avg_comp = sum(comp_prices[key]) / len(comp_prices[key])
            diff_pct = ((p["price"] - avg_comp) / avg_comp) * 100 if avg_comp else 0
            position = "below" if diff_pct < -5 else "above" if diff_pct > 5 else "at"
            comparisons.append({
                "name": p["name"], "brand": p["brand"], "category": p["category"],
                "your_price": p["price"], "market_avg": avg_comp, "diff_pct": diff_pct, "position": position
            })
    return comparisons

def get_category_mix(products):
    """Get category distribution percentages."""
    cats = defaultdict(int)
    for p in products:
        cats[p["category"]] += 1
    total = sum(cats.values()) or 1
    return {cat: (count / total) * 100 for cat, count in cats.items()}

# Load dispensaries
dispensaries = load_dispensaries()
disp_names = ["Select your dispensary..."] + [d["name"] for d in dispensaries]

# Sidebar controls
with st.sidebar:
    st.markdown("### Your Dispensary")
    selected_name = st.selectbox("Select dispensary", disp_names, index=0, label_visibility="collapsed")

    my_disp = next((d for d in dispensaries if d["name"] == selected_name), None)

    if my_disp:
        st.success(f"📍 {my_disp['county']}")

        st.markdown("---")
        st.markdown("### Compare To")

        comparison_type = st.radio(
            "Comparison type",
            ["Nearby (by distance)", "Same County", "State Average"],
            index=0,
            label_visibility="collapsed"
        )

        radius_miles = None
        if comparison_type == "Nearby (by distance)":
            radius_miles = st.select_slider(
                "Distance radius",
                options=[1, 2, 3, 4, 5, 10, 15, 20],
                value=5,
                format_func=lambda x: f"{x} mile{'s' if x > 1 else ''}"
            )

# Main content
if not my_disp:
    st.info("👈 Select your dispensary from the sidebar to get started.")

    st.markdown("### What You'll Get")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
        **Product Gap Analysis** - Products competitors carry that you don't

        **Brand Gap Analysis** - Popular brands missing from your shelves
        """)
    with c2:
        st.markdown("""
        **Price Comparison** - Your prices vs market average

        **Category Mix** - How your product mix compares to market
        """)
else:
    # Determine comparison scope
    if comparison_type == "State Average":
        comp_type = "state"
        comp_label = "Maryland"
    elif comparison_type == "Same County":
        comp_type = "county"
        comp_label = my_disp["county"]
    else:
        comp_type = "radius"
        comp_label = f"within {radius_miles} miles"

    # Find competitors
    competitors = find_competitors(my_disp, dispensaries, comp_type, radius_miles)
    comp_ids = [c["id"] for c in competitors]

    st.markdown(f"### {selected_name} vs {comp_label}")
    st.caption(f"Comparing to {len(competitors)} dispensaries")

    # Load data
    with st.spinner("Loading data..."):
        my_products = load_products_for_dispensary(my_disp["id"])
        comp_products = load_products_for_dispensaries(comp_ids) if comp_ids else []

    if not my_products:
        st.warning("No product data available for your dispensary yet.")
    else:
        # Metrics row
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f'<div class="metric-card"><p class="metric-value">{len(my_products):,}</p><p class="metric-label">Your Products</p></div>', unsafe_allow_html=True)
        with m2:
            my_brands = len({p["brand"] for p in my_products if p["brand"]})
            st.markdown(f'<div class="metric-card"><p class="metric-value">{my_brands}</p><p class="metric-label">Your Brands</p></div>', unsafe_allow_html=True)
        with m3:
            st.markdown(f'<div class="metric-card"><p class="metric-value">{len(comp_products):,}</p><p class="metric-label">Market Products</p></div>', unsafe_allow_html=True)
        with m4:
            comp_brands = len({p["brand"] for p in comp_products if p.get("brand")})
            st.markdown(f'<div class="metric-card"><p class="metric-value">{comp_brands}</p><p class="metric-label">Market Brands</p></div>', unsafe_allow_html=True)

        st.markdown("---")

        # Analysis tabs
        tab1, tab2, tab3, tab4 = st.tabs(["Product Gaps", "Brand Gaps", "Price Comparison", "Category Mix"])

        with tab1:
            product_gaps, _ = analyze_gaps(my_products, comp_products)

            if product_gaps:
                # Category filter
                gap_cats = list(set(g[1]["category"] for g in product_gaps if g[1]["category"]))
                cat_filter = st.selectbox("Filter by category", ["All"] + sorted(gap_cats), key="gap_cat")

                filtered = product_gaps
                if cat_filter != "All":
                    filtered = [(k, v) for k, v in product_gaps if v["category"] == cat_filter]

                st.markdown(f"**{len(filtered)} products** competitors carry that you don't:")

                for (brand, name), info in filtered[:20]:
                    carriers = len(set(info["carriers"]))
                    avg_price = sum(info["prices"]) / len(info["prices"]) if info["prices"] else 0
                    st.markdown(f"""
                    <div class="gap-item">
                        <strong>{name}</strong> · {brand}<br>
                        <small>Category: {info['category']} · Avg: ${avg_price:.2f} · {carriers} competitor(s)</small>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.success("No product gaps found - you carry everything competitors have!")

        with tab2:
            _, brand_gaps = analyze_gaps(my_products, comp_products)

            if brand_gaps:
                st.markdown(f"**{len(brand_gaps)} brands** in the market you don't carry:")
                for brand, carriers in brand_gaps[:20]:
                    st.markdown(f"- **{brand}** ({len(carriers)} dispensaries)")
            else:
                st.success("No brand gaps - you carry all brands in this market!")

        with tab3:
            price_comps = analyze_prices(my_products, comp_products)

            if price_comps:
                below = len([p for p in price_comps if p["position"] == "below"])
                at = len([p for p in price_comps if p["position"] == "at"])
                above = len([p for p in price_comps if p["position"] == "above"])

                p1, p2, p3 = st.columns(3)
                p1.metric("Below Market", below, help=">5% below average")
                p2.metric("At Market", at, help="Within 5% of average")
                p3.metric("Above Market", above, help=">5% above average")

                avg_diff = sum(p["diff_pct"] for p in price_comps) / len(price_comps)
                if avg_diff < -2:
                    st.success(f"Your prices are **{abs(avg_diff):.1f}% below** market average")
                elif avg_diff > 2:
                    st.warning(f"Your prices are **{avg_diff:.1f}% above** market average")
                else:
                    st.info(f"Your prices are **at market** average ({avg_diff:+.1f}%)")

                # Show table
                cat_filter = st.selectbox("Filter", ["All", "Below Market", "At Market", "Above Market"], key="price_filter")
                filtered = price_comps
                if cat_filter == "Below Market":
                    filtered = [p for p in price_comps if p["position"] == "below"]
                elif cat_filter == "At Market":
                    filtered = [p for p in price_comps if p["position"] == "at"]
                elif cat_filter == "Above Market":
                    filtered = [p for p in price_comps if p["position"] == "above"]

                data = [{"Product": p["name"][:35], "Brand": p["brand"][:15] if p["brand"] else "", "You": f"${p['your_price']:.2f}", "Market": f"${p['market_avg']:.2f}", "Diff": f"{p['diff_pct']:+.1f}%"} for p in sorted(filtered, key=lambda x: x["diff_pct"])[:30]]
                if data:
                    st.dataframe(data, use_container_width=True, hide_index=True)
            else:
                st.info("No overlapping products to compare prices.")

        with tab4:
            my_cats = get_category_mix(my_products)
            comp_cats = get_category_mix(comp_products)
            all_cats = sorted(set(my_cats.keys()) | set(comp_cats.keys()))

            if all_cats:
                data = []
                for cat in all_cats:
                    my_pct = my_cats.get(cat, 0)
                    comp_pct = comp_cats.get(cat, 0)
                    diff = my_pct - comp_pct
                    status = "Under" if diff < -5 else "Over" if diff > 5 else "Balanced"
                    data.append({"Category": cat, "You": f"{my_pct:.1f}%", "Market": f"{comp_pct:.1f}%", "Diff": f"{diff:+.1f}%", "Status": status})

                st.dataframe(data, use_container_width=True, hide_index=True)

                # Chart
                import pandas as pd
                chart_df = pd.DataFrame({"Category": all_cats, "Your Store": [my_cats.get(c, 0) for c in all_cats], "Market": [comp_cats.get(c, 0) for c in all_cats]})
                st.bar_chart(chart_df.set_index("Category"))

st.markdown("---")
st.caption("Data updated daily. Contact support@cannalinx.com for custom analysis.")
