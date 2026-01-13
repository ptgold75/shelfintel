# ShelfIntel / CannLinx Quick Start Guide

## Project Overview

ShelfIntel (CannLinx) is a multi-state shelf intelligence platform for the cannabis industry. It tracks products, prices, and availability across dispensaries in Maryland, New Jersey, Illinois, and expanding markets.

---

## CURRENT PRIORITY: Maryland Test Case

**Maryland is our primary test market** - all data collection and cleanup must be completed here first before expanding to other states.

### Maryland Status (January 2026)

| Metric | Count | Status |
|--------|-------|--------|
| Total MD Dispensaries | 222 | In database |
| **Actual Real Dispensaries** | ~112 | Per state records |
| Duplicates to Remove | ~60-100 | Need cleanup |
| Stores with Menu Data | 85+ | Scraped |
| Products Scraped | 43,500+ | Active |

### MD Cleanup Tasks

1. **Auto-cleanup duplicates** - Admin page can identify and deactivate ~63 duplicates automatically
2. **Manual review** - ~47 stores need manual verification (could be smoke shops or legitimate)
3. **Mark smoke shops** - Set `store_type = 'smoke_shop'` for non-dispensaries
4. **Verify coverage** - Ensure all 112 real dispensaries have menu data

### MD Cleanup Admin Page

Navigate to: **Admin > Dispensaries > "MD Cleanup" tab**

Features:
- Auto-detect duplicates by name/address similarity
- One-click auto-cleanup (keeps store with most products)
- Manual checkbox selection for bulk actions
- Filter by store type, active status, search

---

## Current Coverage (January 2026)

| State | Stores w/ Data | Products | Status |
|-------|----------------|----------|--------|
| MD | 85 | 43,500+ | **PRIMARY - Test Case** |
| IL | 45 | 32,000+ | Active |
| NJ | 44 | 30,500+ | Active |
| CO | 27 | 17,700+ | Active |
| OR | 26 | 7,800+ | Active |
| MI | 23 | 6,700+ | Active |
| + 16 more | ~205 | ~29,000+ | Expanding |
| **TOTAL** | **455+** | **167,000+** | Growing |

**Database Totals**: 19,520 dispensaries tracked, 22 states with coverage

---

## Provider Status & Configuration

### PRIORITY ORDER for Scraping

1. **Sweed** - Works reliably, scrape first
2. **Dutchie** - Works with undetected-chromedriver (headed)
3. **Leafly** - Works with Playwright
4. **Jane** - Intermittent, try last

### Provider Quick Reference

| Provider | Status | Method | Proxy? | Notes |
|----------|--------|--------|--------|-------|
| **Sweed** | ✅ Working | REST API | ❌ NO | Proxy IPs blocked |
| **Dutchie** | ✅ Working | undetected-chromedriver | ❌ NO | Must be HEADED browser |
| **Leafly** | ✅ Working | Playwright | Optional | Browser automation |
| **Jane** | ⚠️ Intermittent | REST API | Try both | Cloudflare blocks sometimes |

### Sweed (WORKING)

**Status**: ✅ Fully functional - 121 stores scraped, 79,141 products

```bash
# Batch scrape all Sweed stores
./venv/bin/python scripts/scrape_sweed_batch.py

# Scrape specific state
./venv/bin/python scripts/scrape_sweed_batch.py MD
```

**Key Points**:
- **DO NOT use proxy** - Decodo IPs are blocked by Sweed
- Requires `store_id` in `dispensary.provider_metadata`
- API: `https://web-ui-production.sweedpos.com/_api/proxy`

### Dutchie (WORKING)

**Status**: ✅ Working with undetected-chromedriver (HEADED browser)

```bash
# Batch scrape (browser window will be visible)
./venv/bin/python scripts/scrape_dutchie_uc.py

# Scrape specific state
./venv/bin/python scripts/scrape_dutchie_uc.py MD

# Limit stores
./venv/bin/python scripts/scrape_dutchie_uc.py --limit=10
```

**Key Points**:
- **MUST use headed browser** - headless is detected by Cloudflare
- Browser window will be visible during scraping
- ~30 seconds per store
- Install: `pip install undetected-chromedriver`

**What Doesn't Work**:
- ❌ Direct GraphQL API (403 Forbidden)
- ❌ Playwright headless (Cloudflare blocks)
- ❌ undetected-chromedriver headless (Still detected)
- ❌ Proxy rotation (Cloudflare still blocks)

### Leafly (WORKING)

```bash
# Discovery and import
./venv/bin/python scripts/scrape_leafly_and_import.py

# Menu scraping
./venv/bin/python scripts/scrape_leafly_menus.py
```

---

## Proxy Configuration

**Provider**: Decodo Residential Proxies

```
Host: gate.decodo.com
Ports: 10001-10010 (rotating)
User: spn1pjbpd4
Pass: k0xH_iq29reyWfz3JR
```

### When to Use Proxy

| Provider | Use Proxy? | Reason |
|----------|------------|--------|
| Sweed | ❌ NO | Proxy IPs are blocked |
| Dutchie | ❌ NO | Cloudflare still blocks |
| Leafly | ⚠️ Optional | Helps with rate limits |
| Jane | ⚠️ Try both | May help avoid blocks |

