import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import streamlit as st
import pandas as pd
from sqlalchemy import text
from zoneinfo import ZoneInfo

from core.db import get_engine

# -----------------------------
# Config
# -----------------------------
LOCAL_TZ_NAME = "America/New_York"
LOCAL_TZ = ZoneInfo(LOCAL_TZ_NAME)

st.set_page_config(page_title="Availability", layout="wide")
st.title("Availability")
st.caption(f"Times shown in {LOCAL_TZ_NAME}")

engine = get_engine()

# -----------------------------
# Helpers
# -----------------------------
def to_local_series(s: pd.Series) -> pd.Series:
    """Convert a timestamp-like series to local timezone for display."""
    if s is None or len(s) == 0:
        return s
    dt = pd.to_datetime(s, utc=True, errors="coerce")
    try:
        return dt.dt.tz_convert(LOCAL_TZ_NAME)
    except Exception:
        return dt


@st.cache_data(ttl=60)
def list_columns(table_name: str) -> list[str]:
    q = """
    select column_name
    from information_schema.columns
    where table_schema='public' and table_name = :t
    order by ordinal_position
    """
    with engine.connect() as conn:
        rows = conn.execute(text(q), {"t": table_name}).fetchall()
    return [r[0] for r in rows]


@st.cache_data(ttl=60)
def load_dispensaries() -> pd.DataFrame:
    q = """
    select dispensary_id, name, state, city, menu_provider, menu_url
    from public.dispensary
    order by name
    """
    return pd.read_sql(q, engine)


def pick_first(existing_cols: list[str], candidates: list[str]) -> str | None:
    for c in candidates:
        if c in existing_cols:
            return c
    return None


# -----------------------------
# Load dispensaries
# -----------------------------
disp_df = load_dispensaries()
if disp_df.empty:
    st.warning("No dispensaries found in the database yet.")
    st.stop()

label_map = {
    row["name"]: row["dispensary_id"]
    for _, row in disp_df.iterrows()
}

left, right = st.columns([2, 1])
with left:
    selected_name = st.selectbox("Dispensary", list(label_map.keys()), index=0)
selected_id = label_map[selected_name]

with right:
    days = st.number_input("Lookback window (days)", min_value=1, max_value=90, value=7, step=1)

# -----------------------------
# Table/column introspection (robust across schema tweaks)
# -----------------------------
state_cols = list_columns("menu_item_state")
event_cols = list_columns("menu_item_event")
raw_cols = list_columns("raw_menu_item")

listed_col = pick_first(state_cols, ["is_listed", "listed", "active", "in_stock", "available"])
state_seen_col = pick_first(state_cols, ["last_seen_at", "observed_at", "updated_at", "seen_at", "created_at"])
event_time_col = pick_first(event_cols, ["event_at", "created_at", "observed_at", "timestamp", "ts"])
event_type_col = pick_first(event_cols, ["event_type", "type"])
event_name_col = pick_first(event_cols, ["name", "raw_name", "product_name"])
event_brand_col = pick_first(event_cols, ["brand", "raw_brand"])
event_category_col = pick_first(event_cols, ["category", "raw_category"])

raw_time_col = pick_first(raw_cols, ["observed_at", "created_at"])
raw_name_col = pick_first(raw_cols, ["raw_name"])
raw_brand_col = pick_first(raw_cols, ["raw_brand"])
raw_category_col = pick_first(raw_cols, ["raw_category"])
raw_price_col = pick_first(raw_cols, ["raw_price"])
raw_disc_price_col = pick_first(raw_cols, ["raw_discount_price"])

start_expr = f"now() - interval '{int(days)} days'"

# -----------------------------
# KPIs
# -----------------------------
k1, k2, k3, k4 = st.columns(4)

with engine.connect() as conn:
    # Current listed count (prefer menu_item_state if it has a listed flag)
    current_listed = None
    if listed_col:
        q_listed = f"""
        select count(*) 
        from public.menu_item_state
        where dispensary_id = :d and {listed_col} = true
        """
        current_listed = conn.execute(text(q_listed), {"d": selected_id}).scalar()

    # Fallback: use latest scrape snapshot from raw_menu_item
    if current_listed is None:
        if raw_time_col and raw_name_col:
            q_latest = f"""
            with latest as (
              select max({raw_time_col}) as mx
              from public.raw_menu_item
              where dispensary_id = :d
            )
            select count(*)
            from public.raw_menu_item r
            join latest on r.{raw_time_col} = latest.mx
            where r.dispensary_id = :d
            """
            current_listed = conn.execute(text(q_latest), {"d": selected_id}).scalar()
        else:
            current_listed = 0

    # Appeared/disappeared counts (prefer menu_item_event)
    appeared = disappeared = 0
    if event_time_col and event_type_col:
        q_events_counts = f"""
        select
          sum(case when {event_type_col} = 'appeared' then 1 else 0 end) as appeared,
          sum(case when {event_type_col} = 'disappeared' then 1 else 0 end) as disappeared
        from public.menu_item_event
        where dispensary_id = :d
          and {event_time_col} >= {start_expr}
        """
        row = conn.execute(text(q_events_counts), {"d": selected_id}).fetchone()
        if row:
            appeared = int(row[0] or 0)
            disappeared = int(row[1] or 0)

    # Last observed timestamp
    last_seen = None
    if raw_time_col:
        q_last = f"""
        select max({raw_time_col})
        from public.raw_menu_item
        where dispensary_id = :d
        """
        last_seen = conn.execute(text(q_last), {"d": selected_id}).scalar()

