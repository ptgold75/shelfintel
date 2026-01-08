"""Investor Intelligence - Public Cannabis Company Tracking."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import sys
sys.path.insert(0, '/Users/gleaf/shelfintel')

from core.db import get_engine
from sqlalchemy import text

st.set_page_config(page_title="Investor Intelligence", page_icon="📈", layout="wide")

# Navigation
from components.nav import render_nav
render_nav(require_login=False)

st.title("📈 Investor Intelligence")
st.markdown("Track public cannabis companies, stock prices, shelf analytics, and financial metrics")


@st.cache_data(ttl=300)
def load_companies():
    """Load all public companies with latest prices."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                c.company_id, c.name, c.ticker_us, c.ticker_ca,
                c.exchange_us, c.exchange_ca, c.company_type,
                c.market_cap_millions, c.headquarters,
                c.website,
                sp.close_price as latest_price,
                sp.price_date as price_date,
                sp.volume as latest_volume
            FROM public_company c
            LEFT JOIN LATERAL (
                SELECT close_price, price_date, volume
                FROM stock_price
                WHERE company_id = c.company_id
                ORDER BY price_date DESC
                LIMIT 1
            ) sp ON true
            WHERE c.is_active = true
            ORDER BY c.market_cap_millions DESC NULLS LAST
        """))
        return pd.DataFrame(result.fetchall(), columns=result.keys())


@st.cache_data(ttl=300)
def load_stock_prices(company_id, days=90):
    """Load stock price history for a company."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT price_date, open_price, high_price, low_price, close_price, volume
            FROM stock_price
            WHERE company_id = :company_id
            AND price_date >= CURRENT_DATE - :days
            ORDER BY price_date
        """), {"company_id": company_id, "days": days})
        return pd.DataFrame(result.fetchall(), columns=result.keys())


@st.cache_data(ttl=300)
def load_financials(company_id=None):
    """Load financial data for companies."""
    engine = get_engine()
    with engine.connect() as conn:
        query = """
            SELECT
                c.name, c.ticker_us, f.*
            FROM company_financials f
            JOIN public_company c ON c.company_id = f.company_id
            WHERE f.period_type = 'annual'
        """
        if company_id:
            query += " AND f.company_id = :company_id"
        query += " ORDER BY c.name, f.fiscal_year DESC"

        result = conn.execute(text(query), {"company_id": company_id} if company_id else {})
        return pd.DataFrame(result.fetchall(), columns=result.keys())


@st.cache_data(ttl=300)
def load_all_financials_summary():
    """Load latest financials for all companies."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            WITH latest_annual AS (
                SELECT DISTINCT ON (company_id)
                    company_id, fiscal_year, revenue_millions, gross_profit_millions,
                    operating_income_millions, net_income_millions, ebitda_millions,
                    adjusted_ebitda_millions, total_assets_millions, total_debt_millions,
                    cash_millions, eps
                FROM company_financials
                WHERE period_type = 'annual'
                ORDER BY company_id, fiscal_year DESC
            )
            SELECT
                c.name, c.ticker_us, c.market_cap_millions,
                la.fiscal_year, la.revenue_millions, la.gross_profit_millions,
                la.operating_income_millions, la.net_income_millions,
                la.ebitda_millions, la.adjusted_ebitda_millions,
                la.total_assets_millions, la.total_debt_millions, la.cash_millions,
                la.eps
            FROM public_company c
            LEFT JOIN latest_annual la ON la.company_id = c.company_id
            WHERE c.is_active = true
            ORDER BY c.market_cap_millions DESC NULLS LAST
        """))
        return pd.DataFrame(result.fetchall(), columns=result.keys())


@st.cache_data(ttl=300)
def load_shelf_analytics():
    """Load shelf analytics for all companies with brand mappings."""
    engine = get_engine()
    with engine.connect() as conn:
        # Get total dispensaries for penetration calculation
        total_stores = conn.execute(text(
            "SELECT COUNT(DISTINCT dispensary_id) FROM raw_menu_item"
        )).scalar() or 1

        # Get shelf analytics by company
        result = conn.execute(text("""
            SELECT
                c.company_id, c.name, c.ticker_us, c.company_type,
                COUNT(DISTINCT r.raw_name) as total_skus,
                COUNT(DISTINCT r.dispensary_id) as store_count,
                COUNT(DISTINCT cb.brand_name) as brand_count,
                STRING_AGG(DISTINCT cb.brand_name, ', ' ORDER BY cb.brand_name) as brands
            FROM public_company c
            JOIN company_brand cb ON cb.company_id = c.company_id
            LEFT JOIN raw_menu_item r ON LOWER(r.raw_brand) = LOWER(cb.brand_name)
            WHERE c.is_active = true
            GROUP BY c.company_id, c.name, c.ticker_us, c.company_type
            ORDER BY total_skus DESC
        """))
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
        df['penetration_pct'] = (df['store_count'] / total_stores * 100).round(1)
        df['total_stores'] = total_stores
        return df


@st.cache_data(ttl=300)
def load_shelf_analytics_by_state():
    """Load shelf analytics broken down by state."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                c.company_id, c.name, c.ticker_us,
                d.state,
                COUNT(DISTINCT r.raw_name) as total_skus,
                COUNT(DISTINCT r.dispensary_id) as store_count
            FROM public_company c
            JOIN company_brand cb ON cb.company_id = c.company_id
            LEFT JOIN raw_menu_item r ON LOWER(r.raw_brand) = LOWER(cb.brand_name)
            LEFT JOIN dispensary d ON d.dispensary_id = r.dispensary_id
            WHERE c.is_active = true AND d.state IS NOT NULL
            GROUP BY c.company_id, c.name, c.ticker_us, d.state
            ORDER BY c.name, d.state
        """))
        return pd.DataFrame(result.fetchall(), columns=result.keys())


@st.cache_data(ttl=300)
def load_state_totals():
    """Load total dispensaries per state for penetration calculation."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT d.state, COUNT(DISTINCT r.dispensary_id) as total_stores
            FROM raw_menu_item r
            JOIN dispensary d ON d.dispensary_id = r.dispensary_id
            WHERE d.state IS NOT NULL
            GROUP BY d.state
        """))
        return dict(result.fetchall())


@st.cache_data(ttl=300)
def load_brand_details(company_id):
    """Load detailed brand analytics for a specific company."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                cb.brand_name,
                cb.is_primary,
                COUNT(DISTINCT r.raw_name) as sku_count,
                COUNT(DISTINCT r.dispensary_id) as store_count,
                ROUND(AVG(r.raw_price)::numeric, 2) as avg_price,
                COUNT(DISTINCT r.raw_category) as category_count
            FROM company_brand cb
            LEFT JOIN raw_menu_item r ON LOWER(r.raw_brand) = LOWER(cb.brand_name)
            WHERE cb.company_id = :company_id
            GROUP BY cb.brand_name, cb.is_primary
            ORDER BY sku_count DESC
        """), {"company_id": company_id})
        return pd.DataFrame(result.fetchall(), columns=result.keys())


# Load data
companies = load_companies()

# Tabs for different views
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Overview", "🏪 Shelf Analytics", "📈 Stock Charts", "💰 Financials", "🔬 Company Details"])

with tab1:
    st.subheader("Public Cannabis Companies")

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Companies Tracked", len(companies))
    with col2:
        msos = len(companies[companies['company_type'] == 'MSO'])
        st.metric("US MSOs", msos)
    with col3:
        lps = len(companies[companies['company_type'] == 'LP'])
        st.metric("Canadian LPs", lps)
    with col4:
        total_mcap = companies['market_cap_millions'].sum()
        st.metric("Total Market Cap", f"${total_mcap/1000:.1f}B" if total_mcap else "N/A")

    # Master table
    st.markdown("### Market Overview")

    # Prepare display dataframe
    display_df = companies[['name', 'ticker_us', 'ticker_ca', 'exchange_us', 'company_type',
                           'latest_price', 'market_cap_millions', 'latest_volume']].copy()
    display_df.columns = ['Company', 'US Ticker', 'CA Ticker', 'Exchange', 'Type',
                         'Price ($)', 'Market Cap ($M)', 'Volume']

    # Format columns
    display_df['Price ($)'] = display_df['Price ($)'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "-")
    display_df['Market Cap ($M)'] = display_df['Market Cap ($M)'].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "-")
    display_df['Volume'] = display_df['Volume'].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "-")

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Market cap bar chart
    st.markdown("### Market Capitalization Comparison")
    mcap_df = companies[companies['market_cap_millions'].notna()].copy()
    if not mcap_df.empty:
        mcap_df = mcap_df.sort_values('market_cap_millions', ascending=True)
        fig = px.bar(mcap_df, x='market_cap_millions', y='name',
                    color='company_type', orientation='h',
                    labels={'market_cap_millions': 'Market Cap ($M)', 'name': '', 'company_type': 'Type'},
                    color_discrete_map={'MSO': '#2ecc71', 'LP': '#3498db', 'REIT': '#9b59b6', 'Tech': '#e74c3c'})
        fig.update_layout(height=500, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Shelf Analytics")
    st.markdown("Track SKU counts, shelf penetration, and market presence by company")

    shelf_data = load_shelf_analytics()
    state_data = load_shelf_analytics_by_state()
    state_totals = load_state_totals()

    if not shelf_data.empty:
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            companies_with_data = len(shelf_data[shelf_data['total_skus'] > 0])
            st.metric("Companies with Shelf Data", companies_with_data)
        with col2:
            total_skus = shelf_data['total_skus'].sum()
            st.metric("Total SKUs Tracked", f"{total_skus:,}")
        with col3:
            avg_penetration = shelf_data[shelf_data['penetration_pct'] > 0]['penetration_pct'].mean()
            st.metric("Avg Shelf Penetration", f"{avg_penetration:.1f}%" if pd.notna(avg_penetration) else "N/A")
        with col4:
            total_stores = shelf_data['total_stores'].iloc[0] if len(shelf_data) > 0 else 0
            st.metric("Total Stores Tracked", f"{total_stores:,}")

        # Master shelf analytics table
        st.markdown("### Company Shelf Presence")

        shelf_display = shelf_data[['name', 'ticker_us', 'company_type', 'total_skus',
                                    'store_count', 'penetration_pct', 'brands']].copy()
        shelf_display.columns = ['Company', 'Ticker', 'Type', 'SKUs', 'Stores', 'Penetration %', 'Brands']

        st.dataframe(shelf_display, use_container_width=True, hide_index=True)

        # SKU count bar chart
        st.markdown("### SKU Count by Company")
        sku_df = shelf_data[shelf_data['total_skus'] > 0].sort_values('total_skus', ascending=True)
        if not sku_df.empty:
            fig = px.bar(sku_df, x='total_skus', y='name', orientation='h',
                        color='company_type',
                        labels={'total_skus': 'Number of SKUs', 'name': '', 'company_type': 'Type'},
                        color_discrete_map={'MSO': '#2ecc71', 'LP': '#3498db', 'REIT': '#9b59b6', 'Tech': '#e74c3c'})
            fig.update_layout(height=400, showlegend=True)
            st.plotly_chart(fig, use_container_width=True)

        # Shelf penetration chart
        st.markdown("### Shelf Penetration by Company")
        pen_df = shelf_data[shelf_data['penetration_pct'] > 0].sort_values('penetration_pct', ascending=True)
        if not pen_df.empty:
            fig = px.bar(pen_df, x='penetration_pct', y='name', orientation='h',
                        color='penetration_pct',
                        labels={'penetration_pct': 'Penetration %', 'name': ''},
                        color_continuous_scale='Greens')
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        # State breakdown
        st.markdown("---")
        st.markdown("### State-by-State Analysis")

        if not state_data.empty:
            # State filter
            states = sorted(state_data['state'].dropna().unique())
            selected_state = st.selectbox("Select State", ["All States"] + list(states))

            if selected_state == "All States":
                # Show heatmap of companies vs states
                pivot = state_data.pivot_table(index='name', columns='state',
                                               values='total_skus', aggfunc='sum', fill_value=0)
                if not pivot.empty:
                    fig = px.imshow(pivot, labels=dict(x="State", y="Company", color="SKUs"),
                                   color_continuous_scale='Greens', aspect='auto')
                    fig.update_layout(height=500)
                    st.plotly_chart(fig, use_container_width=True)
            else:
                # Show details for selected state
                state_stores = state_totals.get(selected_state, 1)
                state_df = state_data[state_data['state'] == selected_state].copy()
                state_df['penetration_pct'] = (state_df['store_count'] / state_stores * 100).round(1)

                col1, col2 = st.columns(2)
                with col1:
                    st.metric(f"Dispensaries in {selected_state}", state_stores)
                with col2:
                    companies_in_state = len(state_df[state_df['total_skus'] > 0])
                    st.metric("Companies Present", companies_in_state)

                # State table
                state_display = state_df[['name', 'ticker_us', 'total_skus', 'store_count', 'penetration_pct']].copy()
                state_display.columns = ['Company', 'Ticker', 'SKUs', 'Stores', 'Penetration %']
                state_display = state_display.sort_values('total_skus', ascending=False)
                st.dataframe(state_display, use_container_width=True, hide_index=True)

                # Bar chart for state
                if not state_df.empty:
                    fig = px.bar(state_df.sort_values('total_skus', ascending=True),
                                x='total_skus', y='name', orientation='h',
                                labels={'total_skus': 'SKUs', 'name': ''},
                                title=f"SKU Count in {selected_state}")
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No shelf analytics data available. Brand mappings may need to be added.")

with tab3:
    st.subheader("Stock Price Charts")

    # Company selector
    company_options = dict(zip(companies['name'] + ' (' + companies['ticker_us'].fillna(companies['ticker_ca']) + ')',
                               companies['company_id']))
    selected_company = st.selectbox("Select Company", list(company_options.keys()))

    if selected_company:
        company_id = company_options[selected_company]

        # Time range selector
        col1, col2 = st.columns([1, 4])
        with col1:
            days = st.selectbox("Time Range", [30, 60, 90, 180, 365], index=2,
                               format_func=lambda x: f"{x} days")

        prices = load_stock_prices(company_id, days)

        if not prices.empty:
            # Candlestick chart
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                               vertical_spacing=0.03, row_heights=[0.7, 0.3])

            fig.add_trace(go.Candlestick(
                x=prices['price_date'],
                open=prices['open_price'],
                high=prices['high_price'],
                low=prices['low_price'],
                close=prices['close_price'],
                name='Price'
            ), row=1, col=1)

            fig.add_trace(go.Bar(
                x=prices['price_date'],
                y=prices['volume'],
                name='Volume',
                marker_color='rgba(52, 152, 219, 0.5)'
            ), row=2, col=1)

            fig.update_layout(
                title=f"{selected_company} - Stock Price",
                yaxis_title="Price ($)",
                yaxis2_title="Volume",
                xaxis_rangeslider_visible=False,
                height=500
            )
            st.plotly_chart(fig, use_container_width=True)

            # Price metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                current = prices['close_price'].iloc[-1]
                st.metric("Current Price", f"${current:.2f}")
            with col2:
                high = prices['high_price'].max()
                st.metric(f"{days}D High", f"${high:.2f}")
            with col3:
                low = prices['low_price'].min()
                st.metric(f"{days}D Low", f"${low:.2f}")
            with col4:
                if len(prices) > 1:
                    change = ((prices['close_price'].iloc[-1] / prices['close_price'].iloc[0]) - 1) * 100
                    st.metric(f"{days}D Change", f"{change:+.1f}%")
        else:
            st.info("No price data available for this company")

    # Multi-company comparison
    st.markdown("---")
    st.markdown("### Compare Multiple Companies")

    compare_companies = st.multiselect(
        "Select companies to compare",
        list(company_options.keys()),
        default=list(company_options.keys())[:5] if len(company_options) >= 5 else list(company_options.keys())
    )

    if compare_companies:
        comparison_data = []
        for comp_name in compare_companies:
            comp_id = company_options[comp_name]
            prices = load_stock_prices(comp_id, 90)
            if not prices.empty:
                # Normalize to 100 at start
                prices['normalized'] = (prices['close_price'] / prices['close_price'].iloc[0]) * 100
                prices['company'] = comp_name.split(' (')[0]  # Short name
                comparison_data.append(prices[['price_date', 'normalized', 'company']])

        if comparison_data:
            combined = pd.concat(comparison_data)
            fig = px.line(combined, x='price_date', y='normalized', color='company',
                         labels={'price_date': 'Date', 'normalized': 'Normalized Price (Base=100)', 'company': 'Company'})
            fig.update_layout(height=400, title="90-Day Relative Performance (Normalized to 100)")
            st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("Financial Metrics")

    financials = load_all_financials_summary()

    if not financials.empty and financials['revenue_millions'].notna().any():
        # Filter to companies with financial data
        fin_df = financials[financials['revenue_millions'].notna()].copy()

        if not fin_df.empty:
            # Revenue comparison
            st.markdown("### Revenue Comparison (Latest FY)")
            fig = px.bar(fin_df.sort_values('revenue_millions', ascending=True),
                        x='revenue_millions', y='name', orientation='h',
                        labels={'revenue_millions': 'Revenue ($M)', 'name': ''},
                        color='revenue_millions', color_continuous_scale='Greens')
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

            # Financial metrics table
            st.markdown("### Financial Summary")
            fin_display = fin_df[['name', 'ticker_us', 'fiscal_year', 'revenue_millions',
                                  'gross_profit_millions', 'net_income_millions',
                                  'total_assets_millions', 'total_debt_millions', 'cash_millions']].copy()
            fin_display.columns = ['Company', 'Ticker', 'FY', 'Revenue ($M)', 'Gross Profit ($M)',
                                  'Net Income ($M)', 'Total Assets ($M)', 'Total Debt ($M)', 'Cash ($M)']

            # Format numbers
            for col in ['Revenue ($M)', 'Gross Profit ($M)', 'Net Income ($M)',
                       'Total Assets ($M)', 'Total Debt ($M)', 'Cash ($M)']:
                fin_display[col] = fin_display[col].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "-")

            st.dataframe(fin_display, use_container_width=True, hide_index=True)

            # Profitability scatter
            if fin_df['net_income_millions'].notna().any():
                st.markdown("### Revenue vs Profitability")
                scatter_df = fin_df[fin_df['net_income_millions'].notna()].copy()
                if not scatter_df.empty:
                    fig = px.scatter(scatter_df, x='revenue_millions', y='net_income_millions',
                                    size='market_cap_millions', hover_name='name',
                                    labels={'revenue_millions': 'Revenue ($M)',
                                           'net_income_millions': 'Net Income ($M)'},
                                    color='net_income_millions',
                                    color_continuous_scale=['red', 'yellow', 'green'],
                                    color_continuous_midpoint=0)
                    fig.add_hline(y=0, line_dash="dash", line_color="gray")
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Financial data is being collected. Run the SEC filing script to populate this section.")

        # Show what we have
        st.markdown("### Companies with SEC Filings")
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT c.name, c.ticker_us, c.cik, COUNT(f.id) as filing_count
                FROM public_company c
                LEFT JOIN company_financials f ON f.company_id = c.company_id
                WHERE c.cik IS NOT NULL
                GROUP BY c.company_id, c.name, c.ticker_us, c.cik
                ORDER BY filing_count DESC
            """))
            sec_df = pd.DataFrame(result.fetchall(), columns=['Company', 'Ticker', 'CIK', 'Filing Periods'])
            st.dataframe(sec_df, use_container_width=True, hide_index=True)

