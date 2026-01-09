#!/usr/bin/env python3
"""Direct Dutchie scraper using Playwright - scrapes stores with dutchie.com URLs."""

import asyncio
import uuid
import sys
from datetime import datetime
from playwright.async_api import async_playwright
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg://postgres:Tattershall2020@db.trteltlgtmcggdbrqwdw.supabase.co:5432/postgres"

CATEGORIES = ["flower", "vaporizers", "pre-rolls", "edibles", "concentrates", "tinctures", "topicals"]


def get_engine():
    return create_engine(DATABASE_URL)


async def scrape_store(url, store_name):
    """Scrape a single Dutchie store."""
    all_products = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()

        async def capture_response(response):
            if "graphql" in response.url and response.status == 200:
                try:
                    data = await response.json()
                    fp = data.get("data", {}).get("filteredProducts", {})
                    if fp and isinstance(fp, dict) and "products" in fp:
                        for prod in fp.get("products", []):
                            pid = prod.get("_id") or prod.get("id")
                            if pid:
                                all_products[pid] = prod
                except:
                    pass

        page.on("response", capture_response)

        try:
            # Load base URL
            print(f"  Loading {url}...", flush=True)
            await page.goto(url, timeout=60000, wait_until="networkidle")
            await asyncio.sleep(3)

            # Handle age gate
            try:
                age_button = page.locator("button:has-text('Yes'), button:has-text('I am'), button:has-text('Enter'), button:has-text('21')")
                if await age_button.count() > 0:
                    await age_button.first.click()
                    await asyncio.sleep(2)
            except:
                pass

            # Navigate categories
            for cat in CATEGORIES:
                base = url.rstrip('/').split('?')[0]
                cat_url = f"{base}/products/{cat}"
                print(f"    {cat}...", end=" ", flush=True)

                try:
                    await page.goto(cat_url, timeout=45000)
                    await asyncio.sleep(2)

                    # Scroll to load products
                    prev_count = 0
                    no_change = 0
                    while no_change < 4:
                        await page.evaluate("window.scrollBy(0, 1000)")
                        await asyncio.sleep(0.4)
                        if len(all_products) == prev_count:
                            no_change += 1
                        else:
                            no_change = 0
                        prev_count = len(all_products)

                    print(f"{len(all_products)} total")
                except Exception as e:
                    print(f"error")

        except Exception as e:
            print(f"  Error: {e}")
        finally:
            await browser.close()

    return list(all_products.values())


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

        conn.execute(text("DELETE FROM raw_menu_item WHERE dispensary_id = :id"), {"id": dispensary_id})

        for p in products:
            try:
                name = p.get("name", "") or ""
                brand = p.get("brand", {})
                brand_name = brand.get("name", "") if isinstance(brand, dict) else str(brand) if brand else ""
                category = p.get("category", "") or ""

                prices = p.get("variants", [])
                price = None
                if prices:
                    first_variant = prices[0]
                    if isinstance(first_variant, dict):
                        price = first_variant.get("price") or first_variant.get("priceRec")

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


async def main():
    """Main entry point."""
    print("="*60)
    print("DUTCHIE DIRECT SCRAPER")
    print("="*60)

    engine = get_engine()

    # Get stores with dutchie.com URLs
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT d.dispensary_id, d.name, d.state, d.menu_url
            FROM dispensary d
            LEFT JOIN raw_menu_item r ON d.dispensary_id = r.dispensary_id
            WHERE d.is_active = true
            AND (d.menu_url LIKE '%dutchie.com%' OR d.menu_url LIKE '%dutchie.%')
            AND r.dispensary_id IS NULL
            ORDER BY d.state, d.name
            LIMIT 50
        """))
        stores = result.fetchall()

    print(f"Found {len(stores)} stores to scrape\n")

    total_products = 0
    total_stores = 0

    for dispensary_id, name, state, url in stores:
        print(f"\n{'='*50}")
        print(f"{state} - {name}")
        print(f"URL: {url}")

        try:
            products = await scrape_store(url, name)

            if products:
                saved = save_products(products, dispensary_id, name)
                print(f"  Saved: {saved} products")
                total_products += saved
                total_stores += 1
            else:
                print(f"  No products found")

        except Exception as e:
            print(f"  Error: {e}")

    print(f"\n{'='*60}")
    print(f"TOTAL: {total_stores} stores, {total_products} products")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
