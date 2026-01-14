# app/pages/93_Admin_Loyalty.py
"""Admin page for managing loyalty program SMS subscriptions."""

import streamlit as st
import pandas as pd
from sqlalchemy import text
from components.sidebar_nav import render_nav
from components.auth import is_authenticated, is_admin
from core.db import get_engine
from core.loyalty import create_subscription, generate_random_address, parse_deal_with_ai

st.set_page_config(
    page_title="Loyalty Subscriptions - Admin - CannaLinx",
    layout="wide",
    initial_sidebar_state="expanded"
)

render_nav(require_login=True)

# Check admin access
if not is_authenticated() or not is_admin():
    st.error("Admin access required")
    st.stop()

st.title("Loyalty Program Subscriptions")
st.markdown("Manage SMS subscriptions to dispensary loyalty programs")

engine = get_engine()


@st.cache_data(ttl=60)
def get_subscriptions():
    """Get all loyalty subscriptions."""
    with engine.connect() as conn:
        return pd.read_sql(text("""
            SELECT
                ls.subscription_id,
                d.name as dispensary_name,
                d.state,
                d.city,
                ls.twilio_phone,
                ls.dispensary_phone,
                ls.signup_name,
                ls.signup_address,
                ls.signup_city,
                ls.is_active,
                ls.signup_date,
                (SELECT COUNT(*) FROM loyalty_message lm WHERE lm.subscription_id = ls.subscription_id) as message_count,
                (SELECT MAX(received_at) FROM loyalty_message lm WHERE lm.subscription_id = ls.subscription_id) as last_message
            FROM loyalty_subscription ls
            JOIN dispensary d ON ls.dispensary_id = d.dispensary_id
            ORDER BY ls.signup_date DESC
        """), conn)


@st.cache_data(ttl=60)
def get_dispensaries_without_subscription(state=None):
    """Get dispensaries that don't have a loyalty subscription yet."""
    query = """
        SELECT d.dispensary_id, d.name, d.state, d.city
        FROM dispensary d
        WHERE d.is_active = true
        AND d.dispensary_id NOT IN (
            SELECT dispensary_id FROM loyalty_subscription WHERE is_active = true
        )
    """
    params = {}

    if state:
        query += " AND d.state = :state"
        params["state"] = state

    query += " ORDER BY d.state, d.name LIMIT 200"

    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)


@st.cache_data(ttl=60)
def get_recent_messages(limit=50):
    """Get recent SMS messages."""
    with engine.connect() as conn:
        return pd.read_sql(text("""
            SELECT
                lm.message_id,
                d.name as dispensary,
                d.state,
                lm.from_number,
                lm.raw_message,
                lm.deal_type,
                lm.discount_percent,
                lm.promo_code,
                lm.received_at
            FROM loyalty_message lm
            JOIN loyalty_subscription ls ON lm.subscription_id = ls.subscription_id
            JOIN dispensary d ON ls.dispensary_id = d.dispensary_id
            ORDER BY lm.received_at DESC
            LIMIT :limit
        """), conn, params={"limit": limit})


# Stats at top
subs_df = get_subscriptions()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Active Subscriptions", len(subs_df[subs_df['is_active'] == True]) if not subs_df.empty else 0)
with col2:
    st.metric("Total Messages", f"{subs_df['message_count'].sum():,}" if not subs_df.empty else 0)
with col3:
    states = subs_df['state'].nunique() if not subs_df.empty else 0
    st.metric("States Covered", states)
with col4:
    # Count messages today
    msgs_df = get_recent_messages(500)
    today_count = len(msgs_df[pd.to_datetime(msgs_df['received_at']).dt.date == pd.Timestamp.now().date()]) if not msgs_df.empty else 0
    st.metric("Messages Today", today_count)

st.divider()

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["Subscriptions", "Add New", "Messages", "Test Parser"])