with tab5:
    st.subheader("Company Details")

    # Company selector
    detail_company = st.selectbox("Select Company for Details", list(company_options.keys()), key="detail_select")

    if detail_company:
        company_id = company_options[detail_company]
        company_data = companies[companies['company_id'] == company_id].iloc[0]

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Company Info")
            st.markdown(f"**Name:** {company_data['name']}")
            st.markdown(f"**Type:** {company_data['company_type']}")
            if company_data['ticker_us']:
                st.markdown(f"**US Ticker:** {company_data['ticker_us']} ({company_data['exchange_us']})")
            if company_data['ticker_ca']:
                st.markdown(f"**CA Ticker:** {company_data['ticker_ca']} ({company_data['exchange_ca']})")
            if company_data.get('headquarters'):
                st.markdown(f"**Headquarters:** {company_data['headquarters']}")
            if company_data['website']:
                st.markdown(f"**Website:** [{company_data['website']}]({company_data['website']})")

        with col2:
            st.markdown("### Market Data")
            if pd.notna(company_data['latest_price']):
                st.metric("Latest Price", f"${company_data['latest_price']:.2f}")
            if pd.notna(company_data['market_cap_millions']):
                st.metric("Market Cap", f"${company_data['market_cap_millions']:,.0f}M")
            if pd.notna(company_data['latest_volume']):
                st.metric("Latest Volume", f"{company_data['latest_volume']:,.0f}")

        # Shelf analytics for this company
        st.markdown("---")
        st.markdown("### Shelf Analytics")

        brand_details = load_brand_details(company_id)
        if not brand_details.empty and brand_details['sku_count'].sum() > 0:
            col1, col2, col3 = st.columns(3)
            with col1:
                total_skus = brand_details['sku_count'].sum()
                st.metric("Total SKUs", f"{total_skus:,}")
            with col2:
                total_stores = brand_details['store_count'].max()
                st.metric("Store Presence", f"{total_stores:,}")
            with col3:
                avg_price = brand_details[brand_details['avg_price'].notna()]['avg_price'].mean()
                st.metric("Avg Price", f"${avg_price:.2f}" if pd.notna(avg_price) else "N/A")

            # Brand breakdown
            st.markdown("#### Brand Performance")
            brand_display = brand_details[['brand_name', 'is_primary', 'sku_count', 'store_count', 'avg_price', 'category_count']].copy()
            brand_display.columns = ['Brand', 'Primary', 'SKUs', 'Stores', 'Avg Price', 'Categories']
            brand_display['Primary'] = brand_display['Primary'].apply(lambda x: 'Yes' if x else '')
            brand_display['Avg Price'] = brand_display['Avg Price'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "-")
            st.dataframe(brand_display, use_container_width=True, hide_index=True)
        else:
            st.info("No shelf data available for this company's brands.")

        # Historical financials for this company
        st.markdown("---")
        st.markdown("### Financial History")

        company_fin = load_financials(company_id)
        if not company_fin.empty:
            # Revenue trend
            annual = company_fin[company_fin['period_type'] == 'annual'].sort_values('fiscal_year')
            if not annual.empty and annual['revenue_millions'].notna().any():
                fig = go.Figure()
                fig.add_trace(go.Bar(x=annual['fiscal_year'], y=annual['revenue_millions'], name='Revenue'))
                if annual['net_income_millions'].notna().any():
                    fig.add_trace(go.Scatter(x=annual['fiscal_year'], y=annual['net_income_millions'],
                                            name='Net Income', mode='lines+markers'))
                fig.update_layout(title="Annual Revenue & Net Income",
                                 xaxis_title="Fiscal Year", yaxis_title="$M",
                                 height=350)
                st.plotly_chart(fig, use_container_width=True)

            # Show raw data
            st.markdown("### Raw Financial Data")
            st.dataframe(company_fin[['fiscal_year', 'period_type', 'revenue_millions',
                                     'gross_profit_millions', 'net_income_millions',
                                     'total_assets_millions', 'cash_millions']],
                        use_container_width=True, hide_index=True)
        else:
            st.info("No SEC filing data available for this company. This may be a Canadian LP filing with SEDAR.")

# Footer
st.markdown("---")
st.caption("Data sources: Yahoo Finance (stock prices), SEC EDGAR (financial filings)")
