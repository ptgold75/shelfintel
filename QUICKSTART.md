# ShelfIntel / CannLinx Quick Start Guide

## Project Overview

ShelfIntel (CannLinx) is a multi-state shelf intelligence platform for the cannabis industry. It tracks products, prices, and availability across dispensaries in Maryland, New Jersey, Illinois, and expanding markets.

## Current Coverage (January 2026)

| State | Stores w/ Data | Products | Status |
|-------|----------------|----------|--------|
| MD | 85 | 43,500+ | Primary market |
| IL | 45 | 32,000+ | Active |
| NJ | 44 | 30,500+ | Active |
| CO | 27 | 17,700+ | Active |
| OR | 26 | 7,800+ | Active |
| MI | 23 | 6,700+ | Active |
| + 16 more | ~205 | ~29,000+ | Expanding |
| **TOTAL** | **455+** | **167,000+** | Growing |

**Database Totals**: 19,520 dispensaries tracked, 22 states with coverage

## Directory Structure

```
shelfintel/
├── app/                      # Streamlit web application
│   ├── Home.py               # Main homepage with stats & registration
│   ├── static/               # Images, CSS
│   │   └── cannalinx_banner.png
│   ├── components/
│   │   ├── nav.py            # Navigation with dropdown menus
│   │   └── auth.py           # Authentication & client management
│   └── pages/                # App pages
│       ├── 10_Brand_Intelligence.py     # Brand dashboard
│       ├── 20_Retail_Intelligence.py    # Dispensary dashboard
│       ├── 30_Grower_Intelligence.py    # Cultivator dashboard
│       ├── 40_Investor_Intelligence.py  # Public company tracking
│       ├── 90_Admin_Clients.py          # Client management
│       └── ...
├── core/                     # Core utilities
│   ├── db.py                 # Database connection (Supabase)
│   └── category_utils.py     # Category normalization
├── ingest/                   # Data ingestion
│   ├── run_scrape.py         # Main scraper orchestrator
│   └── providers/            # Menu scraping providers
├── scripts/                  # Utility scripts
│   ├── fetch_stock_prices.py      # Yahoo Finance stock data
│   ├── fetch_sec_filings.py       # SEC EDGAR parser
│   ├── import_state_dispensaries.py
│   ├── scrape_dutchie_batch_v2.py # Fast Dutchie GraphQL scraper
│   ├── scrape_leafly_and_import.py # Leafly dispensary discovery
│   └── scrape_leafly_menus.py     # Leafly menu scraper
├── .env                      # Proxy credentials (do not commit)
├── .streamlit/
│   ├── config.toml           # Streamlit config
│   └── secrets.toml          # DATABASE_URL (do not commit)
└── QUICKSTART.md             # This file
```

## Quick Start

### 1. Environment Setup
```bash
cd /Users/gleaf/shelfintel
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuration Files

**`.env` (Proxy for Cloudflare bypass)**
```
PROXY_HOST=gate.decodo.com
PROXY_PORT=10001
PROXY_USER=spn1pjbpd4
PROXY_PASS=k0xH_iq29reyWfz3JR
```

**`.streamlit/secrets.toml` (Database)**
```toml
DATABASE_URL="postgresql+psycopg://postgres:Tattershall2020@db.trteltlgtmcggdbrqwdw.supabase.co:5432/postgres?sslmode=require"
```

### 3. Run the App
```bash
source .venv/bin/activate
streamlit run app/Home.py --server.port 8501
```
Open http://localhost:8501

---

## Navigation Structure

| Menu | Pages | Description |
|------|-------|-------------|
| **Home** | Landing page | Stats, registration form |
| **Brands** | Brand Intelligence, Brand Assets | Performance, distribution, images |
| **Retail** | Retail Intelligence, Availability | Competitive analysis, pricing |
| **Growers** | Grower Intelligence | Category trends, strain rankings |
| **Tools** | Product Search, Price Analysis | Search, compare, analyze |
| **Investors** | Investor Intelligence | Public companies, stocks, financials |
| **Admin** | Dispensaries, Naming, Clients | Admin-only management |

---

## Authentication System

### User Types

| Type | Access |
|------|--------|
| **Public** | Demo mode - sample data only |
| **Client** | Real data for permitted states |
| **Admin** | All states + admin pages |

### Demo Mode Pattern

```python
from components.auth import is_authenticated