with tab1:
    st.subheader("Current Subscriptions")

    if not subs_df.empty:
        # Filter by state
        states = ["All"] + sorted(subs_df['state'].unique().tolist())
        filter_state = st.selectbox("Filter by State", states, key="sub_state_filter")

        display_df = subs_df.copy()
        if filter_state != "All":
            display_df = display_df[display_df['state'] == filter_state]

        # Format for display
        display_df['Status'] = display_df['is_active'].apply(lambda x: "Active" if x else "Inactive")
        display_df['Messages'] = display_df['message_count']
        display_df['Last Message'] = pd.to_datetime(display_df['last_message']).dt.strftime('%Y-%m-%d %H:%M')

        st.dataframe(
            display_df[['dispensary_name', 'state', 'city', 'twilio_phone', 'Status', 'Messages', 'Last Message']],
            column_config={
                "dispensary_name": "Dispensary",
                "state": "State",
                "city": "City",
                "twilio_phone": "Twilio Phone",
                "Status": "Status",
                "Messages": st.column_config.NumberColumn("Messages"),
                "Last Message": "Last Message"
            },
            use_container_width=True,
            hide_index=True
        )

        # Deactivate subscription
        st.markdown("---")
        st.markdown("**Manage Subscription**")

        sub_to_manage = st.selectbox(
            "Select Subscription",
            options=display_df['subscription_id'].tolist(),
            format_func=lambda x: display_df[display_df['subscription_id'] == x]['dispensary_name'].values[0]
        )

        if st.button("Deactivate Selected", type="secondary"):
            with engine.connect() as conn:
                conn.execute(text("""
                    UPDATE loyalty_subscription SET is_active = false WHERE subscription_id = :id
                """), {"id": sub_to_manage})
                conn.commit()
            st.success("Subscription deactivated")
            st.cache_data.clear()
            st.rerun()
    else:
        st.info("No subscriptions yet. Add one in the 'Add New' tab.")

with tab2:
    st.subheader("Add New Subscription")

    st.markdown("""
    **Instructions:**
    1. Select a dispensary to subscribe to
    2. Enter your Twilio phone number (the number that will receive SMS)
    3. Enter the dispensary's SMS signup number (if known)
    4. Click 'Create Subscription'
    5. Manually sign up for their loyalty program using the generated info
    """)

    col1, col2 = st.columns(2)

    with col1:
        # Filter by state
        state_filter = st.selectbox(
            "Filter by State",
            ["MD", "NJ", "PA", "DE", "VA", "IL"],
            key="add_state_filter"
        )

        available = get_dispensaries_without_subscription(state_filter)

        if not available.empty:
            selected_disp = st.selectbox(
                "Select Dispensary",
                options=available['dispensary_id'].tolist(),
                format_func=lambda x: f"{available[available['dispensary_id'] == x]['name'].values[0]} ({available[available['dispensary_id'] == x]['city'].values[0]})"
            )

            # Show dispensary info
            disp_info = available[available['dispensary_id'] == selected_disp].iloc[0]
            st.markdown(f"**{disp_info['name']}**")
            st.caption(f"{disp_info['city']}, {disp_info['state']}")
        else:
            st.warning("No available dispensaries in this state without subscriptions")
            selected_disp = None

    with col2:
        twilio_phone = st.text_input(
            "Twilio Phone Number",
            placeholder="+1XXXXXXXXXX",
            help="Your Twilio number that will receive SMS messages"
        )

        dispensary_phone = st.text_input(
            "Dispensary SMS Number (optional)",
            placeholder="+1XXXXXXXXXX",
            help="The number you text to sign up for their loyalty program"
        )

        notes = st.text_area(
            "Notes",
            placeholder="Any notes about this subscription...",
            height=100
        )

    # Preview signup info
    if selected_disp:
        st.markdown("---")
        st.markdown("**Signup Information Preview**")

        disp_row = available[available['dispensary_id'] == selected_disp].iloc[0]
        preview_addr = generate_random_address(
            disp_row['city'] or "Baltimore",
            disp_row['state'] or "MD"
        )

        col1, col2 = st.columns(2)
        with col1:
            st.text(f"Name: {preview_addr['name']}")
            st.text(f"Address: {preview_addr['address']}")
        with col2:
            st.text(f"City: {preview_addr['city']}")
            st.text(f"State: {preview_addr['state']} {preview_addr['zip']}")

        if st.button("Create Subscription", type="primary", disabled=not twilio_phone):
            if selected_disp and twilio_phone:
                try:
                    sub_id = create_subscription(
                        dispensary_id=selected_disp,
                        twilio_phone=twilio_phone,
                        dispensary_phone=dispensary_phone or None,
                        notes=notes or None
                    )
                    st.success(f"Subscription created! ID: {sub_id}")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.error("Please select a dispensary and enter a Twilio phone number")

