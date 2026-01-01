import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
from sqlalchemy import text

from core.db import get_engine

st.set_page_config(page_title="ShelfIntel", layout="wide")

st.title("Real-time Digital Shelf Intelligence")
st.write(
    "Track **menu availability**, pricing, and product movement across dispensaries—"
    "so wholesalers and brands can spot off-menu events, distribution growth, and promo signals."
)
st.info("Signals are based on **menu availability**, not vault inventory.")

engine = get_engine()

with engine.connect() as conn:
    dispensaries_md = conn.execute(
        text("select count(*) from dispensary where state = 'MD'")
    ).scalar() or 0

    observed_24h = conn.execute(
        text("select count(*) from raw_menu_item where observed_at >= now() - interval '24 hours'")
    ).scalar() or 0

    removals_7d = conn.execute(
        text("""
            select count(*)
            from menu_item_event
            where event_type = 'disappeared'
              and event_at >= now() - interval '7 days'
        """)
    ).scalar() or 0

c1, c2, c3 = st.columns(3)
c1.metric("Dispensaries tracked (MD)", int(dispensaries_md))
c2.metric("Menu items observed (24h)", int(observed_24h))
c3.metric("Menu removals detected (7d)", int(removals_7d))

st.write("Use the pages in the left sidebar to view dashboards and admin tools.")
