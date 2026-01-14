# app/pages/99_Data_Licensing.py
"""Data Licensing - Purchase state-level dispensary data."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
from sqlalchemy import text
from core.db import get_engine

st.set_page_config(
    page_title="Data Licensing | CannaLinx",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import and render navigation
from components.sidebar_nav import render_nav
render_nav(require_login=False)

st.title("Cannabis Retail Data Licensing")
st.markdown("### Comprehensive dispensary and smoke shop data, available by state")

st.divider()

# Pricing section
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("""
    ## $2,500 per State

    Get complete, verified data for licensed cannabis dispensaries in any US state.

    ### What's Included

    Each state dataset includes the following fields for every location:

    | Field | Description | Coverage |
    |-------|-------------|----------|
    | **Company Name** | Official business name | 100% |
    | **Street Address** | Full street address | 100% |
    | **City** | City/municipality | 100% |
    | **State** | State code | 100% |
    | **ZIP Code** | Postal code | 95%+ |
    | **County** | County name | 90%+ |
    | **Phone Number** | Business phone | 40-60% |
    | **Email Address** | Contact email | Where available |
    | **Website URL** | Menu or company website | 70-95% |
    | **Menu Provider** | Dutchie, Jane, Leafly, etc. | Where detected |
    | **Store Type** | Dispensary, smoke shop, or unverified | 100% |
    """)

with col2:
    st.markdown("""
    ### Quick Facts
    """)

    # Load state stats
    @st.cache_data(ttl=3600)
    def load_state_stats():
        engine = get_engine()
        with engine.connect() as conn:
            df = pd.read_sql(text("""
                SELECT
                    state,
                    SUM(CASE WHEN store_type = 'dispensary' THEN 1 ELSE 0 END) as dispensaries,
                    SUM(CASE WHEN store_type = 'smoke_shop' THEN 1 ELSE 0 END) as smoke_shops,
                    SUM(CASE WHEN phone IS NOT NULL AND phone != '' THEN 1 ELSE 0 END) as with_phone,
                    SUM(CASE WHEN menu_url IS NOT NULL AND menu_url != '' THEN 1 ELSE 0 END) as with_url
                FROM dispensary
                WHERE is_active = true
                GROUP BY state
                ORDER BY dispensaries DESC
            """), conn)
            return df

    try:
        state_stats = load_state_stats()
        total_dispensaries = state_stats['dispensaries'].sum()
        total_smoke_shops = state_stats['smoke_shops'].sum()
        total_states = len(state_stats)

        st.metric("Total Dispensaries", f"{total_dispensaries:,}")
        st.metric("Smoke Shops Tracked", f"{total_smoke_shops:,}")
        st.metric("States Covered", f"{total_states}")

        st.markdown("---")
        st.markdown("### Contact Sales")
        st.markdown("""
        **Email:** sales@cannlinx.com

        **Volume Discounts:**
        - 5+ states: 10% off
        - 10+ states: 20% off
        - All 50 states: Contact us

        **Enterprise API:** Custom pricing
        """)
    except:
        st.info("Contact sales@cannlinx.com for pricing")

# Horizontal info boxes
st.markdown("""
<style>
.info-box {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 1.25rem;
    height: 100%;
}
.info-box h4 {
    color: #1e3a5f;
    margin: 0 0 0.75rem 0;
    font-size: 1rem;
    font-weight: 600;
}
.info-box ul {
    margin: 0;
    padding-left: 1.2rem;
    color: #475569;
    font-size: 0.9rem;
}
.info-box li {
    margin-bottom: 0.4rem;
}
</style>
""", unsafe_allow_html=True)

box1, box2, box3 = st.columns(3)

with box1:
    st.markdown("""
    <div class="info-box">
        <h4>Data Quality</h4>
        <ul>
            <li><strong>Verified</strong> against state licensing databases</li>
            <li><strong>Cross-referenced</strong> with Google Places</li>
            <li><strong>Updated regularly</strong> with new openings/closures</li>
            <li><strong>Classified</strong> by store type</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with box2:
    st.markdown("""
    <div class="info-box">
        <h4>Delivery Format</h4>
        <ul>
            <li>CSV or Excel format</li>
            <li>JSON available upon request</li>
            <li>API access for enterprise</li>
            <li>One-time or subscription</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with box3:
    st.markdown("""
    <div class="info-box">
        <h4>Use Cases</h4>
        <ul>
            <li>Market research & competitive analysis</li>
            <li>Sales prospecting</li>
            <li>Location intelligence</li>
            <li>Investment due diligence</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# State availability table
st.markdown("## Available States")
st.markdown("Browse data availability by state. Click any state to see sample data.")

@st.cache_data(ttl=3600)
def load_detailed_state_stats():
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text("""
            SELECT
                state as "State",
                SUM(CASE WHEN store_type = 'dispensary' THEN 1 ELSE 0 END) as "Dispensaries",
                SUM(CASE WHEN store_type = 'smoke_shop' THEN 1 ELSE 0 END) as "Smoke Shops",
                ROUND(100.0 * SUM(CASE WHEN menu_url IS NOT NULL AND menu_url != '' THEN 1 ELSE 0 END) /
                      NULLIF(COUNT(*), 0), 0) as "URL Coverage %",
                ROUND(100.0 * SUM(CASE WHEN phone IS NOT NULL AND phone != '' THEN 1 ELSE 0 END) /
                      NULLIF(COUNT(*), 0), 0) as "Phone Coverage %"
            FROM dispensary
            WHERE is_active = true
            GROUP BY state
            HAVING SUM(CASE WHEN store_type = 'dispensary' THEN 1 ELSE 0 END) > 0
            ORDER BY "Dispensaries" DESC
        """), conn)
        return df

