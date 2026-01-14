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
from core.state_regulations import (
    STATE_REGULATIONS, LegalStatus, STATUS_COLORS, STATUS_LABELS,
    get_status_summary, get_states_by_status, UPCOMING_BALLOTS
)
from sqlalchemy import text
import numpy as np

st.set_page_config(page_title="Investor Intelligence", page_icon=None, layout="wide")

# Navigation
from components.sidebar_nav import render_nav
from components.auth import is_authenticated

# Handle section parameter for tab navigation
def get_section_from_params():
    params = st.query_params
    return params.get("section", None)

render_nav(require_login=False)

# Import and apply shared styles
from components.styles import get_page_styles, COLORS
st.markdown(get_page_styles(), unsafe_allow_html=True)

# Check if user is authenticated for real data vs demo
DEMO_MODE = not is_authenticated()

# Section to tab mapping
section = get_section_from_params()
TAB_MAP = {"companies": 0, "stocks": 2, "financials": 3, "states": 1, "shelf": 4}

st.title("Investor Intelligence")
st.markdown("Track public cannabis companies, stock prices, shelf analytics, and financial metrics")

if DEMO_MODE:
    st.info("**Demo Mode** - Explore cannabis industry investment data. [Login](/Login) for full access.")


# ==================== DEMO DATA ====================
def get_demo_companies():
    """Generate realistic demo company data - Q3 2025 data."""
    return pd.DataFrame([
        {"company_id": "1", "name": "Curaleaf Holdings", "ticker_us": "CURLF", "ticker_ca": "CURA",
         "exchange_us": "OTC", "exchange_ca": "CSE", "company_type": "MSO",
         "market_cap_millions": 1910, "headquarters": "New York, NY", "website": "curaleaf.com",
         "latest_price": 2.47, "price_date": datetime.now().date(), "latest_volume": 1250000},
        {"company_id": "2", "name": "Green Thumb Industries", "ticker_us": "GTBIF", "ticker_ca": "GTII",
         "exchange_us": "OTC", "exchange_ca": "CSE", "company_type": "MSO",
         "market_cap_millions": 1850, "headquarters": "Chicago, IL", "website": "gtigrows.com",
         "latest_price": 7.85, "price_date": datetime.now().date(), "latest_volume": 890000},
        {"company_id": "3", "name": "Trulieve Cannabis", "ticker_us": "TCNNF", "ticker_ca": "TRUL",
         "exchange_us": "OTC", "exchange_ca": "CSE", "company_type": "MSO",
         "market_cap_millions": 1500, "headquarters": "Tallahassee, FL", "website": "trulieve.com",
         "latest_price": 8.37, "price_date": datetime.now().date(), "latest_volume": 720000},
        {"company_id": "4", "name": "Verano Holdings", "ticker_us": "VRNOF", "ticker_ca": "VRNO",
         "exchange_us": "OTC", "exchange_ca": "CSE", "company_type": "MSO",
         "market_cap_millions": 474, "headquarters": "Chicago, IL", "website": "verano.com",
         "latest_price": 1.26, "price_date": datetime.now().date(), "latest_volume": 650000},
        {"company_id": "5", "name": "Tilray Brands", "ticker_us": "TLRY", "ticker_ca": "TLRY",
         "exchange_us": "NASDAQ", "exchange_ca": "TSX", "company_type": "LP",
         "market_cap_millions": 2800, "headquarters": "New York, NY", "website": "tilray.com",
         "latest_price": 8.99, "price_date": datetime.now().date(), "latest_volume": 22500000},
        {"company_id": "6", "name": "Canopy Growth", "ticker_us": "CGC", "ticker_ca": "WEED",
         "exchange_us": "NASDAQ", "exchange_ca": "TSX", "company_type": "LP",
         "market_cap_millions": 180, "headquarters": "Smiths Falls, ON", "website": "canopygrowth.com",
         "latest_price": 1.19, "price_date": datetime.now().date(), "latest_volume": 8500000},
        {"company_id": "7", "name": "Cresco Labs", "ticker_us": "CRLBF", "ticker_ca": "CL",
         "exchange_us": "OTC", "exchange_ca": "CSE", "company_type": "MSO",
         "market_cap_millions": 450, "headquarters": "Chicago, IL", "website": "crescolabs.com",
         "latest_price": 1.20, "price_date": datetime.now().date(), "latest_volume": 520000},
        {"company_id": "8", "name": "Cannabist Company", "ticker_us": "CBSTF", "ticker_ca": "CBST",
         "exchange_us": "OTC", "exchange_ca": "CSE", "company_type": "MSO",
         "market_cap_millions": 28, "headquarters": "New York, NY", "website": "cannabistcompany.com",
         "latest_price": 0.055, "price_date": datetime.now().date(), "latest_volume": 380000},
        {"company_id": "9", "name": "TerrAscend", "ticker_us": "TRSSF", "ticker_ca": "TER",
         "exchange_us": "OTC", "exchange_ca": "TSX", "company_type": "MSO",
         "market_cap_millions": 480, "headquarters": "Mississauga, ON", "website": "terrascend.com",
         "latest_price": 1.55, "price_date": datetime.now().date(), "latest_volume": 290000},
        {"company_id": "10", "name": "Ayr Wellness", "ticker_us": "AYRWF", "ticker_ca": "AYR.A",
         "exchange_us": "OTC", "exchange_ca": "CSE", "company_type": "MSO",
         "market_cap_millions": 8, "headquarters": "Miami, FL", "website": "ayrwellness.com",
         "latest_price": 0.023, "price_date": datetime.now().date(), "latest_volume": 210000},
        {"company_id": "11", "name": "Vireo Growth", "ticker_us": "VREOF", "ticker_ca": "VREO",
         "exchange_us": "OTCQX", "exchange_ca": "CSE", "company_type": "MSO",
         "market_cap_millions": 650, "headquarters": "Minneapolis, MN", "website": "vireohealth.com",
         "latest_price": 0.62, "price_date": datetime.now().date(), "latest_volume": 185000},
    ])


def get_demo_stock_history(company_name, days=90):
    """Generate realistic stock price history."""
    np.random.seed(hash(company_name) % 2**32)

    base_prices = {
        "Curaleaf Holdings": 2.47, "Green Thumb Industries": 8.17,
        "Trulieve Cannabis": 8.20, "Verano Holdings": 1.21,
        "Tilray Brands": 8.99, "Canopy Growth": 1.19,
        "Cresco Labs": 1.20, "Cannabist Company": 0.055,
        "TerrAscend": 1.55, "Ayr Wellness": 0.023,
        "Vireo Growth": 0.62
    }
    base_price = base_prices.get(company_name, 5.0)

    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    prices = [base_price]

    for i in range(1, days):
        change = np.random.normal(0, 0.03)  # 3% daily volatility
        prices.append(max(0.10, prices[-1] * (1 + change)))

    return pd.DataFrame({
        'price_date': dates,
        'open_price': prices,
        'high_price': [p * (1 + abs(np.random.normal(0, 0.02))) for p in prices],
        'low_price': [p * (1 - abs(np.random.normal(0, 0.02))) for p in prices],
        'close_price': [p * (1 + np.random.normal(0, 0.01)) for p in prices],
        'volume': [int(np.random.uniform(200000, 2000000)) for _ in prices]
    })


