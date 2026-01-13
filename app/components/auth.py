# app/components/auth.py
"""Authentication and authorization utilities."""

import hashlib
import sys
import os
from pathlib import Path

# Add parent directory to path so we can import core module
_app_dir = Path(__file__).parent.parent  # app/
_root_dir = _app_dir.parent  # shelfintel/
if str(_root_dir) not in sys.path:
    sys.path.insert(0, str(_root_dir))

import streamlit as st
from sqlalchemy import text
from typing import Optional, List


def hash_password(password: str) -> str:
    """Hash a password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


def get_db_engine():
    """Get database engine."""
    from core.db import get_engine
    return get_engine()


def authenticate_user(email: str, password: str) -> Optional[dict]:
    """Authenticate user and return client info if valid."""
    try:
        engine = get_db_engine()
        password_hash = hash_password(password)

        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT client_id, company_name, contact_name, email, is_admin, is_active
                FROM client
                WHERE LOWER(email) = LOWER(:email) AND password_hash = :password_hash
            """), {"email": email.strip(), "password_hash": password_hash})
            row = result.fetchone()

            if row and row[5]:  # is_active
                return {
                    "client_id": str(row[0]),
                    "company_name": row[1],
                    "contact_name": row[2],
                    "email": row[3],
                    "is_admin": row[4]
                }
        return None
    except RuntimeError as e:
        # DATABASE_URL not set
        import streamlit as st
        st.error(f"Database not configured. Please check secrets.")
        return None
    except Exception as e:
        import streamlit as st
        st.error(f"Login error: {type(e).__name__}: {str(e)[:100]}")
        return None


@st.cache_data(ttl=300)  # Cache for 5 minutes
def _fetch_client_states(client_id: str) -> List[str]:
    """Cached query for client states."""
    engine = get_db_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT state FROM client_state_permission
            WHERE client_id = :client_id
              AND is_active = true
              AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY state
        """), {"client_id": client_id})
        return [row[0] for row in result]


def get_client_states(client_id: str) -> List[str]:
    """Get list of states a client has access to."""
    return _fetch_client_states(client_id)


def check_state_permission(client_id: str, state: str) -> bool:
    """Check if client has permission for a specific state."""
    states = get_client_states(client_id)
    return state in states


def init_session_state():
    """Initialize authentication session state."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "client" not in st.session_state:
        st.session_state.client = None
    if "allowed_states" not in st.session_state:
        st.session_state.allowed_states = []


def login(email: str, password: str) -> bool:
    """Attempt to log in a user."""
    client = authenticate_user(email, password)
    if client:
        st.session_state.authenticated = True
        st.session_state.client = client
        st.session_state.allowed_states = get_client_states(client["client_id"])
        return True
    return False


def logout():
    """Log out the current user."""
    st.session_state.authenticated = False
    st.session_state.client = None
    st.session_state.allowed_states = []
    st.session_state.selected_state = None


def is_authenticated() -> bool:
    """Check if user is authenticated."""
    init_session_state()
    return st.session_state.authenticated


def is_admin() -> bool:
    """Check if current user is an admin."""
    if not is_authenticated():
        return False
    return st.session_state.client.get("is_admin", False)


def get_current_client() -> Optional[dict]:
    """Get current logged-in client info."""
    if is_authenticated():
        return st.session_state.client
    return None


def can_access_state(state: str) -> bool:
    """Check if current user can access a specific state."""
    if not is_authenticated():
        return False
    return state in st.session_state.allowed_states


def get_allowed_states() -> List[str]:
    """Get list of states current user can access."""
    if not is_authenticated():
        return []
    return st.session_state.allowed_states


def render_login_form():
    """Render the login form."""
    st.markdown("### Login")

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            if login(email, password):
                st.success(f"Welcome, {st.session_state.client['contact_name'] or st.session_state.client['company_name']}!")
                st.rerun()
            else:
                st.error("Invalid email or password")


def render_user_menu():
    """Render the user menu in the header."""
    if is_authenticated():
        client = get_current_client()
        col1, col2 = st.columns([3, 1])
        with col1:
            states = get_allowed_states()
            st.caption(f"Logged in as **{client['company_name']}** | States: {', '.join(states)}")
        with col2:
            if st.button("Logout", key="logout_btn"):
                logout()
                st.rerun()


def require_auth(allowed_states: List[str] = None):
    """
    Decorator/function to require authentication.
    If allowed_states is provided, also checks state permission.
    Returns True if access granted, False otherwise.
    """
    init_session_state()

    if not is_authenticated():
        return False

    if allowed_states:
        user_states = get_allowed_states()
        if not any(s in user_states for s in allowed_states):
            return False

    return True


def require_admin():
    """Check if current user is an admin."""
    return is_authenticated() and is_admin()
