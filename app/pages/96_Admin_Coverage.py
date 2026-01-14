# app/pages/96_Admin_Coverage.py
"""Admin Coverage Tracker - Monitor scraping coverage by state."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from core.db import get_engine

st.set_page_config(page_title="Admin: Coverage | CannaLinx", page_icon=None, layout="wide", initial_sidebar_state="expanded")

# Import and render navigation
from components.sidebar_nav import render_nav
render_nav()

st.title("Scraping Coverage Tracker")
st.markdown("Monitor data collection progress across all states")

engine = get_engine()


@st.cache_data(ttl=60)
def get_coverage_stats():
    """Get comprehensive coverage statistics by state."""
    with engine.connect() as conn:
        df = pd.read_sql(text("""
            SELECT
                d.state,
                COUNT(DISTINCT d.dispensary_id) as total_dispensaries,
                COUNT(DISTINCT CASE WHEN d.menu_url IS NOT NULL THEN d.dispensary_id END) as with_menu_url,
                COUNT(DISTINCT CASE WHEN r.dispensary_id IS NOT NULL THEN d.dispensary_id END) as with_menu_data,
                COUNT(DISTINCT r.raw_menu_item_id) as total_products,
                COUNT(DISTINCT r.raw_brand) as unique_brands
            FROM dispensary d
            LEFT JOIN raw_menu_item r ON r.dispensary_id = d.dispensary_id
            WHERE d.is_active = true AND d.state IS NOT NULL
            GROUP BY d.state
            ORDER BY d.state
        """), conn)

    # Calculate percentages
    df['url_pct'] = (df['with_menu_url'] / df['total_dispensaries'] * 100).round(1)
    df['data_pct'] = (df['with_menu_data'] / df['with_menu_url'] * 100).fillna(0).round(1)
    df['needs_url'] = df['total_dispensaries'] - df['with_menu_url']
    df['needs_scrape'] = df['with_menu_url'] - df['with_menu_data']

    return df


@st.cache_data(ttl=60)
def get_provider_breakdown():
    """Get coverage breakdown by menu provider."""
    with engine.connect() as conn:
        df = pd.read_sql(text("""
            SELECT
                COALESCE(d.menu_provider, 'unknown') as provider,
                COUNT(DISTINCT d.dispensary_id) as total,
                COUNT(DISTINCT CASE WHEN r.dispensary_id IS NOT NULL THEN d.dispensary_id END) as with_data,
                COUNT(DISTINCT r.raw_menu_item_id) as products
            FROM dispensary d
            LEFT JOIN raw_menu_item r ON r.dispensary_id = d.dispensary_id
            WHERE d.is_active = true AND d.menu_url IS NOT NULL
            GROUP BY d.menu_provider
            ORDER BY total DESC
        """), conn)

    df['success_rate'] = (df['with_data'] / df['total'] * 100).round(1)
    return df


@st.cache_data(ttl=60)
def get_recent_scrape_activity():
    """Get recent scraping activity summary."""
    with engine.connect() as conn:
        df = pd.read_sql(text("""
            SELECT
                DATE(s.started_at) as scrape_date,
                COUNT(*) as total_runs,
                SUM(CASE WHEN s.status = 'success' THEN 1 ELSE 0 END) as successes,
                SUM(CASE WHEN s.status = 'fail' THEN 1 ELSE 0 END) as failures,
                SUM(s.records_found) as products_scraped
            FROM scrape_run s
            WHERE s.started_at > NOW() - INTERVAL '7 days'
            GROUP BY DATE(s.started_at)
            ORDER BY scrape_date DESC
        """), conn)
    return df


@st.cache_data(ttl=60)
def get_blockers():
    """Get breakdown of dispensaries blocked from scraping."""
    with engine.connect() as conn:
        df = pd.read_sql(text("""
            SELECT
                d.state,
                CASE
                    WHEN d.menu_provider IN ('jane', 'iheartjane') THEN 'Jane API (Cloudflare)'
                    WHEN d.menu_provider = 'dutchie' THEN 'Dutchie (needs discovery)'
                    WHEN d.menu_provider = 'breakwater' THEN 'Breakwater (custom)'
                    WHEN d.menu_url LIKE '%example.com%' THEN 'Placeholder URL'
                    WHEN d.menu_url IS NULL THEN 'No URL'
                    ELSE 'Other/Unknown'
                END as blocker_type,
                d.name,
                d.menu_provider,
                d.menu_url
            FROM dispensary d
            LEFT JOIN raw_menu_item r ON r.dispensary_id = d.dispensary_id
            WHERE d.is_active = true
              AND r.dispensary_id IS NULL
            ORDER BY d.state, blocker_type
        """), conn)
    return df


# Load data
coverage_df = get_coverage_stats()
provider_df = get_provider_breakdown()
activity_df = get_recent_scrape_activity()
blockers_df = get_blockers()

# Calculate totals
total_dispensaries = coverage_df['total_dispensaries'].sum()
total_with_url = coverage_df['with_menu_url'].sum()
total_with_data = coverage_df['with_menu_data'].sum()
total_products = coverage_df['total_products'].sum()
overall_coverage = round(total_with_data / total_with_url * 100, 1) if total_with_url > 0 else 0

# Header metrics
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Dispensaries", f"{total_dispensaries:,}")
col2.metric("With Menu URL", f"{total_with_url:,}", f"{round(total_with_url/total_dispensaries*100)}%")
col3.metric("With Menu Data", f"{total_with_data:,}", f"{overall_coverage}%")
col4.metric("Total Products", f"{total_products:,}")
col5.metric("Needs Scraping", f"{total_with_url - total_with_data:,}")

st.divider()

# Main content tabs
tab1, tab2, tab3, tab4 = st.tabs(["Coverage by State", "Provider Analysis", "Blockers", "Activity"])

with tab1:
    st.subheader("Coverage by State")

    # Coverage chart
    fig = go.Figure()

    # Sort by coverage percentage
    coverage_sorted = coverage_df.sort_values('data_pct', ascending=True)

    # Add bars for coverage
    fig.add_trace(go.Bar(
        y=coverage_sorted['state'],
        x=coverage_sorted['data_pct'],
        orientation='h',
        name='Data Coverage %',
        marker_color=coverage_sorted['data_pct'].apply(
            lambda x: '#22c55e' if x >= 90 else ('#f59e0b' if x >= 70 else '#ef4444')
        ),
        text=coverage_sorted['data_pct'].apply(lambda x: f"{x:.0f}%"),
        textposition='inside',
    ))

    fig.update_layout(
        title="Data Coverage by State",
        xaxis_title="Coverage %",
        yaxis_title="State",
        height=max(400, len(coverage_df) * 40),
        showlegend=False,
        xaxis=dict(range=[0, 105]),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Detailed table
    st.subheader("Detailed Coverage Table")

    display_df = coverage_df.copy()
    display_df['Status'] = display_df['data_pct'].apply(
        lambda x: 'Complete' if x >= 90 else ('Partial' if x >= 70 else 'Needs Work')
    )

    # Format for display
    table_df = display_df[[
        'state', 'total_dispensaries', 'with_menu_url', 'with_menu_data',
        'needs_url', 'needs_scrape', 'data_pct', 'total_products', 'unique_brands', 'Status'
    ]].copy()
    table_df.columns = [
        'State', 'Total', 'Has URL', 'Has Data',
        'Needs URL', 'Needs Scrape', 'Coverage %', 'Products', 'Brands', 'Status'
    ]

    # Color the status column
    def highlight_status(row):
        if row['Status'] == 'Complete':
            return [''] * len(row)
        elif row['Status'] == 'Partial':
            return ['background-color: #fef3c7'] * len(row)
        else:
            return ['background-color: #fee2e2'] * len(row)

    styled_df = table_df.style.apply(highlight_status, axis=1)
    st.dataframe(styled_df, use_container_width=True, height=450)

    # Summary by status
    st.markdown("---")
    status_counts = display_df['Status'].value_counts()
    scol1, scol2, scol3 = st.columns(3)
    scol1.metric("Complete (90%+)", status_counts.get('Complete', 0), delta="states")
    scol2.metric("Partial (70-89%)", status_counts.get('Partial', 0), delta="states")
    scol3.metric("Needs Work (<70%)", status_counts.get('Needs Work', 0), delta="states", delta_color="inverse")

with tab2:
    st.subheader("Provider Analysis")
    st.markdown("Success rate by menu provider type")

    # Provider success chart
    fig2 = go.Figure()

    fig2.add_trace(go.Bar(
        x=provider_df['provider'],
        y=provider_df['total'],
        name='Total Dispensaries',
        marker_color='#94a3b8',
    ))

    fig2.add_trace(go.Bar(
        x=provider_df['provider'],
        y=provider_df['with_data'],
        name='With Data',
        marker_color='#22c55e',
    ))

    fig2.update_layout(
        title="Dispensaries by Provider",
        xaxis_title="Provider",
        yaxis_title="Count",
        barmode='overlay',
        height=400,
    )

    st.plotly_chart(fig2, use_container_width=True)

    # Provider table
    provider_table = provider_df.copy()
    provider_table['needs_work'] = provider_table['total'] - provider_table['with_data']
    provider_table.columns = ['Provider', 'Total', 'With Data', 'Products', 'Success Rate %', 'Needs Work']

    st.dataframe(provider_table, use_container_width=True)

    # Provider recommendations
    st.markdown("---")
    st.markdown("**Provider Notes:**")
    for _, row in provider_df.iterrows():
        if row['success_rate'] < 50:
            st.warning(f"**{row['provider']}**: Only {row['success_rate']}% success rate - may need proxy/Playwright fixes")
        elif row['success_rate'] < 90:
            st.info(f"**{row['provider']}**: {row['success_rate']}% success rate - some dispensaries need attention")

with tab3:
    st.subheader("Blockers Analysis")
    st.markdown("Dispensaries that are blocked from scraping")

    if blockers_df.empty:
        st.success("No blocked dispensaries! All dispensaries have data.")
    else:
        # Summary by blocker type
        blocker_summary = blockers_df.groupby('blocker_type').size().reset_index(name='count')
        blocker_summary = blocker_summary.sort_values('count', ascending=False)

        fig3 = px.pie(
            blocker_summary,
            values='count',
            names='blocker_type',
            title="Blockers by Type",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        st.plotly_chart(fig3, use_container_width=True)

        # Detailed blocker list by state
        st.markdown("---")
        st.subheader("Blocked Dispensaries by State")

        state_filter = st.selectbox(
            "Filter by State",
            ["All"] + sorted(blockers_df['state'].dropna().unique().tolist())
        )

        filtered_blockers = blockers_df.copy()
        if state_filter != "All":
            filtered_blockers = filtered_blockers[filtered_blockers['state'] == state_filter]

        # Group by blocker type
        for blocker_type in filtered_blockers['blocker_type'].unique():
            type_df = filtered_blockers[filtered_blockers['blocker_type'] == blocker_type]
            with st.expander(f"{blocker_type} ({len(type_df)} dispensaries)"):
                for _, row in type_df.iterrows():
                    url_display = row['menu_url'][:60] + '...' if row['menu_url'] and len(row['menu_url']) > 60 else row['menu_url']
                    st.markdown(f"- **{row['state']}** | {row['name']} | `{row['menu_provider'] or 'unknown'}` | {url_display or 'No URL'}")

with tab4:
    st.subheader("Recent Scraping Activity")
    st.markdown("Last 7 days of scraping activity")

    if activity_df.empty:
        st.info("No scraping activity in the last 7 days")
    else:
        # Activity chart
        fig4 = go.Figure()

        fig4.add_trace(go.Bar(
            x=activity_df['scrape_date'],
            y=activity_df['successes'],
            name='Successes',
            marker_color='#22c55e',
        ))

        fig4.add_trace(go.Bar(
            x=activity_df['scrape_date'],
            y=activity_df['failures'],
            name='Failures',
            marker_color='#ef4444',
        ))

        fig4.update_layout(
            title="Scrape Runs by Day",
            xaxis_title="Date",
            yaxis_title="Scrape Runs",
            barmode='stack',
            height=350,
        )

        st.plotly_chart(fig4, use_container_width=True)

        # Products scraped
        fig5 = px.line(
            activity_df,
            x='scrape_date',
            y='products_scraped',
            title="Products Scraped by Day",
            markers=True
        )
        fig5.update_layout(height=300)
        st.plotly_chart(fig5, use_container_width=True)

        # Activity table
        st.markdown("---")
        activity_table = activity_df.copy()
        activity_table['success_rate'] = (activity_table['successes'] / activity_table['total_runs'] * 100).round(1)
        activity_table.columns = ['Date', 'Total Runs', 'Successes', 'Failures', 'Products', 'Success Rate %']
        st.dataframe(activity_table, use_container_width=True)

st.divider()

# Quick actions
st.subheader("Quick Actions")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("Refresh Coverage Stats"):
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO scrape_coverage (state, total_dispensaries, with_menu_url, with_menu_data, last_updated)
                SELECT d.state, COUNT(DISTINCT d.dispensary_id),
                       COUNT(DISTINCT CASE WHEN d.menu_url IS NOT NULL THEN d.dispensary_id END),
                       COUNT(DISTINCT CASE WHEN r.dispensary_id IS NOT NULL THEN d.dispensary_id END),
                       NOW()
                FROM dispensary d
                LEFT JOIN raw_menu_item r ON r.dispensary_id = d.dispensary_id
                WHERE d.is_active = true AND d.state IS NOT NULL
                GROUP BY d.state
                ON CONFLICT (state) DO UPDATE SET
                    total_dispensaries = EXCLUDED.total_dispensaries,
                    with_menu_url = EXCLUDED.with_menu_url,
                    with_menu_data = EXCLUDED.with_menu_data,
                    last_updated = NOW()
            """))
            conn.commit()
        st.success("Coverage stats refreshed!")
        st.cache_data.clear()
        st.rerun()

with col2:
    if st.button("Export Coverage Report"):
        csv = coverage_df.to_csv(index=False)
        st.download_button("Download CSV", csv, "coverage_report.csv", "text/csv")

with col3:
    if st.button("Export Blockers List"):
        csv = blockers_df.to_csv(index=False)
        st.download_button("Download CSV", csv, "blockers_list.csv", "text/csv")

st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Data refreshes every 60 seconds")
