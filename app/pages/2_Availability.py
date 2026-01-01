import streamlit as st
import pandas as pd
from sqlalchemy import text
from zoneinfo import ZoneInfo

from core.db import get_engine

st.set_page_config(page_title="Availability", layout="wide")

engine = get_engine()

# -----------------------------
# Timezone display (store UTC, display local)
# -----------------------------
LOCAL_TZ_NAME = "America/New_York"
LOCAL_TZ = ZoneInfo(LOCAL_TZ_NAME)


def df_tz_convert(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Convert tz-aware datetime columns to LOCAL_TZ for display."""
    if df is None or df.empty:
        return df
    for c in cols:
        if c in df.columns:
            # Only convert if the dtype is datetime-like
            try:
                df[c] = pd.to_datetime(df[c], utc=True).dt.tz_convert(LOCAL_TZ_NAME)
            except Exception:
                # If conversion fails (e.g., already local or not datetime), leave as-is
                pass
    return df


# -----------------------------
# Helpers
# -----------------------------
@st.cache_data(ttl=60)
def load_dispensaries():
    q = """
    select dispensary_id, name
    from dispensary
    order by name
    """
    return pd.read_sql(q, engine)


def query_df(sql: str, params: dict):
    return pd.read_sql(text(sql), engine, params=params)


# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.header("Filters")

disp_df = load_dispensaries()
if disp_df.empty:
    st.error("No dispensaries found.")
    st.stop()

disp_name = st.sidebar.selectbox("Dispensary", disp_df["name"].tolist())
disp_id = disp_df.loc[disp_df["name"] == disp_name, "dispensary_id"].iloc[0]

window_days = st.sidebar.selectbox("Activity window (days)", [7, 14, 30, 60, 90], index=2)
stable_days = st.sidebar.selectbox("Stability threshold (days)", [7, 14, 30, 60], index=2)

params = {"dispensary_id": disp_id, "window_days": window_days, "stable_days": stable_days}

# -----------------------------
# Header
# -----------------------------
st.title("📦 Availability Intelligence")
st.caption(f"{disp_name} · Times shown in {LOCAL_TZ_NAME}")

# -----------------------------
# Last scrape
# -----------------------------
last_scrape = query_df(
    """
    select started_at, finished_at, status, records_found
    from scrape_run
    where dispensary_id = :dispensary_id
    order by started_at desc
    limit 1
    """,
    params,
)

last_scrape = df_tz_convert(last_scrape, ["started_at", "finished_at"])

if not last_scrape.empty:
    r = last_scrape.iloc[0]
    finished = r.get("finished_at")
    finished_str = ""
    if pd.notna(finished):
        finished_str = finished.strftime("%Y-%m-%d %I:%M %p %Z")
    st.info(
        f"Last scrape: **{r['status']}** · "
        f"{int(r['records_found']) if pd.notna(r['records_found']) else '—'} items · "
        f"Finished at {finished_str or '—'}"
    )

# -----------------------------
# KPI Row
# -----------------------------
counts = query_df(
    """
    select
      count(*) filter (where currently_listed = 1) as listed_count,
      count(*) filter (where currently_listed = 0) as missing_count
    from menu_item_state
    where dispensary_id = :dispensary_id
    """,
    params,
)

events = query_df(
    """
    select event_type, count(*) as cnt
    from menu_item_event
    where dispensary_id = :dispensary_id
      and event_at >= now() - (:window_days || ' days')::interval
    group by event_type
    """,
    params,
)

appeared = int(events.loc[events["event_type"] == "appeared", "cnt"].sum()) if not events.empty else 0
disappeared = int(events.loc[events["event_type"] == "disappeared", "cnt"].sum()) if not events.empty else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Listed now", int(counts["listed_count"].iloc[0]) if not counts.empty else 0)
c2.metric("Missing now", int(counts["missing_count"].iloc[0]) if not counts.empty else 0)
c3.metric(f"Appeared ({window_days}d)", appeared)
c4.metric(f"Disappeared ({window_days}d)", disappeared)

# -----------------------------
# Tabs
# -----------------------------
tab_recent, tab_volatility, tab_stability = st.tabs(["Recent Changes", "Volatility", "Stability"])

# -----------------------------
# Recent Changes
# -----------------------------
with tab_recent:
    st.subheader("Recent events")

    recent_events = query_df(
        """
        select
          event_at,
          event_type,
          raw_name,
          raw_category,
          raw_brand
        from menu_item_event
        where dispensary_id = :dispensary_id
          and event_at >= now() - (:window_days || ' days')::interval
        order by event_at desc
        limit 200
        """,
        params,
    )
    recent_events = df_tz_convert(recent_events, ["event_at"])
    st.dataframe(recent_events, use_container_width=True)

    st.subheader("Recently disappeared")

    disappeared_recent = query_df(
        """
        select
          provider_product_id,
          max(event_at) as last_disappeared_at,
          max(raw_name) as raw_name,
          max(raw_category) as raw_category,
          max(raw_brand) as raw_brand
        from menu_item_event
        where dispensary_id = :dispensary_id
          and event_type = 'disappeared'
          and event_at >= now() - (:window_days || ' days')::interval
        group by provider_product_id
        order by last_disappeared_at desc
        limit 200
        """,
        params,
    )
    disappeared_recent = df_tz_convert(disappeared_recent, ["last_disappeared_at"])
    st.dataframe(disappeared_recent, use_container_width=True)

# -----------------------------
# Volatility
# -----------------------------
with tab_volatility:
    st.subheader("Most volatile products (by disappear events)")

    volatility = query_df(
        """
        select
          provider_product_id,
          max(raw_name) as raw_name,
          max(raw_category) as raw_category,
          max(raw_brand) as raw_brand,
          count(*) as disappeared_events
        from menu_item_event
        where dispensary_id = :dispensary_id
          and event_type = 'disappeared'
          and event_at >= now() - (:window_days || ' days')::interval
        group by provider_product_id
        order by disappeared_events desc
        limit 100
        """,
        params,
    )

    st.dataframe(volatility, use_container_width=True)

# -----------------------------
# Stability
# -----------------------------
with tab_stability:
    st.subheader("Longest on menu (currently listed)")

    longest = query_df(
        """
        select
          provider_product_id,
          raw_name,
          raw_category,
          raw_brand,
          first_seen_at,
          last_seen_at
        from menu_item_state
        where dispensary_id = :dispensary_id
          and currently_listed = 1
        order by first_seen_at asc
        limit 200
        """,
        params,
    )
    longest = df_tz_convert(longest, ["first_seen_at", "last_seen_at"])
    st.dataframe(longest, use_container_width=True)

    st.subheader(f"Listed continuously for ≥ {stable_days} days")

    stable = query_df(
        """
        select
          provider_product_id,
          raw_name,
          raw_category,
          raw_brand,
          first_seen_at,
          last_seen_at,
          last_missing_at
        from menu_item_state
        where dispensary_id = :dispensary_id
          and currently_listed = 1
          and (last_missing_at is null or last_missing_at < now() - (:stable_days || ' days')::interval)
        order by last_seen_at desc
        limit 200
        """,
        params,
    )
    stable = df_tz_convert(stable, ["first_seen_at", "last_seen_at", "last_missing_at"])
    st.dataframe(stable, use_container_width=True)
