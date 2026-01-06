# app/Home.py
"""CannLinx - Home Page with Horizontal Navigation"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from sqlalchemy import text
from core.db import get_engine
from pathlib import Path
import re
import json

st.set_page_config(
    page_title="CannLinx - Marketplace Intelligence",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Hide sidebar and style
st.markdown("""
<style>
    [data-testid="stSidebar"] {display: none;}
    .block-container {padding-top: 0.5rem; padding-bottom: 1rem; max-width: 1200px;}
    header {visibility: hidden;}

    /* Horizontal nav with dropdowns */
    .nav-container {
        display: flex;
        justify-content: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        background: #5a7fa8;
        margin: 0 auto 1rem auto;
        max-width: 1200px;
        border-radius: 4px;
    }
    .nav-link {
        color: white !important;
        text-decoration: none !important;
        padding: 0.5rem 1rem;
        border-radius: 4px;
        font-size: 0.9rem;
        transition: background 0.2s;
    }
    .nav-link:hover {background: rgba(255,255,255,0.2); text-decoration: none !important;}
    .nav-link:visited {color: white !important; text-decoration: none !important;}
    .nav-link:active {color: white !important; text-decoration: none !important;}

    /* Dropdown styles */
    .nav-dropdown {
        position: relative;
        display: inline-block;
    }
    .nav-dropdown-btn {
        color: white;
        padding: 0.5rem 1rem;
        font-size: 0.9rem;
        border: none;
        background: transparent;
        cursor: pointer;
        border-radius: 4px;
        transition: background 0.2s;
    }
    .nav-dropdown-btn:hover {background: rgba(255,255,255,0.2);}
    .nav-dropdown-content {
        display: none;
        position: absolute;
        background: white;
        min-width: 180px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        border-radius: 6px;
        z-index: 1000;
        top: 100%;
        left: 50%;
        transform: translateX(-50%);
        padding: 0.5rem 0;
    }
    .nav-dropdown:hover .nav-dropdown-content {display: block;}
    .nav-dropdown-content a {
        color: #1e3a5f !important;
        padding: 0.5rem 1rem;
        text-decoration: none !important;
        display: block;
        font-size: 0.85rem;
        transition: background 0.2s;
    }
    .nav-dropdown-content a:hover {background: #f0f2f5;}

    /* Stats bar - single unified bar */
    .stats-bar {
        display: flex;
        justify-content: space-around;
        align-items: center;
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
        border-radius: 8px;
        padding: 0.8rem 1rem;
        color: white;
        margin-bottom: 1rem;
    }
    .stat-item {
        text-align: center;
        padding: 0 1rem;
        border-right: 1px solid rgba(255,255,255,0.2);
    }
    .stat-item:last-child {border-right: none;}
    .stat-value {font-size: 1.4rem; font-weight: bold; margin: 0;}
    .stat-label {font-size: 0.65rem; text-transform: uppercase; opacity: 0.85; margin: 0;}

    /* Feature boxes */
    .feature-box {
        background: #f4f6f8;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        border: 1px solid #e1e5e9;
        height: 100%;
        margin-bottom: 0.75rem;
    }
    .feature-box h4 {margin: 0 0 0.4rem 0; color: #1e3a5f; font-size: 1.1rem; font-weight: 600;}
    .feature-box ul {margin: 0 0 0.5rem 0; padding-left: 1.1rem; font-size: 0.95rem; color: #495057;}
    .feature-box li {margin-bottom: 0.15rem;}
    .feature-box .learn-more {
        display: inline-block;
        color: #1e3a5f;
        font-size: 0.85rem;
        text-decoration: none;
        font-weight: 500;
        margin-top: 0.3rem;
    }
    .feature-box .learn-more:hover {text-decoration: underline;}

    /* Centered section header */
    .section-header-centered {
        font-size: 1.5rem !important;
        font-weight: 600;
        color: #1e3a5f;
        margin-bottom: 0.8rem;
        text-align: center;
    }

    /* Form */
    div[data-testid="stForm"] {
        background: #f4f6f8;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #e1e5e9;
    }

    /* Tagline */
    .tagline {font-size: 0.95rem; color: #6c757d; margin: 0.3rem 0 0.8rem 0; text-align: center;}

    /* Section header - larger */
    .section-header {font-size: 1.4rem !important; font-weight: 600; color: #1e3a5f; margin-bottom: 0.8rem;}
</style>
""", unsafe_allow_html=True)

# Hero Banner
banner_path = Path(__file__).parent / "static" / "cannalinx_banner.png"
if banner_path.exists():
    st.image(str(banner_path), width="stretch")

# Horizontal Navigation - no underlines
st.markdown("""
<div class="nav-container">
    <a href="/" target="_self" class="nav-link">Home</a>
    <div class="nav-dropdown">
        <span class="nav-dropdown-btn">Analytics ▾</span>
        <div class="nav-dropdown-content">
            <a href="/Dashboard" target="_self">Dashboard</a>
            <a href="/Availability" target="_self">Availability</a>
            <a href="/Competitive_Intel" target="_self">Competitive Intel</a>
            <a href="/Price_Analysis" target="_self">Price Analysis</a>
        </div>
    </div>
    <div class="nav-dropdown">
        <span class="nav-dropdown-btn">Solutions ▾</span>
        <div class="nav-dropdown-content">
            <a href="/For_Manufacturers" target="_self">Manufacturers</a>
            <a href="/For_Brands" target="_self">Brands</a>
            <a href="/For_Dispensaries" target="_self">Dispensaries</a>
            <a href="/For_Investors" target="_self">Investors</a>
            <a href="/For_Consumers" target="_self">Consumers</a>
            <a href="/For_MA" target="_self">M&A Due Diligence</a>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<p class="tagline">Real-time shelf intelligence for the cannabis industry. Track products, monitor competitors, make data-driven decisions.</p>', unsafe_allow_html=True)

# Load stats combining DB data with local dispensary count
@st.cache_data(ttl=300)
def load_stats():
    # Get dispensary count from local JSON (includes all tracked dispensaries)
    try:
        json_path = Path(__file__).parent.parent / "md_dispensaries_by_provider.json"
        with open(json_path) as f:
            data = json.load(f)
        json_dispensaries = sum(len(v) for v in data.values())
    except:
        json_dispensaries = 72

    # Get scraped data from database
    try:
        engine = get_engine()
        with engine.connect() as conn:
            unique_products = conn.execute(text("""
                SELECT COUNT(DISTINCT raw_name) FROM raw_menu_item WHERE raw_name IS NOT NULL
            """)).scalar() or 0
            total_observations = conn.execute(text("SELECT COUNT(*) FROM raw_menu_item")).scalar() or 0
            brands = conn.execute(text("SELECT COUNT(DISTINCT raw_brand) FROM raw_menu_item WHERE raw_brand IS NOT NULL")).scalar() or 0

            # Count states from JSON file - currently only MD
            states = {"MD": json_dispensaries}

            return {"unique_skus": unique_products, "observations": total_observations}, brands, states, json_dispensaries
    except:
        return {"unique_skus": 0, "observations": 0}, 0, {"MD": json_dispensaries}, json_dispensaries

stats, brands_count, state_counts, total_dispensaries = load_stats()

# Stats bar - unified single bar
states_str = ", ".join(state_counts.keys()) if state_counts else "MD"
st.markdown(f"""
<div class="stats-bar">
    <div class="stat-item">
        <p class="stat-value">{stats.get("unique_skus", 0):,}</p>
        <p class="stat-label">Products Tracked</p>
    </div>
    <div class="stat-item">
        <p class="stat-value">{total_dispensaries}</p>
        <p class="stat-label">Dispensaries</p>
    </div>
    <div class="stat-item">
        <p class="stat-value">{brands_count if brands_count else 500}+</p>
        <p class="stat-label">Brands</p>
    </div>
    <div class="stat-item">
        <p class="stat-value">{stats.get("observations", 0):,}</p>
        <p class="stat-label">Data Points</p>
    </div>
    <div class="stat-item">
        <p class="stat-value">{len(state_counts)}</p>
        <p class="stat-label">States ({states_str})</p>
    </div>
</div>
""", unsafe_allow_html=True)

# Who We Serve - centered header
st.markdown('<p class="section-header-centered">Who We Serve</p>', unsafe_allow_html=True)

# First row of boxes
f1, f2, f3 = st.columns(3)

with f1:
    st.markdown("""
    <div class="feature-box">
        <h4>Manufacturers</h4>
        <ul>
            <li>Track distribution coverage</li>
            <li>Monitor retail pricing</li>
            <li>Market share insights</li>
            <li>Sales territory intel</li>
        </ul>
        <a href="/For_Manufacturers" target="_self" class="learn-more">Learn More →</a>
    </div>
    """, unsafe_allow_html=True)

with f2:
    st.markdown("""
    <div class="feature-box">
        <h4>Brands</h4>
        <ul>
            <li>Brand visibility tracking</li>
            <li>SKU performance metrics</li>
            <li>Competitive positioning</li>
            <li>New launch tracking</li>
        </ul>
        <a href="/For_Brands" target="_self" class="learn-more">Learn More →</a>
    </div>
    """, unsafe_allow_html=True)

with f3:
    st.markdown("""
    <div class="feature-box">
        <h4>Dispensaries</h4>
        <ul>
            <li>Competitor comparison</li>
            <li>Product gap analysis</li>
            <li>Price positioning</li>
            <li>Category mix insights</li>
        </ul>
        <a href="/For_Dispensaries" target="_self" class="learn-more">Learn More →</a>
    </div>
    """, unsafe_allow_html=True)

# Spacer between rows
st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)

# Second row of boxes
f4, f5, f6 = st.columns(3)

with f4:
    st.markdown("""
    <div class="feature-box">
        <h4>Investors</h4>
        <ul>
            <li>Market sizing data</li>
            <li>Brand performance metrics</li>
            <li>Competitive landscape</li>
            <li>Growth trend analysis</li>
        </ul>
        <a href="/For_Investors" target="_self" class="learn-more">Learn More →</a>
    </div>
    """, unsafe_allow_html=True)

with f5:
    st.markdown("""
    <div class="feature-box">
        <h4>Consumers</h4>
        <ul>
            <li>Find products near you</li>
            <li>Compare prices across stores</li>
            <li>Track product availability</li>
            <li>Discover new brands</li>
        </ul>
        <a href="/For_Consumers" target="_self" class="learn-more">Learn More →</a>
    </div>
    """, unsafe_allow_html=True)

with f6:
    st.markdown("""
    <div class="feature-box">
        <h4>M&A Due Diligence</h4>
        <ul>
            <li>Target company analysis</li>
            <li>Market position assessment</li>
            <li>Competitive benchmarking</li>
            <li>Distribution footprint</li>
        </ul>
        <a href="/For_MA" target="_self" class="learn-more">Learn More →</a>
    </div>
    """, unsafe_allow_html=True)

# Registration form
st.markdown("---")
reg_left, reg_center, reg_right = st.columns([1, 2, 1])
with reg_center:
    st.markdown('<p class="section-header-centered">Get Started</p>', unsafe_allow_html=True)
    with st.form("registration_form", clear_on_submit=True):
        user_type = st.selectbox("User Type", ["I am a Dispensary", "I am a Manufacturer/Grower", "I am a Brand", "Other"], label_visibility="collapsed")
        company = st.text_input("Company", placeholder="Company Name *", label_visibility="collapsed")

        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name", placeholder="Contact Name *", label_visibility="collapsed")
        with col2:
            title = st.text_input("Title", placeholder="Title", label_visibility="collapsed")

        email = st.text_input("Email", placeholder="Email *", label_visibility="collapsed")
        phone = st.text_input("Phone", placeholder="Phone", label_visibility="collapsed")

        submitted = st.form_submit_button("Register for Access", use_container_width=True, type="primary")

        if submitted:
            user_type_clean = user_type.replace("I am a ", "").replace("I am an ", "")
            errors = []
            if not company: errors.append("Company required")
            if not name: errors.append("Name required")
            if not email: errors.append("Email required")
            elif not re.match(r"[^@]+@[^@]+\.[^@]+", email): errors.append("Invalid email")

            if errors:
                st.error(" | ".join(errors))
            else:
                try:
                    engine = get_engine()
                    with engine.connect() as conn:
                        conn.execute(text("""
                            CREATE TABLE IF NOT EXISTS registrations (
                                id SERIAL PRIMARY KEY, user_type VARCHAR(50), company_name VARCHAR(255),
                                contact_name VARCHAR(255), email VARCHAR(255), phone VARCHAR(50), title VARCHAR(100),
                                created_at TIMESTAMP DEFAULT NOW(), status VARCHAR(50) DEFAULT 'pending'
                            )
                        """))
                        conn.execute(text("""
                            INSERT INTO registrations (user_type, company_name, contact_name, email, phone, title)
                            VALUES (:ut, :co, :nm, :em, :ph, :ti)
                        """), {"ut": user_type_clean, "co": company, "nm": name, "em": email, "ph": phone or None, "ti": title or None})
                        conn.commit()
                    st.success("Registered! We'll contact you within 24 hours.")
                except Exception as e:
                    st.error(f"Error: {e}")

st.markdown("---")

# How it works
st.markdown('<p class="section-header">How It Works</p>', unsafe_allow_html=True)
h1, h2, h3, h4 = st.columns(4)
with h1:
    st.markdown("**Collect**<br><small>Daily menu scans from dispensaries</small>", unsafe_allow_html=True)
with h2:
    st.markdown("**Normalize**<br><small>Match & dedupe across platforms</small>", unsafe_allow_html=True)
with h3:
    st.markdown("**Analyze**<br><small>Identify trends & opportunities</small>", unsafe_allow_html=True)
with h4:
    st.markdown("**Deliver**<br><small>Custom dashboards & alerts</small>", unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("<div style='text-align:center;color:#6c757d;font-size:0.8rem;'><strong>CannLinx</strong> · Marketplace Intelligence · support@cannlinx.com</div>", unsafe_allow_html=True)
