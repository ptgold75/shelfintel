#!/usr/bin/env python3
"""
Curaleaf Scraper - Uses saved cookies from manual authentication.

Run curaleaf_manual_auth.py first to set up cookies.

Usage:
    python scripts/scrape_curaleaf.py
"""

import asyncio
import json
import uuid
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.async_api import async_playwright
from core.db import get_engine
from sqlalchemy import text

# Proxy support
try:
    from ingest.proxy_config import get_playwright_proxy, get_rate_limiter
    PROXY_AVAILABLE = True
except ImportError:
    PROXY_AVAILABLE = False

COOKIE_FILE = "data/curaleaf_cookies.json"

# MD Curaleaf stores
CURALEAF_MD_STORES = [
    ("Curaleaf MD Gaithersburg", "https://curaleaf.com/stores/curaleaf-md-gaithersburg-montgomery-village-au"),
    ("Curaleaf MD Columbia", "https://curaleaf.com/stores/curaleaf-md-columbia-au"),
    ("Curaleaf MD Frederick", "https://curaleaf.com/stores/curaleaf-dispensary-md-frederick-au"),
    ("Curaleaf MD Reisterstown", "https://curaleaf.com/stores/curaleaf-md-reisterstown-au"),
]


def load_cookies():
    """Load saved cookies from file."""
    if not os.path.exists(COOKIE_FILE):
        print(f"ERROR: Cookie file not found: {COOKIE_FILE}")
        print("Run 'python scripts/curaleaf_manual_auth.py' first")
        return None

    with open(COOKIE_FILE, 'r') as f:
        cookies = json.load(f)

    # Check expiration
    now = datetime.now().timestamp()
    valid_cookies = []
    expired = 0

    for c in cookies:
        exp = c.get('expires', -1)
        if exp == -1 or exp > now:
            valid_cookies.append(c)
        else:
            expired += 1

    if expired > 0:
        print(f"WARNING: {expired} cookies have expired")

    if not valid_cookies:
        print("ERROR: All cookies expired. Re-run manual auth.")
        return None

    return valid_cookies


async def scrape_store(context, name, url):
    """Scrape a single Curaleaf store."""
    products = {}

    page = await context.new_page()

    async def capture_response(response):
        if response.status == 200:
            try:
                ct = response.headers.get('content-type', '')
                if 'json' in ct:
                    data = await response.json()

                    def extract(obj, depth=0):
                        if depth > 8 or not obj:
                            return
                        if isinstance(obj, dict):
                            # Look for product-like objects
                            if obj.get('name') and (obj.get('price') or obj.get('variants') or obj.get('thcContent')):
                                pid = obj.get('id') or obj.get('productId') or str(len(products))
                                products[pid] = obj
                            for v in obj.values():
                                extract(v, depth + 1)
                        elif isinstance(obj, list):
                            for item in obj:
                                extract(item, depth + 1)

                    extract(data)
            except:
                pass

    page.on("response", capture_response)

    try:
        print(f"  Loading {url[:60]}...")
        await page.goto(url, timeout=45000, wait_until="networkidle")
        await asyncio.sleep(2)

        # Check if we passed age gate
        if 'age-gate' in page.url:
            print(f"  ERROR: Cookies expired or invalid - redirected to age gate")
            await page.close()
            return None

        # Scroll to load more products
        for _ in range(15):
            await page.evaluate("window.scrollBy(0, 600)")
            await asyncio.sleep(0.3)

        # Click through category tabs to capture all products
        categories = ['Flower', 'Pre-Rolls', 'Vaporizers', 'Edibles', 'Concentrates', 'Tinctures']
        for cat in categories:
            try:
                cat_btn = page.locator(f"button:has-text('{cat}'), a:has-text('{cat}')")
                if await cat_btn.count() > 0:
                    await cat_btn.first.click()
                    await asyncio.sleep(1)
                    for _ in range(5):
                        await page.evaluate("window.scrollBy(0, 600)")
                        await asyncio.sleep(0.2)
            except:
                pass

    except Exception as e:
        print(f"  Error: {e}")
    finally:
        await page.close()

    return list(products.values())


