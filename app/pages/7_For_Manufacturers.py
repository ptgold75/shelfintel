# app/pages/7_For_Manufacturers.py
"""For Manufacturers - Detailed use cases and features."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st

st.set_page_config(page_title="For Manufacturers | CannaLinx", page_icon=None, layout="wide")

st.markdown("""
<style>
    .block-container {padding-top: 1rem; max-width: 1100px;}

    /* Hero section */
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

    /* Stats row */
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

    /* Use case cards */
    .use-case-card {
        background: white;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transition: box-shadow 0.2s;
    }
    .use-case-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .use-case-card h4 {
        margin: 0 0 0.5rem 0;
        color: #1e3a5f;
        font-size: 1rem;
        font-weight: 600;
    }
    .use-case-card p {
        margin: 0;
        color: #495057;
        font-size: 0.9rem;
        line-height: 1.5;
    }

    /* Section headers */
    .section-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #1e3a5f;
        margin: 1.5rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #e9ecef;
    }

    /* Example box */
    .example-box {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 1.25rem;
        margin-bottom: 1rem;
    }
    .example-box h5 {
        margin: 0 0 0.75rem 0;
        color: #1e3a5f;
        font-size: 1rem;
    }

    /* CTA section */
    .cta-section {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 1.5rem;
        text-align: center;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Hero section
st.markdown("""
<div class="hero-section">
    <h1>For Manufacturers & Growers</h1>
    <p>Track your products from cultivation to shelf. Know exactly where your products are stocked, how they're priced, and where to expand.</p>
</div>
""", unsafe_allow_html=True)

# Stats row
st.markdown("""
<div class="stats-row">
    <div class="stat-box">
        <h3>72</h3>
        <p>Dispensaries Tracked</p>
    </div>
    <div class="stat-box">
        <h3>Daily</h3>
        <p>Menu Updates</p>
    </div>
    <div class="stat-box">
        <h3>23</h3>
        <p>MD Counties</p>
    </div>
    <div class="stat-box">
        <h3>100%</h3>
        <p>Real Market Data</p>
    </div>
</div>
""", unsafe_allow_html=True)

# Use Cases section
st.markdown('<p class="section-title">What You Can Do</p>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="use-case-card">
        <h4>Distribution Coverage Mapping</h4>
        <p>See exactly which dispensaries carry your products. Identify white space opportunities where competitors are stocked but you're not. Track expansion progress over time.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Retail Price Monitoring</h4>
        <p>Monitor how dispensaries price your products vs. your MSRP. Identify retailers pricing above or below market. Ensure pricing consistency across your distribution network.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Market Share Analysis</h4>
        <p>Understand your shelf presence relative to competitors. Track share by category (flower, concentrates, edibles) and by region. Benchmark against state averages.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>New Product Launch Tracking</h4>
        <p>Monitor rollout of new SKUs across your distribution network. Track adoption rate by retailer. Identify which dispensaries are slow to stock new products.</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="use-case-card">
        <h4>Sales Territory Intelligence</h4>
        <p>Equip your sales team with actionable data. Show reps which accounts are missing products. Prioritize calls based on opportunity size.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Competitor Tracking</h4>
        <p>Monitor competitor distribution and pricing. See when competitors launch new products. Track their expansion into new dispensaries.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Account Compliance</h4>
        <p>Verify retailers are carrying agreed-upon SKUs. Monitor promotional pricing compliance. Track out-of-stock situations by account.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>SKU Rationalization</h4>
        <p>Identify underperforming SKUs with limited distribution. Find products that aren't getting shelf space. Make data-driven decisions on product portfolio.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Brand Integrity & Image Audit</h4>
        <p>See exactly how your products are displayed at each dispensary. Audit product images for quality, consistency, and brand compliance. Identify retailers using poor or incorrect product photos.</p>
    </div>
    """, unsafe_allow_html=True)

# Example insights section
st.markdown('<p class="section-title">Sample Insights</p>', unsafe_allow_html=True)

with st.expander("Distribution Gap Analysis", expanded=True):
    st.markdown("""
    **Scenario:** You manufacture "Green Valley Farms" flower products.

    **Current State:**
    - Your products are carried by 45 of 72 dispensaries (63% distribution)
    - Top competitor "Blue Ridge Cultivators" has 82% distribution

    **Gap by Region:**
    | Region | Your Coverage | Competitor | Gap |
    |--------|--------------|------------|-----|
    | Montgomery County | 5 of 15 | 12 of 15 | -7 |
    | Baltimore County | 8 of 18 | 15 of 18 | -7 |
    | Prince George's | 10 of 12 | 11 of 12 | -1 |

    **Recommendation:** Focus sales efforts on Montgomery and Baltimore counties where you have the largest gap vs. competition.
    """)

with st.expander("Pricing Intelligence"):
    st.markdown("""
    **Product:** Your 3.5g flower (MSRP: $45)

    **Market Analysis:**
    - Average retail price across all dispensaries: $47.50
    - 23 dispensaries price at $45 (MSRP)
    - 15 dispensaries price at $50+
    - 7 dispensaries price below $40

    **Recommendation:** Work with high-price retailers on promotional opportunities. Investigate why some retailers are discounting below MSRP.
    """)

with st.expander("Brand Integrity Audit"):
    st.markdown("""
    **Product:** Your "Sunset Sherbet" 3.5g flower

    **Image Audit Results:**
    - Carried by 45 dispensaries
    - 38 dispensaries using approved product image
    - 4 dispensaries using generic/stock photos
    - 3 dispensaries with no product image

    **Issues Found:**
    | Dispensary | Issue |
    |------------|-------|
    | Store A | Using outdated packaging photo |
    | Store B | Low resolution image |
    | Store C | No image uploaded |

    **Recommendation:** Contact stores with image issues and provide approved marketing assets. Consider requiring image compliance in distribution agreements.
    """)

# CTA section
st.markdown("""
<div class="cta-section">
    <h4 style="margin: 0 0 0.5rem 0; color: #1e3a5f;">Ready to Get Started?</h4>
    <p style="margin: 0 0 1rem 0; color: #6c757d;">Register on the home page to get access to manufacturer insights tailored to your products.</p>
</div>
""", unsafe_allow_html=True)

st.page_link("Home.py", label="Back to Home", use_container_width=True)
