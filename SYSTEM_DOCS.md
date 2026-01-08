# ShelfIntel / CannLinx - System Documentation

## Quick Start

```bash
# Activate virtual environment
cd /Users/gleaf/shelfintel
source venv/bin/activate

# Run the Streamlit app
./venv/bin/python -m streamlit run app/Home.py --server.port 8501

# Run scrapers
./venv/bin/python ingest/run_scrape.py --state NJ    # Scrape specific state
./venv/bin/python ingest/run_scrape.py --all          # Scrape all
```

## Project Structure

```
shelfintel/
├── app/                          # Streamlit application
│   ├── Home.py                   # Main homepage
│   ├── components/
│   │   ├── nav.py               # Navigation & auth wrapper
│   │   └── auth.py              # Authentication logic
│   └── pages/
│       ├── 10_Brand_Intelligence.py
│       ├── 20_Retail_Intelligence.py
│       ├── 30_Grower_Intelligence.py
│       ├── 40_Investor_Intelligence.py   # Public company tracking
│       ├── 90_Admin_Clients.py
│       ├── 91_Login.py
│       └── 92_Logout.py
├── core/
│   ├── db.py                    # Database connection (SQLAlchemy)
│   └── models.py                # ORM models
├── ingest/                       # Data scraping
│   ├── run_scrape.py            # Main scraper orchestrator
│   ├── providers/
│   │   ├── dutchie_provider.py  # Dutchie API
│   │   ├── jane_provider.py     # iHeartJane API
│   │   ├── sweed_provider.py    # Sweed API
│   │   └── generic_html.py      # Generic HTML scraper
│   └── availability.py          # Product availability tracking
├── scripts/
│   ├── fetch_stock_prices.py    # Yahoo Finance stock prices
│   ├── fetch_sec_filings.py     # SEC EDGAR 10-K/10-Q parser
│   └── import_state_dispensaries.py
└── venv/                         # Python 3.9 virtual environment
```

## Database Schema (Supabase PostgreSQL)

### Core Tables

```sql
-- Dispensaries
dispensary (
    dispensary_id UUID PRIMARY KEY,
    name VARCHAR(255),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(2),
    county VARCHAR(100),
    phone VARCHAR(50),
    menu_url TEXT,
    menu_provider VARCHAR(50),  -- dutchie, jane, sweed, etc.
    is_active BOOLEAN,
    source VARCHAR(50),         -- state_database, leafly, google_places_csv, etc.
    store_type VARCHAR(50)      -- dispensary, smoke_shop, unverified
)

-- Menu items (raw scraped data)
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

-- Scrape tracking
scrape_run (
    scrape_run_id UUID PRIMARY KEY,
    dispensary_id UUID,
    status VARCHAR(20),
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    records_found INT,
    error_message TEXT
)
```

### Authentication Tables

```sql
-- Clients (companies using the platform)
client (
    client_id UUID PRIMARY KEY,
    company_name VARCHAR(255),
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    is_admin BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true
)

-- State permissions per client
client_state_permission (
    client_id UUID,
    state VARCHAR(2),
    PRIMARY KEY (client_id, state)
)
```

### Investor Intelligence Tables

```sql
-- Public cannabis companies
public_company (
    company_id UUID PRIMARY KEY,
    name VARCHAR(255),
    ticker_us VARCHAR(20),
    ticker_ca VARCHAR(20),
    exchange_us VARCHAR(50),
    exchange_ca VARCHAR(50),
    company_type VARCHAR(50),   -- MSO, LP, REIT, Tech
    cik VARCHAR(20),            -- SEC identifier
    market_cap_millions DECIMAL,
    is_active BOOLEAN
)

-- Stock prices (daily)
stock_price (
    company_id UUID,
    ticker VARCHAR(20),
    price_date DATE,
    open_price, high_price, low_price, close_price DECIMAL,
    volume BIGINT,
    UNIQUE(company_id, price_date)
)

-- SEC financial data
company_financials (
    id SERIAL PRIMARY KEY,
    company_id UUID,
    period_type VARCHAR(20),    -- annual, quarterly
    fiscal_year INT,
    fiscal_quarter INT,
    revenue_millions DECIMAL,
    net_income_millions DECIMAL,
    total_assets_millions DECIMAL,
    total_debt_millions DECIMAL
)

-- Brand-to-company mapping
company_brand (
    company_id UUID,
    brand_name VARCHAR(255),
    is_primary BOOLEAN,
    PRIMARY KEY (company_id, brand_name)
)

-- Coverage tracking
scrape_coverage (
    state VARCHAR(2) PRIMARY KEY,
    total_dispensaries INT,
    with_menu_url INT,
    with_menu_data INT,
    last_updated TIMESTAMP
)
```

