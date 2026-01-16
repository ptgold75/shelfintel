#!/usr/bin/env python3
"""
Scrape high-priority California small independent stores.
Focuses on stores with known scrapable platforms (Weedmaps, Dutchie).
"""

import requests
import uuid
import time
import json
import sys
import os
import re
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.db import get_engine
from sqlalchemy import text

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}


def fetch_weedmaps_menu(slug, max_pages=10):
    """Fetch all menu items from Weedmaps for a dispensary."""
    base_url = f"https://api-g.weedmaps.com/discovery/v1/listings/dispensaries/{slug}/menu_items"

    all_items = []
    page = 1
    page_size = 100

    while page <= max_pages:
        params = {"page_size": page_size, "page": page}

        try:
            r = requests.get(base_url, params=params, headers=HEADERS, timeout=30)
            if r.status_code != 200:
                print(f"      HTTP {r.status_code}")
                break

            data = r.json()
            items = data.get("data", {}).get("menu_items", [])

            if not items:
                break

            all_items.extend(items)

            meta = data.get("meta", {})
            total = meta.get("total_count", 0)
            if len(all_items) >= total:
                break

            page += 1
            time.sleep(0.3)

        except Exception as e:
            print(f"      Error: {e}")
            break

    return all_items


def extract_weedmaps_slug(url):
    """Extract Weedmaps slug from URL."""
    # Handle different URL formats
    # https://weedmaps.com/dispensaries/store-name
    # https://storename.wm.store/
    # https://www.storename.wm.store/

    if '.wm.store' in url:
        # Handle both with and without www
        match = re.search(r'https?://(?:www\.)?([^.]+)\.wm\.store', url)
        if match:
            return match.group(1)

    if 'weedmaps.com/dispensaries/' in url:
        match = re.search(r'weedmaps\.com/dispensaries/([^/?&]+)', url)
        if match:
            return match.group(1)

    if 'weedmaps.com/deliveries/' in url:
        match = re.search(r'weedmaps\.com/deliveries/([^/?&]+)', url)
        if match:
            return match.group(1)

    return None


