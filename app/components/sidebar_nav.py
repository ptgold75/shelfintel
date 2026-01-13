# app/components/sidebar_nav.py
"""Clean sidebar navigation organized by user type."""

import streamlit as st
from pathlib import Path


def render_sidebar_nav():
    """Render the sidebar navigation panel."""
    from components.auth import is_authenticated, is_admin, get_current_client, get_allowed_states, init_session_state

    init_session_state()

    # Sidebar styling - clean and compact
    st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            min-width: 240px;
            max-width: 240px;
        }
        [data-testid="stSidebar"] > div:first-child {
            padding-top: 0.5rem;
        }
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1e3a5f 0%, #0f2744 100%);
        }
        section[data-testid="stSidebar"] * {
            color: white !important;
        }
        section[data-testid="stSidebar"] hr {
            border-color: rgba(255,255,255,0.1);
            margin: 0.5rem 0;
        }
        /* Navigation link styling */
        section[data-testid="stSidebar"] a {
            text-decoration: none !important;
        }
        section[data-testid="stSidebar"] .stPageLink > div {
            padding: 0.4rem 0.6rem;
            border-radius: 4px;
            margin: 1px 0;
            transition: background 0.15s;
            font-size: 0.9rem;
        }
        section[data-testid="stSidebar"] .stPageLink > div:hover {
            background: rgba(255,255,255,0.1);
        }
        /* Expander styling - compact */
        section[data-testid="stSidebar"] .streamlit-expanderHeader {
            font-size: 0.95rem;
            font-weight: 600;
            padding: 0.5rem 0.5rem;
            background: rgba(255,255,255,0.05);
            border-radius: 6px;
            margin: 0.25rem 0;
        }
        section[data-testid="stSidebar"] .streamlit-expanderHeader:hover {
            background: rgba(255,255,255,0.12);
        }
        section[data-testid="stSidebar"] .streamlit-expanderContent {
            padding: 0.25rem 0 0.25rem 0.5rem;
        }
        /* Logo area - compact */
        .sidebar-logo {
            text-align: center;
            padding: 0.25rem 0 0.5rem 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 0.5rem;
        }
        .sidebar-logo h2 {
            margin: 0;
            font-size: 1.2rem;
            font-weight: 700;
            color: white !important;
        }
        .sidebar-logo p {
            margin: 0.1rem 0 0 0;
            font-size: 0.65rem;
            opacity: 0.6;
        }
        /* User info box - compact */
        .user-info-box {
            background: rgba(255,255,255,0.08);
            border-radius: 6px;
            padding: 0.5rem;
            margin-bottom: 0.5rem;
            font-size: 0.8rem;
        }
        .user-info-box .company-name {
            font-weight: 600;
            font-size: 0.85rem;
        }
        .user-info-box .user-meta {
            font-size: 0.7rem;
            opacity: 0.7;
        }
        /* CTA box */
        .cta-box {
            padding: 0.6rem;
            background: rgba(37,99,235,0.25);
            border-radius: 6px;
            margin: 0.5rem 0;
            font-size: 0.8rem;
        }
        .cta-box p {
            margin: 0;
            font-size: 0.75rem;
        }
        .cta-box .cta-title {
            font-weight: 600;
            margin-bottom: 0.25rem;
        }
    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        # Logo - compact
        st.markdown("""
        <div class="sidebar-logo">
            <h2>CannLinx</h2>
            <p>Market Intelligence</p>
        </div>
        """, unsafe_allow_html=True)

        logged_in = is_authenticated()
        admin = is_admin() if logged_in else False

        if logged_in:
            # User info - compact
            client = get_current_client()
            states = get_allowed_states()
            role = "Admin" if admin else "Client"
            states_str = ", ".join(states[:2]) + ("+" if len(states) > 2 else "") if states else "All"

            st.markdown(f"""
            <div class="user-info-box">
                <div class="company-name">{client['company_name']}</div>
                <div class="user-meta">{role} | {states_str}</div>
            </div>
            """, unsafe_allow_html=True)

        # HOME - always visible
        st.page_link("Home.py", label="Home")

        # RETAIL INTELLIGENCE
        with st.expander("Retail", expanded=False):
            st.caption("For dispensaries & retailers")
            st.page_link("pages/20_Retail_Intelligence.py", label="Dashboard")
            st.page_link("pages/50_Deals_Dashboard.py", label="Deals & Promos")
            st.page_link("pages/6_Price_Analysis.py", label="Price Analysis")
            st.page_link("pages/6_Competitor_Compare.py", label="Competitor Compare")
            if logged_in:
                st.page_link("pages/2_Availability.py", label="Stock Alerts")
                st.page_link("pages/8_County_Insights.py", label="County Insights")

        # WHOLESALE / GROWERS
        with st.expander("Wholesale", expanded=False):
            st.caption("For growers & manufacturers")
            st.page_link("pages/30_Grower_Intelligence.py", label="Dashboard")
            if logged_in:
                st.page_link("pages/8_County_Insights.py", label="Territory Analysis")
                st.page_link("pages/9_Product_Search.py", label="Product Lookup")

        # BRANDS
        with st.expander("Brands", expanded=False):
            st.caption("For brand owners")
            st.page_link("pages/10_Brand_Intelligence.py", label="Dashboard")
            st.page_link("pages/16_Brand_Heatmap.py", label="Coverage Map")
            if logged_in:
                st.page_link("pages/15_Market_Share.py", label="Market Share")
                st.page_link("pages/11_Brand_Assets.py", label="Image Consistency")
                st.page_link("pages/14_Brand_Integrity.py", label="Naming Standards")

        # INVESTORS
        with st.expander("Investors", expanded=False):
            st.caption("For analysts & investors")
            st.page_link("pages/40_Investor_Intelligence.py", label="Dashboard")
            if logged_in:
                st.page_link("pages/15_Market_Share.py", label="Market Analysis")

        # ADMIN (logged in admins only)
        if logged_in and admin:
            with st.expander("Admin", expanded=False):
                st.page_link("pages/90_Admin_Clients.py", label="Clients")
                st.page_link("pages/98_Admin_Dispensaries.py", label="Dispensaries")
                st.page_link("pages/99_Admin_Brands.py", label="Brand Hierarchy")
                st.page_link("pages/97_Admin_Naming.py", label="Naming Rules")
                st.page_link("pages/93_Admin_Loyalty.py", label="Loyalty SMS")

        st.divider()

        if logged_in:
            st.page_link("pages/92_Logout.py", label="Logout")
        else:
            # CTA for non-logged in users
            st.markdown("""
            <div class="cta-box">
                <p class="cta-title">Get Full Access</p>
                <p>Login to unlock all features and real-time data.</p>
            </div>
            """, unsafe_allow_html=True)
            st.page_link("pages/91_Login.py", label="Login")


