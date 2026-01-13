# app/Home.py
"""CannLinx - Clean Homepage with User Type Selection"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from sqlalchemy import text
from core.db import get_engine
from components.sidebar_nav import render_nav

st.set_page_config(
    page_title="CannLinx - Cannabis Market Intelligence",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

render_nav(require_login=False)

# Compact styling
st.markdown("""
<style>
    /* Reduce default padding */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    /* Stats bar */
    .stats-bar {
        display: flex;
        justify-content: center;
        gap: 2rem;
        padding: 0.75rem;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        margin-bottom: 1.5rem;
    }
    .stat-item {text-align: center;}
    .stat-value {font-size: 1.5rem; font-weight: 700; color: #1e3a5f; margin: 0;}
    .stat-label {font-size: 0.65rem; color: #64748b; text-transform: uppercase; margin: 0;}
    /* User type cards */
    .user-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem;
        height: 100%;
        transition: all 0.2s;
        cursor: pointer;
    }
    .user-card:hover {
        box-shadow: 0 4px 12px rgba(30, 58, 95, 0.15);
        border-color: #1e3a5f;
        transform: translateY(-2px);
    }
    .user-card h3 {
        color: #1e3a5f;
        font-size: 1rem;
        margin: 0 0 0.5rem 0;
        font-weight: 600;
    }
    .user-card p {
        color: #64748b;
        font-size: 0.8rem;
        margin: 0 0 0.75rem 0;
        line-height: 1.4;
    }
    .user-card ul {
        margin: 0;
        padding-left: 1rem;
        color: #475569;
        font-size: 0.75rem;
    }
    .user-card li {margin-bottom: 0.2rem;}
    .card-link {
        display: inline-block;
        margin-top: 0.5rem;
        color: #2563eb;
        font-weight: 600;
        font-size: 0.8rem;
    }
    /* Section header */
    .section-header {
        font-size: 1rem;
        font-weight: 600;
        color: #1e3a5f;
        margin: 1rem 0 0.75rem 0;
        text-align: center;
    }
    /* Tagline */
    .tagline {
        font-size: 1rem;
        color: #64748b;
        text-align: center;
        margin-bottom: 1rem;
    }
    /* How it works */
    .how-step {
        text-align: center;
        padding: 0.5rem;
    }
    .how-step-num {
        display: inline-block;
        width: 28px;
        height: 28px;
        background: #1e3a5f;
        color: white;
        border-radius: 50%;
        line-height: 28px;
        font-weight: 600;
        font-size: 0.8rem;
        margin-bottom: 0.25rem;
    }
    .how-step-title {font-weight: 600; color: #1e3a5f; font-size: 0.85rem; margin-bottom: 0.15rem;}
    .how-step-desc {font-size: 0.7rem; color: #64748b;}
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="tagline">Real-time shelf intelligence for the cannabis industry</p>', unsafe_allow_html=True)

# Stats bar - compact
@st.cache_data(ttl=300)
def load_stats():
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT
                    COUNT(*) as products,
                    COUNT(DISTINCT r.dispensary_id) as stores,
                    COUNT(DISTINCT r.raw_brand) FILTER (WHERE r.raw_brand IS NOT NULL) as brands,
                    COUNT(DISTINCT d.state) as states
                FROM raw_menu_item r
                JOIN dispensary d ON r.dispensary_id = d.dispensary_id
                WHERE d.is_active = true
            """)).fetchone()
            return int(result[0] or 0), int(result[1] or 0), int(result[2] or 0), int(result[3] or 0)
    except:
        return 0, 0, 0, 0

products, stores, brands, states = load_stats()

st.markdown(f"""
<div class="stats-bar">
    <div class="stat-item">
        <p class="stat-value">{products:,}</p>
        <p class="stat-label">Products</p>
    </div>
    <div class="stat-item">
        <p class="stat-value">{stores:,}</p>
        <p class="stat-label">Dispensaries</p>
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

st.markdown('<p class="section-header">Choose Your Role</p>', unsafe_allow_html=True)

# User type cards - 4 columns
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
    <a href="/Retail_Intelligence" target="_self" style="text-decoration:none;">
        <div class="user-card">
            <h3>Dispensaries</h3>
            <p>Competitive pricing & inventory insights</p>
            <ul>
                <li>Price vs competitors</li>
                <li>Assortment gaps</li>
                <li>Category optimization</li>
                <li>Stock alerts</li>
            </ul>
            <span class="card-link">Explore Retail Tools &rarr;</span>
        </div>
    </a>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <a href="/Grower_Intelligence" target="_self" style="text-decoration:none;">
        <div class="user-card">
            <h3>Growers</h3>
            <p>Distribution & territory insights</p>
            <ul>
                <li>Strain rankings</li>
                <li>Category trends</li>
                <li>Territory analysis</li>
                <li>Product tracking</li>
            </ul>
            <span class="card-link">Explore Wholesale Tools &rarr;</span>
        </div>
    </a>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <a href="/Brand_Intelligence" target="_self" style="text-decoration:none;">
        <div class="user-card">
            <h3>Brands</h3>
            <p>Distribution & compliance tracking</p>
            <ul>
                <li>Store coverage</li>
                <li>Pricing compliance</li>
                <li>Image consistency</li>
                <li>Naming standards</li>
            </ul>
            <span class="card-link">Explore Brand Tools &rarr;</span>
        </div>
    </a>
    """, unsafe_allow_html=True)

with col4:
    st.markdown("""
    <a href="/Investor_Intelligence" target="_self" style="text-decoration:none;">
        <div class="user-card">
            <h3>Investors</h3>
            <p>Public company analytics</p>
            <ul>
                <li>Stock prices</li>
                <li>SKU penetration</li>
                <li>Market share</li>
                <li>Financials</li>
            </ul>
            <span class="card-link">Explore Investor Tools &rarr;</span>
        </div>
    </a>
    """, unsafe_allow_html=True)

# How It Works - compact
st.markdown('<p class="section-header">How It Works</p>', unsafe_allow_html=True)

h1, h2, h3, h4 = st.columns(4)

with h1:
    st.markdown(f"""
    <div class="how-step">
        <div class="how-step-num">1</div>
        <div class="how-step-title">Collect</div>
        <div class="how-step-desc">Daily scans from {stores:,}+ menus</div>
    </div>
    """, unsafe_allow_html=True)

with h2:
    st.markdown("""
    <div class="how-step">
        <div class="how-step-num">2</div>
        <div class="how-step-title">Normalize</div>
        <div class="how-step-desc">Match products across stores</div>
    </div>
    """, unsafe_allow_html=True)

with h3:
    st.markdown("""
    <div class="how-step">
        <div class="how-step-num">3</div>
        <div class="how-step-title">Analyze</div>
        <div class="how-step-desc">Identify trends & gaps</div>
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

# Simple CTA
st.markdown("---")
cta_col1, cta_col2, cta_col3 = st.columns([1, 2, 1])
with cta_col2:
    st.markdown("""
    <div style="text-align:center; padding:1rem; background:#f0f9ff; border-radius:8px;">
        <p style="margin:0 0 0.5rem 0; font-weight:600; color:#1e3a5f;">Ready to get started?</p>
        <p style="margin:0; font-size:0.85rem; color:#64748b;">
            <a href="/Login" style="color:#2563eb; font-weight:600;">Login</a> for full access or
            contact <a href="mailto:support@cannlinx.com" style="color:#2563eb;">support@cannlinx.com</a>
        </p>
    </div>
    """, unsafe_allow_html=True)

# Footer - minimal
st.markdown(
    f"<div style='text-align:center;color:#94a3b8;font-size:0.7rem;margin-top:1rem;'>"
    f"CannLinx &middot; {states} States &middot; support@cannlinx.com"
    "</div>",
    unsafe_allow_html=True
)
