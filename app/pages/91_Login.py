# app/pages/91_Login.py
"""Login page."""

import streamlit as st
from components.sidebar_nav import render_nav
from components.auth import login, is_authenticated, init_session_state

st.set_page_config(
    page_title="Login - CannLinx",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

init_session_state()

# Show nav without requiring login
render_nav(require_login=False)

if is_authenticated():
    st.success("You are already logged in!")
    st.page_link("pages/10_Brand_Intelligence.py", label="Go to Brand Dashboard")
else:
    st.markdown("### Login to CannLinx")
    st.markdown("Access your market intelligence dashboard.")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        with st.form("login_form"):
            email = st.text_input("Email or Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", width="stretch", type="primary")

            if submitted:
                if email and password:
                    if login(email, password):
                        st.success("Login successful! Redirecting...")
                        st.switch_page("pages/10_Brand_Intelligence.py")
                    else:
                        st.error("Invalid credentials. Please try again.")
                else:
                    st.warning("Please enter your email and password.")

        st.markdown("---")
        st.markdown("Don't have an account? [Contact us](mailto:support@cannlinx.com) to get started.")
