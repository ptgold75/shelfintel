# ShelfIntel / CannLinx Quick Start Guide

## Project Overview
ShelfIntel (CannLinx) is a shelf intelligence platform for Maryland's cannabis industry. It tracks products, prices, and availability across 96+ dispensaries.

## Directory Structure
```
shelfintel/
├── app/                    # Streamlit web application
│   ├── Home.py            # Main homepage
│   ├── static/            # Images, CSS
│   ├── components/
│   │   └── nav.py         # Navigation component
│   └── pages/             # App pages (Dashboard, Search, etc.)
├── core/                  # Core utilities
│   ├── db.py              # Database connection (Supabase)
│   └── product_normalizer.py  # Product name normalization
├── ingest/                # Data ingestion
│   ├── providers/         # Menu scraping providers
│   ├── scrape_dutchie_batch.py  # Dutchie batch scraper with proxy
│   ├── scrape_weedmaps.py      # Weedmaps fallback scraper
│   └── discover_*.py           # Provider discovery scripts
├── analytics/             # Analytics modules
├── data/                  # Data files
├── .env                   # Proxy credentials (do not commit)
├── .streamlit/
│   ├── config.toml        # Streamlit config
│   └── secrets.toml       # DATABASE_URL (do not commit)
└── QUICKSTART.md          # This file
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

## Database Schema (Key Tables)

```sql
-- Dispensaries
dispensary (
    dispensary_id VARCHAR PRIMARY KEY,
    name VARCHAR,
    state VARCHAR,
    address VARCHAR, city VARCHAR, county VARCHAR, zip VARCHAR,
    phone VARCHAR, email VARCHAR,
    menu_url TEXT,
    menu_provider VARCHAR,  -- dutchie, jane, sweed, weedmaps, etc.
    is_active BOOLEAN,
    created_at TIMESTAMP
)

-- Raw Menu Items (scraped product data)
raw_menu_item (
    raw_menu_item_id VARCHAR PRIMARY KEY,
    scrape_run_id VARCHAR,
    dispensary_id VARCHAR,
    observed_at TIMESTAMP,
    raw_name TEXT,
    raw_category VARCHAR,
    raw_brand VARCHAR,
    raw_price DOUBLE PRECISION,
    raw_description TEXT,      -- Product description
    provider_product_id VARCHAR
)

-- Scrape Runs
scrape_run (
    scrape_run_id VARCHAR PRIMARY KEY,
    dispensary_id VARCHAR,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    status VARCHAR,
    records_found INTEGER
)
```

## Menu Providers

| Provider | Stores | Notes |
|----------|--------|-------|
| dutchie | 50 | Most common, uses GraphQL API. Many blocked by Cloudflare. |
| jane | 18 | JSON API, generally works without proxy |
| sweed | 8 | JSON API, gLeaf and similar |
| leafbridge | 7 | Custom scraper |
| weedmaps | fallback | Public API, works when others blocked |
| curaleaf | 3 | Custom platform |
| trulieve | 2 | Custom platform |

## Scraping

### Dutchie Stores (with Playwright + Proxy)
For stores blocked by Cloudflare, use Playwright with the Decodo proxy:

```python
from playwright.async_api import async_playwright

PROXY_HOST = 'gate.decodo.com'
PROXY_USER = 'spn1pjbpd4'
PROXY_PASS = 'k0xH_iq29reyWfz3JR'

# Use rotating ports 10002-10010 to avoid rate limits
async with async_playwright() as p:
    browser = await p.chromium.launch(
        headless=True,
        proxy={
            "server": f"http://{PROXY_HOST}:10002",
            "username": PROXY_USER,
            "password": PROXY_PASS
        }
    )
```

### Category Navigation Pattern (Critical!)
Dutchie stores require navigating to each category URL to get all products (otherwise only 25 per category):

```python
CATEGORIES = ["flower", "vaporizers", "pre-rolls", "edibles",
              "concentrates", "tinctures", "topicals", "accessories"]

for cat in CATEGORIES:
    await page.goto(f"{base_url}/products/{cat}")
    # Scroll to load all products
    # Capture GraphQL responses containing filteredProducts.products
```

### Weedmaps Fallback (When All Else Fails)
```python
import requests

