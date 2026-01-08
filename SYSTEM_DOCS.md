# ShelfIntel / CannLinx - System Documentation

## Quick Start

```bash
# 1. Activate virtual environment
cd /Users/gleaf/shelfintel
source venv/bin/activate

# 2. Run the Streamlit app
./venv/bin/python -m streamlit run app/Home.py --server.port 8501

# 3. Run scrapers
./venv/bin/python ingest/run_scrape.py --state NJ    # Scrape specific state
./venv/bin/python ingest/run_scrape.py --all          # Scrape all states
```

Open http://localhost:8501

---

## Current Coverage (January 2026)

### Store Classification

| Type | Count | Description |
|------|-------|-------------|
| **Dispensary** | 13,628 | Verified licensed cannabis dispensaries |
| **Smoke Shop** | 1,336 | CBD, Delta-8, THCA, kratom stores |
| **Unverified** | 897 | Pending verification or gray market |
| **TOTAL** | ~15,861 | Active locations across 50 states |

### Top States by Licensed Dispensary Count

| State | Dispensaries | Smoke Shops | Official Count |
|-------|--------------|-------------|----------------|
| CA | 1,684 | 63 | ~1,800 |
| OK | 1,417 | 61 | ~2,000 |
| MI | 973 | 18 | ~600 |
| NY | 968 | 63 | ~556 |
| FL | 756 | 85 | ~700 |
| CO | 682 | 18 | ~700 |
| NM | 680 | 11 | ~400 |
| OR | 615 | 25 | ~600 |
| IL | 504 | 30 | ~200 |
| OH | 216 | 25 | ~190 |
| PA | 195 | 24 | ~192 |
| NJ | 382 | 22 | ~150 |

### Data Fields Available

| Field | Coverage | Description |
|-------|----------|-------------|
| Company Name | 100% | Official business name |
| Street Address | 100% | Full street address |
| City | 100% | City/municipality |
| State | 100% | State code |
| ZIP Code | 95%+ | Postal code |
| County | 90%+ | County name |
| Phone Number | 15-63% | Business phone (varies by state) |
| Email Address | Where available | Contact email |
| Website URL | 48-97% | Menu or company website |
| Menu Provider | Where detected | Dutchie, Jane, Leafly, etc. |
| Store Type | 100% | dispensary, smoke_shop, or unverified |

---

## Project Structure

```
shelfintel/
├── app/                          # Streamlit application
│   ├── Home.py                   # Main homepage
│   ├── components/
│   │   ├── nav.py               # Navigation & auth wrapper
│   │   └── auth.py              # Authentication logic
│   └── pages/
│       ├── 1_Dashboard.py        # Market overview
│       ├── 2_Availability.py     # Product availability
│       ├── 6_Price_Analysis.py   # Price comparisons
│       ├── 7_Brand_Analytics.py  # Brand performance
│       ├── 9_Product_Search.py   # Search products
│       ├── 40_Investor_Intelligence.py  # Public company tracking
│       ├── 50_Smoke_Shop_Intelligence.py # Gray market dashboard
│       ├── 90_Admin_Clients.py   # Client management
│       ├── 96_Admin_Coverage.py  # Coverage tracker
│       └── 99_Data_Licensing.py  # Data sales page
├── core/
│   ├── db.py                    # Database connection
│   └── category_utils.py        # Category normalization
├── ingest/
│   ├── run_scrape.py            # Main scraper orchestrator
│   └── providers/
│       ├── dutchie_provider.py  # Dutchie GraphQL
│       ├── jane_provider.py     # iHeartJane API
│       ├── sweed_provider.py    # Sweed API
│       └── smoke_shop_provider.py # CBD/smoke shop scraper
├── scripts/
│   ├── fetch_stock_prices.py    # Yahoo Finance stock prices
│   └── fetch_sec_filings.py     # SEC EDGAR parser
└── venv/                        # Python 3.9 virtual environment
```

---

## Database Schema (Supabase PostgreSQL)

### dispensary
```sql
dispensary (
    dispensary_id UUID PRIMARY KEY,
    name VARCHAR(255),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(2),
    zip VARCHAR(20),
    county VARCHAR(100),
    phone VARCHAR(50),
    email VARCHAR(255),
    menu_url TEXT,
    menu_provider VARCHAR(50),   -- dutchie, jane, sweed, leafly, etc.
    store_type VARCHAR(50),      -- dispensary, smoke_shop, unverified
    source VARCHAR(50),          -- pa_doh, ny_ocm, google_csv, leafly, etc.
    is_active BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
```

### raw_menu_item
```sql
raw_menu_item (
    raw_menu_item_id UUID PRIMARY KEY,
    scrape_run_id UUID,
    dispensary_id UUID,
    observed_at TIMESTAMP,
    raw_name TEXT,
    raw_category VARCHAR(100),
    raw_brand VARCHAR(255),
    raw_price DECIMAL,
    raw_thc VARCHAR(50),
    raw_cbd VARCHAR(50)
)
```

