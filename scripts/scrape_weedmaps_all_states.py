#!/usr/bin/env python3
"""Comprehensive Weedmaps scraper for all US states."""

import requests
import uuid
import time
import json
import sys
import os
from datetime import datetime
from sqlalchemy import create_engine, text

# Database connection
DATABASE_URL = "postgresql+psycopg://postgres:Tattershall2020@db.trteltlgtmcggdbrqwdw.supabase.co:5432/postgres"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}

# All US states with legal cannabis
STATES = [
    ("california", "CA"), ("colorado", "CO"), ("illinois", "IL"), ("michigan", "MI"),
    ("arizona", "AZ"), ("nevada", "NV"), ("massachusetts", "MA"), ("new-jersey", "NJ"),
    ("new-york", "NY"), ("florida", "FL"), ("pennsylvania", "PA"), ("maryland", "MD"),
    ("ohio", "OH"), ("missouri", "MO"), ("connecticut", "CT"), ("new-mexico", "NM"),
    ("maine", "ME"), ("vermont", "VT"), ("montana", "MT"), ("oregon", "OR"),
    ("washington", "WA"), ("alaska", "AK"), ("oklahoma", "OK"), ("virginia", "VA"),
    ("minnesota", "MN"), ("delaware", "DE"), ("rhode-island", "RI"), ("hawaii", "HI"),
    ("arkansas", "AR"), ("louisiana", "LA"), ("mississippi", "MS"), ("utah", "UT"),
    ("west-virginia", "WV"), ("south-dakota", "SD"), ("north-dakota", "ND"),
    ("district-of-columbia", "DC"),
]


def get_engine():
    return create_engine(DATABASE_URL)


def fetch_weedmaps_dispensaries(state_slug, page=1, page_size=100):
    """Fetch dispensaries from Weedmaps for a state."""
    url = f"https://api-g.weedmaps.com/discovery/v2/listings"
    params = {
        "filter[region_slug[dispensaries]]": state_slug,
        "filter[license_type]": "recreational,medical",
        "page[size]": page_size,
        "page[number]": page,
        "sort_by": "name",
    }

    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if r.status_code == 200:
            return r.json()
        else:
            print(f"    HTTP {r.status_code}")
            return None
    except Exception as e:
        print(f"    Error: {e}")
        return None


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
            print(f"      Menu error: {e}")
            break

    return all_items


def parse_menu_item(item):
    """Parse a Weedmaps menu item."""
    name = item.get("name", "")

    brand = ""
    if item.get("brand"):
        if isinstance(item["brand"], dict):
            brand = item["brand"].get("name", "")
        else:
            brand = str(item["brand"])

    if not brand and " - " in name:
        parts = name.split(" - ")
        if len(parts) >= 2:
            brand = parts[0].strip()

    category = ""
    if item.get("category"):
        if isinstance(item["category"], dict):
            category = item["category"].get("name", "")
        else:
            category = str(item["category"])

    category_map = {
        "Hybrid": "Flower", "Indica": "Flower", "Sativa": "Flower",
        "Pre-Roll": "Pre-Rolls", "Vape": "Vaporizers",
        "Concentrate": "Concentrates", "Edible": "Edibles",
        "Tincture": "Tinctures", "Topical": "Topicals",
    }
    category = category_map.get(category, category)

    price = None
    prices = item.get("prices", {})
    if prices:
        for key in ["unit", "half_gram", "gram", "eighth", "quarter", "half_ounce", "ounce"]:
            if key in prices and prices[key]:
                price_data = prices[key]
                if isinstance(price_data, dict):
                    price = price_data.get("price")
                else:
                    price = price_data
                if price:
                    break

    if not price:
        price = item.get("price")

    return {
        "name": name,
        "brand": brand,
        "category": category,
        "price": float(price) if price else None,
        "provider_id": str(item.get("id", ""))
    }