def render_main_header():
    """Render the main content area header with banner."""
    banner_path = Path(__file__).parent.parent / "static" / "cannalinx_banner.png"
    if banner_path.exists():
        st.image(str(banner_path), width="stretch")


def render_state_filter():
    """Render a state filter dropdown and return the selected state."""
    from components.auth import is_authenticated, is_admin, get_allowed_states
    from sqlalchemy import text
    from core.db import get_engine

    @st.cache_data(ttl=600)
    def get_available_states():
        """Get list of states that have dispensary data."""
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT d.state
                FROM dispensary d
                JOIN raw_menu_item r ON d.dispensary_id = r.dispensary_id
                WHERE d.is_active = true
                ORDER BY d.state
            """))
            return [row[0] for row in result]

    if not is_authenticated():
        return None

    if is_admin():
        states = get_available_states()
    else:
        user_states = get_allowed_states()
        available = get_available_states()
        states = [s for s in user_states if s in available]

    if not states:
        return None

    if "selected_state" not in st.session_state:
        st.session_state.selected_state = states[0] if states else None

    if st.session_state.selected_state not in states:
        st.session_state.selected_state = states[0] if states else None

    if len(states) == 1:
        st.session_state.selected_state = states[0]
        return states[0]

    # State selector in main area (not sidebar)
    selected = st.selectbox(
        "State",
        states,
        index=states.index(st.session_state.selected_state) if st.session_state.selected_state in states else 0,
        key="state_filter_select"
    )
    st.session_state.selected_state = selected
    return selected


def get_selected_state():
    """Get the currently selected state from session state."""
    return st.session_state.get("selected_state", None)


def get_section_from_params():
    """Get the section parameter from URL query params."""
    params = st.query_params
    return params.get("section", None)


def render_nav(require_login=True):
    """Main entry point - render sidebar nav and handle authentication."""
    from components.auth import is_authenticated, render_login_form

    render_sidebar_nav()
    render_main_header()

    if require_login and not is_authenticated():
        render_login_form()
        st.stop()
