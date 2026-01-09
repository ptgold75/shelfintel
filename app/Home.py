# app/Home.py
"""CannLinx - Clean Professional Homepage"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from sqlalchemy import text
from core.db import get_engine
from pathlib import Path
import re
import json
from components.nav import render_nav

st.set_page_config(
    page_title="CannLinx - Marketplace Intelligence",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Render shared header with banner and navigation (public page - no login required)
render_nav(require_login=False)

# Import shared styles
from components.styles import COLORS

# Page-specific styling with brighter blues
st.markdown(f"""
<style>
    /* Stats bar */
    .stats-bar {{
        display: flex;
        justify-content: center;
        gap: 3rem;
        padding: 1.25rem;
        background: {COLORS['bg_highlight']};
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        margin-bottom: 2rem;
    }}
    .stat-item {{text-align: center;}}
    .stat-value {{font-size: 2rem; font-weight: 700; color: {COLORS['primary']}; margin: 0;}}
    .stat-label {{font-size: 0.75rem; color: {COLORS['text_muted']}; text-transform: uppercase; margin: 0; letter-spacing: 0.5px;}}

    /* Segment cards - clickable */
    .segment-card-link {{
        display: block;
        text-decoration: none !important;
        height: 100%;
        color: inherit;
    }}
    .segment-card-link:hover {{
        text-decoration: none !important;
    }}
    .segment-card-link * {{
        text-decoration: none !important;
    }}
    .segment-card {{
        background: white;
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        padding: 1.5rem;
        height: 100%;
        transition: all 0.2s ease;
        cursor: pointer;
    }}
    .segment-card:hover {{
        box-shadow: 0 8px 25px rgba(37, 99, 235, 0.15);
        border-color: {COLORS['primary']};
        transform: translateY(-3px);
    }}
    .segment-card h3 {{
        color: {COLORS['primary']};
        font-size: 1.15rem;
        margin: 0 0 0.75rem 0;
        font-weight: 600;
    }}
    .segment-card p {{
        color: {COLORS['text_secondary']};
        font-size: 0.9rem;
        margin: 0 0 1rem 0;
        line-height: 1.5;
    }}
    .segment-card ul {{
        margin: 0;
        padding-left: 1.2rem;
        color: {COLORS['text_muted']};
        font-size: 0.85rem;
    }}
    .segment-card li {{margin-bottom: 0.35rem;}}
    .segment-link {{
        display: inline-block;
        margin-top: 1rem;
        color: {COLORS['primary']};
        font-weight: 600;
        text-decoration: none !important;
        font-size: 0.9rem;
    }}

    /* Section headers */
    .section-title {{
        font-size: 1.5rem;
        font-weight: 600;
        color: {COLORS['primary']};
        margin: 2rem 0 1rem 0;
        text-align: center;
    }}

    /* Tagline */
    .tagline {{
        font-size: 1.15rem;
        color: {COLORS['text_secondary']};
        text-align: center;
        margin-bottom: 1.5rem;
    }}

    /* How it works */
    .how-step {{
        text-align: center;
        padding: 1rem;
    }}
    .how-step-num {{
        display: inline-block;
        width: 36px;
        height: 36px;
        background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['primary_dark']} 100%);
        color: white;
        border-radius: 50%;
        line-height: 36px;
        font-weight: 600;
        margin-bottom: 0.5rem;
        box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3);
    }}
    .how-step-title {{font-weight: 600; color: {COLORS['text_primary']}; margin-bottom: 0.25rem;}}
    .how-step-desc {{font-size: 0.85rem; color: {COLORS['text_muted']};}}
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="tagline">Real-time shelf intelligence for the cannabis industry</p>', unsafe_allow_html=True)

# Load stats from database - accurate counts of monitored data
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_stats():
    try:
        engine = get_engine()
        with engine.connect() as conn:
            # Get actual scraped data counts (stores with menu data)
            result = conn.execute(text("""
                SELECT
                    COUNT(*) as products,
                    COUNT(DISTINCT r.dispensary_id) as stores_with_menus,
                    COUNT(DISTINCT r.raw_brand) FILTER (WHERE r.raw_brand IS NOT NULL) as brands,
                    COUNT(DISTINCT d.state) as states
                FROM raw_menu_item r
                JOIN dispensary d ON r.dispensary_id = d.dispensary_id
                WHERE d.is_active = true
            """)).fetchone()

            products = result[0] or 0
            stores = result[1] or 0
            brands = result[2] or 0
            states = result[3] or 0

            return int(products), int(brands), int(stores), int(states)
    except Exception as e:
        st.error(f"Error loading stats: {e}")
        return 0, 0, 0, 0

