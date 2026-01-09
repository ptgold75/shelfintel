#!/usr/bin/env python3
"""Scrape menus from Leafly dispensary pages."""

import asyncio
import uuid
import sys
import re
from datetime import datetime
from playwright.async_api import async_playwright
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg://postgres:Tattershall2020@db.trteltlgtmcggdbrqwdw.supabase.co:5432/postgres"


def get_engine():
    return create_engine(DATABASE_URL)


async def scrape_leafly_store(url, store_name, timeout_ms=30000):
    """Scrape menu from a Leafly dispensary page."""
    all_products = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()

        try:
            # Load the menu page
            menu_url = url.rstrip('/') + '/menu'
            await page.goto(menu_url, timeout=timeout_ms, wait_until="domcontentloaded")
            await asyncio.sleep(2)

            # Scroll to load products
            for _ in range(5):
                await page.evaluate("window.scrollBy(0, 1000)")
                await asyncio.sleep(0.5)

            # Extract product data from the page
            products = await page.evaluate('''() => {
                const items = [];
                // Try to find product cards
                const cards = document.querySelectorAll('[data-testid="menu-product-card"], .product-card, [class*="ProductCard"]');
                cards.forEach(card => {
                    try {
                        const nameEl = card.querySelector('[data-testid="product-name"], h3, h4, [class*="name"]');
                        const brandEl = card.querySelector('[data-testid="product-brand"], [class*="brand"]');
                        const priceEl = card.querySelector('[data-testid="product-price"], [class*="price"]');
                        const categoryEl = card.querySelector('[class*="category"], [class*="type"]');

                        const name = nameEl ? nameEl.innerText.trim() : '';
                        const brand = brandEl ? brandEl.innerText.trim() : '';
                        const priceText = priceEl ? priceEl.innerText.trim() : '';
                        const category = categoryEl ? categoryEl.innerText.trim() : '';

                        // Extract price number
                        const priceMatch = priceText.match(/\\$([\\d.]+)/);
                        const price = priceMatch ? parseFloat(priceMatch[1]) : null;

                        if (name) {
                            items.push({name, brand, price, category});
                        }
                    } catch (e) {}
                });
                return items;
            }''')

            all_products.extend(products)

        except Exception as e:
            pass
        finally:
            await browser.close()

    return all_products


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

        saved = 0
        for p in products:
            try:
                conn.execute(text("""
                    INSERT INTO raw_menu_item
                    (raw_menu_item_id, dispensary_id, scrape_run_id, raw_brand, raw_name, raw_category, raw_price, observed_at)
                    VALUES (:id, :dispensary_id, :scrape_run_id, :brand, :name, :category, :price, :observed_at)
                """), {
                    "id": str(uuid.uuid4()),
                    "dispensary_id": dispensary_id,
                    "scrape_run_id": scrape_run_id,
                    "brand": p.get("brand", ""),
                    "name": p.get("name", ""),
                    "category": p.get("category", ""),
                    "price": p.get("price"),
                    "observed_at": now
                })
                saved += 1
            except:
                pass

        conn.commit()

    return saved


async def main():
    """Main entry point."""
    state_filter = sys.argv[1:] if len(sys.argv) > 1 else None

    print("="*60)
    print("LEAFLY MENU SCRAPER")
    if state_filter:
        print(f"States: {', '.join(state_filter)}")
    print("="*60)

    engine = get_engine()

    # Get stores with leafly URLs
    query = """
        SELECT d.dispensary_id, d.name, d.state, d.menu_url
        FROM dispensary d
        LEFT JOIN raw_menu_item r ON d.dispensary_id = r.dispensary_id
        WHERE d.is_active = true
        AND d.menu_url LIKE '%leafly.com%'
        AND r.dispensary_id IS NULL
    """
    if state_filter:
        query += f" AND d.state IN ({','.join([repr(s) for s in state_filter])})"
    query += " ORDER BY d.state, d.name LIMIT 50"

    with engine.connect() as conn:
        result = conn.execute(text(query))
        stores = result.fetchall()

    print(f"Found {len(stores)} Leafly stores to scrape\n")

    total_products = 0
    total_stores = 0

    for dispensary_id, name, state, url in stores:
        print(f"{state} - {name[:45]:45}", end=" ", flush=True)

        try:
            products = await scrape_leafly_store(url, name)

            if products:
                saved = save_products(products, dispensary_id, name)
                print(f"-> {saved} products")
                total_products += saved
                total_stores += 1
            else:
                print(f"-> 0")

        except Exception as e:
            print(f"-> error")

    print(f"\n{'='*60}")
    print(f"TOTAL: {total_stores} stores, {total_products} products")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
