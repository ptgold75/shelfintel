#!/usr/bin/env python3
"""Scrape dispensary menus from Jane (iheartjane.com)."""

import requests
import uuid
import time
import re
import json
import sys
from datetime import datetime
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg://postgres:Tattershall2020@db.trteltlgtmcggdbrqwdw.supabase.co:5432/postgres"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}


def get_engine():
    return create_engine(DATABASE_URL)


def extract_jane_store_id(url):
    """Extract store ID from Jane URL."""
    if not url:
        return None

    # Match patterns like /stores/1234/ or /stores/1234/store-name
    match = re.search(r'/stores/(\d+)', url)
    if match:
        return match.group(1)
    return None


def fetch_jane_menu(store_id, max_pages=20):
    """Fetch menu items from Jane API."""
    all_products = []
    page = 1
    page_size = 100

    while page <= max_pages:
        url = f"https://api.iheartjane.com/v1/stores/{store_id}/products"
        params = {
            "page": page,
            "per_page": page_size
        }

        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=30)
            if r.status_code == 404:
                print(f"      Store {store_id} not found")
                break
            elif r.status_code != 200:
                print(f"      HTTP {r.status_code}")
                break

            data = r.json()
            products = data.get("data", [])

            if not products:
                break

            all_products.extend(products)

            # Check pagination
            meta = data.get("meta", {})
            total_pages = meta.get("total_pages", 1)
            if page >= total_pages:
                break

            page += 1
            time.sleep(0.3)

        except Exception as e:
            print(f"      Error: {e}")
            break

    return all_products


def parse_jane_product(item):
    """Parse a Jane product into our format."""
    name = item.get("name", "")
    brand = item.get("brand", {}).get("name", "") if isinstance(item.get("brand"), dict) else str(item.get("brand", ""))

    category = item.get("kind", "") or item.get("category", "")

    # Map Jane categories
    category_map = {
        "flower": "Flower",
        "preroll": "Pre-Rolls",
        "pre-roll": "Pre-Rolls",
        "vape": "Vaporizers",
        "vaporizer": "Vaporizers",
        "concentrate": "Concentrates",
        "edible": "Edibles",
        "tincture": "Tinctures",
        "topical": "Topicals",
        "accessory": "Accessories",
    }
    category = category_map.get(category.lower(), category.title())

    # Get price
    price = None
    if item.get("prices"):
        prices = item["prices"]
        if isinstance(prices, list) and prices:
            price = prices[0].get("price") or prices[0].get("amount")
        elif isinstance(prices, dict):
            price = prices.get("price") or prices.get("unit")

    if not price:
        price = item.get("price") or item.get("min_price")

    return {
        "name": name,
        "brand": brand,
        "category": category,
        "price": float(price) if price else None,
        "provider_id": str(item.get("id", ""))
    }


def save_menu_items(conn, dispensary_id, products, store_name):
    """Save menu items to database."""
    if not products:
        return 0

    scrape_run_id = str(uuid.uuid4())
    now = datetime.utcnow()

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
    saved = 0
    for p in products:
        try:
            conn.execute(text("""
                INSERT INTO raw_menu_item
                (raw_menu_item_id, dispensary_id, scrape_run_id, raw_brand, raw_name, raw_category, raw_price, provider_product_id, observed_at)
                VALUES (:id, :dispensary_id, :scrape_run_id, :brand, :name, :category, :price, :provider_id, :observed_at)
            """), {
                "id": str(uuid.uuid4()),
                "dispensary_id": dispensary_id,
                "scrape_run_id": scrape_run_id,
                "brand": p["brand"],
                "name": p["name"],
                "category": p["category"],
                "price": p["price"],
                "provider_id": p["provider_id"],
                "observed_at": now
            })
            saved += 1
        except Exception as e:
            pass

    conn.commit()
    return saved


def main():
    """Main entry point."""
    print("="*60)
    print("JANE STORES SCRAPER")
    print("="*60)

    engine = get_engine()

    # Get Jane stores with iheartjane.com URLs that need scraping
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT d.dispensary_id, d.name, d.state, d.menu_url
            FROM dispensary d
            LEFT JOIN raw_menu_item r ON d.dispensary_id = r.dispensary_id
            WHERE d.is_active = true
            AND (d.menu_url LIKE '%iheartjane.com%' OR d.menu_provider = 'jane')
            AND r.dispensary_id IS NULL
            ORDER BY d.state, d.name
        """))
        stores = result.fetchall()

    print(f"Found {len(stores)} Jane stores to scrape\n")

    total_products = 0
    total_stores = 0

    for dispensary_id, name, state, menu_url in stores:
        store_id = extract_jane_store_id(menu_url)

        if not store_id:
            print(f"  {state} - {name[:40]:40} -> No store ID in URL: {menu_url}")
            continue

        print(f"  {state} - {name[:40]:40} (ID: {store_id})", end=" ", flush=True)

        try:
            # Fetch menu
            products_raw = fetch_jane_menu(store_id)

            if products_raw:
                products = [parse_jane_product(p) for p in products_raw]
                products = [p for p in products if p["name"]]

                with engine.connect() as conn:
                    saved = save_menu_items(conn, dispensary_id, products, name)

                print(f"-> {saved} products")
                total_products += saved
                total_stores += 1
            else:
                print(f"-> 0 products")

            time.sleep(0.5)

        except Exception as e:
            print(f"-> Error: {e}")

    print(f"\n{'='*60}")
    print(f"TOTAL: {total_stores} stores, {total_products} products")
    print("="*60)


if __name__ == "__main__":
    main()