## Database Connection

```python
# Host: db.trteltlgtmcggdbrqwdw.supabase.co
# Database: postgres
# Port: 5432
# SSL: required
```

Credentials in: `app/.streamlit/secrets.toml`

## User Accounts

| Email | Password | Role | States |
|-------|----------|------|--------|
| admin@cannlinx.com | admin123 | Admin | All |
| ptgold75 | cl1029! | Admin | All |
| test@example.com | test123 | Client | NJ only |

## Menu Provider Types

| Provider | API Type | Notes |
|----------|----------|-------|
| dutchie | GraphQL | Most common, needs retailer_id |
| jane / iheartjane | REST API | Needs store_id |
| sweed | REST API | Needs api_key or store_id |
| gleaf | Playwright | Requires browser automation |
| generic_html | BeautifulSoup | Fallback scraper |

## Current Coverage (Updated: 2026-01-08)

**Store Classification:**
| Type | Count | Description |
|------|-------|-------------|
| Dispensary | 15,216 | Verified licensed cannabis dispensaries |
| Smoke Shop | 1,132 | CBD, hemp, kratom, tobacco stores |
| Unverified | 237 | Gray market or unverifiable locations |
| **TOTAL** | **16,585** | Active locations across 50 states + DC |

- 339 dispensaries with menu data
- 151,222 products tracked

### Top 15 States by Verified Dispensary Count

| State | Dispensaries | Smoke Shops | Unverified |
|-------|--------------|-------------|------------|
| CA | 1,722 | 25 | 0 |
| NY | 1,616 | 47 | 0 |
| OK | 1,444 | 34 | 0 |
| MI | 979 | 12 | 0 |
| OH | 896 | 69 | 0 |
| FL | 764 | 77 | 12 |
| CO | 690 | 10 | 0 |
| NM | 684 | 7 | 0 |
| OR | 632 | 8 | 0 |
| IL | 508 | 26 | 0 |
| WA | 500 | 5 | 0 |
| ME | 473 | 2 | 0 |
| MA | 408 | 7 | 0 |
| NJ | 388 | 16 | 0 |
| PA | 194 | 25 | 198 |

### States with Best Data Coverage

| State | Dispensaries | With Data | Products | Coverage |
|-------|--------------|-----------|----------|----------|
| MD | 354 | 83 | 43,398 | 26% |
| OH | 896 | 103 | 6,010 | 11% |
| IL | 508 | 40 | 31,707 | 8% |
| NJ | 388 | 44 | 30,547 | 11% |
| NV | 251 | 7 | 3,746 | 3% |
| CO | 690 | 25 | 17,411 | 4% |
| AZ | 426 | 8 | 6,527 | 2% |

### Provider Distribution

| Provider | Count | Scrapeable |
|----------|-------|------------|
| Sweed | 1,377 | Yes |
| Dutchie | 1,178 | Yes (Playwright) |
| Leafly | 883 | Yes |
| Jane | 430 | Yes (Playwright) |
| Weedmaps | 311 | Planned |
| Unknown | ~12,000 | Need detection |

### Data Sources
- **PA**: PA DOH official PDF (184 licensed dispensaries)
- **NY**: NY OCM official database (564 with URLs)
- **OH**: Leafly + Ohio DCC (896 dispensaries)
- **All States**: Google Places cannabis store database

