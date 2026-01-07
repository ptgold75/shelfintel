#!/usr/bin/env python3
"""Weedmaps fallback scraper for dispensary menus."""

import requests
import uuid
import time
from datetime import datetime
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg://postgres:Tattershall2020@db.trteltlgtmcggdbrqwdw.supabase.co:5432/postgres"

# Weedmaps slug mappings for Maryland dispensaries
WEEDMAPS_SLUGS = {
    # Stores with 0 products - map to their Weedmaps slugs
    "Chesapeake Apothecary Clinton": "chesapeake-apothecary-clinton",
    "Culta Baltimore": "culta",
    "Salvera": "salvera",
    "Summit Wellness Cannabis": "summit-wellness",
    "Cookies Baltimore": "cookies-baltimore",
    "Curaleaf Columbia": "curaleaf-columbia",
    "Curaleaf Frederick": "curaleaf-frederick",
    "Curaleaf Reisterstown": "curaleaf-reisterstown",
    "Elevated Releaf": "elevated-releaf",
    "Greenlight Therapeutics": "greenlight-therapeutics",
    "HerbaFi Silver Spring": "herbafi-wellness",
    "Liberty Cannabis Oxon Hill": "liberty-oxon-hill",
    "Mana Supply Middle River": "mana-middle-river",
    "Trilogy Wellness Ellicott City": "trilogy-wellness",
    "Trulieve Halethorpe": "trulieve-halethorpe",
    "Trulieve Lutherville": "trulieve-lutherville",
    "The Apothecarium Nottingham": "the-apothecarium-nottingham",
    "The Apothecarium Salisbury": "the-apothecarium-salisbury",
    "Verilife New Market": "verilife-maryland",
    "Story Cannabis Waldorf": "story-cannabis-company",
}


def get_engine():
    return create_engine(DATABASE_URL)


def fetch_weedmaps_menu(slug: str, max_pages: int = 10) -> list:
    """Fetch all menu items from Weedmaps for a dispensary."""
    base_url = f"https://api-g.weedmaps.com/discovery/v1/listings/dispensaries/{slug}/menu_items"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    all_items = []
    page = 1
    page_size = 100

    while page <= max_pages:
        params = {
            "page_size": page_size,
            "page": page
        }

        try:
            r = requests.get(base_url, params=params, headers=headers, timeout=30)
            if r.status_code != 200:
                print(f"    Page {page}: HTTP {r.status_code}")
                break

            data = r.json()
            items = data.get("data", {}).get("menu_items", [])

            if not items:
                break

            all_items.extend(items)
            print(f"    Page {page}: {len(items)} items (total: {len(all_items)})")

            # Check if there are more pages
            meta = data.get("meta", {})
            total = meta.get("total_count", 0)
            if len(all_items) >= total:
                break

            page += 1
            time.sleep(0.5)  # Rate limiting

        except Exception as e:
            print(f"    Error on page {page}: {e}")
            break

    return all_items


def parse_weedmaps_item(item: dict) -> dict:
    """Parse a Weedmaps menu item into our format."""
    name = item.get("name", "")

    # Extract brand from name or brand field
    brand = ""
    if item.get("brand"):
        if isinstance(item["brand"], dict):
            brand = item["brand"].get("name", "")
        else:
            brand = str(item["brand"])

    # Try to extract brand from name if not present
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

    # Map Weedmaps categories to our standard categories
    category_map = {
        "Hybrid": "Flower",
        "Indica": "Flower",
        "Sativa": "Flower",
        "Pre-Roll": "Pre-Rolls",
        "Vape": "Vaporizers",
        "Concentrate": "Concentrates",
        "Edible": "Edibles",
        "Tincture": "Tinctures",
        "Topical": "Topicals",
        "Accessory": "Accessories",
    }
    category = category_map.get(category, category)

    # Price - get the first available price
    price = None
    prices = item.get("prices", {})
    if prices:
        # Try different price keys
        for key in ["unit", "half_gram", "gram", "eighth", "quarter", "half_ounce", "ounce"]:
            if key in prices and prices[key]:
                price_data = prices[key]
                if isinstance(price_data, dict):
                    price = price_data.get("price")
                else:
                    price = price_data
                if price:
                    break

    # Fallback to price field
    if not price:
        price = item.get("price")

    return {
        "name": name,
        "brand": brand,
        "category": category,
        "price": float(price) if price else None,
        "provider_id": str(item.get("id", ""))
    }


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
                print(f"    Error saving: {e}")

        conn.commit()

    return len(products)


def scrape_store(name: str, dispensary_id: str, weedmaps_slug: str) -> int:
    """Scrape a single store from Weedmaps."""
    print(f"\n{'='*50}")
    print(f"Scraping: {name}")
    print(f"Weedmaps slug: {weedmaps_slug}")

    # Fetch from Weedmaps
    items = fetch_weedmaps_menu(weedmaps_slug)

    if not items:
        print(f"  No items found")
        return 0

    # Parse items
    products = [parse_weedmaps_item(item) for item in items]

    # Filter out empty products
    products = [p for p in products if p["name"]]

    print(f"  Parsed {len(products)} products")

    # Save to database
    saved = save_products(products, dispensary_id, name)
    print(f"  Saved {saved} products")

    return saved


def main():
    """Main entry point."""
    engine = get_engine()

    # Get stores with 0 products that have Weedmaps slugs
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT d.dispensary_id, d.name
            FROM dispensary d
            LEFT JOIN raw_menu_item r ON d.dispensary_id = r.dispensary_id
            WHERE d.is_active = true
            GROUP BY d.dispensary_id, d.name
            HAVING COUNT(r.raw_menu_item_id) = 0
            ORDER BY d.name
        """))
        stores = result.fetchall()

    print(f"Found {len(stores)} stores with 0 products")

    total_scraped = 0

    for dispensary_id, name in stores:
        slug = WEEDMAPS_SLUGS.get(name)
        if not slug:
            print(f"\nSkipping {name} - no Weedmaps slug mapped")
            continue

        count = scrape_store(name, dispensary_id, slug)
        total_scraped += count
        time.sleep(1)  # Rate limiting between stores

    print(f"\n{'='*50}")
    print(f"Total scraped: {total_scraped} products")


if __name__ == "__main__":
    main()