**Lesson Learned**: Proxy doesn't help bypass Cloudflare. Use undetected-chromedriver instead.

---

## Quick Start

### 1. Environment Setup
```bash
cd /Users/gleaf/shelfintel
source venv/bin/activate
```

### 2. Run the App
```bash
streamlit run app/Home.py --server.port 8501
```
Open http://localhost:8501

### 3. Scrape Data (Priority Order)

```bash
# 1. Sweed stores (fast, reliable)
./venv/bin/python scripts/scrape_sweed_batch.py MD

# 2. Dutchie stores (headed browser required)
./venv/bin/python scripts/scrape_dutchie_uc.py MD

# 3. Leafly stores
./venv/bin/python scripts/scrape_leafly_menus.py
```

---

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
│       ├── 98_Admin_Dispensaries.py     # Dispensary management + MD Cleanup
│       └── ...
├── core/                     # Core utilities
│   ├── db.py                 # Database connection (Supabase)
│   └── category_utils.py     # Category normalization
├── ingest/                   # Data ingestion
│   ├── run_scrape.py         # Main scraper orchestrator
│   ├── proxy_config.py       # Decodo proxy configuration
│   └── providers/            # Menu scraping providers
│       ├── sweed_api.py      # Sweed REST API (WORKING)
│       ├── dutchie_provider.py
│       └── jane_provider.py
├── scripts/                  # Utility scripts
│   ├── scrape_sweed_batch.py       # Sweed batch scraper
│   ├── scrape_dutchie_uc.py        # Dutchie undetected-chromedriver
│   ├── scrape_dutchie_batch_v2.py  # Legacy Dutchie GraphQL
│   ├── scrape_leafly_and_import.py # Leafly dispensary discovery
│   ├── fetch_stock_prices.py       # Yahoo Finance stock data
│   └── fetch_sec_filings.py        # SEC EDGAR parser
├── QUICKSTART.md             # This file
├── SYSTEM_DOCS.md            # Detailed system documentation
└── venv/                     # Python virtual environment
```

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

### Admin Login

```
Email: phil@leadstorm.com
Password: rock21!
```

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
    provider_metadata JSONB,  -- store_id, etc.
    store_type VARCHAR,  -- NULL, 'smoke_shop', 'duplicate'
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

## Progress Notes (January 2026)

### Completed

- ✅ Sweed API integration working (NO proxy needed)
- ✅ Sweed batch scrape: 121 stores, 79,141 products
- ✅ Dutchie bypass with undetected-chromedriver (HEADED)
- ✅ MD Cleanup admin page created
- ✅ Duplicate detection algorithm implemented
- ✅ Provider configuration documented

### In Progress

- 🔄 Maryland data cleanup (priority)
- 🔄 Testing Dutchie scraper on MD stores
- 🔄 Verifying all 112 real MD dispensaries have data

### Blocked/Won't Work

- ❌ Proxy for Sweed (blocked)
- ❌ Proxy for Dutchie Cloudflare bypass (doesn't help)
- ❌ Headless browser for Dutchie (detected)
- ❌ Direct Dutchie GraphQL API (403)

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

### Check MD Coverage
```bash
./venv/bin/python -c "
from core.db import get_engine
from sqlalchemy import text
engine = get_engine()
with engine.connect() as conn:
    result = conn.execute(text('''
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE is_active) as active,
            COUNT(DISTINCT r.dispensary_id) as with_data
        FROM dispensary d
        LEFT JOIN raw_menu_item r ON d.dispensary_id = r.dispensary_id
        WHERE d.state = 'MD'
    '''))
    row = result.fetchone()
    print(f'MD: {row[0]} total, {row[1]} active, {row[2]} with menu data')
"
```

### Check Provider Status (Last 24h)
```bash
./venv/bin/python -c "
from sqlalchemy import create_engine, text
engine = create_engine('postgresql+psycopg://postgres:Tattershall2020@db.trteltlgtmcggdbrqwdw.supabase.co:5432/postgres')
with engine.connect() as conn:
    result = conn.execute(text('''
        SELECT d.menu_provider, sr.status, COUNT(*) as runs, SUM(sr.records_found) as products
        FROM scrape_run sr
        JOIN dispensary d ON sr.dispensary_id = d.dispensary_id
        WHERE sr.started_at > NOW() - INTERVAL '24 hours'
        GROUP BY d.menu_provider, sr.status
        ORDER BY d.menu_provider, sr.status
    '''))
    for row in result:
        print(f'{row[0]:15} | {row[1]:10} | {row[2]:4} runs | {row[3] or 0:6} products')
"
```

---

## Credentials Reference

| Service | Host | User | Password |
|---------|------|------|----------|
| Supabase DB | db.trteltlgtmcggdbrqwdw.supabase.co | postgres | Tattershall2020 |
| Decodo Proxy | gate.decodo.com | spn1pjbpd4 | k0xH_iq29reyWfz3JR |
| Admin Login | - | phil@leadstorm.com | rock21! |

---

*Last updated: January 2026*
