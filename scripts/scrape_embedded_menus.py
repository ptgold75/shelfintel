#!/usr/bin/env python3
"""
Scrape dispensary menus using Playwright to bypass Cloudflare.
Works for Dutchie-embedded sites and native platforms like Curaleaf.
"""

import asyncio
import re
import json
import uuid
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.async_api import async_playwright
from core.db import get_engine
from sqlalchemy import text

# Proxy support
try:
    from ingest.proxy_config import get_playwright_proxy
    PROXY_AVAILABLE = True
except ImportError:
    PROXY_AVAILABLE = False


async def scrape_dutchie_embedded(url, name):
    """Scrape a Dutchie-embedded menu by capturing GraphQL responses."""
    products = {}

    # Get proxy config if available
    proxy_config = None
    if PROXY_AVAILABLE:
        proxy_config = get_playwright_proxy(force_rotate=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            proxy=proxy_config,
        )
        page = await context.new_page()

        async def capture_response(response):
            if response.status != 200:
                return
            resp_url = response.url.lower()

            # Capture Dutchie GraphQL responses
            if 'dutchie' in resp_url and ('graphql' in resp_url or 'api' in resp_url):
                try:
                    data = await response.json()

                    # Look for products in various response shapes
                    def extract_products(obj, path=""):
                        if isinstance(obj, dict):
                            # Check for product arrays
                            for key in ['products', 'menuProducts', 'filteredProducts', 'items']:
                                if key in obj:
                                    items = obj[key]
                                    if isinstance(items, dict) and 'products' in items:
                                        items = items['products']
                                    if isinstance(items, list):
                                        for item in items:
                                            if isinstance(item, dict):
                                                pid = item.get('id') or item.get('_id')
                                                if pid and item.get('name'):
                                                    products[pid] = item
                            # Recurse
                            for k, v in obj.items():
                                extract_products(v, f"{path}.{k}")
                        elif isinstance(obj, list):
                            for i, v in enumerate(obj):
                                extract_products(v, f"{path}[{i}]")

                    extract_products(data)
                except:
                    pass

        page.on("response", capture_response)

        try:
            print(f"  Loading {url[:60]}...")
            await page.goto(url, timeout=45000, wait_until="domcontentloaded")
            await asyncio.sleep(2)

            # Handle age gates
            for selector in ["button:has-text('Yes')", "button:has-text('YES')",
                           "button:has-text('Enter')", "button:has-text('21')",
                           "button:has-text('I am')", "[data-testid='age-gate-yes']"]:
                try:
                    btn = page.locator(selector)
                    if await btn.count() > 0:
                        await btn.first.click()
                        await asyncio.sleep(2)
                        break
                except:
                    pass

            await asyncio.sleep(3)

            # Scroll to trigger lazy loading
            prev_count = 0
            no_change = 0
            while no_change < 5:
                await page.evaluate("window.scrollBy(0, 800)")
                await asyncio.sleep(0.5)
                if len(products) == prev_count:
                    no_change += 1
                else:
                    no_change = 0
                prev_count = len(products)

            # Try navigating to menu/categories if available
            for cat in ['flower', 'vaporizers', 'edibles', 'concentrates', 'pre-rolls']:
                try:
                    cat_link = page.locator(f"a:has-text('{cat}')")
                    if await cat_link.count() > 0:
                        await cat_link.first.click()
                        await asyncio.sleep(2)
                        # Scroll in category
                        for _ in range(3):
                            await page.evaluate("window.scrollBy(0, 800)")
                            await asyncio.sleep(0.5)
                except:
                    pass

        except Exception as e:
            print(f"  Error: {e}")
        finally:
            await browser.close()

    return list(products.values())


async def scrape_curaleaf(url, name):
    """Scrape Curaleaf menu using their native site."""
    products = {}

    # Get proxy config if available
    proxy_config = None
    if PROXY_AVAILABLE:
        proxy_config = get_playwright_proxy(force_rotate=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            proxy=proxy_config,
        )
        page = await context.new_page()

        async def capture_response(response):
            if response.status != 200:
                return
            resp_url = response.url

            # Curaleaf uses GraphQL
            if 'graphql' in resp_url.lower() or 'api' in resp_url.lower():
                try:
                    data = await response.json()

                    def extract_products(obj):
                        if isinstance(obj, dict):
                            # Look for product data
                            if 'products' in obj:
                                for item in obj['products']:
                                    if isinstance(item, dict) and item.get('name'):
                                        pid = item.get('id') or item.get('productId')
                                        if pid:
                                            products[pid] = item
                            # Check for menu items
                            if 'menuItems' in obj or 'items' in obj:
                                items = obj.get('menuItems') or obj.get('items', [])
                                for item in items:
                                    if isinstance(item, dict) and item.get('name'):
                                        pid = item.get('id') or item.get('productId')
                                        if pid:
                                            products[pid] = item
                            # Recurse
                            for v in obj.values():
                                extract_products(v)
                        elif isinstance(obj, list):
                            for v in obj:
                                extract_products(v)

                    extract_products(data)
                except:
                    pass

        page.on("response", capture_response)

        try:
            print(f"  Loading {url[:60]}...")
            await page.goto(url, timeout=45000, wait_until="domcontentloaded")
            await asyncio.sleep(2)

            # Handle Curaleaf age gate
            try:
                yes_btn = page.locator("button:has-text('YES'), button:has-text('Yes')")
                if await yes_btn.count() > 0:
                    await yes_btn.first.click()
                    await asyncio.sleep(3)
            except:
                pass

            await asyncio.sleep(4)

            # Scroll extensively
            for i in range(10):
                await page.evaluate("window.scrollBy(0, 600)")
                await asyncio.sleep(0.5)

            # Try clicking category tabs
            categories = ['Flower', 'Vaporizers', 'Edibles', 'Concentrates', 'Pre-Rolls', 'Topicals']
            for cat in categories:
                try:
                    cat_btn = page.locator(f"button:has-text('{cat}'), a:has-text('{cat}')")
                    if await cat_btn.count() > 0:
                        await cat_btn.first.click()
                        await asyncio.sleep(2)
                        for _ in range(5):
                            await page.evaluate("window.scrollBy(0, 600)")
                            await asyncio.sleep(0.3)
                except:
                    pass

        except Exception as e:
            print(f"  Error: {e}")
        finally:
            await browser.close()

    return list(products.values())


