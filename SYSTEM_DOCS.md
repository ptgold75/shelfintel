# ShelfIntel / CannLinx - System Documentation

---

## CURRENT PRIORITY: Maryland Test Case

**Maryland is the primary test market.** All data collection, cleanup, and validation must be completed here before expanding focus to other states.

### Maryland Status (January 2026)

| Metric | Count | Notes |
|--------|-------|-------|
| Total MD Dispensaries in DB | 222 | Includes duplicates |
| **Actual Real Dispensaries** | ~112 | Per state records |
| Duplicates to Remove | ~60-100 | Auto-detected + manual |
| Stores with Menu Data | 85+ | Successfully scraped |
| Products Scraped | 43,500+ | Active inventory |

### MD Cleanup Priority Tasks

1. **Run auto-cleanup** - Admin page identifies ~63 duplicates automatically
2. **Manual review** - ~47 stores need human verification
3. **Mark smoke shops** - Non-dispensaries should have `store_type = 'smoke_shop'`
4. **Verify 100% coverage** - All 112 real dispensaries must have menu data

### MD Cleanup Admin Page

**Location**: Admin > Dispensaries > "MD Cleanup" tab

**Features**:
- Auto-detect duplicates by name/address/company similarity
- One-click auto-cleanup (keeps store with most products)
- Manual checkbox selection with bulk actions
- Filter by store type, active status, search term

---

## Progress Notes (January 2026)

### Completed

| Item | Details |
|------|---------|
| ✅ Sweed API | Working without proxy - 121 stores, 79,141 products |
| ✅ Dutchie bypass | undetected-chromedriver with HEADED browser |
| ✅ MD Cleanup page | Admin tab with auto-detect and bulk actions |
| ✅ Provider docs | Configurations documented with what works/doesn't |
| ✅ Admin login | phil@leadstorm.com / rock21! |

### In Progress

| Item | Status |
|------|--------|
| 🔄 MD data cleanup | Need to run auto-cleanup + manual review |
| 🔄 Dutchie MD scrape | Testing on Maryland stores |
| 🔄 Coverage verification | Confirm all 112 real MD dispensaries |

### Blocked / Won't Work

| Item | Reason |
|------|--------|
| ❌ Proxy for Sweed | Decodo IPs blocked by Sweed |
| ❌ Proxy for Dutchie | Doesn't help with Cloudflare |
| ❌ Headless Dutchie | All headless modes detected |
| ❌ Direct Dutchie API | 403 Forbidden |

---

## Quick Start

```bash
# 1. Activate virtual environment
cd /Users/gleaf/shelfintel
source venv/bin/activate

# 2. Run the Streamlit app
./venv/bin/python -m streamlit run app/Home.py --server.port 8501

# 3. Run scrapers (PRIORITY ORDER)
./venv/bin/python scripts/scrape_sweed_batch.py MD    # Sweed first (fastest)
./venv/bin/python scripts/scrape_dutchie_uc.py MD     # Dutchie (headed browser)
./venv/bin/python scripts/scrape_leafly_menus.py      # Leafly last
```

Open http://localhost:8501

---

## Current Coverage (January 2026)

### Multi-State Operations

| State | Stores w/ Data | Products | Status |
|-------|----------------|----------|--------|
| MD | 85 | 43,500+ | Primary market |
| IL | 45 | 32,000+ | Active |
| NJ | 44 | 30,500+ | Active |
| CO | 27 | 17,700+ | Active |
| OR | 26 | 7,800+ | Active |
| MI | 23 | 6,700+ | Active |
| FL | 40 | 2,000+ | Active |
| NY | 10 | 2,100+ | Active |
| + 14 more states | ~155 | ~25,000+ | Expanding |
| **TOTAL** | **455+** | **167,000+** | Growing |

### Total Database
- **19,520** dispensaries tracked
- **455** stores with active menu data
- **167,275** products scraped
- **22** states with coverage

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

---

## Project Structure

