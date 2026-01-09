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

### Multi-State Operations

| State | Dispensaries | Products | Status |
|-------|--------------|----------|--------|
| MD | 96+ | 30,000+ | Primary market |
| NJ | 15+ | 5,000+ | Active expansion |
| IL | 43+ | 12,000+ | Active expansion |
| **TOTAL** | 150+ | 47,000+ | Growing |

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
│   ├── fetch_stock_prices.py    # Yahoo Finance stock prices
│   ├── fetch_sec_filings.py     # SEC EDGAR financial parser
│   └── import_state_dispensaries.py  # State data imports
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

## Menu Provider Types

| Provider | API Type | Count | Notes |
|----------|----------|-------|-------|
| Sweed | REST API | ~1,400 | Most common, needs store_id |
| Dutchie | GraphQL | ~1,200 | Needs retailer_id, Cloudflare issues |
| Leafly | HTML/API | ~900 | Scraping supported |
| Jane | REST API | ~430 | Needs store_id, Cloudflare issues |
| Weedmaps | REST API | ~300 | Fallback scraper |

---

## Running Scrapers

### Scrape by State
```bash
./venv/bin/python ingest/run_scrape.py --state NJ
./venv/bin/python ingest/run_scrape.py --state IL
./venv/bin/python ingest/run_scrape.py --state MD
```

### Scrape All States
```bash
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

---

*Last updated: January 2026*