try:
    detailed_stats = load_detailed_state_stats()

    # Add pricing column
    detailed_stats['Price'] = '$2,500'

    # Display in a nice table
    st.dataframe(
        detailed_stats.style.format({
            'Dispensaries': '{:,}',
            'Smoke Shops': '{:,}',
            'URL Coverage %': '{:.0f}%',
            'Phone Coverage %': '{:.0f}%'
        }),
        use_container_width=True,
        height=600
    )

except Exception as e:
    st.error(f"Error loading state data: {e}")

st.divider()

# Sample data section
st.markdown("## Sample Data Preview")
st.markdown("See what's included in each state dataset.")

@st.cache_data(ttl=3600)
def load_sample_data(state):
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text("""
            SELECT
                name as "Company Name",
                address as "Address",
                city as "City",
                state as "State",
                zip as "ZIP",
                county as "County",
                CASE WHEN phone IS NOT NULL AND phone != '' THEN phone ELSE '—' END as "Phone",
                CASE WHEN menu_url IS NOT NULL AND menu_url != '' THEN menu_url ELSE '—' END as "Website",
                store_type as "Type"
            FROM dispensary
            WHERE is_active = true
            AND state = :state
            AND store_type = 'dispensary'
            ORDER BY city, name
            LIMIT 10
        """), conn, params={"state": state})
        return df

# State selector for sample
sample_col1, sample_col2 = st.columns([1, 3])

with sample_col1:
    try:
        states_list = detailed_stats['State'].tolist()
        selected_state = st.selectbox(
            "Select state to preview",
            states_list,
            index=0 if states_list else None
        )
    except:
        selected_state = "CA"
        st.selectbox("Select state to preview", ["CA"])

with sample_col2:
    if selected_state:
        try:
            sample = load_sample_data(selected_state)
            st.markdown(f"**Sample of {selected_state} data** (showing 10 of {detailed_stats[detailed_stats['State']==selected_state]['Dispensaries'].values[0]:,} dispensaries)")

            # Truncate URLs for display
            if 'Website' in sample.columns:
                sample['Website'] = sample['Website'].apply(lambda x: x[:50] + '...' if len(str(x)) > 50 else x)

            st.dataframe(sample, use_container_width=True, hide_index=True)
        except Exception as e:
            st.info("Select a state to see sample data")

st.divider()

# Smoke shop data section
st.markdown("## Smoke Shop / Gray Market Data")
st.markdown("""
In addition to licensed dispensaries, we track **CBD stores, Delta-8 shops, and smoke shops** separately.

This data is valuable for:
- Understanding the gray market opportunity
- Identifying unlicensed competition
- Tracking hemp-derived cannabinoid retail expansion

**Smoke shop data is included FREE** with any state dispensary purchase.
""")

st.divider()

# Contact form
st.markdown("## Request Data")

with st.form("data_request"):
    col1, col2 = st.columns(2)

    with col1:
        name = st.text_input("Your Name")
        email = st.text_input("Email Address")
        company = st.text_input("Company Name")

    with col2:
        states_interested = st.multiselect(
            "States of Interest",
            detailed_stats['State'].tolist() if 'detailed_stats' in dir() else ["CA", "CO", "FL", "NY", "TX"],
            default=[]
        )
        use_case = st.selectbox(
            "Primary Use Case",
            ["Market Research", "Sales Prospecting", "Investment Analysis", "Compliance", "Other"]
        )
        message = st.text_area("Additional Notes", height=100)

    submitted = st.form_submit_button("Submit Request", type="primary")

    if submitted:
        if name and email:
            st.success(f"""
            Thank you for your interest! We'll contact you at {email} within 24 hours.

            **Your Request:**
            - States: {', '.join(states_interested) if states_interested else 'Not specified'}
            - Use Case: {use_case}
            """)
            # TODO: Actually send this to a database or email
        else:
            st.error("Please provide your name and email address.")

st.divider()
st.caption("CannaLinx Data Licensing | sales@cannlinx.com | Data updated daily")