def get_or_create_dispensary(conn, name, state, address=None, city=None, slug=None):
    """Get existing dispensary or create new one."""
    # Check if exists by name and state
    result = conn.execute(text("""
        SELECT dispensary_id FROM dispensary
        WHERE LOWER(name) = LOWER(:name) AND state = :state
        LIMIT 1
    """), {"name": name, "state": state})
    row = result.fetchone()

    if row:
        return row[0]

    # Create new
    dispensary_id = str(uuid.uuid4())
    conn.execute(text("""
        INSERT INTO dispensary (dispensary_id, name, state, address, city, menu_provider, is_active, source)
        VALUES (:id, :name, :state, :address, :city, 'weedmaps', true, 'weedmaps')
        ON CONFLICT DO NOTHING
    """), {
        "id": dispensary_id,
        "name": name,
        "state": state,
        "address": address,
        "city": city,
    })
    conn.commit()
    return dispensary_id


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
        except Exception as e:
            pass

    conn.commit()
    return len(products)


def scrape_state(state_slug, state_abbrev, engine):
    """Scrape all dispensaries in a state."""
    print(f"\n{'='*60}")
    print(f"SCRAPING {state_abbrev} ({state_slug})")
    print('='*60)

    total_dispensaries = 0
    total_products = 0
    page = 1

    while True:
        print(f"  Fetching page {page}...")
        data = fetch_weedmaps_dispensaries(state_slug, page)

        if not data:
            break

        listings = data.get("data", {}).get("listings", [])
        if not listings:
            print(f"  No more listings")
            break

        print(f"  Found {len(listings)} dispensaries")

        with engine.connect() as conn:
            for listing in listings:
                try:
                    name = listing.get("name", "")
                    slug = listing.get("slug", "")
                    city = listing.get("city", "")
                    address = listing.get("address", "")

                    if not name or not slug:
                        continue

                    print(f"    {name[:45]:45}", end=" ", flush=True)

                    # Get or create dispensary
                    dispensary_id = get_or_create_dispensary(conn, name, state_abbrev, address, city, slug)

                    # Fetch menu
                    menu_items = fetch_weedmaps_menu(slug)

                    if menu_items:
                        products = [parse_menu_item(item) for item in menu_items]
                        products = [p for p in products if p["name"]]

                        saved = save_menu_items(conn, dispensary_id, products, name)
                        print(f"-> {saved} products")
                        total_products += saved
                    else:
                        print(f"-> 0 products")

                    total_dispensaries += 1
                    time.sleep(0.5)

                except Exception as e:
                    print(f"  Error: {e}")
                    continue

        # Check for more pages
        meta = data.get("meta", {})
        total_pages = meta.get("total_pages", 1)
        if page >= total_pages:
            break

        page += 1
        time.sleep(1)

    print(f"\n  {state_abbrev} TOTAL: {total_dispensaries} dispensaries, {total_products} products")
    return total_dispensaries, total_products


def main():
    """Main entry point."""
    print("="*60)
    print("WEEDMAPS MULTI-STATE SCRAPER")
    print("="*60)

    engine = get_engine()

    # Filter to specific states if provided
    target_states = STATES
    if len(sys.argv) > 1:
        state_filter = [s.upper() for s in sys.argv[1:]]
        target_states = [(slug, abbrev) for slug, abbrev in STATES if abbrev in state_filter]
        print(f"Filtering to states: {state_filter}")

    grand_total_dispensaries = 0
    grand_total_products = 0

    for state_slug, state_abbrev in target_states:
        try:
            disp, prods = scrape_state(state_slug, state_abbrev, engine)
            grand_total_dispensaries += disp
            grand_total_products += prods
        except Exception as e:
            print(f"Error scraping {state_abbrev}: {e}")
            continue

    print(f"\n{'='*60}")
    print(f"GRAND TOTAL: {grand_total_dispensaries} dispensaries, {grand_total_products} products")
    print('='*60)


if __name__ == "__main__":
    main()
