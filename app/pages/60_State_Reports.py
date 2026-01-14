# app/pages/60_State_Reports.py
"""State Reports - Comprehensive state-level cannabis market intelligence."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="State Reports - CannaLinx", layout="wide")

# Navigation
from components.sidebar_nav import render_nav
render_nav(require_login=False)

# Import shared styles
from components.styles import get_page_styles, COLORS
st.markdown(get_page_styles(), unsafe_allow_html=True)

st.title("State Cannabis Market Reports")
st.markdown("Comprehensive state-level regulatory and market intelligence")

# State selector
AVAILABLE_STATES = {
    "CA": "California",
    "NJ": "New Jersey",
    "MD": "Maryland",
    "IL": "Illinois",
    "PA": "Pennsylvania",
}

selected_state = st.selectbox(
    "Select State",
    options=list(AVAILABLE_STATES.keys()),
    format_func=lambda x: AVAILABLE_STATES[x],
    index=0
)

st.divider()

# ==============================================================================
# CALIFORNIA REPORT
# ==============================================================================
if selected_state == "CA":
    st.header("California Cannabis Market Report")
    st.caption("Data as of January 2026 | Source: California Department of Cannabis Control")

    # Key Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Active Licenses", "8,252")
    with col2:
        st.metric("Retail Licenses", "1,450", help="Storefront dispensaries (not smoke shops)")
    with col3:
        st.metric("Cultivation Licenses", "4,711")
    with col4:
        st.metric("Manufacturing Licenses", "559")

    # Tabs for different sections
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Overview", "License Breakdown", "Geographic Distribution", "Major Companies", "Regulatory Notes"
    ])

    with tab1:
        st.subheader("Market Overview")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            ### California Cannabis Market

            California has the **largest legal cannabis market** in the United States, with:
            - **8,252 active licenses** across all categories
            - **1,450 retail cannabis licenses** (storefront dispensaries)
            - **285 non-storefront/delivery** retailers
            - **4,711 cultivation licenses** across 19 different types
            - **559 manufacturing licenses**

            #### Key Facts
            - Recreational cannabis legalized: **November 2016** (Prop 64)
            - Sales began: **January 2018**
            - Medical program started: **1996** (first in US)
            - Estimated annual sales: **$4.4 billion** (2023)
            """)

        with col2:
            # License breakdown pie chart
            license_data = pd.DataFrame({
                'Type': ['Cultivation', 'Retail', 'Distribution', 'Manufacturing', 'Microbusiness', 'Retail Delivery', 'Transport', 'Events', 'Testing'],
                'Count': [4711, 1450, 927, 559, 364, 285, 132, 35, 23]
            })

            fig = px.pie(license_data, values='Count', names='Type',
                        title='License Distribution by Type',
                        color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)

        # Additional stats
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Jurisdictions Allowing Cannabis", "167", delta="31% of 539")
        with col2:
            st.metric("Jurisdictions Banning", "372", delta="69% ban some/all")
        with col3:
            st.metric("Counties with Licenses", "28+")

    with tab2:
        st.subheader("License Type Breakdown")

        # Detailed license table
        license_details = pd.DataFrame([
            {"Category": "Retail (Storefront)", "License Type": "Type 10", "Count": 1450, "Notes": "Brick-and-mortar dispensaries"},
            {"Category": "Retail (Delivery)", "License Type": "Type 9", "Count": 285, "Notes": "Non-storefront/delivery only"},
            {"Category": "Cultivation - Small", "License Type": "Type 1/1A/1B/1C/1D", "Count": 2800, "Notes": "Up to 10,000 sq ft canopy"},
            {"Category": "Cultivation - Medium", "License Type": "Type 2/2A/2B", "Count": 1200, "Notes": "10,001-22,000 sq ft"},
            {"Category": "Cultivation - Large", "License Type": "Type 3/3A/3B/5/5A/5B", "Count": 500, "Notes": "22,001+ sq ft"},
            {"Category": "Cultivation - Nursery", "License Type": "Type 4", "Count": 200, "Notes": "Immature plants only"},
            {"Category": "Manufacturing - Volatile", "License Type": "Type 7", "Count": 150, "Notes": "Butane, propane extraction"},
            {"Category": "Manufacturing - Non-Volatile", "License Type": "Type 6", "Count": 371, "Notes": "CO2, ethanol, mechanical"},
            {"Category": "Manufacturing - Infusion", "License Type": "Type N", "Count": 55, "Notes": "Infused products"},
            {"Category": "Manufacturing - Packaging", "License Type": "Type P", "Count": 23, "Notes": "Packaging/labeling only"},
            {"Category": "Distribution", "License Type": "Distributor", "Count": 927, "Notes": "Transport, testing, wholesale"},
            {"Category": "Distribution (Transport)", "License Type": "Transport Only", "Count": 132, "Notes": "Transport only"},
            {"Category": "Microbusiness", "License Type": "Microbusiness", "Count": 364, "Notes": "3+ activities combined"},
            {"Category": "Testing", "License Type": "Testing Lab", "Count": 23, "Notes": "Quality/safety testing"},
            {"Category": "Events", "License Type": "Event Organizer", "Count": 35, "Notes": "Cannabis events"},
        ])

        st.dataframe(license_details, use_container_width=True, hide_index=True)

        # Cultivation types detail
        st.markdown("---")
        st.subheader("Cultivation License Types")

        cult_types = pd.DataFrame([
            {"Type": "Small Outdoor", "Code": "Type 1", "Max Canopy": "5,000 sq ft"},
            {"Type": "Small Outdoor", "Code": "Type 1A", "Max Canopy": "5,001-10,000 sq ft"},
            {"Type": "Small Indoor", "Code": "Type 1C", "Max Canopy": "5,000 sq ft"},
            {"Type": "Small Mixed-Light Tier 1", "Code": "Type 1B", "Max Canopy": "5,000 sq ft"},
            {"Type": "Small Mixed-Light Tier 2", "Code": "Type 1D", "Max Canopy": "5,000 sq ft"},
            {"Type": "Medium Outdoor", "Code": "Type 2", "Max Canopy": "10,001+ sq ft"},
            {"Type": "Medium Indoor", "Code": "Type 2A", "Max Canopy": "5,001-10,000 sq ft"},
            {"Type": "Medium Mixed-Light", "Code": "Type 2B", "Max Canopy": "5,001-10,000 sq ft"},
            {"Type": "Large Indoor", "Code": "Type 3", "Max Canopy": "10,001-22,000 sq ft"},
            {"Type": "Large Mixed-Light", "Code": "Type 3A/3B", "Max Canopy": "10,001-22,000 sq ft"},
            {"Type": "Large Outdoor", "Code": "Type 5", "Max Canopy": "1+ acre"},
            {"Type": "Large Indoor", "Code": "Type 5A", "Max Canopy": "22,001+ sq ft"},
            {"Type": "Large Mixed-Light", "Code": "Type 5B", "Max Canopy": "22,001+ sq ft"},
            {"Type": "Nursery", "Code": "Type 4", "Max Canopy": "Varies"},
            {"Type": "Processor", "Code": "Processor", "Max Canopy": "N/A"},
        ])

        st.dataframe(cult_types, use_container_width=True, hide_index=True)

    with tab3:
        st.subheader("Geographic Distribution")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Top Counties by License Count")

            county_data = pd.DataFrame({
                'County': ['Alameda', 'Los Angeles', 'Riverside', 'Humboldt', 'Monterey',
                          'San Diego', 'Santa Barbara', 'Mendocino', 'Sacramento', 'San Francisco'],
                'Licenses': [114, 90, 84, 60, 42, 35, 30, 28, 25, 20]
            })

            fig = px.bar(county_data, x='Licenses', y='County', orientation='h',
                        title='Top 10 Counties (Manufacturing Licenses)',
                        color='Licenses', color_continuous_scale='Viridis')
            fig.update_layout(yaxis={'categoryorder': 'total ascending'}, height=400)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("#### Top Cities by License Count")

            city_data = pd.DataFrame({
                'City': ['Los Angeles', 'Oakland', 'San Francisco', 'San Diego', 'Sacramento',
                        'Desert Hot Springs', 'Long Beach', 'Santa Rosa', 'Cathedral City', 'Palm Springs'],
                'Licenses': [180, 97, 85, 75, 60, 45, 30, 35, 32, 28]
            })

            fig2 = px.bar(city_data, x='Licenses', y='City', orientation='h',
                         title='Top 10 Cities (All License Types)',
                         color='Licenses', color_continuous_scale='Greens')
            fig2.update_layout(yaxis={'categoryorder': 'total ascending'}, height=400)
            st.plotly_chart(fig2, use_container_width=True)

        # Cultivation hotspots
        st.markdown("---")
        st.subheader("Cultivation Regions")

        st.markdown("""
        **Emerald Triangle** (Humboldt, Mendocino, Trinity counties):
        - Historic cannabis cultivation region
        - Highest concentration of outdoor/mixed-light licenses
        - Known for craft/artisan cannabis

        **Central Coast** (Monterey, Santa Barbara, San Luis Obispo):
        - Growing cultivation hub
        - Mix of indoor and greenhouse operations

        **Coachella Valley** (Riverside County):
        - Major manufacturing and cultivation hub
        - Desert Hot Springs, Cathedral City, Palm Springs
        - Climate favorable for year-round cultivation
        """)

    with tab4:
        st.subheader("Major California Cannabis Companies")

        # MSOs and major operators
        st.markdown("#### Multi-State Operators (MSOs) in California")

        mso_data = pd.DataFrame([
            {"Company": "Curaleaf", "Type": "MSO", "Operations": "Retail, Cultivation, Manufacturing"},
            {"Company": "Trulieve", "Type": "MSO", "Operations": "Retail, Cultivation"},
            {"Company": "Verano", "Type": "MSO", "Operations": "Retail, Manufacturing"},
            {"Company": "Green Thumb Industries", "Type": "MSO", "Operations": "Retail"},
            {"Company": "Cresco Labs", "Type": "MSO", "Operations": "Manufacturing, Distribution"},
        ])
        st.dataframe(mso_data, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("#### Major California-Based Companies")

        ca_companies = pd.DataFrame([
            {"Company": "Cookies", "HQ": "San Francisco", "Category": "Brand/Retail", "Known For": "Premium flower, lifestyle brand"},
            {"Company": "Connected Cannabis", "HQ": "Sacramento", "Category": "Vertically Integrated", "Known For": "Premium flower, Alien Labs"},
            {"Company": "Stiiizy", "HQ": "Los Angeles", "Category": "Brand", "Known For": "Vape pods, largest CA brand"},
            {"Company": "Raw Garden", "HQ": "Santa Barbara", "Category": "Brand", "Known For": "Live resin, concentrates"},
            {"Company": "Kiva Confections", "HQ": "Oakland", "Category": "Brand", "Known For": "Edibles, chocolate bars"},
            {"Company": "Jetty Extracts", "HQ": "Oakland", "Category": "Brand", "Known For": "Vapes, concentrates"},
            {"Company": "PAX Labs", "HQ": "San Francisco", "Category": "Device/Brand", "Known For": "Vaporizers, Era pods"},
            {"Company": "710 Labs", "HQ": "Los Angeles", "Category": "Brand", "Known For": "Premium concentrates"},
            {"Company": "Glass House Brands", "HQ": "Long Beach", "Category": "Cultivator", "Known For": "Large-scale cultivation"},
            {"Company": "Lowell Farms", "HQ": "Santa Barbara", "Category": "Brand", "Known For": "Pre-rolls, flower"},
            {"Company": "Papa & Barkley", "HQ": "Eureka", "Category": "Brand", "Known For": "Topicals, wellness"},
            {"Company": "AbsoluteXtracts (ABX)", "HQ": "Santa Rosa", "Category": "Brand", "Known For": "Vapes, softgels"},
        ])
        st.dataframe(ca_companies, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("#### Major Distributors")

        dist_data = pd.DataFrame([
            {"Company": "Nabis", "HQ": "Oakland", "Notes": "Largest CA cannabis distributor"},
            {"Company": "Herbl", "HQ": "Oakland", "Notes": "Tech-enabled distribution"},
            {"Company": "KGB Reserve", "HQ": "Oakland", "Notes": "Premium brand distribution"},
            {"Company": "3C Farms", "HQ": "Los Angeles", "Notes": "Cultivation + distribution"},
        ])
        st.dataframe(dist_data, use_container_width=True, hide_index=True)

    with tab5:
        st.subheader("Regulatory Notes & Updates")

        st.markdown("""
        ### Key Regulatory Changes (2025-2026)

        #### Provisional License Sunset
        - **January 1, 2025**: DCC can no longer renew provisional licenses
        - **January 1, 2026**: All provisional licenses became ineffective
        - Businesses must have obtained annual licenses or ceased operations

        #### Local Control
        - 69% of California jurisdictions (cities/counties) ban some or all cannabis licenses
        - Each jurisdiction sets its own rules for permitting
        - Some cities allow retail but not cultivation, or vice versa

        #### Track-and-Trace (Metrc)
        - All licensees must use the Metrc system
        - Real-time tracking from seed to sale
        - Integration required with state database

        ### Data Sources
        - [DCC License Search](https://search.cannabis.ca.gov/)
        - [DCC Data Dashboard](https://www.cannabis.ca.gov/resources/data-dashboard/)
        - [Cannabis License Summary Report](https://www.cannabis.ca.gov/resources/data-dashboard/license-report/)

        ### How to Export License Data
        1. Go to [search.cannabis.ca.gov](https://search.cannabis.ca.gov/)
        2. Click "Advanced Search"
        3. Select license type or leave blank for all
        4. Click "Search", then "Export" → "All Data"
        5. Download CSV file

        ### Contact
        - **California DCC**: [cannabis.ca.gov](https://cannabis.ca.gov)
        - **Email**: info@cannabis.ca.gov
        - **Phone**: (844) 612-2322
        """)

# ==============================================================================
# NEW JERSEY REPORT
# ==============================================================================
elif selected_state == "NJ":
    st.header("New Jersey Cannabis Market Report")
    st.caption("Data as of January 2026 | Source: NJ Cannabis Regulatory Commission")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Dispensaries", "~60")
    with col2:
        st.metric("ATCs (Medical)", "12")
    with col3:
        st.metric("Adult-Use Retailers", "~50")
    with col4:
        st.metric("Delivery Services", "2")

    st.markdown("""
    ### New Jersey Cannabis Market

    New Jersey legalized recreational cannabis in **November 2020** (ballot measure), with sales beginning **April 21, 2022**.

    #### License Classes
    - **Class 1**: Cannabis Cultivator
    - **Class 2**: Cannabis Manufacturer
    - **Class 3**: Cannabis Wholesaler
    - **Class 4**: Cannabis Distributor
    - **Class 5**: Cannabis Retailer
    - **Class 6**: Cannabis Delivery Service

    #### Alternative Treatment Centers (ATCs)
    The original 12 medical marijuana ATCs are vertically integrated and can serve both medical patients and adult-use customers.

    ### Data Sources
    - [NJ CRC Dispensary Finder](https://www.nj.gov/cannabis/dispensaries/find/)
    - [NJ Open Data](https://data.nj.gov/)
    """)

# ==============================================================================
# MARYLAND REPORT
# ==============================================================================
elif selected_state == "MD":
    st.header("Maryland Cannabis Market Report")
    st.caption("Data from CannaLinx database")

    # Get actual stats from database
    try:
        from core.db import get_engine
        from sqlalchemy import text
        engine = get_engine()

        with engine.connect() as conn:
            dispensary_count = conn.execute(text(
                "SELECT COUNT(*) FROM dispensary WHERE state = 'MD' AND is_active = true"
            )).scalar() or 0

            product_count = conn.execute(text("""
                SELECT COUNT(DISTINCT raw_name) FROM raw_menu_item r
                JOIN dispensary d ON r.dispensary_id = d.dispensary_id
                WHERE d.state = 'MD'
            """)).scalar() or 0

            brand_count = conn.execute(text("""
                SELECT COUNT(DISTINCT raw_brand) FROM raw_menu_item r
                JOIN dispensary d ON r.dispensary_id = d.dispensary_id
                WHERE d.state = 'MD' AND r.raw_brand IS NOT NULL AND r.raw_brand != ''
            """)).scalar() or 0

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Active Dispensaries", f"{dispensary_count:,}")
        with col2:
            st.metric("Products Tracked", f"{product_count:,}")
        with col3:
            st.metric("Brands", f"{brand_count:,}")
        with col4:
            st.metric("Counties", "24")

    except Exception as e:
        st.error(f"Error loading MD data: {e}")

    st.markdown("""
    ### Maryland Cannabis Market

    Maryland legalized recreational cannabis in **November 2022** (ballot measure), with sales beginning **July 1, 2023**.

    #### License Types
    - **Standard Dispensary**: Full retail operations
    - **Grower**: Cultivation facility
    - **Processor**: Manufacturing/processing
    - **Dispensary Agent**: Delivery services

    #### Key Processors/Cultivators
    - **Curio Wellness** - Timonium
    - **Culta** - Baltimore
    - **SunMed Growers** - Elkridge
    - **Evermore Cannabis** - Baltimore
    - **Harvest** / **Trulieve** - Multiple locations
    """)

# ==============================================================================
# OTHER STATES
# ==============================================================================
else:
    st.info(f"Detailed report for {AVAILABLE_STATES[selected_state]} coming soon.")

    st.markdown("""
    ### Available Data
    We are actively building state-level reports for:
    - **Illinois** - Recreational since 2020
    - **Pennsylvania** - Medical only (largest medical market on East Coast)

    Check back soon for comprehensive state reports.
    """)

st.divider()
st.caption("State reports are updated regularly. For the most current data, contact state regulatory agencies directly.")
