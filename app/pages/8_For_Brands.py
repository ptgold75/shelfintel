# app/pages/8_For_Brands.py
"""For Brands - Detailed use cases and features."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st

st.set_page_config(page_title="For Brands | CannLinx", page_icon=None, layout="wide")

st.markdown("""
<style>
    .block-container {padding-top: 1rem; max-width: 1100px;}

    .hero-section {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
        color: white;
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    .hero-section h1 {margin: 0 0 0.5rem 0; font-size: 2rem;}
    .hero-section p {margin: 0; font-size: 1.1rem; opacity: 0.9;}

    .stats-row {
        display: flex;
        justify-content: space-around;
        background: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1.5rem;
    }
    .stat-box {text-align: center; padding: 0.5rem 1rem;}
    .stat-box h3 {margin: 0; font-size: 1.6rem; color: #1e3a5f;}
    .stat-box p {margin: 0; font-size: 0.75rem; color: #6c757d; text-transform: uppercase;}

    .use-case-card {
        background: white;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transition: box-shadow 0.2s;
    }
    .use-case-card:hover {box-shadow: 0 4px 12px rgba(0,0,0,0.1);}
    .use-case-card h4 {margin: 0 0 0.5rem 0; color: #1e3a5f; font-size: 1rem; font-weight: 600;}
    .use-case-card p {margin: 0; color: #495057; font-size: 0.9rem; line-height: 1.5;}

    .section-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #1e3a5f;
        margin: 1.5rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #e9ecef;
    }

    .cta-section {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 1.5rem;
        text-align: center;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero-section">
    <h1>For Brands</h1>
    <p>Build and protect your brand in the cannabis market. Track visibility, monitor pricing consistency, and measure your competitive position.</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="stats-row">
    <div class="stat-box">
        <h3>90+</h3>
        <p>Brands Tracked</p>
    </div>
    <div class="stat-box">
        <h3>700+</h3>
        <p>Products</p>
    </div>
    <div class="stat-box">
        <h3>Daily</h3>
        <p>Price Updates</p>
    </div>
    <div class="stat-box">
        <h3>All</h3>
        <p>Categories</p>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<p class="section-title">What You Can Do</p>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="use-case-card">
        <h4>Brand Visibility Tracking</h4>
        <p>Monitor where your brand appears across all dispensaries. Track your presence in each product category. Compare visibility vs. competing brands.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>SKU Performance Analysis</h4>
        <p>See which of your products have the widest distribution. Identify top-performing SKUs and underperformers. Track distribution changes over time.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Competitive Positioning</h4>
        <p>Benchmark your brand against competitors. Compare distribution footprint, pricing, and category presence. Identify where competitors are gaining ground.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Pricing Consistency</h4>
        <p>Monitor retail pricing across all dispensaries. Identify outliers pricing too high or too low. Protect your brand value with consistent market pricing.</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="use-case-card">
        <h4>New Launch Monitoring</h4>
        <p>Track rollout of new products across dispensaries. Measure adoption speed by retailer. Identify which accounts are early adopters vs. laggards.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Regional Analysis</h4>
        <p>Understand brand strength by county and region. Identify geographic gaps in distribution. Plan targeted expansion into underserved areas.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Category Trends</h4>
        <p>Track category-level trends across the market. See which product types are growing or declining. Align your portfolio with market demand.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Alert System</h4>
        <p>Get notified when your products are added or removed from menus. Track price changes in real-time. Stay informed about competitive moves.</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<p class="section-title">Sample Insights</p>', unsafe_allow_html=True)

with st.expander("Brand Visibility Report", expanded=True):
    st.markdown("""
    **Brand:** "Sunset Extracts" (Vape Cartridges)

    **Current Distribution:**
    - Total dispensaries carrying brand: 52 of 72 (72%)
    - Category rank: #4 in Vapes (behind Select, Rythm, Cresco)

    **By Region:**
    | Region | Dispensaries | Your Brand | Coverage |
    |--------|-------------|------------|----------|
    | Central MD | 45 | 28 | 62% |
    | Western MD | 18 | 8 | 44% |
    | Eastern Shore | 12 | 4 | 33% |
    | Southern MD | 15 | 6 | 40% |

    **Opportunity:** Eastern Shore and Southern MD have lowest coverage - focus expansion here.
    """)

with st.expander("Pricing Analysis"):
    st.markdown("""
    **Product:** "Sunset OG 0.5g Cartridge" (MSRP: $35)

    **Market Pricing:**
    - Average retail price: $36.50
    - Lowest: $30 (2 dispensaries running promos)
    - Highest: $45 (3 dispensaries)
    - At MSRP: 35 dispensaries

    **Pricing Distribution:**
    - Below MSRP (<$35): 8 dispensaries
    - At MSRP ($35): 35 dispensaries
    - Above MSRP (>$35): 9 dispensaries

    **Note:** 3 dispensaries pricing at $45 may be hurting velocity. Consider reaching out.
    """)

st.markdown("""
<div class="cta-section">
    <h4 style="margin: 0 0 0.5rem 0; color: #1e3a5f;">Ready to Get Started?</h4>
    <p style="margin: 0 0 1rem 0; color: #6c757d;">Register on the home page to get access to brand intelligence tailored to your products.</p>
</div>
""", unsafe_allow_html=True)

st.page_link("Home.py", label="Back to Home", width="stretch")