### public_company
```sql
public_company (
    company_id UUID PRIMARY KEY,
    name VARCHAR(255),
    ticker_us VARCHAR(20),
    ticker_ca VARCHAR(20),
    exchange_us VARCHAR(50),
    exchange_ca VARCHAR(50),
    company_type VARCHAR(50),   -- MSO, LP, REIT, Tech
    cik VARCHAR(20),
    market_cap_millions DECIMAL,
    headquarters VARCHAR(100),
    website VARCHAR(255),
    is_active BOOLEAN
)
```

---

## Database Connection

```python
# Host: db.trteltlgtmcggdbrqwdw.supabase.co
# Port: 5432
# SSL: required
```

Credentials in: `app/.streamlit/secrets.toml`

---

## Menu Provider Types

| Provider | API Type | Count | Notes |
|----------|----------|-------|-------|
| Sweed | REST API | ~1,400 | Most common, needs store_id |
| Dutchie | GraphQL | ~1,200 | Needs retailer_id, Cloudflare issues |
| Leafly | HTML/API | ~900 | Scraping supported |
| Jane | REST API | ~430 | Needs store_id, Cloudflare issues |
| Weedmaps | REST API | ~300 | Planned scraper |

---

## Running Scrapers

### Scrape by State
```bash
./venv/bin/python ingest/run_scrape.py --state NJ
./venv/bin/python ingest/run_scrape.py --state OH
```

### Scrape All States
```bash
./venv/bin/python ingest/run_scrape.py --all
```

### Scrape Single Dispensary
```bash
./venv/bin/python ingest/run_scrape.py --disp-id <UUID>
```

### Scrape Smoke Shops
```python
from ingest.providers.smoke_shop_provider import fetch_menu_items
items = fetch_menu_items('https://shopcbdkratom.com/')
print(f'Found {len(items)} products')
```

---

## Data Licensing ($2,500 per State)

Each state dataset includes:
- Company Name (100%)
- Street Address (100%)
- City, State, ZIP (100%)
- County (90%+)
- Phone Number (varies)
- Website URL (varies)
- Store Type classification

See `/Data_Licensing` page in the app for details.

---

## Key Pages

| Page | URL Path | Description |
|------|----------|-------------|
| Dashboard | /Dashboard | Market overview with charts |
| Product Search | /Product_Search | Search across all menus |
| Price Analysis | /Price_Analysis | Price comparisons by category |
| Brand Analytics | /Brand_Analytics | Brand performance metrics |
| Smoke Shop Intelligence | /Smoke_Shop_Intelligence | Gray market dashboard |
| Investor Intelligence | /Investor_Intelligence | Public company tracking |
| Data Licensing | /Data_Licensing | Purchase state data |
| Admin Coverage | /Admin_Coverage | Scraping coverage stats |

---

## Official State Data Sources

| State | Source | URL |
|-------|--------|-----|
| PA | PA DOH | pa.gov/health/medical-marijuana |
| NY | NY OCM | cannabis.ny.gov |
| OH | Ohio DCC | com.ohio.gov/cannabis-control |
| NJ | NJ CRC | nj.gov/cannabis |

---

## Useful Commands

### Check Database Status
```bash
./venv/bin/python -c "
from core.db import get_engine
from sqlalchemy import text
engine = get_engine()
with engine.connect() as conn:
    disp = conn.execute(text('SELECT COUNT(*) FROM dispensary WHERE is_active = true')).scalar()
    prods = conn.execute(text('SELECT COUNT(*) FROM raw_menu_item')).scalar()
    print(f'Dispensaries: {disp:,}, Products: {prods:,}')
"
```

### Check Coverage by State
```bash
./venv/bin/python -c "
from core.db import get_engine
from sqlalchemy import text
engine = get_engine()
with engine.connect() as conn:
    result = conn.execute(text('''
        SELECT state, store_type, COUNT(*)
        FROM dispensary WHERE is_active = true
        GROUP BY state, store_type
        ORDER BY state, store_type
    '''))
    for row in result: print(f'{row[0]} | {row[1]}: {row[2]}')
"
```

### Update Store Type Classification
```bash
./venv/bin/python -c "
from core.db import get_engine
from sqlalchemy import text
engine = get_engine()
with engine.connect() as conn:
    # Mark CBD/hemp stores as smoke_shop
    result = conn.execute(text('''
        UPDATE dispensary SET store_type = 'smoke_shop'
        WHERE store_type = 'dispensary'
        AND (LOWER(name) LIKE '%cbd%' OR LOWER(name) LIKE '%hemp%')
    '''))
    conn.commit()
    print(f'Updated {result.rowcount} entries')
"
```

---

## Proxy Configuration (Cloudflare Bypass)

For Dutchie/Jane stores blocked by Cloudflare:

```python
# Decodo Residential Proxies
PROXY_HOST = 'gate.decodo.com'
PROXY_USER = 'spn1pjbpd4'
PROXY_PASS = 'k0xH_iq29reyWfz3JR'
PROXY_PORTS = range(10001, 10011)  # Rotate for rate limiting
```

---

## Contact

- **Support**: support@cannlinx.com
- **Sales**: sales@cannlinx.com
- **Data Licensing**: $2,500 per state

---

*Last updated: January 2026*
