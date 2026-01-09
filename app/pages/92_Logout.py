# app/pages/92_Logout.py
"""Logout page."""

import streamlit as st
from components.auth import logout, init_session_state
from components.sidebar_nav import render_sidebar_nav, render_main_header

st.set_page_config(
    page_title="Logout - CannLinx",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

init_session_state()
logout()

# Show sidebar (will reflect logged out state)
render_sidebar_nav()
render_main_header()

st.success("You have been logged out.")
st.page_link("Home.py", label="Return to Home", icon="🏠")
