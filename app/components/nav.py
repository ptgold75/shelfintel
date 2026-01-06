# app/components/nav.py
"""Shared navigation component for all pages."""

import streamlit as st

def render_nav():
    """Render the horizontal navigation bar and hide sidebar."""
    # Hide sidebar and add nav styles
    st.markdown("""
<style>
    [data-testid="stSidebar"] {display: none;}
    .block-container {padding-top: 0.5rem; padding-bottom: 1rem; max-width: 1200px;}
    header {visibility: hidden;}

    /* Horizontal nav */
    .nav-container {
        display: flex;
        justify-content: center;
        gap: 0.25rem;
        padding: 0.5rem 1rem;
        background: #5a7fa8;
        margin: 0 auto 1rem auto;
        max-width: 1200px;
        border-radius: 4px;
        flex-wrap: wrap;
    }
    .nav-link {
        color: white !important;
        text-decoration: none !important;
        padding: 0.5rem 0.9rem;
        border-radius: 4px;
        font-size: 0.85rem;
        transition: background 0.2s;
    }
    .nav-link:hover {background: rgba(255,255,255,0.2); text-decoration: none !important;}
    .nav-link:visited {color: white !important; text-decoration: none !important;}
    .nav-link.active {background: rgba(255,255,255,0.3);}
</style>
    """, unsafe_allow_html=True)

    # Navigation links
    st.markdown("""
<div class="nav-container">
    <a href="/" target="_self" class="nav-link">Home</a>
    <a href="/Dashboard" target="_self" class="nav-link">Dashboard</a>
    <a href="/Product_Search" target="_self" class="nav-link">Search</a>
    <a href="/Price_Analysis" target="_self" class="nav-link">Pricing</a>
    <a href="/Brand_Analytics" target="_self" class="nav-link">Brands</a>
    <a href="/County_Insights" target="_self" class="nav-link">Counties</a>
    <a href="/Competitor_Compare" target="_self" class="nav-link">Compare</a>
</div>
    """, unsafe_allow_html=True)