def get_demo_financials():
    """Generate demo financial data."""
    return pd.DataFrame([
        {"name": "Curaleaf Holdings", "ticker_us": "CURLF", "fiscal_year": 2023,
         "revenue_millions": 1340, "gross_profit_millions": 670, "net_income_millions": -85,
         "total_assets_millions": 3200, "total_debt_millions": 850, "cash_millions": 120,
         "market_cap_millions": 2850},
        {"name": "Green Thumb Industries", "ticker_us": "GTBIF", "fiscal_year": 2023,
         "revenue_millions": 1050, "gross_profit_millions": 525, "net_income_millions": 45,
         "total_assets_millions": 2400, "total_debt_millions": 520, "cash_millions": 180,
         "market_cap_millions": 1950},
        {"name": "Trulieve Cannabis", "ticker_us": "TCNNF", "fiscal_year": 2023,
         "revenue_millions": 1200, "gross_profit_millions": 720, "net_income_millions": -120,
         "total_assets_millions": 2800, "total_debt_millions": 680, "cash_millions": 95,
         "market_cap_millions": 1520},
        {"name": "Tilray Brands", "ticker_us": "TLRY", "fiscal_year": 2023,
         "revenue_millions": 627, "gross_profit_millions": 175, "net_income_millions": -1400,
         "total_assets_millions": 4100, "total_debt_millions": 650, "cash_millions": 220,
         "market_cap_millions": 1680},
        {"name": "Verano Holdings", "ticker_us": "VRNOF", "fiscal_year": 2023,
         "revenue_millions": 880, "gross_profit_millions": 440, "net_income_millions": -65,
         "total_assets_millions": 1900, "total_debt_millions": 420, "cash_millions": 75,
         "market_cap_millions": 420},
        {"name": "Cresco Labs", "ticker_us": "CRLBF", "fiscal_year": 2023,
         "revenue_millions": 780, "gross_profit_millions": 350, "net_income_millions": -210,
         "total_assets_millions": 1600, "total_debt_millions": 380, "cash_millions": 55,
         "market_cap_millions": 380},
    ])


def get_demo_state_operations():
    """Generate demo state operations data - Q3 2025 store counts from latest earnings."""
    return pd.DataFrame([
        # Curaleaf - 151 total dispensaries
        {"name": "Curaleaf Holdings", "ticker_us": "CURLF", "state": "FL", "store_count": 56, "sku_count": 245},
        {"name": "Curaleaf Holdings", "ticker_us": "CURLF", "state": "NY", "store_count": 14, "sku_count": 89},
        {"name": "Curaleaf Holdings", "ticker_us": "CURLF", "state": "NJ", "store_count": 12, "sku_count": 156},
        {"name": "Curaleaf Holdings", "ticker_us": "CURLF", "state": "AZ", "store_count": 15, "sku_count": 178},
        {"name": "Curaleaf Holdings", "ticker_us": "CURLF", "state": "PA", "store_count": 10, "sku_count": 124},
        {"name": "Curaleaf Holdings", "ticker_us": "CURLF", "state": "MA", "store_count": 8, "sku_count": 112},
        {"name": "Curaleaf Holdings", "ticker_us": "CURLF", "state": "IL", "store_count": 9, "sku_count": 145},
        {"name": "Curaleaf Holdings", "ticker_us": "CURLF", "state": "MD", "store_count": 7, "sku_count": 98},
        {"name": "Curaleaf Holdings", "ticker_us": "CURLF", "state": "OH", "store_count": 6, "sku_count": 87},
        {"name": "Curaleaf Holdings", "ticker_us": "CURLF", "state": "Other", "store_count": 14, "sku_count": 165},
        # Green Thumb Industries - 98 Rise dispensaries
        {"name": "Green Thumb Industries", "ticker_us": "GTBIF", "state": "IL", "store_count": 16, "sku_count": 312},
        {"name": "Green Thumb Industries", "ticker_us": "GTBIF", "state": "FL", "store_count": 14, "sku_count": 198},
        {"name": "Green Thumb Industries", "ticker_us": "GTBIF", "state": "NJ", "store_count": 12, "sku_count": 167},
        {"name": "Green Thumb Industries", "ticker_us": "GTBIF", "state": "PA", "store_count": 18, "sku_count": 145},
        {"name": "Green Thumb Industries", "ticker_us": "GTBIF", "state": "OH", "store_count": 15, "sku_count": 134},
        {"name": "Green Thumb Industries", "ticker_us": "GTBIF", "state": "MA", "store_count": 8, "sku_count": 112},
        {"name": "Green Thumb Industries", "ticker_us": "GTBIF", "state": "Other", "store_count": 15, "sku_count": 156},
        # Trulieve - 206 dispensaries (largest retail footprint)
        {"name": "Trulieve Cannabis", "ticker_us": "TCNNF", "state": "FL", "store_count": 140, "sku_count": 425},
        {"name": "Trulieve Cannabis", "ticker_us": "TCNNF", "state": "PA", "store_count": 24, "sku_count": 165},
        {"name": "Trulieve Cannabis", "ticker_us": "TCNNF", "state": "AZ", "store_count": 12, "sku_count": 112},
        {"name": "Trulieve Cannabis", "ticker_us": "TCNNF", "state": "MD", "store_count": 8, "sku_count": 87},
        {"name": "Trulieve Cannabis", "ticker_us": "TCNNF", "state": "MA", "store_count": 7, "sku_count": 78},
        {"name": "Trulieve Cannabis", "ticker_us": "TCNNF", "state": "Other", "store_count": 15, "sku_count": 134},
        # Verano - 145 dispensaries
        {"name": "Verano Holdings", "ticker_us": "VRNOF", "state": "IL", "store_count": 32, "sku_count": 234},
        {"name": "Verano Holdings", "ticker_us": "VRNOF", "state": "FL", "store_count": 28, "sku_count": 189},
        {"name": "Verano Holdings", "ticker_us": "VRNOF", "state": "NJ", "store_count": 18, "sku_count": 145},
        {"name": "Verano Holdings", "ticker_us": "VRNOF", "state": "PA", "store_count": 14, "sku_count": 123},
        {"name": "Verano Holdings", "ticker_us": "VRNOF", "state": "OH", "store_count": 12, "sku_count": 112},
        {"name": "Verano Holdings", "ticker_us": "VRNOF", "state": "AZ", "store_count": 14, "sku_count": 98},
        {"name": "Verano Holdings", "ticker_us": "VRNOF", "state": "MD", "store_count": 10, "sku_count": 87},
        {"name": "Verano Holdings", "ticker_us": "VRNOF", "state": "Other", "store_count": 17, "sku_count": 145},
        # Cresco Labs - 72 Sunnyside dispensaries
        {"name": "Cresco Labs", "ticker_us": "CRLBF", "state": "IL", "store_count": 14, "sku_count": 198},
        {"name": "Cresco Labs", "ticker_us": "CRLBF", "state": "PA", "store_count": 12, "sku_count": 156},
        {"name": "Cresco Labs", "ticker_us": "CRLBF", "state": "FL", "store_count": 12, "sku_count": 134},
        {"name": "Cresco Labs", "ticker_us": "CRLBF", "state": "OH", "store_count": 10, "sku_count": 112},
        {"name": "Cresco Labs", "ticker_us": "CRLBF", "state": "MA", "store_count": 8, "sku_count": 89},
        {"name": "Cresco Labs", "ticker_us": "CRLBF", "state": "Other", "store_count": 16, "sku_count": 123},
        # Cannabist Company (formerly Columbia Care) - 83 dispensaries
        {"name": "Cannabist Company", "ticker_us": "CBSTF", "state": "FL", "store_count": 22, "sku_count": 145},
        {"name": "Cannabist Company", "ticker_us": "CBSTF", "state": "OH", "store_count": 12, "sku_count": 112},
        {"name": "Cannabist Company", "ticker_us": "CBSTF", "state": "VA", "store_count": 10, "sku_count": 98},
        {"name": "Cannabist Company", "ticker_us": "CBSTF", "state": "NJ", "store_count": 8, "sku_count": 87},
        {"name": "Cannabist Company", "ticker_us": "CBSTF", "state": "PA", "store_count": 6, "sku_count": 76},
        {"name": "Cannabist Company", "ticker_us": "CBSTF", "state": "Other", "store_count": 25, "sku_count": 134},
        # TerrAscend - 38 dispensaries
        {"name": "TerrAscend", "ticker_us": "TRSSF", "state": "NJ", "store_count": 12, "sku_count": 145},
        {"name": "TerrAscend", "ticker_us": "TRSSF", "state": "PA", "store_count": 10, "sku_count": 123},
        {"name": "TerrAscend", "ticker_us": "TRSSF", "state": "MD", "store_count": 6, "sku_count": 87},
        {"name": "TerrAscend", "ticker_us": "TRSSF", "state": "MI", "store_count": 5, "sku_count": 78},
        {"name": "TerrAscend", "ticker_us": "TRSSF", "state": "Other", "store_count": 5, "sku_count": 65},
        # Ayr Wellness - 90 dispensaries
        {"name": "Ayr Wellness", "ticker_us": "AYRWF", "state": "FL", "store_count": 28, "sku_count": 167},
        {"name": "Ayr Wellness", "ticker_us": "AYRWF", "state": "MA", "store_count": 12, "sku_count": 134},
        {"name": "Ayr Wellness", "ticker_us": "AYRWF", "state": "PA", "store_count": 14, "sku_count": 112},
        {"name": "Ayr Wellness", "ticker_us": "AYRWF", "state": "NJ", "store_count": 8, "sku_count": 98},
        {"name": "Ayr Wellness", "ticker_us": "AYRWF", "state": "OH", "store_count": 10, "sku_count": 89},
        {"name": "Ayr Wellness", "ticker_us": "AYRWF", "state": "Other", "store_count": 18, "sku_count": 112},
        # Tilray (primarily Canadian LP, limited US retail)
        {"name": "Tilray Brands", "ticker_us": "TLRY", "state": "US Ops", "store_count": 12, "sku_count": 89},
        # Canopy Growth (primarily Canadian LP, minimal US retail)
        {"name": "Canopy Growth", "ticker_us": "CGC", "state": "US Ops", "store_count": 5, "sku_count": 45},
    ])