slug = "culta"  # from weedmaps.com/dispensaries/{slug}
url = f"https://api-g.weedmaps.com/discovery/v1/listings/dispensaries/{slug}/menu_items"
params = {"page_size": 100, "page": 1}
r = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"})
items = r.json()["data"]["menu_items"]
```

### Run Scrapers

```bash
# Dutchie batch scraper
python ingest/scrape_dutchie_batch.py

# Weedmaps fallback
python ingest/scrape_weedmaps.py
```

## App Pages

| Page | File | Description |
|------|------|-------------|
| Home | Home.py | Landing page with stats |
| Dashboard | 1_Dashboard.py | Key metrics overview |
| Product Search | 2_Product_Search.py | Search across all menus |
| Price Analysis | 3_Price_Analysis.py | Price comparisons |
| Brand Analytics | 4_Brand_Analytics.py | Brand performance |
| Market Share | 5_Market_Share.py | Market share analysis |
| County Insights | 6_County_Insights.py | Geographic analysis |
| Competitor Compare | 7_Competitor_Compare.py | Side-by-side comparison |
| Brand Integrity | 8_Brand_Integrity.py | Naming consistency |
| Availability | 95_Availability.py | Product availability |
| Admin Dispensaries | 96_Admin_Dispensaries.py | Store management |
| Admin Naming | 97_Admin_Naming.py | Name normalization |
| Product Dedup | 98_Product_Dedup.py | Duplicate detection |

## Product Normalization

```python
from core.product_normalizer import extract_base_name, extract_size

name = "Curio Wellness - Tropicana Cherry Pre-Packaged (3.5g)"
base = extract_base_name(name)  # "Curio Wellness - Tropicana Cherry"
size = extract_size(name)       # "3.5g"
```

### Deduplication Rules
- Products are potential duplicates if: same brand + same base name + SAME SIZE
- Different sizes = different SKUs (not duplicates)

## Useful Commands

### Check Database Status
```bash
source .venv/bin/activate
python3 -c "
from sqlalchemy import create_engine, text
engine = create_engine('postgresql+psycopg://postgres:Tattershall2020@db.trteltlgtmcggdbrqwdw.supabase.co:5432/postgres')
with engine.connect() as conn:
    stores = conn.execute(text('SELECT COUNT(*) FROM dispensary WHERE is_active = true')).scalar()
    products = conn.execute(text('SELECT COUNT(*) FROM raw_menu_item')).scalar()
    print(f'Stores: {stores}, Products: {products}')
"
```

### Check Stores with No Products
```bash
python3 -c "
from sqlalchemy import create_engine, text
engine = create_engine('postgresql+psycopg://postgres:Tattershall2020@db.trteltlgtmcggdbrqwdw.supabase.co:5432/postgres')
with engine.connect() as conn:
    result = conn.execute(text('''
        SELECT d.name, d.menu_provider
        FROM dispensary d
        LEFT JOIN raw_menu_item r ON d.dispensary_id = r.dispensary_id
        WHERE d.is_active = true
        GROUP BY d.dispensary_id
        HAVING COUNT(r.raw_menu_item_id) = 0
    '''))
    for row in result: print(f'{row[1]}: {row[0]}')
"
```

### Test Proxy Connection
```bash
python3 -c "
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

## Known Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Cloudflare blocks | Direct dutchie.com URLs blocked | Use embedded URLs or Weedmaps fallback |
| Only ~25 products | Only first page loaded | Navigate to each category URL |
| Proxy rate limits | Port 10001 saturated | Rotate ports 10002-10010 |
| Low product counts | Pagination not working | Scroll to trigger lazy loading |

## Current Coverage (Jan 2026)

- **Total Stores**: 96 active
- **With Products**: ~70 stores
- **Total Products**: ~30,000+

---

## Recent Session Work (Jan 7, 2025)

### New/Updated Pages