```
shelfintel/
├── app/                          # Streamlit application
│   ├── Home.py                   # Main homepage with registration
│   ├── components/
│   │   ├── nav.py               # Navigation with dropdown menus
│   │   └── auth.py              # Authentication & client management
│   ├── static/
│   │   └── cannalinx_banner.png # Header banner
│   └── pages/
│       ├── 1_Dashboard.py           # Market overview
│       ├── 2_Availability.py        # Product availability tracker
│       ├── 6_Price_Analysis.py      # Price comparisons by category
│       ├── 6_Competitor_Compare.py  # Side-by-side store comparison
│       ├── 7_Brand_Analytics.py     # Legacy brand page
│       ├── 8_County_Insights.py     # Geographic analysis
│       ├── 9_Product_Search.py      # Cross-store product search
│       │
│       │ # Intelligence Dashboards
│       ├── 10_Brand_Intelligence.py     # Brand performance & distribution
│       ├── 11_Brand_Assets.py           # Image consistency tracking
│       ├── 14_Brand_Integrity.py        # Naming standardization
│       ├── 15_Market_Share.py           # Market share analysis
│       ├── 20_Retail_Intelligence.py    # Dispensary competitive analysis
│       ├── 30_Grower_Intelligence.py    # Cultivator market trends
│       ├── 40_Investor_Intelligence.py  # Public company tracking
│       │
│       │ # Admin Pages
│       ├── 90_Admin_Clients.py      # Client management
│       ├── 91_Login.py              # Login page
│       ├── 92_Logout.py             # Logout page
│       ├── 97_Admin_Naming.py       # Naming rules management
│       └── 98_Admin_Dispensaries.py # Dispensary management
│
├── core/
│   ├── db.py                    # Database connection
│   └── category_utils.py        # Category normalization
├── ingest/
│   ├── run_scrape.py            # Main scraper orchestrator
│   └── providers/
│       ├── dutchie_provider.py  # Dutchie GraphQL
│       ├── jane_provider.py     # iHeartJane API
│       └── sweed_provider.py    # Sweed API
├── scripts/
│   ├── fetch_stock_prices.py        # Yahoo Finance stock prices
│   ├── fetch_sec_filings.py         # SEC EDGAR financial parser
│   ├── import_state_dispensaries.py # State data imports
│   ├── scrape_dutchie_batch_v2.py   # Dutchie GraphQL scraper (fast)
│   ├── scrape_leafly_and_import.py  # Leafly dispensary discovery
│   └── scrape_leafly_menus.py       # Leafly menu scraper
└── venv/                        # Python 3.9 virtual environment
```

---

## Navigation Structure

The app uses a dropdown navigation menu with sections for different user types:

| Menu | Sections | Description |
|------|----------|-------------|
| **Home** | - | Landing page with stats & registration |
| **Brands** | Dashboard, Insights, Distribution, Coverage, Assets | Brand intelligence |
| **Retail** | Dashboard, Insights, Prices, Gaps, Category Mix, Availability | Dispensary tools |
| **Growers** | Dashboard, Category, Strains, Distribution, Prices, Sizes | Cultivator analytics |
| **Tools** | Product Search, Price List, Store Compare, Price Overview | Utility pages |
| **Investors** | Dashboard, Companies, Stocks, Financials, States, Shelf | Public company tracking |
| **Admin** | Dispensaries, Naming, Product Dedup, Clients | Admin only |

---

## Authentication System

### Client Types

| Role | Access |
|------|--------|
| **Admin** | All states, all pages, client management |
| **Client** | Permitted states only, intelligence dashboards |
| **Public** | Demo mode with sample data |

### Demo Mode Pattern

Non-authenticated users see demo data:

```python
from components.auth import is_authenticated

DEMO_MODE = not is_authenticated()

if DEMO_MODE:
    data = get_demo_data()
else:
    data = load_real_data()
```

### Session Management

```python
from components.auth import (
    is_authenticated,
    is_admin,
    get_current_client,
    get_allowed_states
)

# Check authentication
if not is_authenticated():
    st.stop()

# Get user's permitted states
states = get_allowed_states()  # Returns ['MD', 'NJ'] etc.
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

### client (Authentication)
```sql
client (
    client_id UUID PRIMARY KEY,
    company_name VARCHAR(255),
    contact_email VARCHAR(255),
    password_hash VARCHAR(255),
    is_admin BOOLEAN DEFAULT false,
    allowed_states TEXT[],      -- Array of state codes
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP
)
```

### stock_price
```sql
stock_price (
    id SERIAL PRIMARY KEY,
    company_id UUID REFERENCES public_company,
    price_date DATE,
    open_price DECIMAL,
    high_price DECIMAL,
    low_price DECIMAL,
    close_price DECIMAL,
    volume BIGINT
)
```

### company_financials
```sql
company_financials (
    id SERIAL PRIMARY KEY,
    company_id UUID REFERENCES public_company,
    fiscal_year INTEGER,
    period_type VARCHAR(20),    -- annual, quarterly
    revenue_millions DECIMAL,
    gross_profit_millions DECIMAL,
    net_income_millions DECIMAL,
    total_assets_millions DECIMAL,
    total_debt_millions DECIMAL,
    cash_millions DECIMAL
)
```

---

## Database Indexes

Optimized indexes for fast page loads:

```sql
-- Menu item lookups
CREATE INDEX idx_raw_menu_item_dispensary ON raw_menu_item(dispensary_id);
CREATE INDEX idx_raw_menu_item_brand ON raw_menu_item(raw_brand);
CREATE INDEX idx_raw_menu_item_category ON raw_menu_item(raw_category);
CREATE INDEX idx_raw_menu_item_observed ON raw_menu_item(observed_at DESC);
CREATE INDEX idx_raw_menu_item_brand_lower ON raw_menu_item(LOWER(raw_brand));

