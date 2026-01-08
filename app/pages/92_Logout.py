# app/pages/92_Logout.py
"""Logout page."""

import streamlit as st
from components.auth import logout, init_session_state

st.set_page_config(
    page_title="Logout - CannLinx",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed"
)

init_session_state()
logout()

st.success("You have been logged out.")
st.page_link("Home.py", label="Return to Home", icon="🏠")
