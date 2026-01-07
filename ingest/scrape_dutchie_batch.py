#!/usr/bin/env python3
"""Batch scraper for Dutchie stores using Playwright + proxy."""

import asyncio
import uuid
import os
import sys
from datetime import datetime
from playwright.async_api import async_playwright
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Proxy config
PROXY_HOST = os.getenv("PROXY_HOST", "gate.decodo.com")
PROXY_USER = os.getenv("PROXY_USER", "spn1pjbpd4")
PROXY_PASS = os.getenv("PROXY_PASS", "k0xH_iq29reyWfz3JR")

# Rotating proxy ports
PORTS = [10002, 10003, 10004, 10005, 10006, 10007, 10008, 10009, 10010]
port_idx = 0

# Categories to scrape
CATEGORIES = ["flower", "vaporizers", "pre-rolls", "edibles", "concentrates", "tinctures", "topicals", "accessories"]

DATABASE_URL = "postgresql+psycopg://postgres:Tattershall2020@db.trteltlgtmcggdbrqwdw.supabase.co:5432/postgres"


def get_port():
    """Get next rotating port."""
    global port_idx
    port = PORTS[port_idx % len(PORTS)]
    port_idx += 1
    return port


def get_engine():
    return create_engine(DATABASE_URL)


async def scrape_dutchie_store(base_url: str, store_name: str) -> list:
    """Scrape a Dutchie store using category navigation."""
    port = get_port()
    all_products = {}

    print(f"  Using proxy port {port}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            proxy={
                "server": f"http://{PROXY_HOST}:{port}",
                "username": PROXY_USER,
                "password": PROXY_PASS
            }
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
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
            # First try to load the base URL
            print(f"  Loading {base_url}...")
            await page.goto(base_url, timeout=60000, wait_until="networkidle")
            await asyncio.sleep(3)

            # Handle age gate if present
            try:
                age_button = page.locator("button:has-text('Yes'), button:has-text('I am'), button:has-text('Enter'), button:has-text('21')")
                if await age_button.count() > 0:
                    print("  Clicking age gate...")
                    await age_button.first.click()
                    await asyncio.sleep(2)
            except:
                pass

            # Navigate each category
            for cat in CATEGORIES:
                cat_url = f"{base_url.rstrip('/')}/products/{cat}"
                print(f"  Category: {cat}...", end=" ", flush=True)

                try:
                    await page.goto(cat_url, timeout=45000)
                    await asyncio.sleep(2)

                    # Scroll to load all products
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
                    print(f"error: {str(e)[:50]}")

        except Exception as e:
            print(f"  Error: {e}")
        finally:
            await browser.close()

    return list(all_products.values())


def save_products(products: list, dispensary_id: str, store_name: str) -> int:
    """Save products to database."""
    if not products:
        print(f"  No products to save")
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
                name = p.get("name", "") or ""
                brand = p.get("brand", {})
                brand_name = brand.get("name", "") if isinstance(brand, dict) else str(brand) if brand else ""
                category = p.get("category", "") or ""

                # Get price
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
                print(f"    Error saving product: {e}")

        conn.commit()

    print(f"  Saved {len(products)} products")
    return len(products)


async def main():
    """Main entry point."""
    engine = get_engine()

    # Get stores to scrape
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT d.dispensary_id, d.name, d.menu_url
            FROM dispensary d
            LEFT JOIN raw_menu_item r ON d.dispensary_id = r.dispensary_id
            WHERE d.is_active = true AND d.menu_provider = 'dutchie'
            GROUP BY d.dispensary_id, d.name, d.menu_url
            HAVING COUNT(r.raw_menu_item_id) = 0
            ORDER BY d.name
        """))
        stores = result.fetchall()

    print(f"Found {len(stores)} Dutchie stores to scrape\n")

    for dispensary_id, name, url in stores:
        if not url:
            print(f"Skipping {name} - no URL")
            continue

        print(f"\n{'='*60}")
        print(f"Scraping: {name}")
        print(f"URL: {url}")

        products = await scrape_dutchie_store(url, name)

        if products:
            save_products(products, dispensary_id, name)
        else:
            print(f"  No products found")

    print(f"\n{'='*60}")
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