def get_demo_shelf_analytics():
    """Generate demo shelf analytics data - shows stores carrying each brand."""
    # Note: store_count here represents stores carrying brand, not owned stores
    # Based on ~17,000 total dispensaries tracked
    return pd.DataFrame([
        {"company": "Curaleaf Holdings", "brand": "Select", "category": "Vapes", "avg_price": 45.00,
         "store_count": 245, "sku_count": 48, "market_share": 8.2},
        {"company": "Curaleaf Holdings", "brand": "Curaleaf", "category": "Flower", "avg_price": 42.00,
         "store_count": 180, "sku_count": 65, "market_share": 5.4},
        {"company": "Green Thumb Industries", "brand": "RYTHM", "category": "Flower", "avg_price": 48.00,
         "store_count": 312, "sku_count": 72, "market_share": 9.8},
        {"company": "Green Thumb Industries", "brand": "Dogwalkers", "category": "Pre-Rolls", "avg_price": 15.00,
         "store_count": 198, "sku_count": 24, "market_share": 6.2},
        {"company": "Trulieve Cannabis", "brand": "Trulieve", "category": "Flower", "avg_price": 38.00,
         "store_count": 156, "sku_count": 145, "market_share": 4.1},
        {"company": "Cresco Labs", "brand": "Cresco", "category": "Concentrates", "avg_price": 55.00,
         "store_count": 187, "sku_count": 38, "market_share": 7.5},
        {"company": "Verano Holdings", "brand": "Verano", "category": "Flower", "avg_price": 44.00,
         "store_count": 145, "sku_count": 56, "market_share": 4.8},
        {"company": "Vireo Growth", "brand": "Hi*AF", "category": "Flower", "avg_price": 35.00,
         "store_count": 42, "sku_count": 28, "market_share": 1.2},
        {"company": "Vireo Growth", "brand": "R.Greenleaf", "category": "Flower", "avg_price": 32.00,
         "store_count": 35, "sku_count": 22, "market_share": 0.9},
    ])


