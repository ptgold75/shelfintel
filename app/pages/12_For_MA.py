# app/pages/12_For_MA.py
"""For M&A Due Diligence - Detailed use cases and features."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st

st.set_page_config(page_title="M&A Due Diligence | CannLinx", page_icon=None, layout="wide")

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
    <h1>M&A Due Diligence</h1>
    <p>Validate acquisition targets with real market data. Assess market position, competitive threats, and growth potential before you invest.</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="stats-row">
    <div class="stat-box">
        <h3>72</h3>
        <p>Retail Locations</p>
    </div>
    <div class="stat-box">
        <h3>90+</h3>
        <p>Brands Analyzed</p>
    </div>
    <div class="stat-box">
        <h3>Daily</h3>
        <p>Market Data</p>
    </div>
    <div class="stat-box">
        <h3>Historical</h3>
        <p>Trend Data</p>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<p class="section-title">Due Diligence Capabilities</p>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="use-case-card">
        <h4>Target Company Analysis</h4>
        <p>Validate target's market claims with real data. Assess actual distribution footprint vs. stated coverage. Verify shelf presence at claimed accounts.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Market Position Assessment</h4>
        <p>Understand target's true competitive position. Compare distribution vs. category leaders. Identify market share trends over time.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Competitive Benchmarking</h4>
        <p>Compare target against direct competitors. Analyze relative strengths and weaknesses. Identify competitive threats and opportunities.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Distribution Footprint Verification</h4>
        <p>Map actual retail presence vs. management claims. Identify key accounts and concentration risks. Assess geographic coverage quality.</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="use-case-card">
        <h4>Pricing Power Analysis</h4>
        <p>Assess target's pricing relative to market. Evaluate premium positioning sustainability. Identify margin compression risks.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Growth Trajectory Validation</h4>
        <p>Track historical distribution growth. Validate management's growth narrative. Assess momentum vs. peers.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Account Quality Assessment</h4>
        <p>Evaluate quality of retail relationships. Identify strategic vs. low-value accounts. Assess customer concentration risk.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="use-case-card">
        <h4>Red Flag Identification</h4>
        <p>Spot discrepancies between claims and reality. Identify declining distribution trends. Flag competitive vulnerabilities.</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<p class="section-title">Sample Due Diligence Report</p>', unsafe_allow_html=True)

with st.expander("Target Overview", expanded=True):
    st.markdown("""
    **Target:** "Green Valley Brands" (Multi-brand cannabis company)

    **Management Claims:**
    - "Leading flower brand in Maryland"
    - "Present in 85% of dispensaries"
    - "Premium pricing with strong margins"
    - "Rapid growth trajectory"

    **CannLinx Verification:**
    | Claim | Stated | Verified | Assessment |
    |-------|--------|----------|------------|
    | Distribution | 85% | 62% | Overstated |
    | Category Rank | #1 | #4 | Overstated |
    | Price Premium | +15% | +8% | Partially True |
    | YoY Growth | +40% | +22% | Overstated |
    """)

with st.expander("Competitive Position Analysis"):
    st.markdown("""
    **Category: Premium Flower**

    **Market Leaders (by distribution):**
    | Rank | Brand | Coverage | Avg Price | Trend |
    |------|-------|----------|-----------|-------|
    | 1 | Curio | 92% | $55 | Stable |
    | 2 | Verano | 88% | $52 | Growing |
    | 3 | Evermore | 78% | $58 | Stable |
    | 4 | **Target** | 62% | $50 | Declining |
    | 5 | District | 58% | $48 | Growing |

    **Concern:** Target is #4, not #1 as claimed. Distribution declining while competitors grow.
    """)

with st.expander("Risk Summary"):
    st.markdown("""
    **Key Findings:**

    **Red Flags:**
    - Distribution overstated by 23 percentage points
    - Declining market position (lost 8% coverage in 6 months)
    - Below-average penetration in growth markets
    - Price premium narrowing vs. competitors

    **Mitigating Factors:**
    - Strong brand recognition
    - Loyal customer base at existing accounts
    - New product pipeline could drive growth

    **Recommendation:** Adjust valuation to reflect actual market position. Consider earn-out structure tied to distribution milestones.
    """)

st.markdown("""
<div class="cta-section">
    <h4 style="margin: 0 0 0.5rem 0; color: #1e3a5f;">Get Started</h4>
    <p style="margin: 0 0 1rem 0; color: #6c757d;">Contact us for custom due diligence reports on acquisition targets.</p>
</div>
""", unsafe_allow_html=True)

st.page_link("Home.py", label="Back to Home", use_container_width=True)