**Priority actions:**
- Run Sweed scraper on discovered store IDs (1,377 dispensaries)
- Improve Playwright fallback for Cloudflare-blocked providers
- Build Weedmaps scraper for 311 dispensaries
- Run provider detection on ~12,000 unknown dispensaries
- Cross-reference Google data against state databases for verification

## Smoke Shop / Gray Market Tracking

Tracking CBD, Delta-8, THCA, and other hemp-derived products separately from licensed dispensaries.

### Store Classification

| Type | Count | Description |
|------|-------|-------------|
| dispensary | 14,941 | Verified licensed cannabis dispensaries |
| smoke_shop | 1,379 | CBD, hemp, Delta-8, kratom stores |
| unverified | 265 | Gray market or unverifiable locations |

### Smoke Shop Categories

The `store_type = 'smoke_shop'` classification includes:
- **CBD stores** - Full/broad spectrum CBD oils, edibles, topicals
- **Delta-8/Delta-9 shops** - Hemp-derived THC products
- **THCA dispensaries** - High-THCA hemp flower (federally legal loophole)
- **Kratom/Kava bars** - Botanical products
- **Vape/smoke shops** - Hardware and accessories

### Smoke Shop Products by State (Top 10)

| State | Stores | With URL | Products |
|-------|--------|----------|----------|
| TX | 183 | 183 | TBD |
| NC | 118 | 118 | TBD |
| FL | 84 | 84 | TBD |
| TN | 76 | 76 | TBD |
| NY | 63 | 63 | TBD |
| CA | 61 | 61 | TBD |
| OK | 56 | 56 | TBD |
| MN | 54 | 54 | TBD |
| WI | 52 | 52 | TBD |
| GA | 51 | 51 | TBD |

### Smoke Shop Scraper

```bash
# Scrape smoke shop products
./venv/bin/python -c "
from ingest.providers.smoke_shop_provider import fetch_menu_items
items = fetch_menu_items('https://example-cbd-store.com/')
print(f'Found {len(items)} products')
"
```

Provider: `ingest/providers/smoke_shop_provider.py`

Supports:
- Shopify stores (via products.json API)
- WooCommerce (via wp-json API)
- Generic HTML product pages

Product categories detected:
- `cbd_oil`, `cbd_edible`, `cbd_topical`
- `delta8`, `delta9`, `thca`, `hhc`
- `kratom`, `mushroom`
- `vape`, `flower`, `accessory`

### Market Opportunity Analysis

The gray market (smoke shops selling hemp-derived cannabinoids) represents:
- **1,379 tracked locations** across 50 states
- Growing faster than licensed dispensaries in many states
- Key brands: CBD American Shaman, CBD Plus USA, Your CBD Store, etc.
- Product lines: Delta-8 vapes, THCA flower, CBD gummies, kratom

**Use case**: Track market share of unlicensed brands, identify conversion opportunities, monitor regulatory risk exposure.

## Public Companies Tracked

### US MSOs (Multi-State Operators)
- Curaleaf (CURLF) - Brands: Select, Grassroots, Curaleaf
- Green Thumb Industries (GTBIF) - Brands: RYTHM, Dogwalkers, &Shine, incredibles
- Trulieve (TCNNF) - Brands: Trulieve, Alchemy, Sunshine Cannabis
- Verano (VRNOF) - Brands: Verano, Savvy, Encore
- Cresco Labs (CRLBF) - Brands: Cresco, High Supply, Good News
- TerrAscend (TRSSF) - Brands: Kind Tree, Gage, State Flower
- Columbia Care (CCHWF) - Brands: Classix, Triple Seven
- Ascend Wellness (AAWH) - Brands: Ozone, Simply Herb
- AYR Wellness (AYRWF)

### Canadian LPs
- Tilray (TLRY) - Brands: Broken Coast, Good Supply, Redecan
- Canopy Growth (CGC) - Brands: Tweed, Houseplant, Doja
- Aurora (ACB) - Brands: Aurora, San Rafael, Daily Special
- SNDL (SNDL) - Brands: Top Leaf, Palmetto
- Cronos (CRON)
- Organigram (OGI)

