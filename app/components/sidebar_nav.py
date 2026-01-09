# app/components/sidebar_nav.py
"""Static left sidebar navigation that changes based on authentication status."""

import streamlit as st
from pathlib import Path


def render_sidebar_nav():
    """Render the static left sidebar navigation panel."""
    from components.auth import is_authenticated, is_admin, get_current_client, get_allowed_states, init_session_state

    init_session_state()

    # Force sidebar to always be visible
    st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            min-width: 240px;
            max-width: 240px;
        }
        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1rem;
        }
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1e3a5f 0%, #0f2744 100%);
        }
        section[data-testid="stSidebar"] * {
            color: white !important;
        }
        section[data-testid="stSidebar"] hr {
            border-color: rgba(255,255,255,0.1);
        }
        /* Navigation link styling */
        section[data-testid="stSidebar"] a {
            text-decoration: none !important;
        }
        section[data-testid="stSidebar"] .stPageLink > div {
            padding: 0.5rem 0.75rem;
            border-radius: 6px;
            margin: 2px 0;
            transition: background 0.15s;
        }
        section[data-testid="stSidebar"] .stPageLink > div:hover {
            background: rgba(255,255,255,0.1);
        }
        section[data-testid="stSidebar"] .stPageLink[data-active="true"] > div {
            background: rgba(37, 99, 235, 0.3);
            border-left: 3px solid #60a5fa;
        }
        /* Section headers */
        .nav-section-header {
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: rgba(255,255,255,0.5) !important;
            margin: 1rem 0 0.5rem 0.5rem;
            font-weight: 600;
        }
        /* User info box */
        .user-info-box {
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
            padding: 0.75rem;
            margin-bottom: 1rem;
        }
        .user-info-box .company-name {
            font-weight: 600;
            font-size: 0.9rem;
            margin-bottom: 0.25rem;
        }
        .user-info-box .user-role {
            font-size: 0.75rem;
            opacity: 0.8;
        }
        .user-info-box .user-states {
            font-size: 0.7rem;
            opacity: 0.6;
            margin-top: 0.25rem;
        }
        /* Logo area */
        .sidebar-logo {
            text-align: center;
            padding: 0.5rem 0 1rem 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 1rem;
        }
        .sidebar-logo h2 {
            margin: 0;
            font-size: 1.3rem;
            font-weight: 700;
            color: white !important;
        }
        .sidebar-logo p {
            margin: 0.25rem 0 0 0;
            font-size: 0.7rem;
            opacity: 0.7;
        }
    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        # Logo/Brand
        st.markdown("""
        <div class="sidebar-logo">
            <h2>CannLinx</h2>
            <p>Market Intelligence</p>
        </div>
        """, unsafe_allow_html=True)

        logged_in = is_authenticated()
        admin = is_admin() if logged_in else False

        if logged_in:
            # Show user info
            client = get_current_client()
            states = get_allowed_states()
            role = "Admin" if admin else "Client"
            states_str = ", ".join(states[:3]) + ("..." if len(states) > 3 else "") if states else "All"

            st.markdown(f"""
            <div class="user-info-box">
                <div class="company-name">{client['company_name']}</div>
                <div class="user-role">{role}</div>
                <div class="user-states">States: {states_str}</div>
            </div>
            """, unsafe_allow_html=True)

            # LOGGED IN NAVIGATION

            # Main Dashboard
            st.page_link("Home.py", label="Home", icon="🏠")

            # RETAIL Section
            with st.expander("Retail", expanded=False):
                st.page_link("pages/20_Retail_Intelligence.py", label="Dashboard")
                st.page_link("pages/6_Price_Analysis.py", label="Price Comparison")
                st.page_link("pages/6_Competitor_Compare.py", label="Store vs Store")
                st.page_link("pages/2_Availability.py", label="Stock Alerts")
                st.page_link("pages/9_Product_Search.py", label="Product Search")
                st.page_link("pages/8_County_Insights.py", label="County Insights")

            # WHOLESALE Section
            with st.expander("Wholesale", expanded=False):
                st.page_link("pages/30_Grower_Intelligence.py", label="Dashboard")
                st.page_link("pages/8_County_Insights.py", label="Territory Analysis")
                st.page_link("pages/2_Availability.py", label="Restock Alerts")
                st.page_link("pages/9_Product_Search.py", label="Product Lookup")

            # BRANDS Section
            with st.expander("Brands", expanded=False):
                st.page_link("pages/10_Brand_Intelligence.py", label="Dashboard")
                st.page_link("pages/15_Market_Share.py", label="Market Position")
                st.page_link("pages/16_Brand_Heatmap.py", label="Coverage Heat Map")
                st.page_link("pages/11_Brand_Assets.py", label="Image Consistency")
                st.page_link("pages/14_Brand_Integrity.py", label="Naming Standards")

            # INVESTORS Section
            with st.expander("Investors", expanded=False):
                st.page_link("pages/40_Investor_Intelligence.py", label="Dashboard")
                st.page_link("pages/15_Market_Share.py", label="Market Analysis")

            # Admin section
            if admin:
                with st.expander("Admin", expanded=False):
                    st.page_link("pages/90_Admin_Clients.py", label="Manage Clients")
                    st.page_link("pages/97_Admin_Naming.py", label="Naming Rules")
                    st.page_link("pages/98_Admin_Dispensaries.py", label="Dispensaries")

            st.divider()
            st.page_link("pages/93_Alert_Settings.py", label="Alert Settings", icon="🔔")
            st.page_link("pages/92_Logout.py", label="Logout", icon="🚪")

        else:
            # LOGGED OUT NAVIGATION - Show what's available by user type

            st.page_link("Home.py", label="Home", icon="🏠")

            # RETAIL Section
            with st.expander("Retail", expanded=False):
                st.page_link("pages/20_Retail_Intelligence.py", label="Dashboard")
                st.page_link("pages/6_Price_Analysis.py", label="Price Comparison")

            # WHOLESALE Section
            with st.expander("Wholesale", expanded=False):
                st.page_link("pages/30_Grower_Intelligence.py", label="Dashboard")

            # BRANDS Section
            with st.expander("Brands", expanded=False):
                st.page_link("pages/10_Brand_Intelligence.py", label="Dashboard")
                st.page_link("pages/16_Brand_Heatmap.py", label="Coverage Heat Map")

            # INVESTORS Section
            with st.expander("Investors", expanded=False):
                st.page_link("pages/40_Investor_Intelligence.py", label="Dashboard")

            st.divider()

            st.markdown("""
            <div style="padding: 1rem; background: rgba(37,99,235,0.2); border-radius: 8px; margin: 1rem 0;">
                <p style="font-size: 0.85rem; margin: 0 0 0.5rem 0; font-weight: 600;">Ready to get started?</p>
                <p style="font-size: 0.75rem; margin: 0; opacity: 0.8;">Log in to access full market intelligence and track your competition.</p>
            </div>
            """, unsafe_allow_html=True)

            st.page_link("pages/91_Login.py", label="Login", icon="🔑")


def render_main_header():
    """Render the main content area header with banner."""
    # Banner image
    banner_path = Path(__file__).parent.parent / "static" / "cannalinx_banner.png"
    if banner_path.exists():
        st.image(str(banner_path), use_container_width=True)


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

    # Get states based on user permissions
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

    # Initialize session state
    if "selected_state" not in st.session_state:
        st.session_state.selected_state = states[0] if states else None

    # If current selection not in allowed states, reset
    if st.session_state.selected_state not in states:
        st.session_state.selected_state = states[0] if states else None

    # If only one state, don't show filter
    if len(states) == 1:
        st.session_state.selected_state = states[0]
        return states[0]

    # Create state selector in sidebar
    with st.sidebar:
        st.markdown('<p class="nav-section-header">Filter</p>', unsafe_allow_html=True)
        selected = st.selectbox(
            "State",
            states,
            index=states.index(st.session_state.selected_state) if st.session_state.selected_state in states else 0,
            key="state_filter_select",
            label_visibility="collapsed"
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

    # Render sidebar navigation
    render_sidebar_nav()

    # Render banner in main area
    render_main_header()

    # Handle login requirement
    if require_login and not is_authenticated():
        render_login_form()
        st.stop()
