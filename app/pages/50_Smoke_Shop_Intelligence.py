# app/pages/50_Smoke_Shop_Intelligence.py
"""Smoke Shop / Gray Market Intelligence Dashboard

Track CBD, Delta-8, THCA, and hemp-derived products across smoke shops.
Analyze market opportunity and competitive landscape.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import text
from core.db import get_engine

st.set_page_config(
    page_title="Smoke Shop Intelligence | CannLinx",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import and render navigation
from components.sidebar_nav import render_nav
render_nav()

st.title("Smoke Shop / Gray Market Intelligence")
st.markdown("Track CBD, Delta-8, THCA, kratom and hemp-derived products across smoke shops nationwide")

@st.cache_data(ttl=300)
def load_smoke_shop_overview():
    """Load smoke shop overview stats."""
    engine = get_engine()
    with engine.connect() as conn:
        # Overall counts by store type
        store_types = pd.read_sql(text("""
            SELECT store_type, COUNT(*) as count
            FROM dispensary
            WHERE is_active = true
            GROUP BY store_type
            ORDER BY count DESC
        """), conn)

        # Smoke shop counts
        smoke_shop_count = conn.execute(text("""
            SELECT COUNT(*) FROM dispensary
            WHERE is_active = true AND store_type = 'smoke_shop'
        """)).scalar() or 0

        # Smoke shops with product data
        shops_with_data = conn.execute(text("""
            SELECT COUNT(DISTINCT d.dispensary_id)
            FROM dispensary d
            JOIN raw_menu_item r ON d.dispensary_id = r.dispensary_id
            WHERE d.store_type = 'smoke_shop'
        """)).scalar() or 0

        # Total smoke shop products
        total_products = conn.execute(text("""
            SELECT COUNT(*)
            FROM raw_menu_item r
            JOIN dispensary d ON r.dispensary_id = d.dispensary_id
            WHERE d.store_type = 'smoke_shop'
        """)).scalar() or 0

        # Unique brands
        unique_brands = conn.execute(text("""
            SELECT COUNT(DISTINCT r.raw_brand)
            FROM raw_menu_item r
            JOIN dispensary d ON r.dispensary_id = d.dispensary_id
            WHERE d.store_type = 'smoke_shop'
            AND r.raw_brand IS NOT NULL AND r.raw_brand != ''
        """)).scalar() or 0

        stats = {
            "smoke_shops": smoke_shop_count,
            "with_data": shops_with_data,
            "products": total_products,
            "brands": unique_brands
        }

        return stats, store_types

@st.cache_data(ttl=300)
def load_smoke_shop_by_state():
    """Load smoke shop counts by state."""
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text("""
            SELECT
                d.state,
                COUNT(*) as total_shops,
                SUM(CASE WHEN d.menu_url IS NOT NULL AND d.menu_url != '' THEN 1 ELSE 0 END) as with_url,
                COUNT(DISTINCT CASE WHEN r.dispensary_id IS NOT NULL THEN d.dispensary_id END) as with_data,
                COUNT(r.raw_menu_item_id) as products
            FROM dispensary d
            LEFT JOIN raw_menu_item r ON d.dispensary_id = r.dispensary_id
            WHERE d.is_active = true AND d.store_type = 'smoke_shop'
            GROUP BY d.state
            ORDER BY total_shops DESC
        """), conn)
        return df

@st.cache_data(ttl=300)
def load_smoke_shop_products():
    """Load smoke shop product breakdown."""
    engine = get_engine()
    with engine.connect() as conn:
        # Products by category
        categories = pd.read_sql(text("""
            SELECT
                COALESCE(r.raw_category, 'Unknown') as category,
                COUNT(*) as products,
                COUNT(DISTINCT r.raw_brand) as brands,
                AVG(r.raw_price) as avg_price
            FROM raw_menu_item r
            JOIN dispensary d ON r.dispensary_id = d.dispensary_id
            WHERE d.store_type = 'smoke_shop'
            GROUP BY r.raw_category
            ORDER BY products DESC
            LIMIT 15
        """), conn)

        # Top brands
        brands = pd.read_sql(text("""
            SELECT
                r.raw_brand as brand,
                COUNT(*) as products,
                COUNT(DISTINCT d.dispensary_id) as stores,
                AVG(r.raw_price) as avg_price
            FROM raw_menu_item r
            JOIN dispensary d ON r.dispensary_id = d.dispensary_id
            WHERE d.store_type = 'smoke_shop'
            AND r.raw_brand IS NOT NULL AND r.raw_brand != ''
            GROUP BY r.raw_brand
            ORDER BY products DESC
            LIMIT 20
        """), conn)

        # Recent products
        recent = pd.read_sql(text("""
            SELECT
                d.name as store,
                d.state,
                r.raw_name as product,
                r.raw_category as category,
                r.raw_brand as brand,
                r.raw_price as price,
                r.observed_at
            FROM raw_menu_item r
            JOIN dispensary d ON r.dispensary_id = d.dispensary_id
            WHERE d.store_type = 'smoke_shop'
            ORDER BY r.observed_at DESC
            LIMIT 50
        """), conn)

        return categories, brands, recent

@st.cache_data(ttl=300)
def load_smoke_shop_chains():
    """Identify smoke shop chains by name patterns."""
    engine = get_engine()
    with engine.connect() as conn:
        # Common chain patterns
        chains = pd.read_sql(text("""
            SELECT
                CASE
                    WHEN LOWER(name) LIKE '%cbd american shaman%' THEN 'CBD American Shaman'
                    WHEN LOWER(name) LIKE '%cbd plus%' THEN 'CBD Plus USA'
                    WHEN LOWER(name) LIKE '%your cbd%' THEN 'Your CBD Store'
                    WHEN LOWER(name) LIKE '%cbd kratom%' THEN 'CBD Kratom'
                    WHEN LOWER(name) LIKE '%holistic connection%' THEN 'The Holistic Connection'
                    WHEN LOWER(name) LIKE '%sacred leaf%' THEN 'Sacred Leaf'
                    WHEN LOWER(name) LIKE '%cbd store%' THEN 'Generic CBD Store'
                    WHEN LOWER(name) LIKE '%hemp house%' THEN 'Hemp House'
                    WHEN LOWER(name) LIKE '%hemp world%' THEN 'Hemp World'
                    ELSE 'Independent'
                END as chain,
                COUNT(*) as locations,
                COUNT(DISTINCT state) as states
            FROM dispensary
            WHERE is_active = true AND store_type = 'smoke_shop'
            GROUP BY chain
            ORDER BY locations DESC
        """), conn)
        return chains

@st.cache_data(ttl=300)
def load_market_comparison():
    """Compare licensed vs smoke shop markets."""
    engine = get_engine()
    with engine.connect() as conn:
        comparison = pd.read_sql(text("""
            SELECT
                d.state,
                SUM(CASE WHEN d.store_type = 'dispensary' THEN 1 ELSE 0 END) as licensed_dispensaries,
                SUM(CASE WHEN d.store_type = 'smoke_shop' THEN 1 ELSE 0 END) as smoke_shops,
                SUM(CASE WHEN d.store_type = 'unverified' THEN 1 ELSE 0 END) as unverified
            FROM dispensary d
            WHERE d.is_active = true
            GROUP BY d.state
            HAVING SUM(CASE WHEN d.store_type = 'smoke_shop' THEN 1 ELSE 0 END) > 0
            ORDER BY smoke_shops DESC
            LIMIT 20
        """), conn)
        return comparison

# Load data
try:
    stats, store_types = load_smoke_shop_overview()

    # Key metrics row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Smoke Shops Tracked", f"{stats['smoke_shops']:,}")
    c2.metric("With Product Data", f"{stats['with_data']:,}")
    c3.metric("Products Collected", f"{stats['products']:,}")
    c4.metric("Brands Identified", f"{stats['brands']:,}")

    st.divider()

    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["Geographic View", "Product Analysis", "Brand Intelligence", "Market Opportunity"])

    with tab1:
        st.subheader("Smoke Shops by State")

        state_data = load_smoke_shop_by_state()

        if not state_data.empty:
            col1, col2 = st.columns([2, 1])

            with col1:
                # Map visualization
                fig = px.choropleth(
                    state_data,
                    locations='state',
                    locationmode='USA-states',
                    color='total_shops',
                    scope='usa',
                    color_continuous_scale='Oranges',
                    labels={'total_shops': 'Smoke Shops'},
                    title='Smoke Shop Density by State'
                )
                fig.update_layout(margin=dict(t=50, b=20, l=20, r=20), height=400)
                st.plotly_chart(fig, width="stretch")

            with col2:
                st.markdown("**Top States by Smoke Shop Count**")
                top_states = state_data.head(10)
                for _, row in top_states.iterrows():
                    pct_with_url = (row['with_url'] / row['total_shops'] * 100) if row['total_shops'] > 0 else 0
                    st.markdown(f"""
                    <div style="background:#fff3e0; border-radius:6px; padding:10px; margin-bottom:8px; border-left:4px solid #ff9800;">
                        <div style="font-weight:600; font-size:1.1rem;">{row['state']}: {row['total_shops']:,}</div>
                        <div style="font-size:0.8rem; color:#666;">
                            {row['with_url']:,} with URLs ({pct_with_url:.0f}%) | {row['with_data']} with data
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            # Full state table
            st.markdown("---")
            st.markdown("**All States with Smoke Shops**")
            st.dataframe(
                state_data.style.format({
                    'total_shops': '{:,}',
                    'with_url': '{:,}',
                    'with_data': '{:,}',
                    'products': '{:,}'
                }),
                width="stretch",
                height=400
            )
        else:
            st.info("No smoke shop data available")

    with tab2:
        st.subheader("Product Category Analysis")

        categories, brands, recent = load_smoke_shop_products()

        if not categories.empty:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Products by Category**")
                fig = px.bar(
                    categories.head(10),
                    x='products',
                    y='category',
                    orientation='h',
                    color='products',
                    color_continuous_scale='Oranges'
                )
                fig.update_layout(
                    margin=dict(t=20, b=20, l=20, r=20),
                    height=350,
                    yaxis={'categoryorder': 'total ascending'},
                    showlegend=False,
                    coloraxis_showscale=False
                )
                st.plotly_chart(fig, width="stretch")

            with col2:
                st.markdown("**Category Breakdown**")
                # Show category details
                for _, row in categories.head(8).iterrows():
                    cat_name = row['category'] if row['category'] else 'Unknown'
                    avg_price = f"${row['avg_price']:.2f}" if row['avg_price'] else "N/A"
                    st.markdown(f"""
                    <div style="background:#f5f5f5; border-radius:6px; padding:10px; margin-bottom:8px;">
                        <div style="font-weight:600;">{cat_name}</div>
                        <div style="font-size:0.85rem; color:#666;">
                            {row['products']:,} products | {row['brands']} brands | Avg: {avg_price}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            # Product category distribution pie chart
            st.markdown("---")
            st.markdown("**Category Distribution**")
            fig = px.pie(
                categories.head(8),
                values='products',
                names='category',
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=300)
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No product data available yet. Run the smoke shop scraper to collect product data.")

        # Recent products
        if not recent.empty:
            st.markdown("---")
            st.subheader("Recently Collected Products")
            st.dataframe(
                recent[['store', 'state', 'product', 'category', 'brand', 'price']].head(20),
                width="stretch",
                height=400
            )

    with tab3:
        st.subheader("Brand Intelligence")

        categories, brands, recent = load_smoke_shop_products()
        chains = load_smoke_shop_chains()

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Smoke Shop Chains**")
            if not chains.empty:
                # Filter out 'Independent' for the chart
                chain_data = chains[chains['chain'] != 'Independent']
                if not chain_data.empty:
                    fig = px.bar(
                        chain_data.head(10),
                        x='locations',
                        y='chain',
                        orientation='h',
                        color='states',
                        color_continuous_scale='Blues',
                        labels={'locations': 'Locations', 'states': 'States'}
                    )
                    fig.update_layout(
                        margin=dict(t=20, b=20, l=20, r=20),
                        height=350,
                        yaxis={'categoryorder': 'total ascending'},
                        coloraxis_showscale=True
                    )
                    st.plotly_chart(fig, width="stretch")

                # Show independent count
                indep = chains[chains['chain'] == 'Independent']
                if not indep.empty:
                    st.info(f"Plus **{indep.iloc[0]['locations']:,}** independent smoke shops")
            else:
                st.info("No chain data available")

        with col2:
            st.markdown("**Top Product Brands**")
            if not brands.empty:
                for _, row in brands.head(10).iterrows():
                    brand_name = row['brand'] if row['brand'] else 'Unknown'
                    avg_price = f"${row['avg_price']:.2f}" if row['avg_price'] else "N/A"
                    st.markdown(f"""
                    <div style="background:#e3f2fd; border-radius:6px; padding:10px; margin-bottom:8px;">
                        <div style="font-weight:600;">{brand_name[:30]}</div>
                        <div style="font-size:0.85rem; color:#666;">
                            {row['products']:,} products | {row['stores']} stores | Avg: {avg_price}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No brand data available yet")

        # Chain details table
        if not chains.empty:
            st.markdown("---")
            st.markdown("**All Identified Chains**")
            st.dataframe(
                chains.style.format({'locations': '{:,}', 'states': '{:,}'}),
                width="stretch",
                height=300
            )

    with tab4:
        st.subheader("Market Opportunity Analysis")
        st.markdown("Compare licensed dispensary market vs. smoke shop gray market")

        comparison = load_market_comparison()

        if not comparison.empty:
            # Calculate ratios
            comparison['smoke_shop_ratio'] = comparison['smoke_shops'] / (comparison['licensed_dispensaries'] + 1)
            comparison['total_stores'] = comparison['licensed_dispensaries'] + comparison['smoke_shops']

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Licensed vs Gray Market by State**")
                fig = px.bar(
                    comparison.head(15),
                    x='state',
                    y=['licensed_dispensaries', 'smoke_shops'],
                    barmode='group',
                    color_discrete_map={
                        'licensed_dispensaries': '#4caf50',
                        'smoke_shops': '#ff9800'
                    },
                    labels={
                        'value': 'Store Count',
                        'variable': 'Store Type',
                        'licensed_dispensaries': 'Licensed',
                        'smoke_shops': 'Smoke Shops'
                    }
                )
                fig.update_layout(
                    margin=dict(t=20, b=60, l=20, r=20),
                    height=400,
                    xaxis_tickangle=-45,
                    legend=dict(orientation="h", y=1.1)
                )
                st.plotly_chart(fig, width="stretch")

            with col2:
                st.markdown("**States with Highest Gray Market Presence**")
                # States where smoke shops outnumber or rival dispensaries
                high_gray = comparison.nlargest(10, 'smoke_shop_ratio')
                for _, row in high_gray.iterrows():
                    ratio = row['smoke_shop_ratio']
                    if ratio > 1:
                        indicator = "More smoke shops than dispensaries"
                        color = "#ff5722"
                    elif ratio > 0.5:
                        indicator = "Significant gray market"
                        color = "#ff9800"
                    else:
                        indicator = "Licensed market dominant"
                        color = "#4caf50"

                    st.markdown(f"""
                    <div style="background:#f5f5f5; border-radius:6px; padding:10px; margin-bottom:8px; border-left:4px solid {color};">
                        <div style="font-weight:600;">{row['state']}</div>
                        <div style="font-size:0.85rem;">
                            Licensed: {row['licensed_dispensaries']:,} | Smoke Shops: {row['smoke_shops']:,}
                        </div>
                        <div style="font-size:0.75rem; color:{color};">{indicator}</div>
                    </div>
                    """, unsafe_allow_html=True)

            # Opportunity insights
            st.markdown("---")
            st.subheader("Market Insights")

            # States with no/few dispensaries but many smoke shops
            high_opportunity = comparison[
                (comparison['smoke_shops'] > 20) &
                (comparison['licensed_dispensaries'] < 50)
            ].sort_values('smoke_shops', ascending=False)

            if not high_opportunity.empty:
                st.markdown("**High Opportunity States** (Many smoke shops, few licensed dispensaries)")
                st.markdown("These states have significant consumer demand (evidenced by smoke shop presence) but limited licensed retail:")

                cols = st.columns(min(4, len(high_opportunity)))
                for i, (_, row) in enumerate(high_opportunity.head(4).iterrows()):
                    with cols[i]:
                        st.metric(
                            row['state'],
                            f"{row['smoke_shops']} smoke shops",
                            f"{row['licensed_dispensaries']} licensed"
                        )

            # Full comparison table
            st.markdown("---")
            st.markdown("**Full Market Comparison**")
            display_df = comparison[['state', 'licensed_dispensaries', 'smoke_shops', 'unverified']].copy()
            display_df.columns = ['State', 'Licensed Dispensaries', 'Smoke Shops', 'Unverified']
            st.dataframe(
                display_df.style.format({
                    'Licensed Dispensaries': '{:,}',
                    'Smoke Shops': '{:,}',
                    'Unverified': '{:,}'
                }),
                width="stretch",
                height=400
            )
        else:
            st.info("No comparison data available")

except Exception as e:
    st.error(f"Error loading dashboard: {e}")
    import traceback
    st.code(traceback.format_exc())

st.divider()
st.caption("Smoke Shop Intelligence | Gray market tracking for CBD, Delta-8, THCA, and hemp products")
