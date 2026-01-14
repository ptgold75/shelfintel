# app/components/nav.py
"""Shared navigation component with banner and dropdown menus."""

import streamlit as st
from pathlib import Path
from sqlalchemy import text


@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_available_states():
    """Get list of states that have dispensary data."""
    from core.db import get_engine
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


def get_user_allowed_states():
    """Get states the current user has permission to access."""
    from components.auth import is_authenticated, is_admin, get_allowed_states

    if not is_authenticated():
        return []

    # Admins can see all states
    if is_admin():
        return get_available_states()

    # Regular users see their permitted states (that also have data)
    user_states = get_allowed_states()
    available = get_available_states()
    return [s for s in user_states if s in available]


def render_state_filter():
    """Render a state filter dropdown and return the selected state."""
    from components.auth import is_authenticated

    # Get states based on user permissions
    if is_authenticated():
        states = get_user_allowed_states()
    else:
        states = []  # No access without login

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

    # Create state selector
    options = states
    selected = st.selectbox(
        "State",
        options,
        index=options.index(st.session_state.selected_state) if st.session_state.selected_state in options else 0,
        key="state_filter_select"
    )
    st.session_state.selected_state = selected
    return selected


def get_selected_state():
    """Get the currently selected state from session state."""
    return st.session_state.get("selected_state", None)


def render_header():
    """Render the full header with banner and navigation."""

    # CSS for header, nav, and dropdowns - separate call
    st.markdown("""
<style>
    [data-testid="stSidebar"] {display: none;}
    .block-container {padding-top: 0.5rem; padding-bottom: 1rem; max-width: 1200px;}
    header {visibility: hidden;}

    /* Navigation container - brighter blue */
    .nav-container {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 0;
        padding: 0;
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        margin: 0 auto 1.5rem auto;
        max-width: 1200px;
        border-radius: 8px;
        position: relative;
        z-index: 1000;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.25);
    }

    /* Dropdown wrapper */
    .nav-dropdown {
        position: relative;
        display: inline-block;
    }

    /* Main nav links */
    .nav-link {
        color: white !important;
        text-decoration: none !important;
        padding: 0.85rem 1.25rem;
        font-size: 0.9rem;
        font-weight: 500;
        display: block;
        transition: background 0.2s;
        white-space: nowrap;
        cursor: pointer;
    }
    .nav-link:hover {
        background: rgba(255,255,255,0.2);
        text-decoration: none !important;
    }
    .nav-link:visited {color: white !important;}

    /* Dropdown arrow indicator */
    .nav-link.has-dropdown::after {
        content: " ▾";
        font-size: 0.7rem;
        opacity: 0.8;
    }

    /* Dropdown content */
    .dropdown-content {
        display: none;
        position: absolute;
        background: white;
        min-width: 220px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.15);
        z-index: 1001;
        border-radius: 0 0 8px 8px;
        overflow: hidden;
        left: 0;
        top: 100%;
    }
    .nav-dropdown:hover .dropdown-content {
        display: block;
    }

    /* Dropdown items */
    .dropdown-content a {
        color: #1e293b !important;
        padding: 0.75rem 1.25rem;
        text-decoration: none !important;
        display: block;
        font-size: 0.875rem;
        border-bottom: 1px solid #f1f5f9;
        transition: all 0.15s;
    }
    .dropdown-content a:last-child {border-bottom: none;}
    .dropdown-content a:hover {
        background: #eff6ff;
        color: #2563eb !important;
    }

    /* Nav divider */
    .nav-divider {
        color: rgba(255,255,255,0.3);
        padding: 0 0.2rem;
        font-size: 0.8rem;
    }
</style>
    """, unsafe_allow_html=True)

    # Navigation HTML - dynamically built based on auth status
    from components.auth import is_authenticated, is_admin

    # Determine which links to show
    show_admin = is_authenticated() and is_admin()
    logged_in = is_authenticated()

    # Build nav HTML
    nav_html = '''<div class="nav-container">
    <a href="/" target="_self" class="nav-link">Home</a>
    <div class="nav-dropdown">
        <a href="/Brand_Intelligence" target="_self" class="nav-link has-dropdown">Brands</a>
        <div class="dropdown-content">
            <a href="/Brand_Intelligence" target="_self">Brand Dashboard</a>
            <a href="/Brand_Intelligence?section=insights" target="_self">Actionable Insights</a>
            <a href="/Brand_Intelligence?section=distribution" target="_self">Store Distribution</a>
            <a href="/Brand_Intelligence?section=coverage" target="_self">County Coverage</a>
            <a href="/Brand_Assets" target="_self">Brand Assets</a>
        </div>
    </div>
    <div class="nav-dropdown">
        <a href="/Retail_Intelligence" target="_self" class="nav-link has-dropdown">Retail</a>
        <div class="dropdown-content">
            <a href="/Retail_Intelligence" target="_self">Retail Dashboard</a>
            <a href="/Retail_Intelligence?section=insights" target="_self">Actionable Insights</a>
            <a href="/Retail_Intelligence?section=prices" target="_self">Price Comparison</a>
            <a href="/Retail_Intelligence?section=gaps" target="_self">Assortment Gaps</a>
            <a href="/Retail_Intelligence?section=category" target="_self">Category Mix</a>
            <a href="/Availability" target="_self">Availability Tracker</a>
        </div>
    </div>
    <div class="nav-dropdown">
        <a href="/Grower_Intelligence" target="_self" class="nav-link has-dropdown">Growers</a>
        <div class="dropdown-content">
            <a href="/Grower_Intelligence" target="_self">Grower Dashboard</a>
            <a href="/Grower_Intelligence?section=category" target="_self">Category Analysis</a>
            <a href="/Grower_Intelligence?section=strains" target="_self">Top Strains</a>
            <a href="/Grower_Intelligence?section=distribution" target="_self">Brand Distribution</a>
            <a href="/Grower_Intelligence?section=prices" target="_self">Price Benchmarks</a>
            <a href="/Grower_Intelligence?section=sizes" target="_self">Size Distribution</a>
        </div>
    </div>
    <div class="nav-dropdown">
        <a href="/Product_Search" target="_self" class="nav-link has-dropdown">Tools</a>
        <div class="dropdown-content">
            <a href="/Product_Search" target="_self">Product Search</a>
            <a href="/Product_Search?section=prices" target="_self">Price List</a>
            <a href="/Product_Search?section=compare" target="_self">Store Comparison</a>
            <a href="/Price_Analysis" target="_self">Price Overview</a>
            <a href="/Price_Analysis?section=category" target="_self">Category Prices</a>
            <a href="/Price_Analysis?section=vapes" target="_self">Vape Analysis</a>
            <a href="/Price_Analysis?section=deals" target="_self">Best Deals</a>
            <a href="/Price_Analysis?section=search" target="_self">Price Search</a>
            <a href="/Availability" target="_self">Availability Tracker</a>
        </div>
    </div>
    <div class="nav-dropdown">
        <a href="/Investor_Intelligence" target="_self" class="nav-link has-dropdown">Investors</a>
        <div class="dropdown-content">
            <a href="/Investor_Intelligence" target="_self">Investor Dashboard</a>
            <a href="/Investor_Intelligence?section=companies" target="_self">Public Companies</a>
            <a href="/Investor_Intelligence?section=stocks" target="_self">Stock Performance</a>
            <a href="/Investor_Intelligence?section=financials" target="_self">Financial Metrics</a>
            <a href="/Investor_Intelligence?section=states" target="_self">State Operations</a>
            <a href="/Investor_Intelligence?section=shelf" target="_self">Shelf Analytics</a>
        </div>
    </div>'''

    # Add admin menu if logged in as admin
    if show_admin:
        nav_html += '''
    <div class="nav-dropdown">
        <a href="/Admin_Dispensaries" target="_self" class="nav-link has-dropdown">Admin</a>
        <div class="dropdown-content">
            <a href="/Admin_Dispensaries" target="_self">Dispensaries</a>
            <a href="/Admin_Naming" target="_self">Naming Rules</a>
            <a href="/Product_Dedup" target="_self">Product Dedup</a>
            <a href="/Admin_Clients" target="_self">Client Management</a>
        </div>
    </div>'''

    # Add login/logout link
    if logged_in:
        nav_html += '''
    <a href="/Logout" target="_self" class="nav-link">Logout</a>'''
    else:
        nav_html += '''
    <a href="/Login" target="_self" class="nav-link">Login</a>'''

    nav_html += '''
</div>'''

    st.markdown(nav_html, unsafe_allow_html=True)


