import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import streamlit as st
import pandas as pd
from sqlalchemy import text
from zoneinfo import ZoneInfo

from core.db import get_engine

# -----------------------------
# Timezone display
# -----------------------------
LOCAL_TZ_NAME = "America/New_York"
LOCAL_TZ = ZoneInfo(LOCAL_TZ_NAME)

# -----------------------------
# Page setup
# -----------------------------
st.title("Dashboard")
st.caption(f"Times shown in {LOCAL_TZ_NAME}")

engine = get_engine()

# -----------------------------
# Top metrics
# -----------------------------
c1, c2, c3 = st.columns(3)
with engine.connect() as conn:
    d = conn.execute(text("select count(*) from dispensary")).scalar()
    r = conn.execute(text("select count(*) from scrape_run")).scalar()
    i = conn.execute(text("select count(*) from raw_menu_item")).scalar()

c1.metric("Dispensaries", d)
c2.metric("Scrape runs", r)
c3.metric("Raw menu items", i)

# -----------------------------
# Latest raw menu items
# -----------------------------
st.subheader("Latest raw menu items")

q = """
select
  observed_at,
  raw_category,
  raw_brand,
  raw_name,
  raw_price,
  raw_discount_price
from raw_menu_item
order by observed_at desc
limit 200
"""
df = pd.read_sql(q, engine)

# Convert observed_at from UTC → local time for display
if not df.empty:
    df["observed_at"] = (
        pd.to_datetime(df["observed_at"], utc=True)
        .dt.tz_convert(LOCAL_TZ_NAME)
    )

st.dataframe(df, use_container_width=True)
