# app/pages/11_For_Consumers.py
"""For Consumers - Detailed use cases and features."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st

st.set_page_config(page_title="For Consumers | CannLinx", page_icon=None, layout="wide")

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
    <h1>For Consumers</h1>
    <p>Find the best products at the best prices near you. Compare dispensary menus, track availability, and never miss a deal.</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="stats-row">
    <div class="stat-box">
        <h3>72</h3>
        <p>Dispensaries</p>
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
        <h3>90+</h3>
        <p>Brands</p>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<p class="section-title">Features</p>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="use-case-card">
        <h4>Find Products Near You</h4>
        <p>Search for specific products and see which dispensaries near you have them in stock. Filter by distance, price, and brand.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Compare Prices Across Stores</h4>
        <p>See how prices vary for the same product across different dispensaries. Find the best deals without driving all over town.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Track Product Availability</h4>
        <p>Know when your favorite products are in stock. Get alerts when hard-to-find items become available.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Discover New Brands</h4>
        <p>Explore new products and brands entering the market. See what's trending and highly rated.</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="use-case-card">
        <h4>Deal Finder</h4>
        <p>Find dispensaries running specials and promotions. Compare discounted prices across your area.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Menu Explorer</h4>
        <p>Browse complete dispensary menus online. Filter by category, brand, price range, and more.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Price History</h4>
        <p>See how prices have changed over time. Know if you're getting a good deal or should wait for a sale.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Dispensary Comparison</h4>
        <p>Compare dispensaries by selection, pricing, and brands carried. Find the best store for your preferences.</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<p class="section-title">Example Use Cases</p>', unsafe_allow_html=True)

with st.expander("Finding the Best Price", expanded=True):
    st.markdown("""
    **Scenario:** You want to buy "Select Elite Cartridge - Blue Dream 0.5g"

    **Price Comparison (within 10 miles of Rockville):**

    | Dispensary | Price | Distance |
    |------------|-------|----------|
    | Green Valley | $42 | 2.1 mi |
    | Herbal Solutions | $45 | 3.5 mi |
    | Wellness Center | $48 | 5.2 mi |
    | Premium Cannabis | $40 | 8.1 mi |

    **Best Value:** Premium Cannabis at $40 (save $8 vs. highest price)
    """)

with st.expander("Product Availability Search"):
    st.markdown("""
    **Scenario:** Looking for "Cookies - Gary Payton 3.5g" (limited availability strain)

    **Search Results:**

    | Dispensary | In Stock | Price | Last Updated |
    |------------|----------|-------|--------------|
    | Capital Cannabis | Yes | $65 | Today |
    | Metro Dispensary | Yes | $62 | Today |
    | Green Leaf | No | - | - |
    | Herbal Heights | No | - | - |

    **Only 2 of 8 nearby dispensaries have this product in stock!**
    """)

st.markdown("""
<div class="cta-section">
    <h4 style="margin: 0 0 0.5rem 0; color: #1e3a5f;">Coming Soon</h4>
    <p style="margin: 0 0 1rem 0; color: #6c757d;">Consumer features are coming soon. Register on the home page to be notified when we launch.</p>
</div>
""", unsafe_allow_html=True)

st.page_link("Home.py", label="Back to Home", use_container_width=True)