def render_user_bar():
    """Render user status bar with login/logout."""
    from components.auth import is_authenticated, get_current_client, logout, is_admin, get_allowed_states

    if is_authenticated():
        client = get_current_client()
        states = get_allowed_states()
        states_str = ", ".join(states) if states else "None"

        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            role = "Admin" if is_admin() else "Client"
            st.caption(f"**{client['company_name']}** ({role}) | States: {states_str}")
        with col2:
            if is_admin():
                st.page_link("pages/90_Admin_Clients.py", label="Manage Clients", icon="👥")
        with col3:
            if st.button("Logout", key="nav_logout_btn", type="secondary"):
                logout()
                st.rerun()
    else:
        st.info("Please log in to access the dashboard.")


def render_nav(require_login=True):
    """Render the full header with banner and navigation bar."""
    from components.auth import is_authenticated, init_session_state, render_login_form

    init_session_state()

    # Show banner
    banner_path = Path(__file__).parent.parent / "static" / "cannalinx_banner.png"
    if banner_path.exists():
        st.image(str(banner_path), use_container_width=True)

    # Render navigation
    render_header()

    # Show user bar if authenticated, login form if not
    if require_login:
        if not is_authenticated():
            render_login_form()
            st.stop()  # Don't render rest of page
        else:
            render_user_bar()


def get_section_from_params():
    """Get the section parameter from URL query params."""
    params = st.query_params
    return params.get("section", None)