def parse_curaleaf_product(item):
    """Parse Curaleaf product into standard format."""
    name = item.get('name', '')

    # Brand
    brand = ''
    brand_obj = item.get('brand')
    if brand_obj:
        if isinstance(brand_obj, dict):
            brand = brand_obj.get('name', '')
        else:
            brand = str(brand_obj)

    # Category
    category = item.get('category', '') or item.get('type', '')
    if isinstance(category, dict):
        category = category.get('name', '')

    # Price - try various fields
    price = None
    if item.get('price'):
        price = item['price']
    elif item.get('variants'):
        variants = item['variants']
        if variants and isinstance(variants, list):
            price = variants[0].get('price') or variants[0].get('priceRec')
    elif item.get('prices'):
        prices = item['prices']
        if isinstance(prices, dict):
            price = prices.get('rec') or prices.get('med') or prices.get('default')

    # THC/CBD
    thc = item.get('thcContent') or item.get('thc')
    cbd = item.get('cbdContent') or item.get('cbd')

    return {
        'name': name,
        'brand': brand,
        'category': category,
        'price': float(price) if price else None,
        'thc': str(thc) if thc else None,
        'cbd': str(cbd) if cbd else None,
        'provider_id': str(item.get('id') or item.get('productId') or ''),
    }


def save_products(products, dispensary_id, store_name):
    """Save products to database."""
    if not products:
        return 0

    engine = get_engine()
    scrape_run_id = str(uuid.uuid4())
    now = datetime.utcnow()

    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO scrape_run (scrape_run_id, dispensary_id, started_at, finished_at, status, records_found)
            VALUES (:scrape_run_id, :dispensary_id, :started_at, :finished_at, 'success', :records_found)
        """), {
            "scrape_run_id": scrape_run_id,
            "dispensary_id": dispensary_id,
            "started_at": now,
            "finished_at": now,
            "records_found": len(products)
        })

        for item in products:
            p = parse_curaleaf_product(item)
            conn.execute(text("""
                INSERT INTO raw_menu_item
                (raw_menu_item_id, dispensary_id, scrape_run_id, raw_brand, raw_name, raw_category,
                 raw_price, raw_thc, raw_cbd, provider_product_id, observed_at)
                VALUES (:id, :dispensary_id, :scrape_run_id, :brand, :name, :category,
                        :price, :thc, :cbd, :provider_id, :observed_at)
            """), {
                "id": str(uuid.uuid4()),
                "dispensary_id": dispensary_id,
                "scrape_run_id": scrape_run_id,
                "brand": p['brand'],
                "name": p['name'],
                "category": p['category'],
                "price": p['price'],
                "thc": p['thc'],
                "cbd": p['cbd'],
                "provider_id": p['provider_id'],
                "observed_at": now
            })

        conn.commit()

    return len(products)


async def main():
    """Main scraper entry point."""
    print("=" * 60)
    print("CURALEAF SCRAPER")
    print("=" * 60)

    # Load cookies
    cookies = load_cookies()
    if not cookies:
        return

    print(f"Loaded {len(cookies)} cookies\n")

    engine = get_engine()

    async with async_playwright() as p:
        # Get proxy config if available
        proxy_config = None
        if PROXY_AVAILABLE:
            proxy_config = get_playwright_proxy(force_rotate=True)
            if proxy_config:
                print(f"Using proxy: {proxy_config['server']}")

        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            proxy=proxy_config,
        )

        # Add saved cookies
        await context.add_cookies(cookies)

        total_products = 0
        total_stores = 0

        for name, url in CURALEAF_MD_STORES:
            print(f"\n{'=' * 50}")
            print(f"{name}")

            # Get dispensary_id
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT dispensary_id FROM dispensary
                    WHERE state = 'MD' AND name ILIKE :name
                """), {"name": f"%{name.split()[0]}%Gaithersburg%" if 'Gaithersburg' in name else f"%Curaleaf%{name.split()[-1]}%"})
                row = result.fetchone()

            if not row:
                # Try broader search
                with engine.connect() as conn:
                    result = conn.execute(text("""
                        SELECT dispensary_id, name FROM dispensary
                        WHERE state = 'MD' AND name ILIKE '%curaleaf%'
                    """))
                    rows = list(result)
                    print(f"  Available Curaleaf stores: {[r[1] for r in rows]}")
                continue

            dispensary_id = row[0]

            products = await scrape_store(context, name, url)

            if products is None:
                print("  Cookies expired - stopping")
                break

            if products:
                saved = save_products(products, dispensary_id, name)
                print(f"  Saved: {saved} products")
                total_products += saved
                total_stores += 1
            else:
                print(f"  No products found")

        await browser.close()

    print(f"\n{'=' * 60}")
    print(f"TOTAL: {total_stores} stores, {total_products} products")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
