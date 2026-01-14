# app/pages/50_Deals_Dashboard.py
"""Dashboard showing current deals and promotions from loyalty programs."""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text
from components.sidebar_nav import render_nav, render_state_filter
from components.auth import is_authenticated
from core.db import get_engine

st.set_page_config(
    page_title="Deals & Promotions - CannaLinx",
    layout="wide",
    initial_sidebar_state="expanded"
)

render_nav(require_login=False)

DEMO_MODE = not is_authenticated()

st.title("Deals & Promotions")
st.markdown("Real-time deals from dispensary loyalty programs")

engine = get_engine()


@st.cache_data(ttl=60)
def get_active_deals(state=None, hours=48):
    """Get deals from the past N hours."""
    query = """
        SELECT
            lm.message_id,
            d.name as dispensary,
            d.state,
            d.city,
            lm.raw_message,
            lm.deal_type,
            lm.discount_percent,
            lm.affected_brands,
            lm.affected_categories,
            lm.promo_code,
            lm.expires_at,
            lm.received_at,
            lm.parsed_deal
        FROM loyalty_message lm
        JOIN loyalty_subscription ls ON lm.subscription_id = ls.subscription_id
        JOIN dispensary d ON ls.dispensary_id = d.dispensary_id
        WHERE lm.received_at > NOW() - INTERVAL '%s hours'
    """ % hours

    if state:
        query += f" AND d.state = '{state}'"

    query += " ORDER BY lm.received_at DESC"

    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)


@st.cache_data(ttl=60)
def get_deal_stats(days=7):
    """Get deal statistics."""
    with engine.connect() as conn:
        # Total deals
        total = conn.execute(text(f"""
            SELECT COUNT(*) FROM loyalty_message
            WHERE received_at > NOW() - INTERVAL '{days} days'
        """)).scalar() or 0

        # Average discount
        avg = conn.execute(text(f"""
            SELECT AVG(discount_percent) FROM loyalty_message
            WHERE received_at > NOW() - INTERVAL '{days} days'
            AND discount_percent IS NOT NULL
        """)).scalar()

        # By deal type
        by_type = conn.execute(text(f"""
            SELECT deal_type, COUNT(*) FROM loyalty_message
            WHERE received_at > NOW() - INTERVAL '{days} days'
            AND deal_type IS NOT NULL
            GROUP BY deal_type
        """)).fetchall()

        # Best deals (highest discounts)
        best = conn.execute(text(f"""
            SELECT d.name, lm.discount_percent, lm.raw_message
            FROM loyalty_message lm
            JOIN loyalty_subscription ls ON lm.subscription_id = ls.subscription_id
            JOIN dispensary d ON ls.dispensary_id = d.dispensary_id
            WHERE lm.received_at > NOW() - INTERVAL '{days} days'
            AND lm.discount_percent IS NOT NULL
            ORDER BY lm.discount_percent DESC
            LIMIT 5
        """)).fetchall()

        return {
            "total": total,
            "avg_discount": round(float(avg), 1) if avg else None,
            "by_type": dict(by_type),
            "best_deals": best
        }


if DEMO_MODE:
    st.info("Demo Mode - Log in to see real-time deals from loyalty programs")

    # Demo data
    demo_deals = [
        {
            "dispensary": "Curaleaf Gaithersburg",
            "state": "MD",
            "deal_type": "percentage_off",
            "discount_percent": 30,
            "categories": ["flower"],
            "brands": ["Rythm"],
            "message": "FLASH SALE! 30% off all Rythm flower TODAY ONLY!",
            "promo_code": "FLASH30",
            "time_ago": "2 hours ago"
        },
        {
            "dispensary": "Zen Leaf Towson",
            "state": "MD",
            "deal_type": "bogo",
            "discount_percent": None,
            "categories": ["vapes"],
            "brands": ["Select"],
            "message": "BOGO 50% off all Select vapes this weekend!",
            "promo_code": None,
            "time_ago": "4 hours ago"
        },
        {
            "dispensary": "RISE Bloomfield",
            "state": "NJ",
            "deal_type": "percentage_off",
            "discount_percent": 25,
            "categories": ["edibles", "concentrates"],
            "brands": [],
            "message": "25% off edibles and concentrates! Valid through Sunday.",
            "promo_code": "WEEKEND25",
            "time_ago": "6 hours ago"
        },
        {
            "dispensary": "Trulieve Halethorpe",
            "state": "MD",
            "deal_type": "flash_sale",
            "discount_percent": 40,
            "categories": ["pre-rolls"],
            "brands": ["Cookies"],
            "message": "40% off Cookies pre-rolls! Limited stock!",
            "promo_code": None,
            "time_ago": "8 hours ago"
        },
        {
            "dispensary": "Curaleaf Bellmawr",
            "state": "NJ",
            "deal_type": "percentage_off",
            "discount_percent": 20,
            "categories": [],
            "brands": [],
            "message": "20% off your entire purchase! First-time customers get extra 10%",
            "promo_code": "WELCOME20",
            "time_ago": "12 hours ago"
        }
    ]

    # Demo stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Active Deals", len(demo_deals))
    with col2:
        st.metric("Avg Discount", "28%")
    with col3:
        st.metric("States Covered", 2)
    with col4:
        st.metric("Best Deal", "40% off")

    st.divider()

    # Filter
    col1, col2 = st.columns([1, 3])
    with col1:
        state_filter = st.selectbox("State", ["All", "MD", "NJ"], key="demo_state")
        deal_filter = st.selectbox("Deal Type", ["All", "percentage_off", "bogo", "flash_sale"], key="demo_deal")

    # Display deals
    st.subheader("Current Deals")

    for deal in demo_deals:
        if state_filter != "All" and deal["state"] != state_filter:
            continue
        if deal_filter != "All" and deal["deal_type"] != deal_filter:
            continue

        with st.container():
            col1, col2, col3 = st.columns([2, 3, 1])

            with col1:
                st.markdown(f"**{deal['dispensary']}**")
                st.caption(f"{deal['state']} | {deal['time_ago']}")

            with col2:
                st.markdown(deal["message"])
                tags = []
                if deal["discount_percent"]:
                    tags.append(f"**{deal['discount_percent']}% off**")
                if deal["deal_type"] == "bogo":
                    tags.append("**BOGO**")
                if deal["promo_code"]:
                    tags.append(f"`{deal['promo_code']}`")
                if deal["categories"]:
                    tags.extend([f"#{c}" for c in deal["categories"]])
                if deal["brands"]:
                    tags.extend([f"@{b}" for b in deal["brands"]])
                st.caption(" | ".join(tags))

            with col3:
                if deal["discount_percent"]:
                    st.markdown(f"### {deal['discount_percent']}%")
                elif deal["deal_type"] == "bogo":
                    st.markdown("### BOGO")

            st.divider()

