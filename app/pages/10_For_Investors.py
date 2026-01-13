# app/pages/10_For_Investors.py
"""For Investors - Detailed use cases and features."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st

st.set_page_config(page_title="For Investors | CannLinx", page_icon=None, layout="wide")

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
    <h1>For Investors</h1>
    <p>Make informed investment decisions with real market data. Track brand performance, market sizing, competitive dynamics, and growth trends.</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="stats-row">
    <div class="stat-box">
        <h3>$1.8B+</h3>
        <p>MD Market Size</p>
    </div>
    <div class="stat-box">
        <h3>90+</h3>
        <p>Brands Tracked</p>
    </div>
    <div class="stat-box">
        <h3>72</h3>
        <p>Dispensaries</p>
    </div>
    <div class="stat-box">
        <h3>Daily</h3>
        <p>Data Updates</p>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<p class="section-title">What You Can Do</p>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="use-case-card">
        <h4>Market Sizing & TAM Analysis</h4>
        <p>Understand total addressable market by state and category. Track market growth over time. Compare state markets for investment prioritization.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Brand Performance Metrics</h4>
        <p>Evaluate brand distribution and market penetration. Track brand growth trajectories. Identify market leaders and emerging challengers.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Competitive Landscape Mapping</h4>
        <p>Understand competitive dynamics by category. Track market concentration and fragmentation. Identify consolidation opportunities.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Portfolio Company Monitoring</h4>
        <p>Track portfolio company shelf presence and pricing. Monitor competitive threats. Validate management claims with real market data.</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="use-case-card">
        <h4>Growth Trend Analysis</h4>
        <p>Identify fastest-growing categories and brands. Track category shifts over time. Spot emerging product trends early.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Price Point Analysis</h4>
        <p>Understand pricing dynamics by category and brand. Track price compression trends. Analyze margin potential across segments.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Retail Network Analysis</h4>
        <p>Map dispensary networks and ownership. Track retail expansion patterns. Identify acquisition targets with strong market positions.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Due Diligence Support</h4>
        <p>Validate investment opportunities with real data. Compare target performance vs. peers. Identify red flags in market positioning.</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<p class="section-title">Sample Insights</p>', unsafe_allow_html=True)

with st.expander("Market Overview", expanded=True):
    st.markdown("""
    **Maryland Cannabis Market Snapshot**

    **Market Size:** $1.8B annual sales (2024)
    **YoY Growth:** +22%
    **Licensed Dispensaries:** 108
    **Active Brands:** 500+

    **Category Breakdown:**
    | Category | Market Share | YoY Change |
    |----------|-------------|------------|
    | Flower | 45% | -3% |
    | Vapes | 28% | +5% |
    | Edibles | 15% | +8% |
    | Concentrates | 8% | +2% |
    | Other | 4% | -2% |

    **Key Trend:** Vapes and edibles gaining share as market matures.
    """)

with st.expander("Brand Performance"):
    st.markdown("""
    **Top 5 Brands by Distribution (Flower Category)**

    | Rank | Brand | Coverage | Avg Price | YoY Change |
    |------|-------|----------|-----------|------------|
    | 1 | Curio Wellness | 92% | $52 | +5% |
    | 2 | Verano | 88% | $48 | +12% |
    | 3 | District Cannabis | 85% | $45 | +8% |
    | 4 | Evermore | 78% | $50 | -2% |
    | 5 | Culta | 72% | $55 | +3% |

    **Emerging Brand to Watch:** "Green Thumb Industries" - grew from 25% to 58% coverage in 6 months.
    """)

st.markdown("""
<div class="cta-section">
    <h4 style="margin: 0 0 0.5rem 0; color: #1e3a5f;">Ready to Get Started?</h4>
    <p style="margin: 0 0 1rem 0; color: #6c757d;">Register on the home page to get access to investor-grade market intelligence.</p>
</div>
""", unsafe_allow_html=True)

st.page_link("Home.py", label="Back to Home", width="stretch")