| Page | File | Description |
|------|------|-------------|
| Brand Intelligence | `10_Brand_Intelligence.py` | Premium brand dashboard with competitive comparison, category filter |
| Brand Assets | `11_Brand_Assets.py` | Image consistency tracking across stores |
| Retail Intelligence | `20_Retail_Intelligence.py` | Dispensary competitive analysis with size-aware comparisons |
| Grower Intelligence | `30_Grower_Intelligence.py` | Market trends for cultivators |
| Price Analysis | `6_Price_Analysis.py` | Subcategory breakdown (flower sizes, preroll packs, vape types) |

### Key Code Patterns

#### Size Extraction (for accurate price comparisons)
```python
def extract_size_from_name(name: str) -> str:
    """Extract size/weight from product name."""
    # Returns: "3.5g", "7g", "14g", "28g", "100mg", "5pk", "std"
    # Used in: 10_Brand_Intelligence.py, 20_Retail_Intelligence.py
```

#### Subcategory SQL (Price Analysis)
In `6_Price_Analysis.py`, `get_subcategory_sql()` breaks down:
- **Flower**: 1g, 3.5g, 7g, 14g, 28g
- **Pre-Rolls**: Regular vs Infused, by pack size (Single, 2pk, 3pk, 5pk, 7pk, 10pk)
- **Vapes**: Cartridge vs Disposable

#### Category Normalization
`core/category_utils.py` - `get_normalized_category_sql()` uses ILIKE patterns:
```sql
WHEN raw_category ILIKE '%flower%' OR raw_category ILIKE '%bud%' THEN 'Flower'
WHEN raw_category ILIKE '%pre-roll%' OR raw_category ILIKE '%preroll%' THEN 'Pre-Rolls'
-- etc.
```

#### PostgreSQL Array Parameters
Use `= ANY(:param)` NOT `IN :param`:
```python
# WRONG: WHERE category IN :cats  -- causes syntax error
# RIGHT: WHERE category = ANY(:cats)
conn.execute(text("WHERE category = ANY(:cats)"), {"cats": my_list})
```

### Registration Form (Home.py)
- Conditional dropdowns based on user type
- Dispensary selector for "Dispensary / Retailer"
- Brand selector for "Grower / Processor"
- Stores `location_id` and `location_name` in registrations table

### Brand Intelligence Features
- Category filter dropdown
- Competitive gap analysis (your coverage vs competitors)
- Wholesale value estimates (50% of retail = keystone)
- Distribution gaps (only shows stores WITH scraped data)
- County coverage visualization

### Retail Intelligence Features
- Competitor comparison with city in store names
- Size-aware price comparisons (only compares same-size products)
- "Exclusive Products" insight - products you carry that NO local competitor has
- Assortment gaps, pricing insights

### Common Fixes Applied
| Issue | Fix |
|-------|-----|
| `NoneType format` errors | Add `or 0`: `value = metrics['field'] or 0` |
| `IN :param` syntax error | Use `= ANY(:param)` for PostgreSQL |
| Category filter not working | Updated `get_normalized_category_sql()` to use ILIKE |
| Wrong products in filter | Fixed category matching with fuzzy ILIKE patterns |

### Useful SQL Queries

```sql
-- Check raw categories in database
SELECT DISTINCT raw_category, COUNT(*)
FROM raw_menu_item
GROUP BY raw_category ORDER BY COUNT(*) DESC;

-- Stores with data counts
SELECT d.name, d.city, COUNT(r.raw_menu_item_id)
FROM dispensary d
LEFT JOIN raw_menu_item r ON d.dispensary_id = r.dispensary_id
GROUP BY d.name, d.city ORDER BY COUNT DESC;

-- Brand coverage
SELECT UPPER(raw_brand), COUNT(DISTINCT dispensary_id) as stores
FROM raw_menu_item WHERE raw_brand IS NOT NULL
GROUP BY UPPER(raw_brand) ORDER BY stores DESC;
```

---

## Credentials Reference

| Service | Host | User | Password |
|---------|------|------|----------|
| Supabase DB | db.trteltlgtmcggdbrqwdw.supabase.co | postgres | Tattershall2020 |
| Decodo Proxy | gate.decodo.com | spn1pjbpd4 | k0xH_iq29reyWfz3JR |

## Data Sources

- **Dispensary Menus**: Scraped from individual store websites
- **State Data**: MCA Data Dashboard (cannabis.maryland.gov)
- **Fallback**: Weedmaps public API