with tab3:
    st.subheader("Recent Messages")

    msgs_df = get_recent_messages(100)

    if not msgs_df.empty:
        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            msg_state_filter = st.selectbox(
                "Filter by State",
                ["All"] + sorted(msgs_df['state'].unique().tolist()),
                key="msg_state_filter"
            )
        with col2:
            deal_type_filter = st.selectbox(
                "Filter by Deal Type",
                ["All"] + [t for t in msgs_df['deal_type'].unique().tolist() if t],
                key="msg_deal_filter"
            )

        display_msgs = msgs_df.copy()
        if msg_state_filter != "All":
            display_msgs = display_msgs[display_msgs['state'] == msg_state_filter]
        if deal_type_filter != "All":
            display_msgs = display_msgs[display_msgs['deal_type'] == deal_type_filter]

        for _, row in display_msgs.iterrows():
            with st.expander(f"**{row['dispensary']}** ({row['state']}) - {row['received_at']}"):
                st.markdown(f"**Message:**\n{row['raw_message']}")
                st.markdown("---")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.caption(f"Deal Type: {row['deal_type'] or 'Unknown'}")
                with col2:
                    if row['discount_percent']:
                        st.caption(f"Discount: {row['discount_percent']}%")
                with col3:
                    if row['promo_code']:
                        st.caption(f"Code: {row['promo_code']}")
    else:
        st.info("No messages received yet")

with tab4:
    st.subheader("Test Deal Parser")
    st.markdown("Enter a sample SMS message to see how it will be parsed")

    test_message = st.text_area(
        "Sample SMS Message",
        placeholder="Enter a promotional SMS message to test parsing...",
        height=150,
        value="FLASH SALE! 30% off all Rythm flower TODAY ONLY! Use code FLASH30. Exp 1/15"
    )

    if st.button("Parse Message"):
        if test_message:
            result = parse_deal_with_ai(test_message)

            st.markdown("**Parsed Result:**")
            col1, col2 = st.columns(2)

            with col1:
                st.json({
                    "deal_type": result.get("deal_type"),
                    "discount_percent": result.get("discount_percent"),
                    "discount_amount": result.get("discount_amount"),
                    "bogo": result.get("bogo"),
                    "promo_code": result.get("promo_code")
                })

            with col2:
                st.json({
                    "affected_brands": result.get("affected_brands"),
                    "affected_categories": result.get("affected_categories"),
                    "expires_at": result.get("expires_at"),
                    "raw_summary": result.get("raw_summary")
                })
        else:
            st.warning("Please enter a message to parse")


# Twilio Setup Instructions
st.markdown("---")
st.markdown("""
### Twilio Setup Instructions

1. **Create Twilio Account**: Sign up at [twilio.com](https://twilio.com)

2. **Get Phone Numbers**: Buy phone numbers for each state (~$1/month each)

3. **Configure Webhook**: Set the SMS webhook URL to:
   ```
   https://your-app-domain.com/api/sms/webhook
   ```

4. **Environment Variables**: Add to your `.env`:
   ```
   TWILIO_ACCOUNT_SID=your_account_sid
   TWILIO_AUTH_TOKEN=your_auth_token
   ```

5. **Sign Up Process**:
   - Visit the dispensary or their website
   - Sign up for their loyalty/text program
   - Use the generated name (Sam Davidson) and address
   - Use your Twilio phone number as the mobile number
""")
