#!/usr/bin/env python3
"""
Dutchie scraper using undetected-chromedriver to bypass Cloudflare.

IMPORTANT: This uses a HEADED browser (not headless) because headless
is still detected by Cloudflare. The browser window will be visible.

Usage:
    python scripts/scrape_dutchie_uc.py              # Scrape all unscraped stores
    python scripts/scrape_dutchie_uc.py MD           # Scrape only MD stores
    python scripts/scrape_dutchie_uc.py --limit 10   # Limit to 10 stores
"""

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import json
import uuid
import sys
import os
from datetime import datetime
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg://postgres:Tattershall2020@db.trteltlgtmcggdbrqwdw.supabase.co:5432/postgres"

CATEGORIES = ["flower", "vaporizers", "pre-rolls", "edibles", "concentrates", "tinctures", "topicals"]


def get_engine():
    return create_engine(DATABASE_URL)


def scrape_store(url: str, store_name: str) -> list:
    """Scrape a single Dutchie store using undetected-chromedriver."""
    all_products = {}

    print(f"  Starting browser...", flush=True)

    options = uc.ChromeOptions()
    # HEADED mode - required to bypass Cloudflare
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

    driver = uc.Chrome(options=options, version_main=None)

    def capture_graphql():
        """Extract products from GraphQL responses in performance logs."""
        products = {}
        try:
            logs = driver.get_log('performance')
            for entry in logs:
                try:
                    log = json.loads(entry['message'])['message']
                    if log['method'] == 'Network.responseReceived':
                        resp_url = log['params']['response']['url']
                        # Capture both /graphql and /api-4/graphql endpoints
                        if 'graphql' in resp_url and 'FilteredProducts' in resp_url:
                            request_id = log['params']['requestId']
                            try:
                                body = driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': request_id})
                                data = json.loads(body['body'])
                                fp = data.get('data', {}).get('filteredProducts', {})
                                if fp and 'products' in fp:
                                    for prod in fp['products']:
                                        pid = prod.get('_id') or prod.get('id')
                                        if pid:
                                            products[pid] = prod
                            except:
                                pass
                except:
                    pass
        except:
            pass
        return products

    try:
        print(f"  Loading {url}...", flush=True)
        driver.get(url)
        time.sleep(5)

        title = driver.title

        # Check for Cloudflare
        if "cloudflare" in title.lower() or "moment" in title.lower():
            print(f"  Cloudflare detected, waiting...", flush=True)
            time.sleep(10)
            title = driver.title

        if "cloudflare" in title.lower():
            print(f"  Still blocked by Cloudflare", flush=True)
            return []

        print(f"  Page loaded: {title[:50]}", flush=True)

        # Handle age gate
        try:
            buttons = driver.find_elements(By.XPATH,
                "//button[contains(text(), 'Yes') or contains(text(), 'Enter') or contains(text(), '21')]")
            if buttons:
                buttons[0].click()
                time.sleep(2)
        except:
            pass

        # Capture initial products
        all_products.update(capture_graphql())

        # Navigate categories
        base_url = url.rstrip('/').split('?')[0]

        for cat in CATEGORIES:
            cat_url = f"{base_url}/products/{cat}"

            try:
                driver.get(cat_url)
                time.sleep(2)

                # Scroll to trigger lazy loading
                prev_count = len(all_products)
                for _ in range(5):
                    driver.execute_script("window.scrollBy(0, 800)")
                    time.sleep(0.3)
                    all_products.update(capture_graphql())

                new_count = len(all_products) - prev_count
                if new_count > 0:
                    print(f"    {cat}: +{new_count} ({len(all_products)} total)", flush=True)

            except Exception as e:
                pass

        return list(all_products.values())

    except Exception as e:
        print(f"  Error: {e}", flush=True)
        return []
    finally:
        driver.quit()


def save_products(products: list, dispensary_id: str, store_name: str) -> int:
    """Save products to database."""
    if not products:
        return 0

    engine = get_engine()
    scrape_run_id = str(uuid.uuid4())
    now = datetime.utcnow()

    with engine.connect() as conn:
        # Create scrape run
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

        # Clear old products
        conn.execute(text("DELETE FROM raw_menu_item WHERE dispensary_id = :id"), {"id": dispensary_id})

        # Insert new products
        for p in products:
            try:
                name = p.get("Name") or p.get("name") or ""
                brand = p.get("brand", {})
                brand_name = brand.get("name", "") if isinstance(brand, dict) else str(brand) if brand else ""
                category = p.get("type") or p.get("category") or ""

                # Get price from Options/Prices
                price = None
                prices = p.get("Prices") or p.get("recPrices") or []
                if prices and isinstance(prices, list):
                    price = prices[0] if prices[0] else None

                product_id = p.get("_id") or p.get("id") or str(uuid.uuid4())

                conn.execute(text("""
                    INSERT INTO raw_menu_item
                    (raw_menu_item_id, dispensary_id, scrape_run_id, raw_brand, raw_name, raw_category, raw_price, provider_product_id, observed_at)
                    VALUES (:id, :dispensary_id, :scrape_run_id, :brand, :name, :category, :price, :provider_id, :observed_at)
                """), {
                    "id": str(uuid.uuid4()),
                    "dispensary_id": dispensary_id,
                    "scrape_run_id": scrape_run_id,
                    "brand": brand_name,
                    "name": name,
                    "category": category,
                    "price": price,
                    "provider_id": product_id,
                    "observed_at": now
                })
            except Exception as e:
                pass

        conn.commit()

    return len(products)


def main():
    """Main entry point."""
    # Parse arguments
    state_filter = None
    limit = 50  # Default limit

    for arg in sys.argv[1:]:
        if arg.startswith("--limit"):
            if "=" in arg:
                limit = int(arg.split("=")[1])
        elif len(arg) == 2 and arg.isupper():
            state_filter = arg

    print("="*60)
    print("DUTCHIE SCRAPER (undetected-chromedriver)")
    print("NOTE: Using headed browser - window will be visible")
    print("="*60)

    if state_filter:
        print(f"State filter: {state_filter}")
    print(f"Limit: {limit} stores")
    print()

    engine = get_engine()

    # Get stores to scrape
    query = """
        SELECT d.dispensary_id, d.name, d.state, d.menu_url
        FROM dispensary d
        LEFT JOIN raw_menu_item r ON d.dispensary_id = r.dispensary_id
        WHERE d.is_active = true
        AND d.menu_url LIKE '%dutchie.com%'
        AND r.dispensary_id IS NULL
    """
    if state_filter:
        query += f" AND d.state = '{state_filter}'"
    query += f" ORDER BY d.state, d.name LIMIT {limit}"

    with engine.connect() as conn:
        result = conn.execute(text(query))
        stores = result.fetchall()

    print(f"Found {len(stores)} stores to scrape\n")

    total_products = 0
    success_count = 0

    for i, (dispensary_id, name, state, url) in enumerate(stores, 1):
        print(f"\n[{i}/{len(stores)}] {state} - {name}")

        products = scrape_store(url, name)

        if products:
            saved = save_products(products, dispensary_id, name)
            print(f"  Saved: {saved} products")
            total_products += saved
            success_count += 1
        else:
            print(f"  No products found")

        # Brief pause between stores
        time.sleep(2)

    print(f"\n{'='*60}")
    print(f"COMPLETE: {success_count}/{len(stores)} stores, {total_products} products")
    print("="*60)


if __name__ == "__main__":
    main()
