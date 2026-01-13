# app/pages/99_Admin_Brands.py
"""Admin Brand Hierarchy Management - Map child brands to master brands."""

import streamlit as st
import pandas as pd
from sqlalchemy import text
from components.sidebar_nav import render_nav
from components.auth import is_authenticated, is_admin
from core.db import get_engine

st.set_page_config(
    page_title="Brand Hierarchy - Admin - CannLinx",
    layout="wide",
    initial_sidebar_state="expanded"
)

render_nav(require_login=True)

# Check admin access
if not is_authenticated() or not is_admin():
    st.error("Admin access required")
    st.stop()

st.title("Brand Hierarchy Management")
st.markdown("Map child brands to master brands (manufacturers/parent companies)")

engine = get_engine()


@st.cache_data(ttl=60)
def get_brand_hierarchy():
    """Get all brand hierarchy mappings."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, master_brand, child_brand, notes,
                   created_at, updated_at
            FROM brand_hierarchy
            ORDER BY master_brand, child_brand
        """))
        rows = result.fetchall()
        return pd.DataFrame(rows, columns=['ID', 'Master Brand', 'Child Brand', 'Notes', 'Created', 'Updated'])


@st.cache_data(ttl=60)
def get_master_brands():
    """Get list of master brands."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT DISTINCT master_brand FROM brand_hierarchy ORDER BY master_brand
        """))
        return [row[0] for row in result]


@st.cache_data(ttl=60)
def get_unmapped_brands(min_products=10):
    """Get brands that aren't in the hierarchy yet."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT UPPER(r.raw_brand) as brand, COUNT(*) as product_count
            FROM raw_menu_item r
            WHERE r.raw_brand IS NOT NULL AND r.raw_brand != ''
            AND UPPER(r.raw_brand) NOT IN (
                SELECT UPPER(child_brand) FROM brand_hierarchy
            )
            GROUP BY UPPER(r.raw_brand)
            HAVING COUNT(*) >= :min_products
            ORDER BY COUNT(*) DESC
            LIMIT 200
        """), {"min_products": min_products})
        rows = result.fetchall()
        return pd.DataFrame(rows, columns=['Brand', 'Products'])


@st.cache_data(ttl=60)
def get_hierarchy_stats():
    """Get statistics about brand hierarchy."""
    with engine.connect() as conn:
        # Count mapped products
        result = conn.execute(text("""
            SELECT
                (SELECT COUNT(DISTINCT master_brand) FROM brand_hierarchy) as master_count,
                (SELECT COUNT(*) FROM brand_hierarchy) as mapping_count,
                (SELECT COUNT(*) FROM raw_menu_item WHERE UPPER(raw_brand) IN
                    (SELECT UPPER(child_brand) FROM brand_hierarchy)) as mapped_products,
                (SELECT COUNT(*) FROM raw_menu_item WHERE raw_brand IS NOT NULL) as total_products
        """))
        return result.fetchone()


