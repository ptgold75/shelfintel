# app/components/nav.py
"""Shared navigation component with banner and dropdown menus."""

import streamlit as st
from pathlib import Path


def render_header():
    """Render the full header with banner and navigation."""

    # CSS for header, nav, and dropdowns - separate call
    st.markdown("""
<style>
    [data-testid="stSidebar"] {display: none;}
    .block-container {padding-top: 0.5rem; padding-bottom: 1rem; max-width: 1200px;}
    header {visibility: hidden;}

    /* Navigation container */
    .nav-container {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 0;
        padding: 0;
        background: #1e3a5f;
        margin: 0 auto 1rem auto;
        max-width: 1200px;
        border-radius: 4px;
        position: relative;
        z-index: 1000;
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
        padding: 0.75rem 1.1rem;
        font-size: 0.9rem;
        font-weight: 500;
        display: block;
        transition: background 0.2s;
        white-space: nowrap;
        cursor: pointer;
    }
    .nav-link:hover {
        background: rgba(255,255,255,0.15);
        text-decoration: none !important;
    }
    .nav-link:visited {color: white !important;}

    /* Dropdown arrow indicator */
    .nav-link.has-dropdown::after {
        content: " ▾";
        font-size: 0.7rem;
        opacity: 0.7;
    }

    /* Dropdown content */
    .dropdown-content {
        display: none;
        position: absolute;
        background: white;
        min-width: 220px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.2);
        z-index: 1001;
        border-radius: 0 0 6px 6px;
        overflow: hidden;
        left: 0;
        top: 100%;
    }
    .nav-dropdown:hover .dropdown-content {
        display: block;
    }

    /* Dropdown items */
    .dropdown-content a {
        color: #1e3a5f !important;
        padding: 0.7rem 1rem;
        text-decoration: none !important;
        display: block;
        font-size: 0.85rem;
        border-bottom: 1px solid #eee;
        transition: background 0.15s;
    }
    .dropdown-content a:last-child {border-bottom: none;}
    .dropdown-content a:hover {
        background: #f0f4f8;
        color: #1e3a5f !important;
    }

    /* Dropdown section headers */
    .dropdown-header {
        color: #6c757d !important;
        padding: 0.5rem 1rem 0.3rem;
        font-size: 0.7rem;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.5px;
        background: #f8f9fa;
    }

    /* Nav divider */
    .nav-divider {
        color: rgba(255,255,255,0.3);
        padding: 0 0.2rem;
        font-size: 0.8rem;
    }
</style>
    """, unsafe_allow_html=True)

    # Navigation HTML - separate call
    st.markdown("""
<div class="nav-container">
    <a href="/" target="_self" class="nav-link">Home</a>
    <div class="nav-dropdown">
        <a href="/Brand_Intelligence" target="_self" class="nav-link has-dropdown">Brands</a>
        <div class="dropdown-content">
            <a href="/Brand_Intelligence" target="_self">Brand Dashboard</a>
            <div class="dropdown-header">Analysis</div>
            <a href="/Brand_Intelligence?section=insights" target="_self">Actionable Insights</a>
            <a href="/Brand_Intelligence?section=distribution" target="_self">Store Distribution</a>
            <a href="/Brand_Intelligence?section=coverage" target="_self">County Coverage</a>
            <div class="dropdown-header">Related</div>
            <a href="/Brand_Assets" target="_self">Brand Assets</a>
        </div>
    </div>
    <div class="nav-dropdown">
        <a href="/Retail_Intelligence" target="_self" class="nav-link has-dropdown">Retail</a>
        <div class="dropdown-content">
            <a href="/Retail_Intelligence" target="_self">Retail Dashboard</a>
            <div class="dropdown-header">Insights</div>
            <a href="/Retail_Intelligence?section=insights" target="_self">Actionable Insights</a>
            <div class="dropdown-header">Competitive Analysis</div>
            <a href="/Retail_Intelligence?section=prices" target="_self">Price Comparison</a>
            <a href="/Retail_Intelligence?section=gaps" target="_self">Assortment Gaps</a>
            <a href="/Retail_Intelligence?section=category" target="_self">Category Mix</a>
            <div class="dropdown-header">Related</div>
            <a href="/Availability" target="_self">Availability Tracker</a>
        </div>
    </div>
    <div class="nav-dropdown">
        <a href="/Grower_Intelligence" target="_self" class="nav-link has-dropdown">Growers</a>
        <div class="dropdown-content">
            <a href="/Grower_Intelligence" target="_self">Grower Dashboard</a>
            <div class="dropdown-header">Market Analysis</div>
            <a href="/Grower_Intelligence?section=category" target="_self">Category Analysis</a>
            <a href="/Grower_Intelligence?section=strains" target="_self">Top Strains</a>
            <a href="/Grower_Intelligence?section=distribution" target="_self">Brand Distribution</a>
            <a href="/Grower_Intelligence?section=prices" target="_self">Price Benchmarks</a>
        </div>
    </div>
    <div class="nav-dropdown">
        <a href="/Product_Search" target="_self" class="nav-link has-dropdown">Tools</a>
        <div class="dropdown-content">
            <a href="/Product_Search" target="_self">Product Search</a>
            <a href="/Product_Search?section=prices" target="_self">Price List</a>
            <a href="/Product_Search?section=compare" target="_self">Store Comparison</a>
            <div class="dropdown-header">Price Analysis</div>
            <a href="/Price_Analysis" target="_self">Price Overview</a>
            <a href="/Price_Analysis?section=category" target="_self">Category Prices</a>
            <a href="/Price_Analysis?section=vapes" target="_self">Vape Analysis</a>
            <a href="/Price_Analysis?section=deals" target="_self">Best Deals</a>
            <a href="/Price_Analysis?section=search" target="_self">Price Search</a>
            <div class="dropdown-header">Other</div>
            <a href="/Availability" target="_self">Availability Tracker</a>
        </div>
    </div>
    <div class="nav-dropdown">
        <a href="/Admin_Dispensaries" target="_self" class="nav-link has-dropdown">Admin</a>
        <div class="dropdown-content">
            <a href="/Admin_Dispensaries" target="_self">Dispensaries</a>
            <a href="/Admin_Naming" target="_self">Naming Rules</a>
            <a href="/Product_Dedup" target="_self">Product Dedup</a>
        </div>
    </div>
</div>
    """, unsafe_allow_html=True)


def render_nav():
    """Render the full header with banner and navigation bar."""
    # Show banner
    banner_path = Path(__file__).parent.parent / "static" / "cannalinx_banner.png"
    if banner_path.exists():
        st.image(str(banner_path), use_container_width=True)

    # Render navigation
    render_header()


def get_section_from_params():
    """Get the section parameter from URL query params."""
    params = st.query_params
    return params.get("section", None)