products, brands, stores, states = load_stats()

# Stats bar
st.markdown(f"""
<div class="stats-bar">
    <div class="stat-item">
        <p class="stat-value">{products:,}</p>
        <p class="stat-label">Products Tracked</p>
    </div>
    <div class="stat-item">
        <p class="stat-value">{stores:,}</p>
        <p class="stat-label">Dispensaries Monitored</p>
    </div>
    <div class="stat-item">
        <p class="stat-value">{brands:,}</p>
        <p class="stat-label">Brands</p>
    </div>
    <div class="stat-item">
        <p class="stat-value">{states}</p>
        <p class="stat-label">States</p>
    </div>
</div>
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
    <a href="/Brand_Intelligence" target="_self" class="segment-card-link">
        <div class="segment-card">
            <h3>For Brands</h3>
            <p>Track your market presence and ensure brand consistency across retail partners.</p>
            <ul>
                <li>Store coverage & distribution gaps</li>
                <li>Retail pricing compliance</li>
                <li>Product image consistency</li>
                <li>Naming standardization</li>
            </ul>
            <span class="segment-link">Learn more →</span>
        </div>
    </a>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <a href="/Retail_Intelligence" target="_self" class="segment-card-link">
        <div class="segment-card">
            <h3>For Dispensaries</h3>
            <p>Competitive intelligence to optimize your pricing and product mix.</p>
            <ul>
                <li>Price comparison vs competitors</li>
                <li>Assortment gap analysis</li>
                <li>Category mix optimization</li>
                <li>Inventory insights</li>
            </ul>
            <span class="segment-link">Learn more →</span>
        </div>
    </a>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <a href="/Grower_Intelligence" target="_self" class="segment-card-link">
        <div class="segment-card">
            <h3>For Manufacturers</h3>
            <p>Market trends and distribution insights for cultivators and processors.</p>
            <ul>
                <li>Strain popularity rankings</li>
                <li>Category trends</li>
                <li>Brand distribution metrics</li>
                <li>Price benchmarking</li>
            </ul>
            <span class="segment-link">Learn more →</span>
        </div>
    </a>
    """, unsafe_allow_html=True)

with col4:
    st.markdown("""
    <a href="/Investor_Intelligence" target="_self" class="segment-card-link">
        <div class="segment-card">
            <h3>For Investors</h3>
            <p>Public company analytics and shelf intelligence for investment decisions.</p>
            <ul>
                <li>Stock prices & financials</li>
                <li>SKU counts & shelf penetration</li>
                <li>Market share by state</li>
                <li>Revenue & profitability metrics</li>
            </ul>
            <span class="segment-link">Learn more →</span>
        </div>
    </a>
    """, unsafe_allow_html=True)

# How It Works
st.markdown('<p class="section-title">How It Works</p>', unsafe_allow_html=True)

h1, h2, h3, h4 = st.columns(4)

with h1:
    st.markdown(f"""
    <div class="how-step">
        <div class="how-step-num">1</div>
        <div class="how-step-title">Collect</div>
        <div class="how-step-desc">Daily scans from {stores:,}+ store menus</div>
    </div>
    """, unsafe_allow_html=True)

with h2:
    st.markdown("""
    <div class="how-step">
        <div class="how-step-num">2</div>
        <div class="how-step-title">Normalize</div>
        <div class="how-step-desc">Match & dedupe products across stores</div>
    </div>
    """, unsafe_allow_html=True)

with h3:
    st.markdown("""
    <div class="how-step">
        <div class="how-step-num">3</div>
        <div class="how-step-title">Analyze</div>
        <div class="how-step-desc">Identify trends & opportunities</div>
    </div>
    """, unsafe_allow_html=True)

with h4:
    st.markdown("""
    <div class="how-step">
        <div class="how-step-num">4</div>
        <div class="how-step-title">Act</div>
        <div class="how-step-desc">Make data-driven decisions</div>
    </div>
    """, unsafe_allow_html=True)