-- Dispensary lookups
CREATE INDEX idx_dispensary_state ON dispensary(state);
CREATE INDEX idx_dispensary_active ON dispensary(is_active);
CREATE INDEX idx_dispensary_county ON dispensary(county);

-- Stock price lookups
CREATE INDEX idx_stock_price_company_date ON stock_price(company_id, price_date DESC);

-- Financial lookups
CREATE INDEX idx_company_financials_company ON company_financials(company_id, fiscal_year DESC);
```

---

## Intelligence Dashboards

### Brand Intelligence (`10_Brand_Intelligence.py`)

Features:
- Competitive gap analysis vs competitors
- Store distribution map
- County coverage visualization
- Category filter (Flower, Vapes, Edibles, etc.)
- Size-aware price comparisons
- Demo mode with sample brand data

### Retail Intelligence (`20_Retail_Intelligence.py`)

Features:
- Side-by-side competitor comparison
- Price positioning analysis
- Assortment gap identification
- Category mix optimization
- Size-aware price benchmarking

### Grower Intelligence (`30_Grower_Intelligence.py`)

Features:
- Strain popularity rankings
- Category trend analysis
- Brand distribution metrics
- Price benchmarking by size
- Size distribution charts

### Investor Intelligence (`40_Investor_Intelligence.py`)

Features:
- Public company tracking (MSOs & LPs)
- Stock price charts with candlestick view
- Financial metrics (revenue, profit, assets)
- State operations footprint
- Shelf analytics (brand penetration)
- Multi-company comparison charts
- Demo mode with 10 cannabis companies

---

## Database Connection

```python
# Host: db.trteltlgtmcggdbrqwdw.supabase.co
# Port: 5432
# SSL: required
```

Credentials in: `app/.streamlit/secrets.toml`

---

## Menu Provider Types & Configurations

### Provider Priority Order

**Scrape in this order for best results:**

1. **Sweed** - Fastest, most reliable
2. **Dutchie** - Works but requires headed browser
3. **Leafly** - Browser automation works
4. **Jane** - Intermittent, try last

### Provider Status Matrix

| Provider | Status | Method | Proxy? | Speed | Stores |
|----------|--------|--------|--------|-------|--------|
| **Sweed** | ✅ WORKING | REST API | ❌ NO | Fast | ~130 |
| **Dutchie** | ✅ WORKING | undetected-chromedriver | ❌ NO | Medium | ~200+ |
| **Leafly** | ✅ Working | Playwright | Optional | Medium | ~150+ |
| **Jane** | ⚠️ Intermittent | REST API | Try both | Fast | ~40 |
| **Weedmaps** | ⚠️ Unstable | REST API | N/A | - | ~10 |

### Key Lessons Learned

| What We Tried | Result | Lesson |
|---------------|--------|--------|
| Proxy for Sweed | ❌ Blocked | Sweed blocks datacenter/residential proxy IPs |
| Proxy for Dutchie | ❌ Still blocked | Cloudflare detects proxy regardless |
| Playwright headless | ❌ Detected | Cloudflare detects headless browsers |
| undetected-chromedriver headless | ❌ Detected | Even UC is detected in headless mode |
| **undetected-chromedriver headed** | ✅ WORKS | Must have visible browser window |
| Direct Dutchie GraphQL | ❌ 403 | API requires browser context |

---

## Provider Configuration Details

### Sweed (WORKING - January 2026)

**Status**: ✅ Fully functional without proxy

**Optimal Configuration**:
```python
# ✅ WORKING: Direct requests without proxy
from ingest.providers.sweed_api import fetch_all_products_for_category