def safe_float(val):
    """Safely convert a value to float."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val.replace('$', '').replace(',', '').strip())
        except:
            return None
    if isinstance(val, list):
        # Take first non-null value from list
        for v in val:
            result = safe_float(v)
            if result is not None:
                return result
    if isinstance(val, dict):
        # Try to get 'price' key
        return safe_float(val.get('price'))
    return None


def parse_weedmaps_item(item):
    """Parse a Weedmaps menu item into our format."""
    name = item.get("name", "")

    # Extract brand
    brand = ""
    if item.get("brand"):
        if isinstance(item["brand"], dict):
            brand = item["brand"].get("name", "")
        else:
            brand = str(item["brand"])

    # Try to extract from name if no brand
    if not brand and " - " in name:
        parts = name.split(" - ")
        if len(parts) >= 2:
            brand = parts[0].strip()

    # Category
    category = ""
    if item.get("category"):
        if isinstance(item["category"], dict):
            category = item["category"].get("name", "")
        else:
            category = str(item["category"])

    # Map categories
    category_map = {
        "Hybrid": "Flower", "Indica": "Flower", "Sativa": "Flower",
        "Pre-Roll": "Pre-Rolls", "Vape": "Vaporizers",
        "Concentrate": "Concentrates", "Edible": "Edibles",
        "Tincture": "Tinctures", "Topical": "Topicals",
    }
    category = category_map.get(category, category)

    # Prices with all size variants
    prices = item.get("prices", {})
    price_data = {}

    size_map = {
        "unit": "unit",
        "half_gram": "0.5g",
        "gram": "1g",
        "eighth": "3.5g",
        "quarter": "7g",
        "half_ounce": "14g",
        "ounce": "28g"
    }

    primary_price = None

    for key, size_label in size_map.items():
        if key in prices and prices[key]:
            val = safe_float(prices[key])
            if val:
                price_data[size_label] = val
                if primary_price is None:
                    primary_price = val

    # Fallback to single price field
    if not primary_price:
        primary_price = safe_float(item.get("price"))

    return {
        "name": name,
        "brand": brand,
        "category": category,
        "price": primary_price,
        "all_prices": price_data,
        "thc": item.get("thc_percentage"),
        "cbd": item.get("cbd_percentage"),
        "provider_id": str(item.get("id", "")),
        "raw_json": json.dumps(item)  # Store full item for reference
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

    # Insert products - using correct column names for raw_menu_item table
    for p in products:
        item_id = str(uuid.uuid4())
        conn.execute(text("""
            INSERT INTO raw_menu_item (
                raw_menu_item_id, dispensary_id, scrape_run_id, raw_name, raw_brand, raw_category,
                raw_price, raw_thc, raw_cbd, provider_product_id, raw_json, observed_at
            )
            VALUES (
                :item_id, :dispensary_id, :scrape_run_id, :raw_name, :raw_brand, :raw_category,
                :raw_price, :raw_thc, :raw_cbd, :provider_product_id, :raw_json, :observed_at
            )
        """), {
            "item_id": item_id,
            "dispensary_id": dispensary_id,
            "scrape_run_id": scrape_run_id,
            "raw_name": p["name"],
            "raw_brand": p["brand"],
            "raw_category": p["category"],
            "raw_price": p["price"],
            "raw_thc": str(p["thc"]) if p["thc"] else None,
            "raw_cbd": str(p["cbd"]) if p["cbd"] else None,
            "provider_product_id": p["provider_id"],
            "raw_json": p.get("raw_json"),
            "observed_at": now
        })

    conn.commit()
    return len(products)


def scrape_weedmaps_store(engine, dispensary_id, name, url):
    """Scrape a single Weedmaps store."""
    slug = extract_weedmaps_slug(url)
    if not slug:
        print(f"  Could not extract slug from: {url}")
        return 0

    print(f"  Fetching menu for slug: {slug}")
    items = fetch_weedmaps_menu(slug)

    if not items:
        print(f"    No items found")
        return 0

    products = [parse_weedmaps_item(item) for item in items]

    # Use fresh connection for each store to avoid transaction issues
    with engine.connect() as conn:
        try:
            count = save_menu_items(conn, dispensary_id, products, name)
            print(f"    Saved {count} products")
            return count
        except Exception as e:
            conn.rollback()
            raise e


def main():
    """Main scraping function."""
    engine = get_engine()

    print("=" * 60)
    print("CA Small Independent Store Scraper")
    print("=" * 60)

    # Get list of stores to scrape
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT d.dispensary_id, d.name, d.city, d.menu_url
            FROM dispensary d
            WHERE d.state = 'CA' AND d.is_active = true
            AND (d.menu_url ILIKE '%weedmaps%' OR d.menu_url ILIKE '%.wm.store%')
            AND NOT EXISTS (
                SELECT 1 FROM raw_menu_item r WHERE r.dispensary_id = d.dispensary_id
            )
            ORDER BY d.name
        """))
        stores = list(result)

    print(f"\nFound {len(stores)} Weedmaps CA stores to scrape\n")

    total_products = 0
    stores_scraped = 0

    for i, (disp_id, name, city, url) in enumerate(stores, 1):
        print(f"\n[{i}/{len(stores)}] {name} ({city})")
        print(f"  URL: {url}")

        try:
            count = scrape_weedmaps_store(engine, disp_id, name, url)
            if count > 0:
                stores_scraped += 1
                total_products += count
        except Exception as e:
            print(f"  ERROR: {e}")

        # Rate limiting
        time.sleep(1)

    print("\n" + "=" * 60)
    print(f"Summary:")
    print(f"  Stores attempted: {len(stores)}")
    print(f"  Stores with data: {stores_scraped}")
    print(f"  Total products: {total_products}")
    print("=" * 60)


if __name__ == "__main__":
    main()
