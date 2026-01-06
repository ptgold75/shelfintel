# app/pages/9_For_Dispensaries.py
"""For Dispensaries - Detailed use cases and features."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st

st.set_page_config(page_title="For Dispensaries | CannLinx", page_icon=None, layout="wide")

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
    <h1>For Dispensaries</h1>
    <p>Stay competitive in your market. Compare your menu, pricing, and selection against nearby competitors. Identify gaps and opportunities.</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="stats-row">
    <div class="stat-box">
        <h3>72</h3>
        <p>MD Dispensaries</p>
    </div>
    <div class="stat-box">
        <h3>Daily</h3>
        <p>Menu Updates</p>
    </div>
    <div class="stat-box">
        <h3>700+</h3>
        <p>Products Tracked</p>
    </div>
    <div class="stat-box">
        <h3>90+</h3>
        <p>Brands</p>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<p class="section-title">What You Can Do</p>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="use-case-card">
        <h4>Competitor Menu Comparison</h4>
        <p>See exactly what products nearby competitors carry. Compare your selection against stores within 1-5 miles. Identify products they have that you don't.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Price Positioning Analysis</h4>
        <p>Compare your prices against local competitors. Identify where you're priced above or below market. Make data-driven pricing decisions.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Product Gap Identification</h4>
        <p>Find products popular at competitors that you don't carry. Identify brands with strong market presence missing from your menu. Fill gaps to capture more customers.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Category Mix Optimization</h4>
        <p>Compare your category breakdown vs. market averages. See if you're over or under-indexed in flower, vapes, edibles, etc. Optimize your product mix.</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="use-case-card">
        <h4>New Product Alerts</h4>
        <p>Get notified when competitors add new products. Stay ahead of market trends. Be early to stock trending products.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Brand Performance Tracking</h4>
        <p>See which brands are expanding their presence. Identify rising stars and declining brands. Make informed purchasing decisions.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Regional Trends</h4>
        <p>Understand what's popular in your area vs. statewide. Tailor your selection to local preferences. Track regional category trends.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Vendor Negotiations</h4>
        <p>Use market data in vendor discussions. Know the actual street prices of products. Negotiate better terms with suppliers.</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<p class="section-title">Sample Insights</p>', unsafe_allow_html=True)

with st.expander("Competitor Comparison", expanded=True):
    st.markdown("""
    **Your Store:** "Green Valley Dispensary" (Rockville)

    **Nearby Competitors (within 3 miles):** 4 stores

    **Menu Comparison:**
    | Metric | Your Store | Avg Competitor | Gap |
    |--------|-----------|----------------|-----|
    | Total Products | 245 | 312 | -67 |
    | Flower SKUs | 85 | 102 | -17 |
    | Vape SKUs | 62 | 78 | -16 |
    | Edible SKUs | 48 | 65 | -17 |

    **Key Finding:** You have fewer products than average in all categories. Focus on expanding vape and edible selection.
    """)

with st.expander("Price Positioning"):
    st.markdown("""
    **Category:** 3.5g Flower

    **Your Average Price:** $48.50
    **Market Average (3-mile radius):** $45.25

    **By Brand:**
    | Brand | Your Price | Market Avg | Difference |
    |-------|-----------|------------|------------|
    | Curio | $55 | $52 | +$3 |
    | Verano | $50 | $48 | +$2 |
    | District | $45 | $42 | +$3 |

    **Recommendation:** Your flower prices are 7% above market. Consider promotional pricing on slow-moving SKUs.
    """)

st.markdown("""
<div class="cta-section">
    <h4 style="margin: 0 0 0.5rem 0; color: #1e3a5f;">Ready to Get Started?</h4>
    <p style="margin: 0 0 1rem 0; color: #6c757d;">Register on the home page to get access to competitive intelligence for your dispensary.</p>
</div>
""", unsafe_allow_html=True)

st.page_link("Home.py", label="Back to Home", use_container_width=True)