products = fetch_all_products_for_category(
    store_id="376",           # Required - from provider_metadata
    category_or_filters={},   # Empty = all products
    use_proxy=False           # IMPORTANT: Proxy IPs get blocked!
)
```

**Key Points**:
- **DO NOT use proxy** - Decodo IPs are blocked by Sweed
- Requires `store_id` in `dispensary.provider_metadata`
- Use `discover_sweed.py` to find store_ids
- Rate limit: 0.5s delay between stores recommended
- API endpoint: `https://web-ui-production.sweedpos.com/_api/proxy`

**Store ID Discovery**:
```bash
./venv/bin/python ingest/discover_sweed.py --url "https://example.com/order"
```

**Batch Scrape**:
```bash
./venv/bin/python -c "
from ingest.providers.sweed_api import fetch_all_products_for_category
products = fetch_all_products_for_category('376', {}, use_proxy=False)
print(f'Found {len(products)} products')
"
```

---

### Dutchie (WORKING - January 2026)

**Status**: ✅ Working with undetected-chromedriver (HEADED browser)

**What Works**:
- ✅ `undetected-chromedriver` with **headed browser** (not headless)
- ✅ GraphQL response capture via performance logs
- ✅ Category navigation for full product coverage

**What Doesn't Work**:
- ❌ Direct GraphQL API (403 Forbidden)
- ❌ Playwright headless (Cloudflare blocks)
- ❌ undetected-chromedriver headless (Still detected)
- ❌ Proxy rotation (Cloudflare still blocks)

**Optimal Configuration**:
```python
# ✅ WORKING: undetected-chromedriver with HEADED browser
import undetected_chromedriver as uc

options = uc.ChromeOptions()
# NO headless! Must be visible browser
options.add_argument("--no-sandbox")
options.add_argument("--window-size=1920,1080")
options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

driver = uc.Chrome(options=options)
driver.get("https://dutchie.com/dispensary/store-name")
```

**Batch Scrape**:
```bash
# Scrape all unscraped Dutchie stores (headed browser will open)
./venv/bin/python scripts/scrape_dutchie_uc.py

# Scrape specific state
./venv/bin/python scripts/scrape_dutchie_uc.py MD

# Limit number of stores
./venv/bin/python scripts/scrape_dutchie_uc.py --limit=10
```

**Key Points**:
- **MUST use headed browser** - headless is still detected
- Browser window will be visible during scraping
- Captures GraphQL via Chrome DevTools Protocol
- ~30 seconds per store (slower than API but works)
- Install: `pip install undetected-chromedriver`

---

### Leafly (WORKING)

**Status**: ✅ Works with Playwright

**Configuration**:
```python
# Uses Playwright for browser automation
# Discovery script finds dispensaries
./venv/bin/python scripts/scrape_leafly_and_import.py
```

**Key Points**:
- Browser-based scraping
- No proxy needed
- Rate limit between pages recommended

---

### Jane (INTERMITTENT)

**Status**: ⚠️ Often blocked by Cloudflare

**Configuration**:
```python
# Requires store_id
# Similar to Dutchie - subject to Cloudflare blocking
```

**Key Points**:
- Direct API when not blocked
- Requires store_id discovery
- Cloudflare blocks intermittently

---

## Proxy Configuration

**Provider**: Decodo Residential Proxies

```python
# ingest/proxy_config.py
PROXY_HOST = 'gate.decodo.com'
PROXY_USER = 'spn1pjbpd4'
PROXY_PASS = 'k0xH_iq29reyWfz3JR'
PROXY_PORTS = range(10001, 10011)  # 10 rotating ports
```

**Usage**:
```python
from ingest.proxy_config import get_proxies_dict, get_playwright_proxy

# For requests library
proxies = get_proxies_dict(force_rotate=True)
response = requests.get(url, proxies=proxies)

# For Playwright
proxy = get_playwright_proxy(force_rotate=True)
context = await browser.new_context(proxy=proxy)
```

### When to Use Proxy (Updated January 2026)

| Provider | Use Proxy? | Reason |
|----------|------------|--------|
| **Sweed** | ❌ NO | Proxy IPs are blocked - use direct requests |
| **Dutchie** | ❌ NO | Proxy doesn't help bypass Cloudflare |
| **Leafly** | ⚠️ Optional | May help with rate limits |
| **Jane** | ⚠️ Try both | Sometimes helps, sometimes blocked |

