# app/pages/6_Price_Analysis.py
"""Price Analysis - Find deals, compare prices by category/size."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import text
from core.db import get_engine
from core.category_utils import get_normalized_category_sql

st.set_page_config(page_title="Price Analysis | CannLinx", page_icon=None, layout="wide", initial_sidebar_state="collapsed")

# Import and render navigation
from components.nav import render_nav, get_section_from_params
render_nav()

# Handle section parameter for tab navigation
section = get_section_from_params()
TAB_MAP = {"category": 0, "vapes": 1, "deals": 2, "search": 3}
if section and section in TAB_MAP:
    tab_index = TAB_MAP[section]
    st.markdown(f"""
    <script>
        setTimeout(function() {{
            const tabs = document.querySelectorAll('[data-baseweb="tab"]');
            if (tabs && tabs[{tab_index}]) {{ tabs[{tab_index}].click(); }}
        }}, 100);
    </script>
    """, unsafe_allow_html=True)

st.title("Price Analysis")

engine = get_engine()

@st.cache_data(ttl=300)
def get_states():
    with engine.connect() as conn:
        df = pd.read_sql(text("""
            SELECT DISTINCT COALESCE(state, 'Unknown') as state
            FROM dispensary
            WHERE state IS NOT NULL
            ORDER BY state
        """), conn)
    return ['All States'] + df['state'].tolist()

# Inline filters
states = get_states()
filter_col1, filter_col2 = st.columns([2, 2])
with filter_col1:
    selected_state = st.selectbox("State", states, index=0)
with filter_col2:
    min_price_filter = st.slider("Min Price (exclude promos)", 1, 20, 5)

def get_subcategory_sql():
    """SQL CASE statement to determine subcategory based on product name and category."""
    return """
        CASE
            -- Flower by size
            WHEN (raw_category ILIKE '%flower%' OR raw_category ILIKE '%bud%')
                 AND (raw_name ILIKE '%28g%' OR raw_name ILIKE '%28 g%' OR raw_name ILIKE '%1oz%' OR raw_name ILIKE '%1 oz%' OR raw_name ILIKE '%ounce%')
                THEN 'Flower 28g'
            WHEN (raw_category ILIKE '%flower%' OR raw_category ILIKE '%bud%')
                 AND (raw_name ILIKE '%14g%' OR raw_name ILIKE '%14 g%' OR raw_name ILIKE '%half oz%' OR raw_name ILIKE '%1/2 oz%' OR raw_name ILIKE '%half ounce%')
                THEN 'Flower 14g'
            WHEN (raw_category ILIKE '%flower%' OR raw_category ILIKE '%bud%')
                 AND (raw_name ILIKE '%7g%' OR raw_name ILIKE '%7 g%' OR raw_name ILIKE '%quarter%' OR raw_name ILIKE '%1/4%')
                THEN 'Flower 7g'
            WHEN (raw_category ILIKE '%flower%' OR raw_category ILIKE '%bud%')
                 AND (raw_name ILIKE '%3.5g%' OR raw_name ILIKE '%3.5 g%' OR raw_name ILIKE '%eighth%' OR raw_name ILIKE '%1/8%')
                THEN 'Flower 3.5g'
            WHEN (raw_category ILIKE '%flower%' OR raw_category ILIKE '%bud%')
                 AND (raw_name ILIKE '%1g%' OR raw_name ILIKE '%1 g%' OR raw_name ILIKE '% gram%')
                THEN 'Flower 1g'
            WHEN raw_category ILIKE '%flower%' OR raw_category ILIKE '%bud%'
                THEN 'Flower (Other)'

            -- Pre-rolls: infused by pack size
            WHEN (raw_category ILIKE '%pre-roll%' OR raw_category ILIKE '%preroll%' OR raw_category ILIKE '%pre roll%' OR raw_category ILIKE '%joint%')
                 AND (raw_name ILIKE '%infuse%' OR raw_name ILIKE '%diamond%' OR raw_name ILIKE '%caviar%' OR raw_name ILIKE '%moon rock%' OR raw_name ILIKE '%kief%' OR raw_name ILIKE '%hash%' OR raw_name ILIKE '%rosin%' OR raw_name ILIKE '%live%')
                 AND (raw_name ~* '(10|ten)[\s-]*(pk|pack|ct|count)' OR raw_name ILIKE '%10pk%' OR raw_name ILIKE '%10-pack%')
                THEN 'Pre-Roll Infused 10pk'
            WHEN (raw_category ILIKE '%pre-roll%' OR raw_category ILIKE '%preroll%' OR raw_category ILIKE '%pre roll%' OR raw_category ILIKE '%joint%')
                 AND (raw_name ILIKE '%infuse%' OR raw_name ILIKE '%diamond%' OR raw_name ILIKE '%caviar%' OR raw_name ILIKE '%moon rock%' OR raw_name ILIKE '%kief%' OR raw_name ILIKE '%hash%' OR raw_name ILIKE '%rosin%' OR raw_name ILIKE '%live%')
                 AND (raw_name ~* '(7|seven)[\s-]*(pk|pack|ct|count)' OR raw_name ILIKE '%7pk%' OR raw_name ILIKE '%7-pack%')
                THEN 'Pre-Roll Infused 7pk'
            WHEN (raw_category ILIKE '%pre-roll%' OR raw_category ILIKE '%preroll%' OR raw_category ILIKE '%pre roll%' OR raw_category ILIKE '%joint%')
                 AND (raw_name ILIKE '%infuse%' OR raw_name ILIKE '%diamond%' OR raw_name ILIKE '%caviar%' OR raw_name ILIKE '%moon rock%' OR raw_name ILIKE '%kief%' OR raw_name ILIKE '%hash%' OR raw_name ILIKE '%rosin%' OR raw_name ILIKE '%live%')
                 AND (raw_name ~* '(5|five)[\s-]*(pk|pack|ct|count)' OR raw_name ILIKE '%5pk%' OR raw_name ILIKE '%5-pack%')
                THEN 'Pre-Roll Infused 5pk'
            WHEN (raw_category ILIKE '%pre-roll%' OR raw_category ILIKE '%preroll%' OR raw_category ILIKE '%pre roll%' OR raw_category ILIKE '%joint%')
                 AND (raw_name ILIKE '%infuse%' OR raw_name ILIKE '%diamond%' OR raw_name ILIKE '%caviar%' OR raw_name ILIKE '%moon rock%' OR raw_name ILIKE '%kief%' OR raw_name ILIKE '%hash%' OR raw_name ILIKE '%rosin%' OR raw_name ILIKE '%live%')
                 AND (raw_name ~* '(3|three)[\s-]*(pk|pack|ct|count)' OR raw_name ILIKE '%3pk%' OR raw_name ILIKE '%3-pack%')
                THEN 'Pre-Roll Infused 3pk'
            WHEN (raw_category ILIKE '%pre-roll%' OR raw_category ILIKE '%preroll%' OR raw_category ILIKE '%pre roll%' OR raw_category ILIKE '%joint%')
                 AND (raw_name ILIKE '%infuse%' OR raw_name ILIKE '%diamond%' OR raw_name ILIKE '%caviar%' OR raw_name ILIKE '%moon rock%' OR raw_name ILIKE '%kief%' OR raw_name ILIKE '%hash%' OR raw_name ILIKE '%rosin%' OR raw_name ILIKE '%live%')
                 AND (raw_name ~* '(2|two)[\s-]*(pk|pack|ct|count)' OR raw_name ILIKE '%2pk%' OR raw_name ILIKE '%2-pack%')
                THEN 'Pre-Roll Infused 2pk'
            WHEN (raw_category ILIKE '%pre-roll%' OR raw_category ILIKE '%preroll%' OR raw_category ILIKE '%pre roll%' OR raw_category ILIKE '%joint%')
                 AND (raw_name ILIKE '%infuse%' OR raw_name ILIKE '%diamond%' OR raw_name ILIKE '%caviar%' OR raw_name ILIKE '%moon rock%' OR raw_name ILIKE '%kief%' OR raw_name ILIKE '%hash%' OR raw_name ILIKE '%rosin%' OR raw_name ILIKE '%live%')
                THEN 'Pre-Roll Infused Single'

            -- Pre-rolls: regular by pack size
            WHEN (raw_category ILIKE '%pre-roll%' OR raw_category ILIKE '%preroll%' OR raw_category ILIKE '%pre roll%' OR raw_category ILIKE '%joint%')
                 AND (raw_name ~* '(10|ten)[\s-]*(pk|pack|ct|count)' OR raw_name ILIKE '%10pk%' OR raw_name ILIKE '%10-pack%')
                THEN 'Pre-Roll 10pk'
            WHEN (raw_category ILIKE '%pre-roll%' OR raw_category ILIKE '%preroll%' OR raw_category ILIKE '%pre roll%' OR raw_category ILIKE '%joint%')
                 AND (raw_name ~* '(7|seven)[\s-]*(pk|pack|ct|count)' OR raw_name ILIKE '%7pk%' OR raw_name ILIKE '%7-pack%')
                THEN 'Pre-Roll 7pk'
            WHEN (raw_category ILIKE '%pre-roll%' OR raw_category ILIKE '%preroll%' OR raw_category ILIKE '%pre roll%' OR raw_category ILIKE '%joint%')
                 AND (raw_name ~* '(5|five)[\s-]*(pk|pack|ct|count)' OR raw_name ILIKE '%5pk%' OR raw_name ILIKE '%5-pack%')
                THEN 'Pre-Roll 5pk'
            WHEN (raw_category ILIKE '%pre-roll%' OR raw_category ILIKE '%preroll%' OR raw_category ILIKE '%pre roll%' OR raw_category ILIKE '%joint%')
                 AND (raw_name ~* '(3|three)[\s-]*(pk|pack|ct|count)' OR raw_name ILIKE '%3pk%' OR raw_name ILIKE '%3-pack%')
                THEN 'Pre-Roll 3pk'
            WHEN (raw_category ILIKE '%pre-roll%' OR raw_category ILIKE '%preroll%' OR raw_category ILIKE '%pre roll%' OR raw_category ILIKE '%joint%')
                 AND (raw_name ~* '(2|two)[\s-]*(pk|pack|ct|count)' OR raw_name ILIKE '%2pk%' OR raw_name ILIKE '%2-pack%')
                THEN 'Pre-Roll 2pk'
            WHEN raw_category ILIKE '%pre-roll%' OR raw_category ILIKE '%preroll%' OR raw_category ILIKE '%pre roll%' OR raw_category ILIKE '%joint%'
                THEN 'Pre-Roll Single'

            -- Vapes: cartridge vs disposable
            WHEN (raw_category ILIKE '%vape%' OR raw_category ILIKE '%cart%')
                 AND (raw_name ILIKE '%disposable%' OR raw_name ILIKE '%dispo%' OR raw_name ILIKE '%all-in-one%' OR raw_name ILIKE '%all in one%' OR raw_name ILIKE '%AIO%' OR raw_name ILIKE '%pen%')
                THEN 'Vapes (Disposable)'
            WHEN raw_category ILIKE '%vape%' OR raw_category ILIKE '%cart%'
                THEN 'Vapes (Cartridge)'

            -- Concentrates
            WHEN raw_category ILIKE '%concentrate%' OR raw_category ILIKE '%extract%' OR raw_category ILIKE '%dab%' OR raw_category ILIKE '%wax%' OR raw_category ILIKE '%shatter%' OR raw_category ILIKE '%rosin%' OR raw_category ILIKE '%resin%'
                THEN 'Concentrates'

            -- Edibles
            WHEN raw_category ILIKE '%edible%' OR raw_category ILIKE '%gumm%' OR raw_category ILIKE '%chocolate%' OR raw_category ILIKE '%candy%' OR raw_category ILIKE '%beverage%' OR raw_category ILIKE '%drink%'
                THEN 'Edibles'

            -- Topicals
            WHEN raw_category ILIKE '%topical%' OR raw_category ILIKE '%cream%' OR raw_category ILIKE '%balm%' OR raw_category ILIKE '%lotion%' OR raw_category ILIKE '%salve%'
                THEN 'Topicals'

            -- Tinctures
            WHEN raw_category ILIKE '%tincture%' OR raw_category ILIKE '%oil%' OR raw_category ILIKE '%sublingual%' OR raw_category ILIKE '%rso%'
                THEN 'Tinctures'

            -- Accessories
            WHEN raw_category ILIKE '%accessor%' OR raw_category ILIKE '%gear%' OR raw_category ILIKE '%pipe%' OR raw_category ILIKE '%paper%' OR raw_category ILIKE '%grinder%'
                THEN 'Accessories'

            ELSE 'Other'
        END
    """


@st.cache_data(ttl=600)
def get_price_stats_by_category(state, min_price):
    cat_sql = get_normalized_category_sql()
    with engine.connect() as conn:
        if state == 'All States':
            return pd.read_sql(text(f"""
                SELECT {cat_sql} as category,
                       COUNT(*) as products,
                       ROUND(AVG(raw_price)::numeric, 2) as avg_price,
                       ROUND(MIN(raw_price)::numeric, 2) as min_price,
                       ROUND(MAX(raw_price)::numeric, 2) as max_price
                FROM raw_menu_item
                WHERE raw_price >= :min_price AND raw_price < 1000
                AND observed_at > NOW() - INTERVAL '24 hours'
                GROUP BY {cat_sql}
                HAVING COUNT(*) > 50
                ORDER BY avg_price DESC
            """), conn, params={"min_price": min_price})
        else:
            return pd.read_sql(text(f"""
                SELECT {cat_sql} as category,
                       COUNT(*) as products,
                       ROUND(AVG(r.raw_price)::numeric, 2) as avg_price,
                       ROUND(MIN(r.raw_price)::numeric, 2) as min_price,
                       ROUND(MAX(r.raw_price)::numeric, 2) as max_price
                FROM raw_menu_item r
                JOIN dispensary d ON d.dispensary_id = r.dispensary_id
                WHERE r.raw_price >= :min_price AND r.raw_price < 1000
                AND r.observed_at > NOW() - INTERVAL '24 hours'
                AND d.state = :state
                GROUP BY {cat_sql}
                HAVING COUNT(*) > 10
                ORDER BY avg_price DESC
            """), conn, params={"min_price": min_price, "state": state})


@st.cache_data(ttl=600)
def get_price_stats_by_subcategory(state, min_price):
    """Get price stats broken down by subcategory (flower sizes, infused prerolls, vape types)."""
    subcat_sql = get_subcategory_sql()
    with engine.connect() as conn:
        state_filter = "AND d.state = :state" if state != 'All States' else ""
        join_clause = "JOIN dispensary d ON d.dispensary_id = r.dispensary_id" if state != 'All States' else ""
        params = {"min_price": min_price}
        if state != 'All States':
            params["state"] = state

        return pd.read_sql(text(f"""
            SELECT {subcat_sql} as subcategory,
                   COUNT(*) as products,
                   ROUND(AVG(r.raw_price)::numeric, 2) as avg_price,
                   ROUND(MIN(r.raw_price)::numeric, 2) as min_price,
                   ROUND(MAX(r.raw_price)::numeric, 2) as max_price
            FROM raw_menu_item r
            {join_clause}
            WHERE r.raw_price >= :min_price AND r.raw_price < 1000
            AND r.observed_at > NOW() - INTERVAL '24 hours'
            {state_filter}
            GROUP BY {subcat_sql}
            HAVING COUNT(*) > 10
            ORDER BY
                CASE
                    WHEN {subcat_sql} LIKE 'Flower%' THEN 1
                    WHEN {subcat_sql} LIKE 'Pre-Roll%' THEN 2
                    WHEN {subcat_sql} LIKE 'Vape%' THEN 3
                    ELSE 4
                END,
                avg_price DESC
        """), conn, params=params)

@st.cache_data(ttl=600)
def get_cheapest_by_category(category, state, min_price, limit=20):
    cat_sql = get_normalized_category_sql()
    with engine.connect() as conn:
        if state == 'All States':
            return pd.read_sql(text(f"""
                SELECT r.raw_name as product, r.raw_brand as brand,
                       r.raw_price as price, d.name as store, d.state
                FROM raw_menu_item r
                JOIN dispensary d ON d.dispensary_id = r.dispensary_id
                WHERE ({cat_sql}) = :cat
                AND r.raw_price >= :min_price
                AND r.observed_at > NOW() - INTERVAL '24 hours'
                ORDER BY r.raw_price ASC
                LIMIT :lim
            """), conn, params={"cat": category, "min_price": min_price, "lim": limit})
        else:
            return pd.read_sql(text(f"""
                SELECT r.raw_name as product, r.raw_brand as brand,
                       r.raw_price as price, d.name as store, d.state
                FROM raw_menu_item r
                JOIN dispensary d ON d.dispensary_id = r.dispensary_id
                WHERE ({cat_sql}) = :cat
                AND r.raw_price >= :min_price
                AND r.observed_at > NOW() - INTERVAL '24 hours'
                AND d.state = :state
                ORDER BY r.raw_price ASC
                LIMIT :lim
            """), conn, params={"cat": category, "min_price": min_price, "state": state, "lim": limit})

@st.cache_data(ttl=600)
def get_vape_price_analysis(state, min_price):
    with engine.connect() as conn:
        state_filter = "AND d.state = :state" if state != 'All States' else ""
        return pd.read_sql(text(f"""
            SELECT r.raw_name as product, r.raw_brand as brand,
                   r.raw_price as price, d.name as store, d.state,
                   CASE 
                       WHEN r.raw_name ILIKE '%2g%' OR r.raw_name ILIKE '%2000%' THEN '2000mg'
                       WHEN r.raw_name ILIKE '%1g%' OR r.raw_name ILIKE '%1000%' THEN '1000mg'
                       WHEN r.raw_name ILIKE '%.5g%' OR r.raw_name ILIKE '%500%' OR r.raw_name ILIKE '%half%' THEN '500mg'
                       WHEN r.raw_name ILIKE '%300%' THEN '300mg'
                       ELSE 'Other'
                   END as size
            FROM raw_menu_item r
            JOIN dispensary d ON d.dispensary_id = r.dispensary_id
            WHERE (r.raw_category ILIKE '%vape%' OR r.raw_category ILIKE '%cart%')
            AND r.raw_price >= :min_price AND r.raw_price < 200
            AND r.observed_at > NOW() - INTERVAL '24 hours'
            {state_filter}
            ORDER BY r.raw_price ASC
            LIMIT 500
        """), conn, params={"min_price": min_price, "state": state} if state != 'All States' else {"min_price": min_price})

@st.cache_data(ttl=600)
def get_deals(state, min_price):
    cat_sql = get_normalized_category_sql()
    with engine.connect() as conn:
        state_filter = "AND d.state = :state" if state != 'All States' else ""
        params = {"min_price": min_price}
        if state != 'All States':
            params["state"] = state
        return pd.read_sql(text(f"""
            SELECT r.raw_name as product, r.raw_brand as brand, {cat_sql} as category,
                   r.raw_price as original_price, r.raw_discount_price as sale_price,
                   ROUND((r.raw_price - r.raw_discount_price)::numeric, 2) as savings,
                   ROUND(((r.raw_price - r.raw_discount_price) / r.raw_price * 100)::numeric, 0) as pct_off,
                   d.name as store, d.state
            FROM raw_menu_item r
            JOIN dispensary d ON d.dispensary_id = r.dispensary_id
            WHERE r.raw_discount_price IS NOT NULL
            AND r.raw_discount_price >= :min_price
            AND r.raw_discount_price < r.raw_price
            AND r.observed_at > NOW() - INTERVAL '24 hours'
            {state_filter}
            ORDER BY (r.raw_price - r.raw_discount_price) DESC
            LIMIT 50
        """), conn, params=params)

tab1, tab2, tab3, tab4 = st.tabs(["📊 Category Prices", "💨 Vape Analysis", "🏷️ Best Deals", "🔍 Price Search"])

with tab1:
    st.header("Average Prices by Category")

    # Toggle between main categories and subcategories
    view_mode = st.radio("View", ["Subcategories (Detailed)", "Main Categories"], horizontal=True)

    try:
        if view_mode == "Subcategories (Detailed)":
            subcat_df = get_price_stats_by_subcategory(selected_state, min_price_filter)
            if not subcat_df.empty:
                col1, col2 = st.columns([3, 2])
                with col1:
                    # Color by category type
                    def get_color(subcat):
                        if 'Flower' in subcat:
                            return '#2E7D32'  # Green for flower
                        elif 'Pre-Roll' in subcat:
                            return '#F57C00'  # Orange for pre-rolls
                        elif 'Vape' in subcat:
                            return '#1976D2'  # Blue for vapes
                        elif subcat == 'Concentrates':
                            return '#7B1FA2'  # Purple
                        elif subcat == 'Edibles':
                            return '#C2185B'  # Pink
                        else:
                            return '#757575'  # Grey

                    subcat_df['color'] = subcat_df['subcategory'].apply(get_color)

                    fig = px.bar(subcat_df, x='subcategory', y='avg_price',
                                title='Average Price by Subcategory',
                                labels={'avg_price': 'Avg Price ($)', 'subcategory': 'Subcategory'},
                                color='subcategory',
                                color_discrete_sequence=subcat_df['color'].tolist())
                    fig.update_layout(xaxis_tickangle=-45, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    display_df = subcat_df[['subcategory', 'products', 'avg_price', 'min_price', 'max_price']].copy()
                    display_df.columns = ['Subcategory', 'Products', 'Avg Price', 'Min', 'Max']
                    st.dataframe(display_df, use_container_width=True, hide_index=True, height=450)

                # Show breakdown explanation
                st.caption("""
                **Subcategory Breakdown:**
                - **Flower**: Split by size (1g, 3.5g, 7g, 14g, 28g)
                - **Pre-Rolls**: Regular vs Infused, then by pack size (Single, 2pk, 3pk, 5pk, 7pk, 10pk)
                - **Vapes**: Cartridges vs Disposables (all-in-one, pen)
                """)
            else:
                st.warning("No subcategory data found for selected filters")
        else:
            price_df = get_price_stats_by_category(selected_state, min_price_filter)
            if not price_df.empty:
                col1, col2 = st.columns(2)
                with col1:
                    fig = px.bar(price_df.head(15), x='category', y='avg_price',
                                title='Average Price by Category',
                                labels={'avg_price': 'Avg Price ($)'})
                    fig.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    st.dataframe(price_df, use_container_width=True, height=400)
            else:
                st.warning("No price data found for selected filters")

        # Cheapest in category (always show)
        st.subheader("Find Cheapest Products")
        price_df = get_price_stats_by_category(selected_state, min_price_filter)
        if not price_df.empty:
            selected_cat = st.selectbox("Select Category", price_df['category'].tolist())
            if selected_cat:
                cheapest = get_cheapest_by_category(selected_cat, selected_state, min_price_filter)
                st.dataframe(cheapest, use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")

with tab2:
    st.header("💨 Vape/Cartridge Price Analysis")
    try:
        vape_df = get_vape_price_analysis(selected_state, min_price_filter)
        if not vape_df.empty:
            # Group by size
            size_stats = vape_df.groupby('size').agg({
                'price': ['count', 'mean', 'min', 'max']
            }).round(2)
            size_stats.columns = ['count', 'avg_price', 'min_price', 'max_price']
            size_stats = size_stats.reset_index().sort_values('avg_price')
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Price by Size")
                fig = px.bar(size_stats, x='size', y='avg_price', title='Avg Vape Price by Size')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.dataframe(size_stats, use_container_width=True)
            
            # Cheapest vapes
            st.subheader("Cheapest Vapes")
            size_filter = st.selectbox("Filter by Size", ['All'] + size_stats['size'].tolist())
            if size_filter == 'All':
                display_df = vape_df.head(30)
            else:
                display_df = vape_df[vape_df['size'] == size_filter].head(30)
            
            st.dataframe(display_df, use_container_width=True)
        else:
            st.warning("No vape data found for selected filters")
    except Exception as e:
        st.error(f"Error: {e}")

with tab3:
    st.header("🏷️ Best Deals (On Sale)")
    try:
        deals_df = get_deals(selected_state, min_price_filter)
        if not deals_df.empty:
            st.metric("Products on Sale", len(deals_df))
            
            # Format prices
            deals_df['original_price'] = deals_df['original_price'].apply(lambda x: f"${x:.2f}")
            deals_df['sale_price'] = deals_df['sale_price'].apply(lambda x: f"${x:.2f}")
            deals_df['savings'] = deals_df['savings'].apply(lambda x: f"${x:.2f}")
            deals_df['pct_off'] = deals_df['pct_off'].apply(lambda x: f"{x:.0f}%")
            
            st.dataframe(deals_df, use_container_width=True, height=500)
        else:
            st.info("No sale items found for selected filters")
    except Exception as e:
        st.error(f"Error: {e}")

with tab4:
    st.header("🔍 Custom Price Search")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        search_term = st.text_input("Product name contains", "")
    with col2:
        min_price = st.number_input("Min Price", 0, 500, min_price_filter)
    with col3:
        max_price = st.number_input("Max Price", 0, 500, 100)
    
    if st.button("Search") and search_term:
        try:
            cat_sql = get_normalized_category_sql()
            with engine.connect() as conn:
                state_filter = "AND d.state = :state" if selected_state != 'All States' else ""
                params = {"search": f"%{search_term}%", "min": min_price, "max": max_price}
                if selected_state != 'All States':
                    params["state"] = selected_state

                results = pd.read_sql(text(f"""
                    SELECT r.raw_name as product, r.raw_brand as brand, {cat_sql} as category,
                           r.raw_price as price, d.name as store, d.state
                    FROM raw_menu_item r
                    JOIN dispensary d ON d.dispensary_id = r.dispensary_id
                    WHERE r.raw_name ILIKE :search
                    AND r.raw_price BETWEEN :min AND :max
                    AND r.observed_at > NOW() - INTERVAL '24 hours'
                    {state_filter}
                    ORDER BY r.raw_price ASC
                    LIMIT 100
                """), conn, params=params)
            
            if not results.empty:
                st.success(f"Found {len(results)} products")
                st.dataframe(results, use_container_width=True)
            else:
                st.warning("No products found")
        except Exception as e:
            st.error(f"Error: {e}")

st.divider()
st.caption("Prices from last 24 hours of scrapes")