DEMO_MODE = not is_authenticated()

if DEMO_MODE:
    st.info("Demo Mode - Login for full access")
    companies = get_demo_companies()  # Sample data
else:
    companies = load_companies()      # Real database
```

### State Filtering

```python
from components.nav import render_state_filter

# Show state dropdown (filtered by user permissions)
state = render_state_filter()
if not state:
    st.warning("No states available")
    st.stop()

# Use in queries
query = "SELECT * FROM dispensary WHERE state = :state"
```

---

## Database Schema (Key Tables)

```sql
-- Dispensaries
dispensary (
    dispensary_id UUID PRIMARY KEY,
    name VARCHAR,
    state VARCHAR(2),
    address VARCHAR, city VARCHAR, county VARCHAR, zip VARCHAR,
    phone VARCHAR, email VARCHAR,
    menu_url TEXT,
    menu_provider VARCHAR,  -- dutchie, jane, sweed, etc.
    is_active BOOLEAN
)

-- Raw Menu Items (scraped product data)
raw_menu_item (
    raw_menu_item_id UUID PRIMARY KEY,
    scrape_run_id UUID,
    dispensary_id UUID,
    observed_at TIMESTAMP,
    raw_name TEXT,
    raw_category VARCHAR,
    raw_brand VARCHAR,
    raw_price DECIMAL
)

-- Public Companies (Investor Intelligence)
public_company (
    company_id UUID PRIMARY KEY,
    name VARCHAR,
    ticker_us VARCHAR,
    ticker_ca VARCHAR,
    company_type VARCHAR,  -- MSO, LP
    market_cap_millions DECIMAL
)

-- Stock Prices
stock_price (
    company_id UUID,
    price_date DATE,
    open_price DECIMAL,
    high_price DECIMAL,
    low_price DECIMAL,
    close_price DECIMAL,
    volume BIGINT
)

-- Clients (Authentication)
client (
    client_id UUID PRIMARY KEY,
    company_name VARCHAR,
    contact_email VARCHAR,
    password_hash VARCHAR,
    is_admin BOOLEAN,
    allowed_states TEXT[]  -- ['MD', 'NJ', 'IL']
)
```

---

## Intelligence Dashboards

### Brand Intelligence (`10_Brand_Intelligence.py`)
- Competitive gap analysis
- Store distribution visualization
- County coverage map
- Category filtering
- Size-aware price comparisons

### Retail Intelligence (`20_Retail_Intelligence.py`)
- Competitor price comparison
- Assortment gap analysis
- Category mix optimization
- Actionable insights

### Grower Intelligence (`30_Grower_Intelligence.py`)
- Strain popularity rankings
- Category trend analysis
- Price benchmarking
- Size distribution

### Investor Intelligence (`40_Investor_Intelligence.py`)
- Public company tracking (10 MSOs/LPs)
- Stock charts with candlestick view
- Financial metrics comparison
- State operations footprint
- Shelf analytics (brand penetration)

---

## Menu Providers

| Provider | Stores w/ Data | Notes |
|----------|----------------|-------|
| Dutchie | ~200+ | GraphQL via Playwright, use `scrape_dutchie_batch_v2.py` |
| Leafly | ~100+ | Playwright scraper, use `scrape_leafly_and_import.py` for discovery |
| Sweed | ~50 | JSON API, gLeaf and similar |
| Jane | ~40 | JSON API, Cloudflare blocks some |
| Weedmaps | ~10 | API changes frequently |

---

## Scraping Commands

### Dutchie Batch Scraper (Recommended)
```bash
# Scrape specific states (fast, reliable)
./venv/bin/python scripts/scrape_dutchie_batch_v2.py OR CA WA