def parse_product(item, source="dutchie"):
    """Parse a product item into our standard format."""
    name = item.get('name', '')

    # Extract brand
    brand = ''
    brand_obj = item.get('brand')
    if brand_obj:
        if isinstance(brand_obj, dict):
            brand = brand_obj.get('name', '')
        else:
            brand = str(brand_obj)

    # Extract category
    category = ''
    cat_obj = item.get('category') or item.get('type')
    if cat_obj:
        if isinstance(cat_obj, dict):
            category = cat_obj.get('name', '')
        else:
            category = str(cat_obj)

    # Extract price
    price = None

    # Try variants first (Dutchie)
    variants = item.get('variants', [])
    if variants and isinstance(variants, list) and len(variants) > 0:
        v = variants[0]
        if isinstance(v, dict):
            price = v.get('price') or v.get('priceRec') or v.get('priceMed')

    # Try prices object
    if not price:
        prices = item.get('prices', {})
        if isinstance(prices, dict):
            for key in ['unit', 'gram', 'eighth', 'quarter']:
                if key in prices and prices[key]:
                    p = prices[key]
                    if isinstance(p, (int, float)):
                        price = p
                    elif isinstance(p, dict):
                        price = p.get('price')
                    elif isinstance(p, list) and len(p) > 0:
                        price = p[0].get('price') if isinstance(p[0], dict) else p[0]
                    if price:
                        break

    # Try direct price field
    if not price:
        price = item.get('price') or item.get('priceRec')

    return {
        'name': name,
        'brand': brand,
        'category': category,
        'price': float(price) if price else None,
        'provider_id': str(item.get('id') or item.get('_id') or ''),
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

        for p in products:
            parsed = parse_product(p)
            conn.execute(text("""
                INSERT INTO raw_menu_item
                (raw_menu_item_id, dispensary_id, scrape_run_id, raw_brand, raw_name, raw_category, raw_price, provider_product_id, observed_at)
                VALUES (:id, :dispensary_id, :scrape_run_id, :brand, :name, :category, :price, :provider_id, :observed_at)
            """), {
                "id": str(uuid.uuid4()),
                "dispensary_id": dispensary_id,
                "scrape_run_id": scrape_run_id,
                "brand": parsed['brand'],
                "name": parsed['name'],
                "category": parsed['category'],
                "price": parsed['price'],
                "provider_id": parsed['provider_id'],
                "observed_at": now
            })

        conn.commit()

    return len(products)


async def main():
    """Main entry point."""
    print("=" * 60)
    print("EMBEDDED MENU SCRAPER")
    print("=" * 60)

    engine = get_engine()

    # Define stores to scrape
    stores = [
        # Dutchie-embedded stores
        ("Salvera", "https://www.salveramd.com/menu/", "dutchie"),
        ("Storehouse Baltimore", "https://storehousemd.com/dutchie/", "dutchie"),
        ("Mary & Main Capitol Heights", "https://maryandmain.com/", "dutchie"),
        ("Elevated Releaf", "https://elevatedreleaf.com/eldersburg-dispensary-menu/", "dutchie"),
        ("Chesapeake Apothecary Clinton", "https://www.chesapeakeapothecary.com/menu-clinton-chesapeakenorth/", "dutchie"),
        ("Mana Supply Middle River", "https://manasupply.com/shop/middle-river-maryland/", "dutchie"),
        ("Liberty Cannabis Rockville", "https://libertycannabis.com/shop/rockville/", "dutchie"),
        # Curaleaf
        ("Curaleaf MD Gaithersburg", "https://curaleaf.com/shop/maryland/curaleaf-md-gaithersburg", "curaleaf"),
    ]

    total_products = 0
    total_stores = 0

    for name, url, platform in stores:
        print(f"\n{'=' * 50}")
        print(f"{name} ({platform})")

        # Get dispensary_id
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT dispensary_id FROM dispensary
                WHERE state = 'MD' AND name ILIKE :name
            """), {"name": f"%{name.split()[0]}%"})
            row = result.fetchone()

        if not row:
            print(f"  Not found in database, skipping")
            continue

        dispensary_id = row[0]

        try:
            if platform == "dutchie":
                products = await scrape_dutchie_embedded(url, name)
            elif platform == "curaleaf":
                products = await scrape_curaleaf(url, name)
            else:
                products = []

            if products:
                saved = save_products(products, dispensary_id, name)
                print(f"  Saved: {saved} products")
                total_products += saved
                total_stores += 1
            else:
                print(f"  No products found")

        except Exception as e:
            print(f"  Error: {e}")

    print(f"\n{'=' * 60}")
    print(f"TOTAL: {total_stores} stores, {total_products} products")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