k1.metric("Currently listed", int(current_listed or 0))
k2.metric(f"Appeared (last {days}d)", int(appeared))
k3.metric(f"Disappeared (last {days}d)", int(disappeared))
k4.metric("Last observed (UTC)", str(last_seen) if last_seen else "—")

st.divider()

# -----------------------------
# Events table
# -----------------------------
st.subheader("Availability events")

if not (event_time_col and event_type_col):
    st.info("No event columns detected in menu_item_event. Showing latest raw snapshot instead.")
else:
    select_cols = [
        f"{event_time_col} as event_time",
        f"{event_type_col} as event_type",
    ]
    if event_category_col:
        select_cols.append(f"{event_category_col} as category")
    if event_brand_col:
        select_cols.append(f"{event_brand_col} as brand")
    if event_name_col:
        select_cols.append(f"{event_name_col} as name")

    q_events = f"""
    select {", ".join(select_cols)}
    from public.menu_item_event
    where dispensary_id = :d
      and {event_time_col} >= {start_expr}
    order by {event_time_col} desc
    limit 500
    """
    events_df = pd.read_sql(text(q_events), engine, params={"d": selected_id})

    if not events_df.empty and "event_time" in events_df.columns:
        events_df["event_time"] = to_local_series(events_df["event_time"])
        events_df = events_df.rename(columns={"event_time": f"event_time ({LOCAL_TZ_NAME})"})

    st.dataframe(events_df, use_container_width=True)

st.divider()

# -----------------------------
# Current listings view
# -----------------------------
st.subheader("Current / latest snapshot listings")

# Prefer menu_item_state if it contains enough context; otherwise show latest raw_menu_item snapshot.
if listed_col and state_seen_col:
    # Try to show a concise table of listed states
    show_cols = []
    # common descriptive columns if present
    for c in ["category", "raw_category", "brand", "raw_brand", "name", "raw_name", "product_name"]:
        if c in state_cols:
            show_cols.append(c)
    # always include listed + last_seen if present
    show_cols.append(listed_col)
    if state_seen_col not in show_cols:
        show_cols.append(state_seen_col)

    # ensure unique and exist
    show_cols = [c for i, c in enumerate(show_cols) if c in state_cols and c not in show_cols[:i]]
    if not show_cols:
        show_cols = [listed_col, state_seen_col]

    q_state = f"""
    select {", ".join(show_cols)}
    from public.menu_item_state
    where dispensary_id = :d
      and {listed_col} = true
    order by {state_seen_col} desc nulls last
    limit 500
    """
    state_df = pd.read_sql(text(q_state), engine, params={"d": selected_id})
    if not state_df.empty and state_seen_col in state_df.columns:
        state_df[state_seen_col] = to_local_series(state_df[state_seen_col])
        state_df = state_df.rename(columns={state_seen_col: f"{state_seen_col} ({LOCAL_TZ_NAME})"})
    st.dataframe(state_df, use_container_width=True)

else:
    # Latest raw snapshot (by observed_at)
    if not (raw_time_col and raw_name_col):
        st.warning("raw_menu_item does not have the expected columns to show a snapshot.")
    else:
        cols = []
        for c, alias in [
            (raw_time_col, "observed_at"),
            (raw_category_col, "category"),
            (raw_brand_col, "brand"),
            (raw_name_col, "name"),
            (raw_price_col, "price"),
            (raw_disc_price_col, "discount_price"),
        ]:
            if c:
                cols.append(f"{c} as {alias}")

        q_raw = f"""
        with latest as (
          select max({raw_time_col}) as mx
          from public.raw_menu_item
          where dispensary_id = :d
        )
        select {", ".join(cols)}
        from public.raw_menu_item r
        join latest on r.{raw_time_col} = latest.mx
        where r.dispensary_id = :d
        order by r.{raw_name_col} asc
        limit 1000
        """
        snap_df = pd.read_sql(text(q_raw), engine, params={"d": selected_id})
        if not snap_df.empty and "observed_at" in snap_df.columns:
            snap_df["observed_at"] = to_local_series(snap_df["observed_at"])
            snap_df = snap_df.rename(columns={"observed_at": f"observed_at ({LOCAL_TZ_NAME})"})
        st.dataframe(snap_df, use_container_width=True)

# Optional: schema info expander
with st.expander("Debug: detected columns (public schema)"):
    st.write("menu_item_state columns:", state_cols)
    st.write("menu_item_event columns:", event_cols)
    st.write("raw_menu_item columns:", raw_cols)
    st.write(
        {
            "listed_col": listed_col,
            "state_seen_col": state_seen_col,
            "event_time_col": event_time_col,
            "event_type_col": event_type_col,
        }
    )
