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

st.set_page_config(page_title="Admin: Dispensaries | CannaLinx", page_icon=None, layout="wide", initial_sidebar_state="expanded")

# Import and render navigation
from components.sidebar_nav import render_nav
render_nav()

st.title("Dispensary Management")
st.markdown("Track scraping status, fix issues, and manage dispensary data")

engine = get_engine()

@st.cache_data(ttl=60)
def get_md_dispensaries():
    """Get all Maryland dispensaries for cleanup tab."""
    with engine.connect() as conn:
        return pd.read_sql(text("""
            SELECT
                d.dispensary_id,
                d.name,
                d.address,
                d.city,
                d.store_type,
                d.is_active,
                d.menu_url,
                d.menu_provider,
                COALESCE(pc.product_count, 0) as products
            FROM dispensary d
            LEFT JOIN (
                SELECT dispensary_id, COUNT(*) as product_count
                FROM raw_menu_item
                GROUP BY dispensary_id
            ) pc ON d.dispensary_id = pc.dispensary_id
            WHERE d.state = 'MD'
            ORDER BY d.name
        """), conn)


@st.cache_data(ttl=300)
def get_dispensary_status():
    """Get status for active dispensaries only - fast query."""
    with engine.connect() as conn:
        # Only get active dispensaries with product counts
        df = pd.read_sql(text("""
            SELECT
                d.dispensary_id,
                d.name,
                d.state,
                d.menu_url,
                d.menu_provider,
                d.provider_metadata,
                d.is_active,
                COALESCE(pc.product_count, 0) as product_count,
                COALESCE(pc.category_count, 0) as category_count
            FROM dispensary d
            LEFT JOIN (
                SELECT dispensary_id,
                       COUNT(*) as product_count,
                       COUNT(DISTINCT raw_category) as category_count
                FROM raw_menu_item
                GROUP BY dispensary_id
            ) pc ON d.dispensary_id = pc.dispensary_id
            WHERE d.is_active = true
            ORDER BY d.state, d.name
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
tab1, tab2, tab3, tab4 = st.tabs(["Needs Attention", "All Dispensaries", "Product Rankings", "MD Cleanup"])

with tab1:
    st.subheader("Dispensaries Needing Attention")
    st.markdown("Missing data or low product counts")

    # Filter for problem dispensaries - simplified
    problem_df = df[(df['product_count'] == 0) | (df['product_count'] < 50)].head(100)

    if problem_df.empty:
        st.success("All dispensaries are in good shape!")
    else:
        st.info(f"Showing top 100 of {len(df[(df['product_count'] == 0) | (df['product_count'] < 50)])} dispensaries needing attention")
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

            with st.expander(f":{status_color}[{status}] **{row['name']}** ({row['state']}) - {row['product_count']:,} products"):
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**Dispensary Info**")
                    st.write(f"**ID:** `{row['dispensary_id']}`")
                    st.write(f"**State:** {row['state']}")
                    st.write(f"**Provider:** {row['menu_provider'] or 'Unknown'}")

                    if row['menu_url']:
                        st.write(f"**Menu URL:** [{row['menu_url'][:50]}...]({row['menu_url']})")
                    else:
                        st.warning("No menu URL configured")

                with col2:
                    # Action buttons
                    url_input = st.text_input(f"Update Menu URL", value=row['menu_url'] or '', key=f"url_{row['dispensary_id']}")
                    if st.button("Save URL", key=f"save_{row['dispensary_id']}"):
                        with engine.connect() as conn:
                            conn.execute(text("""
                                UPDATE dispensary SET menu_url = :url WHERE dispensary_id = :id
                            """), {"url": url_input, "id": row['dispensary_id']})
                            conn.commit()
                        st.success("URL updated!")
                        get_dispensary_status.clear()
                        st.rerun()

with tab2:
    st.subheader("All Dispensaries")

    # Filters
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        state_filter = st.selectbox("Filter by State", ["All"] + sorted(df['state'].dropna().unique().tolist()))
    with filter_col2:
        provider_filter = st.selectbox("Filter by Provider", ["All"] + sorted(df['menu_provider'].dropna().unique().tolist()))
    with filter_col3:
        status_filter = st.selectbox("Filter by Status", ["All", "Has Data", "No Data", "Low Data (<50)"])

    # Apply filters
    filtered_df = df.copy()
    if state_filter != "All":
        filtered_df = filtered_df[filtered_df['state'] == state_filter]
    if provider_filter != "All":
        filtered_df = filtered_df[filtered_df['menu_provider'] == provider_filter]
    if status_filter == "Has Data":
        filtered_df = filtered_df[filtered_df['product_count'] >= 50]
    elif status_filter == "No Data":
        filtered_df = filtered_df[filtered_df['product_count'] == 0]
    elif status_filter == "Low Data (<50)":
        filtered_df = filtered_df[(filtered_df['product_count'] > 0) & (filtered_df['product_count'] < 50)]

    # Display table
    display_df = filtered_df[['name', 'state', 'menu_provider', 'product_count', 'category_count', 'menu_url']].copy()
    display_df.columns = ['Name', 'State', 'Provider', 'Products', 'Categories', 'Menu URL']
    display_df['Menu URL'] = display_df['Menu URL'].apply(lambda x: x[:50] + '...' if x and len(x) > 50 else x)

    st.dataframe(display_df, use_container_width=True, height=500)

    # Export
    if st.button("Export to CSV"):
        csv = filtered_df.to_csv(index=False)
        st.download_button("Download CSV", csv, "dispensaries.csv", "text/csv")

with tab3:
    st.subheader("Product Count Rankings")
    st.markdown("Stores ranked by total products")

    # Rankings table
    rankings_df = df[df['product_count'] > 0].sort_values('product_count', ascending=False).head(200).copy()
    rankings_df['rank'] = range(1, len(rankings_df) + 1)

    display_rankings = rankings_df[['rank', 'name', 'state', 'product_count', 'category_count', 'menu_provider']].copy()
    display_rankings.columns = ['Rank', 'Dispensary', 'State', 'Products', 'Categories', 'Provider']

    st.dataframe(display_rankings, use_container_width=True, height=600)

    # Summary stats
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    col1.metric("Average Products/Store", f"{rankings_df['product_count'].mean():,.0f}")
    col2.metric("Median Products/Store", f"{rankings_df['product_count'].median():,.0f}")
    col3.metric("Max Products", f"{rankings_df['product_count'].max():,}")

    st.markdown("---")
    st.markdown("**Note:** Stores with < 100 products may have incomplete scrapes (partial categories)")

    # Flag low product stores
    low_product_stores = rankings_df[rankings_df['product_count'] < 100]['name'].tolist()
    if low_product_stores:
        st.warning(f"**Stores with potentially incomplete data:** {', '.join(low_product_stores[:10])}")

with tab4:
    st.subheader("Maryland Dispensary Cleanup")
    st.markdown("Mark duplicates and smoke shops to clean up MD data. Only ~112 are real dispensaries.")

    # Auto-detect duplicates helper
    with st.expander("Auto-Detect Potential Duplicates"):
        st.markdown("These dispensaries have very similar names and may be duplicates:")

        @st.cache_data(ttl=60)
        def find_potential_duplicates():
            with engine.connect() as conn:
                return pd.read_sql(text("""
                    WITH normalized AS (
                        SELECT
                            dispensary_id,
                            name,
                            city,
                            is_active,
                            LOWER(REGEXP_REPLACE(name, '[^a-zA-Z0-9]', '', 'g')) as norm_name
                        FROM dispensary
                        WHERE state = 'MD' AND is_active = true
                    )
                    SELECT
                        n1.name as name1,
                        n1.city as city1,
                        n1.dispensary_id as id1,
                        n2.name as name2,
                        n2.city as city2,
                        n2.dispensary_id as id2
                    FROM normalized n1
                    JOIN normalized n2 ON n1.norm_name = n2.norm_name
                        AND n1.dispensary_id < n2.dispensary_id
                    ORDER BY n1.name
                """), conn)

        dupes = find_potential_duplicates()
        if not dupes.empty:
            st.warning(f"Found {len(dupes)} potential duplicate pairs")
            for _, row in dupes.iterrows():
                st.markdown(f"- **{row['name1']}** ({row['city1']}) = **{row['name2']}** ({row['city2']})")
        else:
            st.success("No exact duplicates found")

        # Also check for similar addresses
        st.markdown("---")
        st.markdown("**Dispensaries at same address:**")

        @st.cache_data(ttl=60)
        def find_same_address():
            with engine.connect() as conn:
                return pd.read_sql(text("""
                    SELECT address, city, STRING_AGG(name, ' | ') as names, COUNT(*) as count
                    FROM dispensary
                    WHERE state = 'MD' AND is_active = true AND address IS NOT NULL
                    GROUP BY address, city
                    HAVING COUNT(*) > 1
                    ORDER BY count DESC
                """), conn)

        same_addr = find_same_address()
        if not same_addr.empty:
            for _, row in same_addr.iterrows():
                st.markdown(f"- **{row['address']}, {row['city']}**: {row['names']}")
        else:
            st.success("No duplicate addresses found")

        st.markdown("---")
        st.markdown("**Grouped by company name (same first word + city):**")

        @st.cache_data(ttl=60)
        def find_company_groups():
            with engine.connect() as conn:
                return pd.read_sql(text("""
                    WITH grouped AS (
                        SELECT
                            dispensary_id,
                            name,
                            city,
                            menu_provider,
                            LOWER(SPLIT_PART(name, ' ', 1)) as first_word,
                            (SELECT COUNT(*) FROM raw_menu_item WHERE dispensary_id = d.dispensary_id) as products
                        FROM dispensary d
                        WHERE state = 'MD' AND is_active = true
                    )
                    SELECT
                        first_word,
                        city,
                        COUNT(*) as count,
                        STRING_AGG(name || ' (' || COALESCE(products::text, '0') || ' products)', ' | ' ORDER BY products DESC) as names
                    FROM grouped
                    GROUP BY first_word, city
                    HAVING COUNT(*) > 1
                    ORDER BY count DESC, first_word
                """), conn)

        groups = find_company_groups()
        if not groups.empty:
            st.warning(f"Found {len(groups)} groups with duplicates in same city")
            for _, row in groups.head(20).iterrows():
                st.markdown(f"- **{row['first_word'].upper()} in {row['city']}** ({row['count']}): {row['names'][:150]}...")
        else:
            st.success("No same-company duplicates in same city")

        # Auto-cleanup button
        st.markdown("---")
        if st.button("Auto-Cleanup: Keep dispensary with most products, deactivate others", type="primary"):
            with engine.connect() as conn:
                # For each group, keep the one with most products
                result = conn.execute(text("""
                    WITH grouped AS (
                        SELECT
                            dispensary_id,
                            name,
                            city,
                            LOWER(SPLIT_PART(name, ' ', 1)) as first_word,
                            (SELECT COUNT(*) FROM raw_menu_item WHERE dispensary_id = d.dispensary_id) as products,
                            ROW_NUMBER() OVER (
                                PARTITION BY LOWER(SPLIT_PART(name, ' ', 1)), city
                                ORDER BY (SELECT COUNT(*) FROM raw_menu_item WHERE dispensary_id = d.dispensary_id) DESC, name
                            ) as rn
                        FROM dispensary d
                        WHERE state = 'MD' AND is_active = true
                    )
                    SELECT dispensary_id, name
                    FROM grouped
                    WHERE rn > 1
                """))

                to_deactivate = [(r[0], r[1]) for r in result]

                if to_deactivate:
                    for did, name in to_deactivate:
                        conn.execute(text("""
                            UPDATE dispensary SET store_type = 'duplicate', is_active = false
                            WHERE dispensary_id = :id
                        """), {"id": did})
                    conn.commit()
                    st.success(f"Deactivated {len(to_deactivate)} duplicates")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.info("No duplicates to clean up")

    # Get MD dispensaries (function defined at module level)
    md_df = get_md_dispensaries()

    # Debug info if empty
    if md_df.empty:
        st.error("No MD dispensaries found in database. Check database connection.")
        st.stop()

    # Summary
    total_md = len(md_df)
    active_md = len(md_df[md_df['is_active'].fillna(False) == True])
    dispensaries = len(md_df[(md_df['store_type'] == 'dispensary') & (md_df['is_active'] == True)])
    smoke_shops = len(md_df[(md_df['store_type'] == 'smoke_shop') & (md_df['is_active'] == True)])
    with_products = len(md_df[md_df['products'] > 0])

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total MD", total_md)
    col2.metric("Active", active_md)
    col3.metric("Dispensaries", dispensaries)
    col4.metric("Smoke Shops", smoke_shops)
    col5.metric("With Products", with_products)

    st.divider()

    # Filter options
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        show_filter = st.selectbox("Show", ["Active Only", "All", "Inactive Only"], key="md_show")
    with filter_col2:
        type_filter = st.selectbox("Store Type", ["All", "dispensary", "smoke_shop", "duplicate"], key="md_type")
    with filter_col3:
        search = st.text_input("Search by name", key="md_search")

    # Apply filters
    display_md = md_df.copy()
    if show_filter == "Active Only":
        display_md = display_md[display_md['is_active'].fillna(False) == True]
    elif show_filter == "Inactive Only":
        display_md = display_md[display_md['is_active'].fillna(False) == False]

    if type_filter != "All":
        display_md = display_md[display_md['store_type'].fillna('dispensary') == type_filter]

    if search:
        display_md = display_md[display_md['name'].str.lower().str.contains(search.lower(), na=False)]

    st.markdown(f"**Showing {len(display_md)} dispensaries**")

    if display_md.empty:
        st.warning("No dispensaries match the current filters. Try changing the filter options.")
        st.stop()

    # Prepare display dataframe with Select column
    table_df = display_md[['name', 'city', 'store_type', 'products', 'is_active', 'menu_provider', 'dispensary_id']].copy()
    table_df = table_df.reset_index(drop=True)

    # Add Select column - all unchecked by default
    table_df.insert(0, 'Select', False)

    st.markdown("### Select Dispensaries to Update")
    st.markdown("Check the boxes, then click an action button. Use the search filter above to find specific names.")

    # Use form to prevent auto-rerun on checkbox change
    with st.form("md_cleanup_form"):
        # Editable table with checkboxes
        edited_df = st.data_editor(
            table_df[['Select', 'name', 'city', 'store_type', 'products']].rename(columns={
                'name': 'Name',
                'city': 'City',
                'store_type': 'Type',
                'products': 'Products'
            }),
            hide_index=True,
            use_container_width=True,
            height=450,
            column_config={
                "Select": st.column_config.CheckboxColumn("Select", default=False, width="small"),
                "Products": st.column_config.NumberColumn("Products", width="small", format="%d"),
                "Type": st.column_config.TextColumn("Type", width="small"),
            },
            disabled=["Name", "City", "Type", "Products"],
            key="md_data_editor"
        )

        # Action buttons inside the form
        st.markdown("**Actions:**")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            smoke_shop_btn = st.form_submit_button("Mark as Smoke Shop", type="primary", use_container_width=True)
        with col2:
            duplicate_btn = st.form_submit_button("Mark as Duplicate", use_container_width=True)
        with col3:
            reactivate_btn = st.form_submit_button("Reactivate", use_container_width=True)
        with col4:
            st.form_submit_button("Refresh", use_container_width=True)

    # Process form submission
    selected_mask = edited_df['Select'].fillna(False)
    selected_ids = table_df.loc[selected_mask, 'dispensary_id'].tolist()

    if smoke_shop_btn and selected_ids:
        with engine.connect() as conn:
            for did in selected_ids:
                conn.execute(text("""
                    UPDATE dispensary SET store_type = 'smoke_shop', is_active = false
                    WHERE dispensary_id = :id
                """), {"id": did})
            conn.commit()
        st.success(f"Marked {len(selected_ids)} as smoke shop! Click 'Refresh' to update the list.")
        get_md_dispensaries.clear()

    if duplicate_btn and selected_ids:
        with engine.connect() as conn:
            for did in selected_ids:
                conn.execute(text("""
                    UPDATE dispensary SET store_type = 'duplicate', is_active = false
                    WHERE dispensary_id = :id
                """), {"id": did})
            conn.commit()
        st.success(f"Marked {len(selected_ids)} as duplicate! Click 'Refresh' to update the list.")
        get_md_dispensaries.clear()

    if reactivate_btn and selected_ids:
        with engine.connect() as conn:
            for did in selected_ids:
                conn.execute(text("""
                    UPDATE dispensary SET store_type = 'dispensary', is_active = true
                    WHERE dispensary_id = :id
                """), {"id": did})
            conn.commit()
        st.success(f"Reactivated {len(selected_ids)}! Click 'Refresh' to update the list.")
        get_md_dispensaries.clear()

    if (smoke_shop_btn or duplicate_btn or reactivate_btn) and not selected_ids:
        st.warning("No dispensaries selected. Check boxes in the table first.")

    st.divider()

    # Quick single action
    st.markdown("### Quick Single Action")
    disp_options = table_df['name'].tolist()
    selected_name = st.selectbox("Or select one dispensary", [""] + disp_options, key="quick_select")

    if selected_name:
        selected_row = table_df[table_df['name'] == selected_name].iloc[0]
        disp_id = selected_row['dispensary_id']

        st.caption(f"ID: {disp_id} | City: {selected_row['city']} | Products: {int(selected_row['products'] or 0):,}")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Smoke Shop", key="quick_smoke"):
                with engine.connect() as conn:
                    conn.execute(text("""
                        UPDATE dispensary SET store_type = 'smoke_shop', is_active = false
                        WHERE dispensary_id = :id
                    """), {"id": disp_id})
                    conn.commit()
                st.success(f"Marked {selected_name} as smoke shop")
                get_md_dispensaries.clear()
                st.rerun()

        with col2:
            if st.button("Duplicate", key="quick_dup"):
                with engine.connect() as conn:
                    conn.execute(text("""
                        UPDATE dispensary SET store_type = 'duplicate', is_active = false
                        WHERE dispensary_id = :id
                    """), {"id": disp_id})
                    conn.commit()
                st.success(f"Marked {selected_name} as duplicate")
                get_md_dispensaries.clear()
                st.rerun()

        with col3:
            if st.button("Reactivate", key="quick_activate"):
                with engine.connect() as conn:
                    conn.execute(text("""
                        UPDATE dispensary SET store_type = 'dispensary', is_active = true
                        WHERE dispensary_id = :id
                    """), {"id": disp_id})
                    conn.commit()
                st.success(f"Reactivated {selected_name}")
                get_md_dispensaries.clear()
                st.rerun()

st.divider()

# URLs needed section
st.subheader("URLs Needed")
st.markdown("These dispensaries need menu URLs or updated configurations:")

no_url_df = df[(df['menu_url'].isna()) | (df['menu_url'] == '') | (df['product_count'] == 0)].head(50)
if not no_url_df.empty:
    st.info(f"Showing first 50 dispensaries needing URLs")
    for _, row in no_url_df.iterrows():
        st.markdown(f"- **{row['name']}** ({row['state']}): `{row['dispensary_id']}`")
else:
    st.success("All dispensaries have URLs configured!")

st.caption("Data refreshes every 5 minutes | Admin access required for edits")