def add_brand_mapping(master_brand: str, child_brand: str, notes: str = None):
    """Add a new brand mapping."""
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO brand_hierarchy (master_brand, child_brand, notes)
            VALUES (:master, :child, :notes)
            ON CONFLICT (child_brand) DO UPDATE SET
                master_brand = EXCLUDED.master_brand,
                notes = EXCLUDED.notes,
                updated_at = NOW()
        """), {"master": master_brand.upper(), "child": child_brand.upper(), "notes": notes})
        conn.commit()


def delete_brand_mapping(child_brand: str):
    """Delete a brand mapping."""
    with engine.connect() as conn:
        conn.execute(text("""
            DELETE FROM brand_hierarchy WHERE UPPER(child_brand) = UPPER(:child)
        """), {"child": child_brand})
        conn.commit()


# Stats at top
stats = get_hierarchy_stats()
if stats:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Master Brands", stats[0])
    with col2:
        st.metric("Total Mappings", stats[1])
    with col3:
        mapped_pct = round(stats[2] / stats[3] * 100, 1) if stats[3] > 0 else 0
        st.metric("Mapped Products", f"{stats[2]:,} ({mapped_pct}%)")
    with col4:
        st.metric("Total Products", f"{stats[3]:,}")

st.markdown("---")

# Tabs for different functions
tab1, tab2, tab3 = st.tabs(["View Hierarchy", "Add Mappings", "Unmapped Brands"])

with tab1:
    st.subheader("Current Brand Hierarchy")

    # Filter by master brand
    master_brands = get_master_brands()
    filter_master = st.selectbox(
        "Filter by Master Brand",
        ["All"] + master_brands,
        key="filter_master"
    )

    df = get_brand_hierarchy()

    if filter_master != "All":
        df = df[df['Master Brand'] == filter_master]

    if not df.empty:
        # Group by master brand for display
        for master in df['Master Brand'].unique():
            master_df = df[df['Master Brand'] == master]
            with st.expander(f"**{master}** ({len(master_df)} brands)", expanded=(filter_master != "All")):
                for _, row in master_df.iterrows():
                    col1, col2, col3 = st.columns([3, 4, 1])
                    with col1:
                        st.write(f"**{row['Child Brand']}**")
                    with col2:
                        st.caption(row['Notes'] or "")
                    with col3:
                        if st.button("Delete", key=f"del_{row['ID']}", type="secondary"):
                            delete_brand_mapping(row['Child Brand'])
                            st.cache_data.clear()
                            st.rerun()
    else:
        st.info("No brand mappings found")

with tab2:
    st.subheader("Add Brand Mapping")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Add to Existing Master Brand**")

        existing_masters = get_master_brands()
        if existing_masters:
            selected_master = st.selectbox("Master Brand", existing_masters, key="add_existing_master")
            new_child = st.text_input("Child Brand Name", key="add_child_existing")
            new_notes = st.text_input("Notes (optional)", key="add_notes_existing")

            if st.button("Add to Master Brand", type="primary"):
                if new_child:
                    add_brand_mapping(selected_master, new_child, new_notes)
                    st.success(f"Added {new_child} under {selected_master}")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Please enter a child brand name")

    with col2:
        st.markdown("**Create New Master Brand**")

        new_master = st.text_input("New Master Brand Name", key="new_master")
        new_child_for_new = st.text_input("First Child Brand", key="new_child_for_new")
        new_notes_for_new = st.text_input("Notes (optional)", key="new_notes_for_new")

        if st.button("Create Master Brand", type="primary"):
            if new_master and new_child_for_new:
                add_brand_mapping(new_master, new_child_for_new, new_notes_for_new)
                st.success(f"Created {new_master} with {new_child_for_new}")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Please enter both master and child brand names")

    st.markdown("---")
    st.markdown("**Bulk Add (paste list)**")

    bulk_master = st.text_input("Master Brand for bulk add", key="bulk_master")
    bulk_brands = st.text_area(
        "Child brands (one per line)",
        height=150,
        key="bulk_brands",
        help="Enter one brand per line. These will all be mapped to the master brand above."
    )

    if st.button("Bulk Add Brands"):
        if bulk_master and bulk_brands:
            brands = [b.strip() for b in bulk_brands.split('\n') if b.strip()]
            added = 0
            for brand in brands:
                try:
                    add_brand_mapping(bulk_master, brand)
                    added += 1
                except Exception as e:
                    st.warning(f"Could not add {brand}: {e}")
            st.success(f"Added {added} brands under {bulk_master}")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("Please enter master brand and at least one child brand")

with tab3:
    st.subheader("Unmapped Brands")
    st.markdown("These brands have products but aren't mapped to any master brand yet.")

    min_products = st.slider("Minimum products", 5, 100, 20)

    unmapped = get_unmapped_brands(min_products)

    if not unmapped.empty:
        st.info(f"Found {len(unmapped)} unmapped brands with {min_products}+ products")

        # Quick add functionality
        st.markdown("**Quick Add** - Select brands to map:")

        quick_master = st.selectbox(
            "Add selected brands to:",
            ["-- Select Master Brand --"] + get_master_brands() + ["+ Create New"],
            key="quick_master"
        )

        if quick_master == "+ Create New":
            quick_master = st.text_input("Enter new master brand name", key="quick_new_master")

        # Show unmapped brands with checkboxes
        selected_brands = []

        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("**Brand**")
        with col2:
            st.markdown("**Products**")

        for _, row in unmapped.head(50).iterrows():
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                if st.checkbox(row['Brand'], key=f"sel_{row['Brand']}"):
                    selected_brands.append(row['Brand'])
            with col2:
                st.write(f"{row['Products']:,}")
            with col3:
                # Quick single add
                if st.button("Add", key=f"quick_{row['Brand']}", type="secondary"):
                    if quick_master and quick_master != "-- Select Master Brand --":
                        add_brand_mapping(quick_master, row['Brand'])
                        st.success(f"Added {row['Brand']} to {quick_master}")
                        st.cache_data.clear()
                        st.rerun()

        if selected_brands:
            st.markdown(f"**Selected: {len(selected_brands)} brands**")
            if st.button(f"Add {len(selected_brands)} brands to {quick_master}", type="primary"):
                if quick_master and quick_master != "-- Select Master Brand --":
                    for brand in selected_brands:
                        add_brand_mapping(quick_master, brand)
                    st.success(f"Added {len(selected_brands)} brands to {quick_master}")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Please select a master brand first")

        # Show full list in expander
        with st.expander("View all unmapped brands"):
            st.dataframe(unmapped, width="stretch", hide_index=True, height=400)
    else:
        st.success("All brands with significant products are mapped!")


# Usage instructions
st.markdown("---")
st.markdown("""
### How Brand Hierarchy Works

**Master Brands** are parent companies or manufacturers (e.g., GTI, Verano, Cresco).

**Child Brands** are the product brands they own (e.g., Rythm, Dogwalkers under GTI).

Once mapped, you can:
- View aggregated data across all brands owned by a manufacturer
- Track total market share by parent company
- Understand true competitive landscape

**Common Master Brands:**
- **GTI (Green Thumb Industries)**: Rythm, Dogwalkers, &Shine, Incredibles, Beboe
- **Verano**: Verano, Verano Reserve, Savvy, Avexia
- **Cresco**: Cresco, High Supply, Good News, Mindy's
- **Trulieve**: Trulieve, Cultivar Collection
- **Cookies**: Cookies, Lemonnade, Grandiflora
""")
