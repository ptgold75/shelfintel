# app/pages/98_Admin_Dispensaries.py
"""Admin Dispensary Management - Track scraping status, URLs, and coverage."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from core.db import get_engine

st.set_page_config(page_title="Admin: Dispensaries | CannLinx", page_icon=None, layout="wide", initial_sidebar_state="collapsed")

# Import and render navigation
from components.nav import render_nav
render_nav()

st.title("Dispensary Management")
st.markdown("Track scraping status, fix issues, and manage dispensary data")

engine = get_engine()

@st.cache_data(ttl=60)
def get_dispensary_status():
    """Get comprehensive status for all dispensaries."""
    with engine.connect() as conn:
        df = pd.read_sql(text("""
            WITH latest_scrapes AS (
                SELECT
                    dispensary_id,
                    MAX(CASE WHEN status = 'success' THEN started_at END) as last_success,
                    MAX(CASE WHEN status = 'failed' THEN started_at END) as last_failure,
                    MAX(started_at) as last_attempt
                FROM scrape_run
                GROUP BY dispensary_id
            ),
            product_stats AS (
                SELECT
                    r.dispensary_id,
                    COUNT(DISTINCT r.raw_menu_item_id) as product_count,
                    COUNT(DISTINCT r.raw_category) as category_count,
                    STRING_AGG(DISTINCT COALESCE(r.raw_category, 'Unknown'), ', ' ORDER BY COALESCE(r.raw_category, 'Unknown')) as categories
                FROM raw_menu_item r
                JOIN scrape_run sr ON r.scrape_run_id = sr.scrape_run_id
                WHERE sr.status = 'success'
                AND sr.started_at = (
                    SELECT MAX(started_at) FROM scrape_run sr2
                    WHERE sr2.dispensary_id = r.dispensary_id AND sr2.status = 'success'
                )
                GROUP BY r.dispensary_id
            )
            SELECT
                d.dispensary_id,
                d.name,
                d.state,
                d.menu_url,
                d.menu_provider,
                d.provider_metadata,
                d.is_active,
                ls.last_success,
                ls.last_failure,
                ls.last_attempt,
                COALESCE(ps.product_count, 0) as product_count,
                COALESCE(ps.category_count, 0) as category_count,
                ps.categories
            FROM dispensary d
            LEFT JOIN latest_scrapes ls ON d.dispensary_id = ls.dispensary_id
            LEFT JOIN product_stats ps ON d.dispensary_id = ps.dispensary_id
            ORDER BY
                -- Priority: No data or failed at top
                CASE
                    WHEN ps.product_count IS NULL OR ps.product_count = 0 THEN 0
                    WHEN ps.product_count < 50 THEN 1
                    WHEN ls.last_failure > ls.last_success THEN 2
                    ELSE 3
                END,
                d.name
        """), conn)

    # Parse metadata
    def parse_meta(row):
        if row['provider_metadata']:
            try:
                meta = json.loads(row['provider_metadata']) if isinstance(row['provider_metadata'], str) else row['provider_metadata']
                return {
                    'county': meta.get('county', ''),
                    'store_id': meta.get('store_id', ''),
                    'retailer_id': meta.get('retailer_id', ''),
                    'address': meta.get('address', ''),
                    'website': meta.get('website', row['menu_url'] or '')
                }
            except:
                pass
        return {'county': '', 'store_id': '', 'retailer_id': '', 'address': '', 'website': row['menu_url'] or ''}

    meta_df = df.apply(parse_meta, axis=1, result_type='expand')
    df = pd.concat([df, meta_df], axis=1)

    return df

# Load data
df = get_dispensary_status()

# Summary metrics
total = len(df)
with_data = len(df[df['product_count'] > 0])
needs_attention = len(df[(df['product_count'] == 0) | (df['product_count'] < 50)])

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Dispensaries", total)
col2.metric("With Data", f"{with_data} ({with_data/total*100:.0f}%)")
col3.metric("Needs Attention", needs_attention, delta=f"-{needs_attention}" if needs_attention > 0 else None, delta_color="inverse")
col4.metric("Total Products", f"{df['product_count'].sum():,}")

st.divider()

# Tabs for different views
tab1, tab2, tab3 = st.tabs(["Needs Attention", "All Dispensaries", "Product Rankings"])

with tab1:
    st.subheader("Dispensaries Needing Attention")
    st.markdown("Missing data, low product counts, or failed scrapes")

    # Filter for problem dispensaries
    problem_df = df[(df['product_count'] == 0) | (df['product_count'] < 50) |
                    (df['last_failure'].notna() & (df['last_failure'] > df['last_success']))]

    if problem_df.empty:
        st.success("All dispensaries are in good shape!")
    else:
        for _, row in problem_df.iterrows():
            # Determine status
            if row['product_count'] == 0:
                status = "NO DATA"
                status_color = "red"
            elif row['product_count'] < 50:
                status = "LOW DATA"
                status_color = "orange"
            else:
                status = "FAILED"
                status_color = "yellow"

            with st.expander(f":{status_color}[{status}] **{row['name']}** - {row['product_count']} products, {row['category_count']} categories"):
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**Dispensary Info**")
                    st.write(f"**ID:** `{row['dispensary_id']}`")
                    st.write(f"**County:** {row['county'] or 'Unknown'}")
                    st.write(f"**Provider:** {row['menu_provider'] or 'Unknown'}")
                    st.write(f"**Store ID:** {row['store_id'] or 'N/A'}")
                    st.write(f"**Retailer ID:** {row['retailer_id'] or 'N/A'}")

                    if row['menu_url']:
                        st.write(f"**Menu URL:** [{row['menu_url'][:50]}...]({row['menu_url']})")
                    else:
                        st.warning("No menu URL configured")

                with col2:
                    st.markdown("**Scrape Status**")
                    if row['last_success']:
                        st.write(f"**Last Success:** {row['last_success']}")
                    else:
                        st.write("**Last Success:** Never")

                    if row['last_failure']:
                        st.write(f"**Last Failure:** {row['last_failure']}")

                    if row['categories']:
                        st.write(f"**Categories Found:** {row['categories'][:100]}")

                    # Action buttons
                    st.markdown("---")
                    url_input = st.text_input(f"Update Menu URL", value=row['menu_url'] or '', key=f"url_{row['dispensary_id']}")
                    if st.button("Save URL", key=f"save_{row['dispensary_id']}"):
                        with engine.connect() as conn:
                            conn.execute(text("""
                                UPDATE dispensary SET menu_url = :url WHERE dispensary_id = :id
                            """), {"url": url_input, "id": row['dispensary_id']})
                            conn.commit()
                        st.success("URL updated!")
                        st.cache_data.clear()
                        st.rerun()

with tab2:
    st.subheader("All Dispensaries")

    # Filters
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        county_filter = st.selectbox("Filter by County", ["All"] + sorted(df['county'].dropna().unique().tolist()))
    with filter_col2:
        provider_filter = st.selectbox("Filter by Provider", ["All"] + sorted(df['menu_provider'].dropna().unique().tolist()))
    with filter_col3:
        status_filter = st.selectbox("Filter by Status", ["All", "Has Data", "No Data", "Low Data (<50)"])

    # Apply filters
    filtered_df = df.copy()
    if county_filter != "All":
        filtered_df = filtered_df[filtered_df['county'] == county_filter]
    if provider_filter != "All":
        filtered_df = filtered_df[filtered_df['menu_provider'] == provider_filter]
    if status_filter == "Has Data":
        filtered_df = filtered_df[filtered_df['product_count'] >= 50]
    elif status_filter == "No Data":
        filtered_df = filtered_df[filtered_df['product_count'] == 0]
    elif status_filter == "Low Data (<50)":
        filtered_df = filtered_df[(filtered_df['product_count'] > 0) & (filtered_df['product_count'] < 50)]

    # Display table
    display_df = filtered_df[['name', 'county', 'menu_provider', 'product_count', 'category_count', 'last_success', 'menu_url']].copy()
    display_df.columns = ['Name', 'County', 'Provider', 'Products', 'Categories', 'Last Success', 'Menu URL']
    display_df['Last Success'] = pd.to_datetime(display_df['Last Success']).dt.strftime('%Y-%m-%d %H:%M')
    display_df['Menu URL'] = display_df['Menu URL'].apply(lambda x: x[:50] + '...' if x and len(x) > 50 else x)

    st.dataframe(display_df, use_container_width=True, height=500)

    # Export
    if st.button("Export to CSV"):
        csv = filtered_df.to_csv(index=False)
        st.download_button("Download CSV", csv, "dispensaries.csv", "text/csv")

with tab3:
    st.subheader("Product Count Rankings")
    st.markdown("Stores ranked by total products (most recent scrape)")

    # Rankings table
    rankings_df = df[df['product_count'] > 0].sort_values('product_count', ascending=False).copy()
    rankings_df['rank'] = range(1, len(rankings_df) + 1)

    display_rankings = rankings_df[['rank', 'name', 'product_count', 'category_count', 'categories', 'menu_provider']].copy()
    display_rankings.columns = ['Rank', 'Dispensary', 'Products', 'Categories', 'Category List', 'Provider']
    display_rankings['Category List'] = display_rankings['Category List'].apply(lambda x: x[:80] + '...' if x and len(x) > 80 else x)

    st.dataframe(display_rankings, use_container_width=True, height=600)

    # Summary stats
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    col1.metric("Average Products/Store", f"{rankings_df['product_count'].mean():.0f}")
    col2.metric("Median Products/Store", f"{rankings_df['product_count'].median():.0f}")
    col3.metric("Max Products", f"{rankings_df['product_count'].max()}")

    st.markdown("---")
    st.markdown("**Note:** Stores with < 100 products may have incomplete scrapes (partial categories)")

    # Flag low product stores
    low_product_stores = rankings_df[rankings_df['product_count'] < 100]['name'].tolist()
    if low_product_stores:
        st.warning(f"**Stores with potentially incomplete data:** {', '.join(low_product_stores[:10])}")

st.divider()

# URLs needed section
st.subheader("URLs Needed")
st.markdown("These dispensaries need menu URLs or updated configurations:")

no_url_df = df[(df['menu_url'].isna()) | (df['menu_url'] == '') | (df['product_count'] == 0)]
if not no_url_df.empty:
    for _, row in no_url_df.iterrows():
        st.markdown(f"- **{row['name']}** ({row['county'] or 'Unknown County'}): `{row['dispensary_id']}`")
else:
    st.success("All dispensaries have URLs configured!")

st.caption("Data refreshes every 60 seconds | Admin access required for edits")