@st.cache_data(ttl=300)
def load_companies():
    """Load all public companies with latest prices."""
    engine = get_engine()
    with engine.connect() as conn:
        # Load companies first
        companies = conn.execute(text("""
            SELECT
                company_id, name, ticker_us, ticker_ca,
                exchange_us, exchange_ca, company_type,
                market_cap_millions, headquarters, website
            FROM public_company
            WHERE is_active = true
            ORDER BY market_cap_millions DESC NULLS LAST
        """))
        df = pd.DataFrame(companies.fetchall(), columns=companies.keys())

        # Load latest prices separately
        prices = conn.execute(text("""
            SELECT DISTINCT ON (company_id)
                company_id, close_price as latest_price, price_date, volume as latest_volume
            FROM stock_price
            ORDER BY company_id, price_date DESC
        """))
        prices_df = pd.DataFrame(prices.fetchall(), columns=prices.keys())

        # Merge
        if not prices_df.empty:
            df = df.merge(prices_df, on='company_id', how='left')
        else:
            df['latest_price'] = None
            df['price_date'] = None
            df['latest_volume'] = None

        return df


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
def load_state_operations():
    """Load state operations data for MSOs (retail, cultivation, processing footprint)."""
    engine = get_engine()
    with engine.connect() as conn:
        # Check if table exists
        try:
            result = conn.execute(text("""
                SELECT
                    c.company_id, c.name, c.ticker_us, c.company_type,
                    ops.state,
                    ops.has_retail, ops.has_cultivation, ops.has_processing,
                    ops.retail_count, ops.notes
                FROM company_state_operations ops
                JOIN public_company c ON c.company_id = ops.company_id
                WHERE c.is_active = true
                ORDER BY c.name, ops.state
            """))
            return pd.DataFrame(result.fetchall(), columns=result.keys())
        except:
            # Return demo data if table doesn't exist
            return pd.DataFrame()


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


@st.cache_data(ttl=60)
def load_company_news(company_id=None, limit=50):
    """Load recent news and SEC filings for companies."""
    engine = get_engine()
    with engine.connect() as conn:
        try:
            query = """
                SELECT
                    n.news_id, n.company_id, c.name as company_name, c.ticker_us,
                    n.news_type, n.event_category, n.title, n.summary,
                    n.source_url, n.filing_type, n.published_date,
                    n.is_significant, n.created_at
                FROM company_news n
                JOIN public_company c ON c.company_id = n.company_id
                WHERE 1=1
            """
            params = {}
            if company_id:
                query += " AND n.company_id = :company_id"
                params['company_id'] = company_id
            query += " ORDER BY n.published_date DESC NULLS LAST, n.created_at DESC LIMIT :limit"
            params['limit'] = limit

            result = conn.execute(text(query), params)
            return pd.DataFrame(result.fetchall(), columns=result.keys())
        except Exception as e:
            return pd.DataFrame()


@st.cache_data(ttl=60)
def load_significant_events(days=30):
    """Load significant events (M&A, executive changes) from recent news."""
    engine = get_engine()
    with engine.connect() as conn:
        try:
            result = conn.execute(text("""
                SELECT
                    n.news_id, c.name as company_name, c.ticker_us,
                    n.event_category, n.title, n.summary,
                    n.source_url, n.filing_type, n.published_date
                FROM company_news n
                JOIN public_company c ON c.company_id = n.company_id
                WHERE n.is_significant = true
                AND (n.published_date >= CURRENT_DATE - :days OR n.created_at >= CURRENT_DATE - :days)
                ORDER BY n.published_date DESC NULLS LAST
                LIMIT 20
            """), {"days": days})
            return pd.DataFrame(result.fetchall(), columns=result.keys())
        except:
            return pd.DataFrame()


def get_demo_news():
    """Generate demo news data."""
    return pd.DataFrame([
        {"company_name": "Curaleaf Holdings", "ticker_us": "CURLF", "news_type": "press_release",
         "title": "Curaleaf Reports Q3 2025 Results with $340M Revenue", "event_category": "financial_results",
         "published_date": datetime.now() - timedelta(days=5), "is_significant": False},
        {"company_name": "Green Thumb Industries", "ticker_us": "GTBIF", "news_type": "press_release",
         "title": "Green Thumb Expands Pennsylvania Retail Footprint with RISE Store", "event_category": "facility_operations",
         "published_date": datetime.now() - timedelta(days=8), "is_significant": False},
        {"company_name": "Trulieve Cannabis", "ticker_us": "TCNNF", "news_type": "sec_filing",
         "title": "Trulieve Cannabis Quarterly Report (10-Q)", "filing_type": "10-Q",
         "published_date": datetime.now() - timedelta(days=12), "is_significant": False},
        {"company_name": "Canopy Growth", "ticker_us": "CGC", "news_type": "sec_filing",
         "title": "Canopy Growth Current Report (8-K)", "filing_type": "8-K", "event_category": "executive_change",
         "summary": "Items: Departure/Appointment of Directors/Officers",
         "published_date": datetime.now() - timedelta(days=3), "is_significant": True},
        {"company_name": "Tilray Brands", "ticker_us": "TLRY", "news_type": "sec_filing",
         "title": "Tilray Brands Quarterly Report (10-Q)", "filing_type": "10-Q",
         "published_date": datetime.now() - timedelta(days=6), "is_significant": False},
        {"company_name": "Verano Holdings", "ticker_us": "VRNOF", "news_type": "press_release",
         "title": "Verano Announces Strategic Partnership in New Market", "event_category": "merger_acquisition",
         "published_date": datetime.now() - timedelta(days=10), "is_significant": True},
        {"company_name": "Cresco Labs", "ticker_us": "CRLBF", "news_type": "press_release",
         "title": "Cresco Labs Opens New Sunnyside Location in Illinois", "event_category": "facility_operations",
         "published_date": datetime.now() - timedelta(days=15), "is_significant": False},
        {"company_name": "Cronos Group", "ticker_us": "CRON", "news_type": "sec_filing",
         "title": "Cronos Group Quarterly Report (10-Q)", "filing_type": "10-Q",
         "published_date": datetime.now() - timedelta(days=20), "is_significant": False},
    ])


# Load data - use demo data in demo mode for consistent display
if DEMO_MODE:
    companies = get_demo_companies()
else:
    companies = load_companies()