### Other
- Innovative Industrial Properties (IIPR) - REIT
- WM Technology (MAPS) - Weedmaps
- High Tide (HITI) - Retail

## Scripts

### Fetch Stock Prices
```bash
./venv/bin/python scripts/fetch_stock_prices.py
```
Fetches daily OHLCV from Yahoo Finance for all companies.

### Fetch SEC Filings
```bash
./venv/bin/python scripts/fetch_sec_filings.py
```
Parses 10-K/10-Q from SEC EDGAR for US-listed companies.

### Run Menu Scraper
```bash
./venv/bin/python ingest/run_scrape.py --state NJ
./venv/bin/python ingest/run_scrape.py --disp-id <UUID>
./venv/bin/python ingest/run_scrape.py --all
```

### Update Coverage Stats
```bash
./venv/bin/python -c "
from core.db import get_engine
from sqlalchemy import text
engine = get_engine()
with engine.connect() as conn:
    conn.execute(text('''
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
    '''))
    conn.commit()
"
```

## TODO / In Progress

### Immediate (Data Collection)
- [x] Import all 50 states from Google Places CSV (30,787 dispensaries)
- [x] Add PA from DOH official PDF (650 dispensaries)
- [x] Add NY from OCM official database (2,348 dispensaries)
- [x] Add OH from Leafly + state sources (1,160 dispensaries)
- [ ] Run Sweed store ID discovery for new states
- [ ] Improve Playwright fallback for Cloudflare-blocked APIs
- [ ] Build Weedmaps scraper (311 dispensaries identified)

### Provider Detection
- [x] Chain name matching (Sunnyside, Curaleaf, Trulieve, etc.)
- [x] URL pattern detection (dutchie.com, iheartjane.com, etc.)
- [ ] Website scraping to detect embedded menu providers
- [ ] Run detection on remaining 22,608 unidentified dispensaries

### Investor Intelligence
- [x] Create public_company table with 18 companies
- [x] Create stock_price table with Yahoo Finance data
- [x] Create company_financials table with SEC data
- [x] Create company_brand mapping
- [x] Build investor dashboard with shelf analytics
- [ ] Add SEDAR parser for Canadian LP financials
- [ ] Add news feed integration

### Scraping Infrastructure
- [x] Proxy configuration (Decodo residential proxies)
- [x] Playwright fallback for Cloudflare bypass
- [x] Admin coverage tracker page (96_Admin_Coverage.py)
- [ ] Set up scheduled scraping (cron or Airflow)
- [ ] Add retry logic for failed scrapes
- [ ] Implement rate limiting per provider

## API Endpoints (for future development)

Currently Streamlit-only. Planned REST API:
- `GET /api/brands/{brand}/coverage` - Brand distribution
- `GET /api/dispensaries/{state}` - Dispensaries by state
- `GET /api/prices/{product}` - Price history
- `GET /api/investors/companies` - Public company list
- `GET /api/investors/{ticker}/shelf` - Shelf analytics for company

## Environment Setup

```bash
# Create venv (Python 3.9+)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install streamlit sqlalchemy psycopg2-binary pandas plotly requests beautifulsoup4 playwright toml

# Install playwright browsers
playwright install chromium

# Set up secrets
mkdir -p app/.streamlit
cat > app/.streamlit/secrets.toml << EOF
[database]
host = "db.trteltlgtmcggdbrqwdw.supabase.co"
database = "postgres"
user = "postgres"
password = "YOUR_PASSWORD"
port = "5432"
EOF
```

## Troubleshooting

### Session state not persisting
All pages must use `from components.nav import render_nav` (not `from app.components.nav`)

### Slow homepage
Uses pg_stats for approximate counts - should load in <1s

### Missing plotly
`./venv/bin/pip install plotly`

### Missing playwright
`./venv/bin/pip install playwright && ./venv/bin/playwright install chromium`

## Contact

Support: support@cannlinx.com