# Registration
st.markdown("---")
st.markdown('<p class="section-title">Get Started</p>', unsafe_allow_html=True)

# Load dispensary and grower lists for dropdowns
@st.cache_data(ttl=300)
def load_dispensary_list():
    """Load all dispensaries for the dropdown."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, name, city, county
                FROM dispensary
                ORDER BY name
            """))
            return [{"id": r[0], "name": r[1], "city": r[2], "county": r[3]} for r in result]
    except:
        return []

@st.cache_data(ttl=300)
def load_grower_list():
    """Load unique growers/processors from brand data."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT raw_brand
                FROM raw_menu_item
                WHERE raw_brand IS NOT NULL
                ORDER BY raw_brand
            """))
            return [r[0] for r in result]
    except:
        return []

dispensary_list = load_dispensary_list()
grower_list = load_grower_list()

reg_left, reg_center, reg_right = st.columns([1, 2, 1])
with reg_center:
    # User type selector outside form for dynamic behavior
    user_type = st.selectbox(
        "I am a...",
        ["Brand / Manufacturer", "Dispensary / Retailer", "Grower / Processor", "Investor / Analyst", "Other"],
        key="user_type_select"
    )

    # Show conditional dropdown based on user type
    selected_location = None
    if user_type == "Dispensary / Retailer" and dispensary_list:
        disp_options = ["-- Select your dispensary --"] + [
            f"{d['name']} ({d['city'] or d['county'] or 'MD'})" for d in dispensary_list
        ]
        selected_disp = st.selectbox(
            "Select your dispensary location",
            disp_options,
            key="dispensary_select",
            label_visibility="collapsed"
        )
        if selected_disp != "-- Select your dispensary --":
            # Find the dispensary ID
            idx = disp_options.index(selected_disp) - 1
            selected_location = {"type": "dispensary", "id": dispensary_list[idx]["id"], "name": dispensary_list[idx]["name"]}

    elif user_type == "Grower / Processor" and grower_list:
        grower_options = ["-- Select your brand/company --"] + grower_list
        selected_grower = st.selectbox(
            "Select your brand/company",
            grower_options,
            key="grower_select",
            label_visibility="collapsed"
        )
        if selected_grower != "-- Select your brand/company --":
            selected_location = {"type": "grower", "name": selected_grower}

    with st.form("registration_form", clear_on_submit=True):
        company = st.text_input("Company", placeholder="Company Name *", label_visibility="collapsed")

        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name", placeholder="Your Name *", label_visibility="collapsed")
        with col2:
            email = st.text_input("Email", placeholder="Email *", label_visibility="collapsed")

        submitted = st.form_submit_button("Request Access", use_container_width=True, type="primary")

        if submitted:
            errors = []
            if not company:
                errors.append("Company required")
            if not name:
                errors.append("Name required")
            if not email:
                errors.append("Email required")
            elif not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                errors.append("Invalid email")

            # Validate location selection for dispensary/grower
            if user_type == "Dispensary / Retailer" and not selected_location:
                errors.append("Please select your dispensary")
            elif user_type == "Grower / Processor" and not selected_location:
                errors.append("Please select your brand/company")

            if errors:
                st.error(" | ".join(errors))
            else:
                try:
                    engine = get_engine()
                    with engine.connect() as conn:
                        # Store with location info
                        location_id = selected_location.get("id") if selected_location else None
                        location_name = selected_location.get("name") if selected_location else None

                        conn.execute(text("""
                            INSERT INTO registrations (user_type, company_name, contact_name, email, location_id, location_name)
                            VALUES (:ut, :co, :nm, :em, :lid, :lnm)
                            ON CONFLICT DO NOTHING
                        """), {
                            "ut": user_type,
                            "co": company,
                            "nm": name,
                            "em": email,
                            "lid": location_id,
                            "lnm": location_name
                        })
                        conn.commit()
                    st.success("Thanks! We'll contact you within 24 hours.")
                except Exception as e:
                    st.error(f"Error: {e}")

# Footer
st.markdown("---")
st.markdown(
    f"<div style='text-align:center;color:#6c757d;font-size:0.8rem;'>"
    f"<strong>CannLinx</strong> · Cannabis Market Intelligence · {states} States · support@cannlinx.com"
    "</div>",
    unsafe_allow_html=True
)
