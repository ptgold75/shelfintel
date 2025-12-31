import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st

st.set_page_config(page_title="ShelfIntel", layout="wide")

st.title("Real-time Digital Shelf Intelligence")
st.write(
    "Track **menu availability**, pricing, and product movement across dispensaries—"
    "so wholesalers and brands can spot off-menu events, distribution growth, and promo signals."
)
st.info("Signals are based on **menu availability**, not vault inventory.")

c1, c2, c3 = st.columns(3)
c1.metric("Dispensaries tracked (MD)", "0")
c2.metric("Menu items observed (24h)", "0")
c3.metric("Menu removals detected (7d)", "0")

st.write("Use the pages in the left sidebar to view dashboards and admin tools.")
