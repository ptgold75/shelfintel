# app/pages/90_Admin_Clients.py
"""Admin interface for managing clients and state permissions."""

import streamlit as st
from sqlalchemy import text
from core.db import get_engine
from components.nav import render_nav, get_available_states
from components.auth import hash_password, is_admin, require_admin

st.set_page_config(
    page_title="Client Management - CannLinx",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed"
)

render_nav(require_login=True)

# Check admin access
if not require_admin():
    st.error("Access denied. Admin privileges required.")
    st.stop()

st.title("Client Management")


def get_all_clients():
    """Load all clients from database."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT c.client_id, c.company_name, c.contact_name, c.email,
                   c.is_active, c.is_admin, c.created_at,
                   COALESCE(array_agg(csp.state ORDER BY csp.state) FILTER (WHERE csp.state IS NOT NULL), '{}') as states
            FROM client c
            LEFT JOIN client_state_permission csp ON c.client_id = csp.client_id AND csp.is_active = true
            GROUP BY c.client_id, c.company_name, c.contact_name, c.email,
                     c.is_active, c.is_admin, c.created_at
            ORDER BY c.company_name
        """))
        return [dict(row._mapping) for row in result]


def get_client_permissions(client_id):
    """Get current state permissions for a client."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT state FROM client_state_permission
            WHERE client_id = :client_id AND is_active = true
            ORDER BY state
        """), {"client_id": client_id})
        return [row[0] for row in result]


def update_client_permissions(client_id, states):
    """Update state permissions for a client."""
    engine = get_engine()
    with engine.connect() as conn:
        # Deactivate all current permissions
        conn.execute(text("""
            UPDATE client_state_permission SET is_active = false
            WHERE client_id = :client_id
        """), {"client_id": client_id})

        # Add new permissions
        for state in states:
            conn.execute(text("""
                INSERT INTO client_state_permission (client_id, state, is_active)
                VALUES (:client_id, :state, true)
                ON CONFLICT (client_id, state) DO UPDATE SET is_active = true, granted_at = NOW()
            """), {"client_id": client_id, "state": state})

        conn.commit()


def create_client(company_name, contact_name, email, password, is_active, is_admin_user, states):
    """Create a new client."""
    engine = get_engine()
    password_hash = hash_password(password)

    with engine.connect() as conn:
        # Insert client
        result = conn.execute(text("""
            INSERT INTO client (company_name, contact_name, email, password_hash, is_active, is_admin)
            VALUES (:company, :contact, :email, :password, :active, :admin)
            RETURNING client_id
        """), {
            "company": company_name,
            "contact": contact_name,
            "email": email.lower(),
            "password": password_hash,
            "active": is_active,
            "admin": is_admin_user
        })
        client_id = result.fetchone()[0]

        # Add state permissions
        for state in states:
            conn.execute(text("""
                INSERT INTO client_state_permission (client_id, state, is_active)
                VALUES (:client_id, :state, true)
            """), {"client_id": str(client_id), "state": state})

        conn.commit()
        return client_id


def toggle_client_status(client_id, is_active):
    """Toggle client active status."""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE client SET is_active = :active, updated_at = NOW()
            WHERE client_id = :client_id
        """), {"client_id": client_id, "active": is_active})
        conn.commit()


# Tabs for different views
tab1, tab2 = st.tabs(["Existing Clients", "Add New Client"])

# Available states
available_states = get_available_states()

with tab1:
    st.subheader("All Clients")

    clients = get_all_clients()

    if not clients:
        st.info("No clients found.")
    else:
        for client in clients:
            with st.expander(f"**{client['company_name']}** - {client['email']}"):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Contact:** {client['contact_name'] or 'N/A'}")
                    st.write(f"**Email:** {client['email']}")
                    st.write(f"**Created:** {client['created_at'].strftime('%Y-%m-%d') if client['created_at'] else 'N/A'}")
                    status = "Active" if client['is_active'] else "Inactive"
                    role = "Admin" if client['is_admin'] else "Client"
                    st.write(f"**Status:** {status} | **Role:** {role}")

                with col2:
                    current_states = client['states'] if client['states'] else []
                    st.write(f"**Current States:** {', '.join(current_states) if current_states else 'None'}")

                    # Edit permissions
                    new_states = st.multiselect(
                        "Edit State Permissions",
                        available_states,
                        default=[s for s in current_states if s in available_states],
                        key=f"states_{client['client_id']}"
                    )

                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("Save Permissions", key=f"save_{client['client_id']}"):
                            update_client_permissions(str(client['client_id']), new_states)
                            st.success("Permissions updated!")
                            st.rerun()

                    with col_b:
                        if client['is_active']:
                            if st.button("Deactivate", key=f"deact_{client['client_id']}", type="secondary"):
                                toggle_client_status(str(client['client_id']), False)
                                st.warning("Client deactivated")
                                st.rerun()
                        else:
                            if st.button("Activate", key=f"act_{client['client_id']}", type="primary"):
                                toggle_client_status(str(client['client_id']), True)
                                st.success("Client activated")
                                st.rerun()

with tab2:
    st.subheader("Create New Client")

    with st.form("new_client_form"):
        company = st.text_input("Company Name *")
        contact = st.text_input("Contact Name")
        email = st.text_input("Email *")
        password = st.text_input("Password *", type="password")
        password_confirm = st.text_input("Confirm Password *", type="password")

        col1, col2 = st.columns(2)
        with col1:
            is_active = st.checkbox("Active", value=True)
        with col2:
            is_admin_user = st.checkbox("Admin User", value=False)

        selected_states = st.multiselect(
            "State Permissions",
            available_states,
            help="Select states this client can access ($399/month per state)"
        )

        # Show pricing
        if selected_states:
            monthly = len(selected_states) * 399
            st.info(f"Monthly subscription: ${monthly:,} ({len(selected_states)} state(s) x $399)")

        submitted = st.form_submit_button("Create Client", use_container_width=True, type="primary")

        if submitted:
            errors = []
            if not company:
                errors.append("Company name required")
            if not email:
                errors.append("Email required")
            if not password:
                errors.append("Password required")
            if password != password_confirm:
                errors.append("Passwords do not match")
            if len(password) < 6:
                errors.append("Password must be at least 6 characters")
            if not selected_states:
                errors.append("Select at least one state")

            # Check email uniqueness
            engine = get_engine()
            with engine.connect() as conn:
                exists = conn.execute(text(
                    "SELECT 1 FROM client WHERE email = :email"
                ), {"email": email.lower()}).fetchone()
                if exists:
                    errors.append("Email already registered")

            if errors:
                for err in errors:
                    st.error(err)
            else:
                try:
                    client_id = create_client(
                        company, contact, email, password,
                        is_active, is_admin_user, selected_states
                    )
                    st.success(f"Client created successfully! ID: {client_id}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error creating client: {e}")

# Summary stats
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    active_clients = sum(1 for c in clients if c['is_active'])
    st.metric("Active Clients", active_clients)
with col2:
    total_permissions = sum(len(c['states']) for c in clients if c['is_active'])
    st.metric("Total State Permissions", total_permissions)
with col3:
    monthly_revenue = total_permissions * 399
    st.metric("Monthly Revenue", f"${monthly_revenue:,}")