# Tabs for different views
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["Overview", "News & Filings", "Regulatory Map", "State Operations", "Stock Charts", "Financials", "Shelf Analytics"])

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

    # Format columns - use 3 decimals for penny stocks
    display_df['Price ($)'] = display_df['Price ($)'].apply(
        lambda x: f"${x:.3f}" if pd.notna(x) and x < 0.10 else (f"${x:.2f}" if pd.notna(x) else "-")
    )
    display_df['Market Cap ($M)'] = display_df['Market Cap ($M)'].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "-")
    display_df['Volume'] = display_df['Volume'].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "-")

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Market cap bar chart
    st.markdown("### Market Capitalization Comparison")
    mcap_df = companies[companies['market_cap_millions'].notna()].copy()
    if not mcap_df.empty:
        mcap_df = mcap_df.sort_values('market_cap_millions', ascending=True)
        # Format market cap labels
        mcap_df['mcap_label'] = mcap_df['market_cap_millions'].apply(
            lambda x: f"${x/1000:.2f}B" if x >= 1000 else f"${x:.0f}M"
        )
        fig = px.bar(mcap_df, x='market_cap_millions', y='name',
                    color='company_type', orientation='h',
                    text='mcap_label',
                    labels={'market_cap_millions': 'Market Cap ($M)', 'name': '', 'company_type': 'Type'},
                    color_discrete_map={'MSO': '#2ecc71', 'LP': '#3498db', 'REIT': '#9b59b6', 'Tech': '#e74c3c'})
        fig.update_traces(textposition='outside', textfont_size=11)
        fig.update_layout(height=500, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("News & SEC Filings")
    st.markdown("Recent press releases, SEC filings (10-K, 10-Q, 8-K), and significant corporate events")

    # Load news data
    if DEMO_MODE:
        news_data = get_demo_news()
    else:
        news_data = load_company_news(limit=50)

    if not news_data.empty:
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_news = len(news_data)
            st.metric("Recent Updates", total_news)
        with col2:
            sec_filings = len(news_data[news_data['news_type'] == 'sec_filing'])
            st.metric("SEC Filings", sec_filings)
        with col3:
            press_releases = len(news_data[news_data['news_type'] == 'press_release'])
            st.metric("Press Releases", press_releases)
        with col4:
            significant = len(news_data[news_data['is_significant'] == True]) if 'is_significant' in news_data.columns else 0
            st.metric("Significant Events", significant, help="M&A, Executive Changes, etc.")

        # Significant Events Section
        st.markdown("### Significant Events")
        st.markdown("Executive changes, M&A activity, and other material events")

        significant_news = news_data[news_data.get('is_significant', False) == True] if 'is_significant' in news_data.columns else pd.DataFrame()

        if not significant_news.empty:
            for _, row in significant_news.head(5).iterrows():
                event_type = row.get('event_category', 'corporate')
                event_colors = {
                    'executive_change': ('#fff3e0', '#e65100', 'Executive Change'),
                    'merger_acquisition': ('#e8f5e9', '#2e7d32', 'M&A'),
                    'capital_raise': ('#e3f2fd', '#1565c0', 'Capital'),
                    'legal_regulatory': ('#fce4ec', '#c62828', 'Legal/Regulatory'),
                }
                bg_color, text_color, label = event_colors.get(event_type, ('#f5f5f5', '#424242', 'Corporate'))

                pub_date = row.get('published_date')
                date_str = pub_date.strftime('%b %d, %Y') if pd.notna(pub_date) else 'Recent'

                st.markdown(f"""
                <div style="background:{bg_color}; padding:1rem; border-radius:8px; margin-bottom:0.75rem; border-left:4px solid {text_color};">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="background:{text_color}; color:white; padding:2px 8px; border-radius:4px; font-size:0.75rem;">{label}</span>
                        <span style="color:#757575; font-size:0.85rem;">{date_str}</span>
                    </div>
                    <p style="margin:0.5rem 0 0.25rem 0; font-weight:600; color:#212121;">{row.get('company_name', '')} ({row.get('ticker_us', '')})</p>
                    <p style="margin:0; color:#424242;">{row.get('title', '')}</p>
                    {f'<p style="margin:0.25rem 0 0 0; font-size:0.85rem; color:#616161;">{row.get("summary", "")}</p>' if row.get('summary') else ''}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No significant events detected in recent filings. Check back for M&A activity, executive changes, and other material events.")

        st.markdown("---")

        # Recent SEC Filings
        st.markdown("### Recent SEC Filings")

        # Filter selector
        col1, col2 = st.columns([1, 3])
        with col1:
            filing_filter = st.selectbox("Filing Type", ["All", "10-K (Annual)", "10-Q (Quarterly)", "8-K (Current)"], key="filing_filter")

        sec_news = news_data[news_data['news_type'] == 'sec_filing'].copy()

        if filing_filter != "All":
            filter_map = {"10-K (Annual)": "10-K", "10-Q (Quarterly)": "10-Q", "8-K (Current)": "8-K"}
            sec_news = sec_news[sec_news['filing_type'] == filter_map[filing_filter]]

        if not sec_news.empty:
            for _, row in sec_news.head(10).iterrows():
                filing_type = row.get('filing_type', '')
                filing_colors = {'10-K': '#1565c0', '10-Q': '#2e7d32', '8-K': '#7b1fa2'}
                badge_color = filing_colors.get(filing_type, '#757575')

                pub_date = row.get('published_date')
                date_str = pub_date.strftime('%b %d, %Y') if pd.notna(pub_date) else 'Recent'
                source_url = row.get('source_url', '#')

                st.markdown(f"""
                <div style="padding:0.75rem; border:1px solid #e0e0e0; border-radius:8px; margin-bottom:0.5rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <span style="background:{badge_color}; color:white; padding:2px 8px; border-radius:4px; font-size:0.8rem; margin-right:8px;">{filing_type}</span>
                            <strong>{row.get('company_name', '')}</strong> <span style="color:#757575;">({row.get('ticker_us', '')})</span>
                        </div>
                        <span style="color:#757575; font-size:0.85rem;">{date_str}</span>
                    </div>
                    <p style="margin:0.5rem 0 0 0; color:#424242;">{row.get('title', '')}</p>
                    {f'<p style="margin:0.25rem 0 0 0; font-size:0.85rem; color:#616161;">{row.get("summary", "")}</p>' if row.get('summary') else ''}
                    <a href="{source_url}" target="_blank" style="font-size:0.85rem;">View Filing</a>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No SEC filings found. Companies with CIK numbers: Tilray, Canopy Growth, Aurora, Cronos, SNDL, and others.")

        st.markdown("---")

        # Recent Press Releases
        st.markdown("### Recent Press Releases")

        # Company filter
        company_list = ["All Companies"] + sorted(news_data['company_name'].dropna().unique().tolist())
        selected_company = st.selectbox("Filter by Company", company_list, key="pr_company_filter")

        pr_news = news_data[news_data['news_type'] == 'press_release'].copy()
        if selected_company != "All Companies":
            pr_news = pr_news[pr_news['company_name'] == selected_company]

        if not pr_news.empty:
            for _, row in pr_news.head(10).iterrows():
                pub_date = row.get('published_date')
                date_str = pub_date.strftime('%b %d, %Y') if pd.notna(pub_date) else 'Recent'
                source_url = row.get('source_url', '#')

                category = row.get('event_category', '')
                cat_labels = {
                    'financial_results': 'Earnings',
                    'facility_operations': 'Operations',
                    'merger_acquisition': 'M&A',
                    'executive_change': 'Leadership',
                    'capital_raise': 'Capital',
                }
                cat_label = cat_labels.get(category, '')

                st.markdown(f"""
                <div style="padding:0.75rem; border:1px solid #e0e0e0; border-radius:8px; margin-bottom:0.5rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <strong>{row.get('company_name', '')}</strong> <span style="color:#757575;">({row.get('ticker_us', '')})</span>
                            {f'<span style="background:#f5f5f5; padding:2px 6px; border-radius:4px; font-size:0.75rem; margin-left:8px;">{cat_label}</span>' if cat_label else ''}
                        </div>
                        <span style="color:#757575; font-size:0.85rem;">{date_str}</span>
                    </div>
                    <p style="margin:0.5rem 0 0 0; color:#424242;">{row.get('title', '')}</p>
                    <a href="{source_url}" target="_blank" style="font-size:0.85rem;">Read More</a>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No press releases found for selected filter.")

    else:
        st.info("News data is being collected. Run the investor news script to populate this section.")
        st.code("python scripts/fetch_investor_news.py", language="bash")

with tab3:
    st.subheader("US Cannabis Regulatory Map")
    st.markdown("Real-time cannabis legalization status across all 50 states")

    # Status summary
    summary = get_status_summary()

    # Metrics row
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        rec_states = len(get_states_by_status(LegalStatus.FULLY_LEGAL))
        st.metric("Recreational", rec_states, help="States with adult-use cannabis")
    with col2:
        med_decrim = len(get_states_by_status(LegalStatus.MEDICAL_DECRIM))
        st.metric("Medical + Decrim", med_decrim)
    with col3:
        med_only = len(get_states_by_status(LegalStatus.MEDICAL_ONLY))
        st.metric("Medical Only", med_only)
    with col4:
        cbd_only = len(get_states_by_status(LegalStatus.CBD_ONLY))
        st.metric("CBD Only", cbd_only)
    with col5:
        decrim = len(get_states_by_status(LegalStatus.DECRIMINALIZED))
        st.metric("Decriminalized", decrim)
    with col6:
        illegal = len(get_states_by_status(LegalStatus.ILLEGAL))
        st.metric("Fully Illegal", illegal)

    st.markdown("---")

    # Create US state map using Plotly choropleth
    import plotly.express as px

    # Prepare data for map
    map_data = []
    for abbr, reg in STATE_REGULATIONS.items():
        map_data.append({
            'state': abbr,
            'state_name': reg.state,
            'status': reg.status.value,
            'status_short': STATUS_LABELS[reg.status],
            'notes': reg.notes,
            'medical_year': reg.medical_year,
            'rec_year': reg.recreational_year,
            'color_code': list(LegalStatus).index(reg.status)
        })

    map_df = pd.DataFrame(map_data)

    # Create choropleth map
    fig = px.choropleth(
        map_df,
        locations='state',
        locationmode='USA-states',
        color='status',
        color_discrete_map={
            LegalStatus.FULLY_LEGAL.value: STATUS_COLORS[LegalStatus.FULLY_LEGAL],
            LegalStatus.MEDICAL_DECRIM.value: STATUS_COLORS[LegalStatus.MEDICAL_DECRIM],
            LegalStatus.MEDICAL_ONLY.value: STATUS_COLORS[LegalStatus.MEDICAL_ONLY],
            LegalStatus.CBD_ONLY.value: STATUS_COLORS[LegalStatus.CBD_ONLY],
            LegalStatus.DECRIMINALIZED.value: STATUS_COLORS[LegalStatus.DECRIMINALIZED],
            LegalStatus.ILLEGAL.value: STATUS_COLORS[LegalStatus.ILLEGAL],
        },
        scope='usa',
        hover_name='state_name',
        hover_data={'status': True, 'notes': True, 'state': False},
        labels={'status': 'Legal Status'},
        title='Cannabis Legalization by State (January 2026)'
    )

    fig.update_layout(
        height=500,
        geo=dict(
            showlakes=True,
            lakecolor='rgb(255, 255, 255)',
        ),
        legend=dict(
            title="Legal Status",
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        )
    )

    st.plotly_chart(fig, use_container_width=True)

    # State details
    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("### Filter by Status")
        status_filter = st.selectbox(
            "Show states with:",
            ["All"] + [s.value for s in LegalStatus],
            key="reg_status_filter"
        )

    with col2:
        st.markdown("### 2026 Ballot Initiatives")
        ballot_col1, ballot_col2 = st.columns(2)
        for i, (state, info) in enumerate(UPCOMING_BALLOTS.items()):
            target_col = ballot_col1 if i % 2 == 0 else ballot_col2
            with target_col:
                reg = STATE_REGULATIONS.get(state)
                st.markdown(f"""
                <div style="background:#fff3e0; padding:0.75rem; border-radius:6px; margin-bottom:0.5rem; border-left:4px solid #ff9800;">
                    <p style="margin:0; font-weight:600;">{reg.state if reg else state} - {info['type']}</p>
                    <p style="margin:0; font-size:0.8rem; color:#666;">{info['description']}</p>
                    <p style="margin:0; font-size:0.75rem; color:#999;">Status: {info['status']}</p>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")

    # State details table
    st.markdown("### State Details")

    if status_filter == "All":
        filtered_states = list(STATE_REGULATIONS.values())
    else:
        filtered_states = [s for s in STATE_REGULATIONS.values() if s.status.value == status_filter]

    state_table_data = []
    for reg in filtered_states:
        state_table_data.append({
            'State': reg.state,
            'Status': STATUS_LABELS[reg.status],
            'Medical Year': reg.medical_year if reg.medical_year else "-",
            'Rec Year': reg.recreational_year if reg.recreational_year else "-",
            'Notes': reg.notes[:80] + "..." if len(reg.notes) > 80 else reg.notes
        })

    if state_table_data:
        st.dataframe(pd.DataFrame(state_table_data), use_container_width=True, hide_index=True, height=400)

    # Investment implications
    st.markdown("---")
    st.markdown("### Investment Implications")

    impl_col1, impl_col2, impl_col3 = st.columns(3)

    with impl_col1:
        st.markdown(f"""
        <div style="background:#e8f5e9; padding:1rem; border-radius:8px;">
            <p style="margin:0 0 0.5rem 0; font-weight:600; color:#2e7d32;">Growth Markets</p>
            <p style="margin:0; font-size:0.85rem; color:#424242;">
            <strong>{rec_states} recreational states</strong> represent the largest addressable market.
            New markets (OH, MN) offer first-mover advantages.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with impl_col2:
        st.markdown(f"""
        <div style="background:#e3f2fd; padding:1rem; border-radius:8px;">
            <p style="margin:0 0 0.5rem 0; font-weight:600; color:#1565c0;">Expansion Opportunities</p>
            <p style="margin:0; font-size:0.85rem; color:#424242;">
            <strong>{med_only} medical-only states</strong> may convert to recreational.
            FL, PA, TX are large population targets.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with impl_col3:
        st.markdown(f"""
        <div style="background:#fff3e0; padding:1rem; border-radius:8px;">
            <p style="margin:0 0 0.5rem 0; font-weight:600; color:#e65100;">Watch List</p>
            <p style="margin:0; font-size:0.85rem; color:#424242;">
            <strong>{len(UPCOMING_BALLOTS)} states</strong> with 2026 ballot initiatives.
            Federal rescheduling to Schedule III pending.
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.caption("Data source: DISA, NCSL, state government websites. Updated January 2026.")

with tab4:
    st.subheader("State Operations")
    st.markdown("Track which states each company operates in and their *owned* retail footprint (company-operated dispensaries)")

    if DEMO_MODE:
        state_ops = get_demo_state_operations()
    else:
        state_ops = load_state_operations()

    if not state_ops.empty:
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            companies_with_ops = state_ops['name'].nunique()
            st.metric("Companies Tracked", companies_with_ops)
        with col2:
            total_states = state_ops['state'].nunique()
            st.metric("States Covered", total_states)
        with col3:
            total_stores = state_ops['store_count'].sum()
            st.metric("Total Store Locations", f"{int(total_stores):,}")
        with col4:
            total_skus = state_ops['sku_count'].sum()
            st.metric("Total SKUs Tracked", f"{int(total_skus):,}")

        # Company selector for detailed view
        st.markdown("---")
        st.markdown("### Company State Footprint")

        company_names = sorted(state_ops['name'].unique())
        selected_company = st.selectbox("Select Company", company_names, key="state_ops_company")

        company_ops = state_ops[state_ops['name'] == selected_company]
        if not company_ops.empty:
            col1, col2 = st.columns([2, 1])

            with col1:
                # Create state presence table
                ops_display = company_ops[['state', 'store_count', 'sku_count']].copy()
                ops_display.columns = ['State', 'Store Count', 'SKU Count']
                st.dataframe(ops_display, use_container_width=True, hide_index=True)

                # Bar chart by state
                fig = px.bar(company_ops, x='state', y='store_count',
                            color='sku_count', color_continuous_scale='Greens',
                            labels={'state': 'State', 'store_count': 'Stores', 'sku_count': 'SKUs'},
                            title=f"{selected_company} - Stores by State")
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Summary for selected company
                total_states = len(company_ops)
                total_stores = company_ops['store_count'].sum()
                total_skus = company_ops['sku_count'].sum()

                st.markdown(f"**{selected_company}**")
                st.metric("States Active", total_states)
                st.metric("Total Stores", f"{int(total_stores):,}")
                st.metric("Total SKUs", f"{int(total_skus):,}")
                avg_stores = total_stores / total_states if total_states > 0 else 0
                st.metric("Avg Stores/State", f"{avg_stores:.1f}")

        # Comparison heatmap
        st.markdown("---")
        st.markdown("### Multi-Company State Comparison")

        # Create pivot table for store presence
        pivot = state_ops.pivot_table(
            index='name',
            columns='state',
            values='store_count',
            aggfunc='sum',
            fill_value=0
        )

        if not pivot.empty:
            fig = px.imshow(
                pivot,
                labels=dict(x="State", y="Company", color="Store Count"),
                color_continuous_scale='Greens',
                aspect='auto'
            )
            fig.update_layout(height=400, title="Retail Presence by State (Store Count)")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("State operations data is being compiled.")

        demo_ops = pd.DataFrame({
            'Company': ['Curaleaf', 'Curaleaf', 'Curaleaf', 'GTI', 'GTI', 'GTI', 'Trulieve', 'Trulieve'],
            'State': ['FL', 'NY', 'NJ', 'IL', 'PA', 'OH', 'FL', 'PA'],
            'Retail': ['Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes'],
            'Cultivation': ['Yes', 'Yes', '', 'Yes', 'Yes', '', 'Yes', 'Yes'],
            'Processing': ['Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes'],
            'Store Count': [62, 15, 12, 18, 22, 8, 147, 28]
        })
        st.dataframe(demo_ops, use_container_width=True, hide_index=True)

with tab5:
    st.subheader("Stock Price Charts")

    # Company selector
    company_options = dict(zip(companies['name'] + ' (' + companies['ticker_us'].fillna(companies['ticker_ca']) + ')',
                               companies['name']))  # Use name as key for demo data compatibility
    selected_stock_company = st.selectbox("Select Company", list(company_options.keys()), key="stock_company")

    if selected_stock_company:
        company_name = company_options[selected_stock_company]

        # Time range selector
        col1, col2 = st.columns([1, 4])
        with col1:
            days = st.selectbox("Time Range", [30, 60, 90, 180, 365], index=2,
                               format_func=lambda x: f"{x} days")

        if DEMO_MODE:
            prices = get_demo_stock_history(company_name, days)
        else:
            company_id = companies[companies['name'] == company_name]['company_id'].iloc[0]
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
                title=f"{company_name} - Stock Price",
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
        default=list(company_options.keys())[:5]  # Default to first 5 companies
    )

    if compare_companies:
        comparison_data = []
        for comp_display_name in compare_companies:
            comp_name = company_options[comp_display_name]
            if DEMO_MODE:
                comp_prices = get_demo_stock_history(comp_name, 90)
            else:
                comp_id = companies[companies['name'] == comp_name]['company_id'].iloc[0]
                comp_prices = load_stock_prices(comp_id, 90)

            if not comp_prices.empty:
                # Normalize to 100 at start
                comp_prices['normalized'] = (comp_prices['close_price'] / comp_prices['close_price'].iloc[0]) * 100
                comp_prices['company'] = comp_display_name.split(' (')[0]  # Short name
                comparison_data.append(comp_prices[['price_date', 'normalized', 'company']])

        if comparison_data:
            combined = pd.concat(comparison_data)
            fig = px.line(combined, x='price_date', y='normalized', color='company',
                         labels={'price_date': 'Date', 'normalized': 'Normalized Price (Base=100)', 'company': 'Company'})
            fig.update_layout(height=400, title="90-Day Relative Performance (Normalized to 100)")
            st.plotly_chart(fig, use_container_width=True)

with tab6:
    st.subheader("Financial Metrics")

    if DEMO_MODE:
        financials = get_demo_financials()
    else:
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
                    # Handle None values in market_cap_millions for size parameter
                    scatter_df['bubble_size'] = scatter_df['market_cap_millions'].fillna(100)
                    scatter_df['bubble_size'] = scatter_df['bubble_size'].apply(lambda x: max(float(x), 10))

                    fig = px.scatter(scatter_df, x='revenue_millions', y='net_income_millions',
                                    size='bubble_size', hover_name='name',
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

with tab7:
    st.subheader("Shelf Analytics")
    st.markdown("Track public company brand presence across retail dispensaries. This shows stores *carrying* brands (based on menu data), which differs from stores *owned* by each company shown in State Operations.")

    if DEMO_MODE:
        shelf_data = get_demo_shelf_analytics()
        is_demo = True
    else:
        shelf_data = load_shelf_analytics()
        is_demo = False
        # Transform to match demo format if needed
        if not shelf_data.empty and 'name' in shelf_data.columns:
            shelf_data = shelf_data.rename(columns={'name': 'company', 'total_skus': 'sku_count'})

    if not shelf_data.empty:
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            companies_tracked = shelf_data['company'].nunique() if 'company' in shelf_data.columns else len(shelf_data)
            st.metric("Companies Tracked", companies_tracked)
        with col2:
            if 'brand' in shelf_data.columns:
                total_brands = shelf_data['brand'].nunique()
            elif 'brand_count' in shelf_data.columns:
                total_brands = shelf_data['brand_count'].sum()
            else:
                total_brands = 0
            st.metric("Brands Tracked", int(total_brands))
        with col3:
            total_stores = shelf_data['store_count'].sum() if 'store_count' in shelf_data.columns else 0
            st.metric("Total Store Presence", f"{int(total_stores):,}")
        with col4:
            sku_col = 'sku_count' if 'sku_count' in shelf_data.columns else 'total_skus'
            total_skus = shelf_data[sku_col].sum() if sku_col in shelf_data.columns else 0
            st.metric("Total SKUs", f"{int(total_skus):,}")

        # Brand performance table - display format depends on data source
        st.markdown("### Brand Performance by Company")
        if is_demo and 'brand' in shelf_data.columns:
            shelf_display = shelf_data.copy()
            shelf_display['avg_price'] = shelf_display['avg_price'].apply(lambda x: f"${x:.2f}")
            shelf_display['market_share'] = shelf_display['market_share'].apply(lambda x: f"{x:.1f}%")
            shelf_display.columns = ['Company', 'Brand', 'Category', 'Avg Price', 'Store Count', 'SKU Count', 'Market Share']
            st.dataframe(shelf_display, use_container_width=True, hide_index=True)
        else:
            # Real data format - company-level summary
            display_cols = ['company', 'ticker_us', 'store_count', 'sku_count', 'brand_count', 'penetration_pct']
            display_cols = [c for c in display_cols if c in shelf_data.columns]
            shelf_display = shelf_data[display_cols].copy()
            col_names = {'company': 'Company', 'ticker_us': 'Ticker', 'store_count': 'Stores Carrying',
                        'sku_count': 'SKU Count', 'brand_count': 'Brands', 'penetration_pct': 'Penetration %'}
            shelf_display = shelf_display.rename(columns=col_names)
            st.dataframe(shelf_display, use_container_width=True, hide_index=True)

        # Visualizations - only show if we have the right columns
        if is_demo and 'market_share' in shelf_data.columns and 'brand' in shelf_data.columns:
            # Market share visualization (demo mode with brand-level data)
            st.markdown("### Market Share by Brand")
            fig = px.bar(shelf_data.sort_values('market_share', ascending=True),
                        x='market_share', y='brand', orientation='h',
                        color='company',
                        labels={'market_share': 'Market Share (%)', 'brand': '', 'company': 'Company'},
                        title="Brand Market Share")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

        # Store presence by company
        st.markdown("### Store Presence by Company")
        if is_demo and 'brand' in shelf_data.columns:
            company_summary = shelf_data.groupby('company').agg({
                'store_count': 'sum',
                'sku_count': 'sum',
                'brand': 'count'
            }).reset_index()
            company_summary.columns = ['Company', 'Total Store Presence', 'Total SKUs', 'Brand Count']
        else:
            # Real data format
            company_summary = shelf_data[['company', 'store_count', 'sku_count']].copy()
            if 'brand_count' in shelf_data.columns:
                company_summary['Brand Count'] = shelf_data['brand_count']
            else:
                company_summary['Brand Count'] = 1
            company_summary.columns = ['Company', 'Total Store Presence', 'Total SKUs', 'Brand Count']

        fig = px.bar(company_summary.sort_values('Total Store Presence', ascending=True),
                    x='Total Store Presence', y='Company', orientation='h',
                    color='Total SKUs', color_continuous_scale='Greens',
                    title="Company Retail Footprint (Stores Carrying Their Brands)")
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

        # Insights
        st.markdown("### Key Insights")
        col1, col2 = st.columns(2)

        if is_demo and 'market_share' in shelf_data.columns and 'brand' in shelf_data.columns:
            with col1:
                top_brand = shelf_data.loc[shelf_data['market_share'].idxmax()]
                st.markdown(f"""
                <div style="background:#e8f5e9; padding:1rem; border-radius:8px; margin-bottom:1rem;">
                    <p style="margin:0 0 0.5rem 0; font-weight:600; color:#2e7d32;">Top Brand by Market Share</p>
                    <p style="margin:0; font-size:1.2rem; color:#1b5e20;"><strong>{top_brand['brand']}</strong> ({top_brand['company']})</p>
                    <p style="margin:0; font-size:0.85rem; color:#424242;">{top_brand['market_share']:.1f}% market share in {top_brand['category']}</p>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                top_presence = shelf_data.loc[shelf_data['store_count'].idxmax()]
                st.markdown(f"""
                <div style="background:#e3f2fd; padding:1rem; border-radius:8px; margin-bottom:1rem;">
                    <p style="margin:0 0 0.5rem 0; font-weight:600; color:#1565c0;">Widest Store Presence</p>
                    <p style="margin:0; font-size:1.2rem; color:#0d47a1;"><strong>{top_presence['brand']}</strong> ({top_presence['company']})</p>
                    <p style="margin:0; font-size:0.85rem; color:#424242;">{int(top_presence['store_count']):,} stores carrying {int(top_presence['sku_count'])} SKUs</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            # Real data - show company-level insights
            if 'store_count' in shelf_data.columns and len(shelf_data) > 0:
                top_company = shelf_data.loc[shelf_data['store_count'].idxmax()]
                with col1:
                    st.markdown(f"""
                    <div style="background:#e8f5e9; padding:1rem; border-radius:8px; margin-bottom:1rem;">
                        <p style="margin:0 0 0.5rem 0; font-weight:600; color:#2e7d32;">Top Company by Penetration</p>
                        <p style="margin:0; font-size:1.2rem; color:#1b5e20;"><strong>{top_company['company']}</strong></p>
                        <p style="margin:0; font-size:0.85rem; color:#424242;">{top_company.get('penetration_pct', 0):.1f}% of stores carry their brands</p>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    st.markdown(f"""
                    <div style="background:#e3f2fd; padding:1rem; border-radius:8px; margin-bottom:1rem;">
                        <p style="margin:0 0 0.5rem 0; font-weight:600; color:#1565c0;">Widest Store Presence</p>
                        <p style="margin:0; font-size:1.2rem; color:#0d47a1;"><strong>{top_company['company']}</strong></p>
                        <p style="margin:0; font-size:0.85rem; color:#424242;">{int(top_company['store_count']):,} stores carrying {int(top_company.get('sku_count', 0))} SKUs</p>
                    </div>
                    """, unsafe_allow_html=True)

    else:
        st.info("Shelf analytics data is being compiled. Check back soon for brand performance metrics.")

# Footer
st.markdown("---")
st.caption("Data sources: SEC EDGAR (filings), Company IR websites (press releases), Yahoo Finance (stock prices)")