# Run multiple state groups in parallel for speed
./venv/bin/python scripts/scrape_dutchie_batch_v2.py FL PA OH &
./venv/bin/python scripts/scrape_dutchie_batch_v2.py NY MA ME CT &
./venv/bin/python scripts/scrape_dutchie_batch_v2.py CA CO MI AZ NV &
```

### Leafly Dispensary Discovery
```bash
# Find and import new dispensaries from Leafly
./venv/bin/python scripts/scrape_leafly_and_import.py
```

### Legacy Scraper
```bash
./venv/bin/python ingest/run_scrape.py --state MD
./venv/bin/python ingest/run_scrape.py --all
```

### Fetch Stock Prices
```bash
./venv/bin/python scripts/fetch_stock_prices.py
```

### Fetch SEC Filings
```bash
./venv/bin/python scripts/fetch_sec_filings.py
```

---

## Key Code Patterns

### Category Normalization
```python
from core.category_utils import get_normalized_category_sql

# Returns SQL CASE statement for category mapping
category_sql = get_normalized_category_sql('raw_category')
# Maps: 'flower', 'bud' -> 'Flower'
#       'pre-roll', 'preroll' -> 'Pre-Rolls'
#       etc.
```

### Size Extraction (Price Comparisons)
```python
def extract_size_from_name(name: str) -> str:
    """Extract size/weight from product name."""
    # Returns: "3.5g", "7g", "14g", "28g", "100mg", "5pk", "std"
```

### PostgreSQL Array Parameters
```python
# WRONG: WHERE state IN :states  -- syntax error
# RIGHT: WHERE state = ANY(:states)
conn.execute(text("WHERE state = ANY(:states)"), {"states": ['MD', 'NJ']})
```

---

## Useful Commands

### Check Database Status
```bash
./venv/bin/python -c "
from core.db import get_engine
from sqlalchemy import text
engine = get_engine()
with engine.connect() as conn:
    stores = conn.execute(text('SELECT COUNT(*) FROM dispensary WHERE is_active = true')).scalar()
    products = conn.execute(text('SELECT COUNT(*) FROM raw_menu_item')).scalar()
    states = conn.execute(text('SELECT COUNT(DISTINCT state) FROM dispensary WHERE is_active = true')).scalar()
    print(f'Stores: {stores}, Products: {products:,}, States: {states}')
"
```

### Check Stores by State
```bash
./venv/bin/python -c "
from core.db import get_engine
from sqlalchemy import text
engine = get_engine()
with engine.connect() as conn:
    result = conn.execute(text('''
        SELECT state, COUNT(*) FROM dispensary
        WHERE is_active = true GROUP BY state ORDER BY COUNT(*) DESC
    '''))
    for row in result: print(f'{row[0]}: {row[1]} stores')
"
```

### Test Proxy Connection
```bash
./venv/bin/python -c "
import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            proxy={
                'server': 'http://gate.decodo.com:10002',
                'username': 'spn1pjbpd4',
                'password': 'k0xH_iq29reyWfz3JR'
            }
        )
        page = await browser.new_page()
        await page.goto('https://httpbin.org/ip')
        print(await page.content())
        await browser.close()

asyncio.run(test())
"
```

---

## Known Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Cloudflare blocks | Direct dutchie URLs blocked | Use proxy or Weedmaps fallback |
| Only ~25 products | Only first page loaded | Navigate to each category URL |
| Proxy rate limits | Port saturated | Rotate ports 10002-10010 |
| Demo data only | Not authenticated | Login for real data |

---

## Common Fixes

| Issue | Fix |
|-------|-----|
| `NoneType format` errors | Add `or 0`: `value = metrics.get('field') or 0` |
| `IN :param` syntax error | Use `= ANY(:param)` for PostgreSQL |
| State filter empty | Check `get_user_allowed_states()` permissions |
| Page spinning forever | Use `pg_class` for large table counts |

---

## Credentials Reference

| Service | Host | User | Password |
|---------|------|------|----------|
| Supabase DB | db.trteltlgtmcggdbrqwdw.supabase.co | postgres | Tattershall2020 |
| Decodo Proxy | gate.decodo.com | spn1pjbpd4 | k0xH_iq29reyWfz3JR |

---

## Data Sources

- **Dispensary Menus**: Scraped from individual store websites
- **State Data**: Official state cannabis commission data
- **Stock Prices**: Yahoo Finance API
- **SEC Filings**: SEC EDGAR
- **Fallback**: Weedmaps public API

---

*Last updated: January 2026*
