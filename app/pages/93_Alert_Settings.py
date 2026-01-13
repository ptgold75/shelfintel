# app/pages/93_Alert_Settings.py
"""Alert Settings - Configure email notifications."""

import streamlit as st
from sqlalchemy import text
from components.sidebar_nav import render_nav
from components.auth import is_authenticated, get_current_client
from core.db import get_engine

st.set_page_config(
    page_title="Alert Settings - CannLinx",
    layout="wide",
    initial_sidebar_state="expanded"
)

render_nav(require_login=True)

st.title("Alert Settings")
st.markdown("Configure your email notification preferences")

if not is_authenticated():
    st.warning("Please log in to manage alert settings")
    st.stop()

client = get_current_client()
client_id = client['client_id']


def ensure_tables_exist():
    """Create alert tables if they don't exist."""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS alert_preferences (
                id SERIAL PRIMARY KEY,
                client_id UUID REFERENCES client(client_id),
                alert_type VARCHAR(50) NOT NULL,
                is_enabled BOOLEAN DEFAULT true,
                threshold_pct DECIMAL DEFAULT 5.0,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(client_id, alert_type)
            )
        """))
        conn.commit()


def get_alert_preferences(client_id):
    """Get current alert preferences for client."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT alert_type, is_enabled, threshold_pct
            FROM alert_preferences
            WHERE client_id = :client_id
        """), {"client_id": client_id})

        prefs = {}
        for row in result:
            prefs[row[0]] = {
                "is_enabled": row[1],
                "threshold_pct": float(row[2]) if row[2] else 5.0
            }
        return prefs


def save_alert_preference(client_id, alert_type, is_enabled, threshold_pct=5.0):
    """Save alert preference."""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO alert_preferences (client_id, alert_type, is_enabled, threshold_pct, updated_at)
            VALUES (:client_id, :alert_type, :is_enabled, :threshold_pct, NOW())
            ON CONFLICT (client_id, alert_type)
            DO UPDATE SET is_enabled = :is_enabled, threshold_pct = :threshold_pct, updated_at = NOW()
        """), {
            "client_id": client_id,
            "alert_type": alert_type,
            "is_enabled": is_enabled,
            "threshold_pct": threshold_pct
        })
        conn.commit()


# Ensure tables exist
ensure_tables_exist()

# Get current preferences
prefs = get_alert_preferences(client_id)

st.markdown("---")

# Stock Alerts Section
st.subheader("Stock Price Alerts")
st.markdown("Get notified when cannabis stocks have significant price movements")

col1, col2 = st.columns([2, 1])

with col1:
    stock_enabled = st.toggle(
        "Enable daily stock alerts",
        value=prefs.get('stock_changes', {}).get('is_enabled', False),
        key="stock_alerts_toggle"
    )

with col2:
    stock_threshold = st.slider(
        "Alert threshold (%)",
        min_value=1.0,
        max_value=20.0,
        value=prefs.get('stock_changes', {}).get('threshold_pct', 5.0),
        step=0.5,
        key="stock_threshold",
        help="Only alert when price changes exceed this percentage"
    )

if st.button("Save Stock Alert Settings", key="save_stock"):
    save_alert_preference(client_id, 'stock_changes', stock_enabled, stock_threshold)
    st.success("Stock alert settings saved!")

st.markdown("---")

# Brand Alerts Section
st.subheader("Brand Coverage Alerts")
st.markdown("Get notified about changes in your brand's market presence")

col1, col2 = st.columns([2, 1])

with col1:
    brand_enabled = st.toggle(
        "Enable brand coverage alerts",
        value=prefs.get('brand_coverage', {}).get('is_enabled', False),
        key="brand_alerts_toggle"
    )

with col2:
    brand_threshold = st.slider(
        "Store change threshold",
        min_value=1,
        max_value=10,
        value=int(prefs.get('brand_coverage', {}).get('threshold_pct', 3)),
        step=1,
        key="brand_threshold",
        help="Alert when brand appears in or disappears from this many stores"
    )

if st.button("Save Brand Alert Settings", key="save_brand"):
    save_alert_preference(client_id, 'brand_coverage', brand_enabled, float(brand_threshold))
    st.success("Brand alert settings saved!")

st.markdown("---")

# Out of Stock Alerts Section
st.subheader("Out of Stock Alerts")
st.markdown("Get notified when products go out of stock at retail partners")

oos_enabled = st.toggle(
    "Enable out of stock alerts",
    value=prefs.get('out_of_stock', {}).get('is_enabled', False),
    key="oos_alerts_toggle"
)

if st.button("Save Out of Stock Alert Settings", key="save_oos"):
    save_alert_preference(client_id, 'out_of_stock', oos_enabled, 0)
    st.success("Out of stock alert settings saved!")

st.markdown("---")

# Price Change Alerts
st.subheader("Price Change Alerts")
st.markdown("Get notified when competitors change prices on similar products")

col1, col2 = st.columns([2, 1])

with col1:
    price_enabled = st.toggle(
        "Enable price change alerts",
        value=prefs.get('price_changes', {}).get('is_enabled', False),
        key="price_alerts_toggle"
    )

with col2:
    price_threshold = st.slider(
        "Price change threshold (%)",
        min_value=5.0,
        max_value=50.0,
        value=prefs.get('price_changes', {}).get('threshold_pct', 10.0),
        step=5.0,
        key="price_threshold",
        help="Only alert when prices change by more than this percentage"
    )

if st.button("Save Price Alert Settings", key="save_price"):
    save_alert_preference(client_id, 'price_changes', price_enabled, price_threshold)
    st.success("Price alert settings saved!")

st.markdown("---")

# Email Preview
st.subheader("Email Delivery")
st.markdown(f"Alerts will be sent to: **{client.get('email', 'Not set')}**")

if not client.get('email'):
    st.warning("Please update your profile to add an email address for alerts")

# Alert History
st.markdown("---")
st.subheader("Recent Alert History")

engine = get_engine()
with engine.connect() as conn:
    # Check if table exists
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'alert_log'
        )
    """))

    if result.scalar():
        history = conn.execute(text("""
            SELECT alert_type, status, details, sent_at
            FROM alert_log
            WHERE client_id = :client_id
            ORDER BY sent_at DESC
            LIMIT 10
        """), {"client_id": client_id})

        rows = history.fetchall()
        if rows:
            import pandas as pd
            df = pd.DataFrame(rows, columns=['Type', 'Status', 'Details', 'Sent'])
            df['Sent'] = pd.to_datetime(df['Sent']).dt.strftime('%Y-%m-%d %H:%M')
            st.dataframe(df, width="stretch", hide_index=True)
        else:
            st.info("No alerts sent yet")
    else:
        st.info("No alert history available")