### Key Insight

**Proxy does NOT help bypass Cloudflare.** For Dutchie and other Cloudflare-protected sites, use `undetected-chromedriver` with a **headed (visible) browser** instead of proxy rotation.

```bash
# Install undetected-chromedriver
pip install undetected-chromedriver

# Use headed browser for Dutchie
./venv/bin/python scripts/scrape_dutchie_uc.py MD
```

---

## Scraping Best Practices

1. **Always test without proxy first** - Many providers block proxy IPs
2. **Store configurations in provider_metadata** - Use JSON field
3. **Rotate between stores** - Don't hammer one provider
4. **Check recent scrape_run status** - Look for patterns
5. **Update this doc when things change** - Provider blocks shift frequently

### Check Provider Status
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

## Running Scrapers

### Dutchie Batch Scraper (Recommended)
```bash
# Scrape specific states (fast, reliable)
./venv/bin/python scripts/scrape_dutchie_batch_v2.py OR CA WA

# Run multiple state groups in parallel
./venv/bin/python scripts/scrape_dutchie_batch_v2.py FL PA OH &
./venv/bin/python scripts/scrape_dutchie_batch_v2.py NY MA ME CT &
./venv/bin/python scripts/scrape_dutchie_batch_v2.py CA CO MI AZ NV &
```

### Leafly Dispensary Discovery
```bash
# Find and import new dispensaries from Leafly
./venv/bin/python scripts/scrape_leafly_and_import.py
```

### Legacy Scraper (ingest/run_scrape.py)
```bash
./venv/bin/python ingest/run_scrape.py --state NJ
./venv/bin/python ingest/run_scrape.py --state IL
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

## Key Pages

| Page | URL Path | Description |
|------|----------|-------------|
| Home | / | Landing page with stats & registration |
| Brand Intelligence | /Brand_Intelligence | Brand performance dashboard |
| Retail Intelligence | /Retail_Intelligence | Dispensary competitive analysis |
| Grower Intelligence | /Grower_Intelligence | Cultivator market trends |
| Investor Intelligence | /Investor_Intelligence | Public company tracking |
| Product Search | /Product_Search | Search across all menus |
| Price Analysis | /Price_Analysis | Price comparisons by category |
| Availability | /Availability | Product availability tracker |
| Admin Clients | /Admin_Clients | Client management (admin only) |
| Login | /Login | Authentication |

---

## State Filter System

All pages support multi-state filtering:

```python
from components.nav import render_state_filter, get_selected_state

# In page:
state = render_state_filter()  # Returns selected state or None
if not state:
    st.warning("No states available")
    st.stop()

# Use in queries:
WHERE d.state = :state
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
    disp = conn.execute(text('SELECT COUNT(*) FROM dispensary WHERE is_active = true')).scalar()
    prods = conn.execute(text('SELECT COUNT(*) FROM raw_menu_item')).scalar()
    states = conn.execute(text('SELECT COUNT(DISTINCT state) FROM dispensary WHERE is_active = true')).scalar()
    print(f'Dispensaries: {disp:,}, Products: {prods:,}, States: {states}')
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
        SELECT state, COUNT(*) as stores,
               (SELECT COUNT(*) FROM raw_menu_item r
                JOIN dispensary d2 ON r.dispensary_id = d2.dispensary_id
                WHERE d2.state = d.state) as products
        FROM dispensary d WHERE is_active = true
        GROUP BY state ORDER BY stores DESC
    '''))
    for row in result: print(f'{row[0]}: {row[1]} stores, {row[2]:,} products')
"
```

### Add New Client
```bash
./venv/bin/python -c "
from core.db import get_engine
from sqlalchemy import text
import hashlib
engine = get_engine()
with engine.connect() as conn:
    pwd_hash = hashlib.sha256('password123'.encode()).hexdigest()
    conn.execute(text('''
        INSERT INTO client (company_name, contact_email, password_hash, allowed_states)
        VALUES (:name, :email, :pwd, :states)
    '''), {'name': 'Test Company', 'email': 'test@example.com', 'pwd': pwd_hash, 'states': ['MD', 'NJ']})
    conn.commit()
"
```

---

## Admin Credentials

```
Email: phil@leadstorm.com
Password: rock21!
```

---

## Contact

- **Support**: support@cannlinx.com
- **Sales**: sales@cannlinx.com

---

*Last updated: January 12, 2026*