else:
    # Real data mode
    state = render_state_filter()

    # Get deals
    deals_df = get_active_deals(state, hours=48)
    stats = get_deal_stats(days=7)

    # Stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Deals (48h)", len(deals_df))
    with col2:
        st.metric("Avg Discount", f"{stats['avg_discount']}%" if stats['avg_discount'] else "N/A")
    with col3:
        st.metric("Deals (7 days)", stats['total'])
    with col4:
        best = stats['best_deals'][0] if stats['best_deals'] else None
        st.metric("Best Deal", f"{best[1]}% at {best[0][:15]}" if best else "N/A")

    st.divider()

    if deals_df.empty:
        st.info("No deals in the past 48 hours. Subscribe to more dispensaries to see deals!")
        st.markdown("Go to **Admin > Loyalty Subscriptions** to add dispensaries")
    else:
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            deal_types = ["All"] + [t for t in deals_df['deal_type'].unique() if t]
            deal_filter = st.selectbox("Deal Type", deal_types)
        with col2:
            # Get unique categories
            all_cats = []
            for cats in deals_df['affected_categories'].dropna():
                if cats:
                    all_cats.extend(cats)
            cat_options = ["All"] + list(set(all_cats))
            cat_filter = st.selectbox("Category", cat_options)
        with col3:
            # Get unique brands
            all_brands = []
            for brands in deals_df['affected_brands'].dropna():
                if brands:
                    all_brands.extend(brands)
            brand_options = ["All"] + list(set(all_brands))
            brand_filter = st.selectbox("Brand", brand_options)

        # Apply filters
        display_df = deals_df.copy()
        if deal_filter != "All":
            display_df = display_df[display_df['deal_type'] == deal_filter]
        if cat_filter != "All":
            display_df = display_df[display_df['affected_categories'].apply(
                lambda x: cat_filter in x if x else False
            )]
        if brand_filter != "All":
            display_df = display_df[display_df['affected_brands'].apply(
                lambda x: brand_filter in x if x else False
            )]

        st.subheader(f"Current Deals ({len(display_df)})")

        for _, row in display_df.iterrows():
            with st.container():
                col1, col2, col3 = st.columns([2, 3, 1])

                with col1:
                    st.markdown(f"**{row['dispensary']}**")
                    time_ago = datetime.now() - pd.to_datetime(row['received_at']).replace(tzinfo=None)
                    hours_ago = int(time_ago.total_seconds() / 3600)
                    st.caption(f"{row['state']} | {hours_ago}h ago")

                with col2:
                    st.markdown(row['raw_message'][:200])
                    tags = []
                    if row['discount_percent']:
                        tags.append(f"**{int(row['discount_percent'])}% off**")
                    if row['deal_type'] == "bogo":
                        tags.append("**BOGO**")
                    if row['promo_code']:
                        tags.append(f"`{row['promo_code']}`")
                    if row['affected_categories']:
                        tags.extend([f"#{c}" for c in row['affected_categories']])
                    if row['affected_brands']:
                        tags.extend([f"@{b}" for b in row['affected_brands']])
                    if tags:
                        st.caption(" | ".join(tags))

                with col3:
                    if row['discount_percent']:
                        st.markdown(f"### {int(row['discount_percent'])}%")
                    elif row['deal_type'] == "bogo":
                        st.markdown("### BOGO")

                st.divider()

        # Best deals section
        if stats['best_deals']:
            st.subheader("Top Deals This Week")

            for disp, discount, msg in stats['best_deals']:
                st.markdown(f"**{int(discount)}% off** at **{disp}**")
                st.caption(msg[:100])
