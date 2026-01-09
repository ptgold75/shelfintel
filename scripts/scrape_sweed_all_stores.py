#!/usr/bin/env python3
"""Comprehensive Sweed scraper for all stores with Sweed store IDs."""

import json
import uuid
import time
import sys
from datetime import datetime
from sqlalchemy import create_engine, text

sys.path.insert(0, '/Users/gleaf/shelfintel')
from ingest.providers.sweed_api import (
    get_categories,
    fetch_all_products_for_category,
    normalize_sweed_product
)

DATABASE_URL = "postgresql+psycopg://postgres:Tattershall2020@db.trteltlgtmcggdbrqwdw.supabase.co:5432/postgres"


def get_engine():
    return create_engine(DATABASE_URL)


def save_products(conn, dispensary_id, products, store_name):
    """Save products to database."""
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
                "brand": p.get("brand"),
                "name": p.get("name"),
                "category": p.get("category"),
                "price": p.get("price"),
                "provider_id": p.get("provider_product_id"),
                "observed_at": now
            })
            saved += 1
        except Exception as e:
            pass

    conn.commit()
    return saved


def scrape_sweed_store(store_id, store_name, referer=None):
    """Scrape all products from a Sweed store."""
    all_products = {}

    try:
        # Get categories
        categories = get_categories(store_id, referer=referer)

        if not categories:
            # Try fetching without categories
            products = fetch_all_products_for_category(
                store_id=store_id,
                category_or_filters={},
                referer=referer,
                max_pages=100
            )
            for p in products:
                pid = p.get("id")
                if pid is not None:
                    all_products[str(pid)] = normalize_sweed_product(p)
        else:
            # Fetch each category
            for cat in categories:
                cat_name = cat.get("name", "")
                filters = cat.get("filter") or {}

                products = fetch_all_products_for_category(
                    store_id=store_id,
                    category_or_filters=filters,
                    referer=referer,
                    max_pages=100
                )

                for p in products:
                    pid = p.get("id")
                    if pid is not None:
                        all_products[str(pid)] = normalize_sweed_product(p, cat_name)

                time.sleep(0.2)

    except Exception as e:
        print(f"      Error: {e}")

    return list(all_products.values())


def main():
    """Main entry point."""
    print("="*60)
    print("SWEED STORES SCRAPER")
    print("="*60)

    engine = get_engine()

    # Get Sweed stores with store_id in metadata that need scraping
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT d.dispensary_id, d.name, d.state, d.menu_url, d.provider_metadata
            FROM dispensary d
            LEFT JOIN raw_menu_item r ON d.dispensary_id = r.dispensary_id
            WHERE d.is_active = true
            AND d.menu_provider = 'sweed'
            AND d.provider_metadata IS NOT NULL
            AND d.provider_metadata::text LIKE '%store_id%'
            AND r.dispensary_id IS NULL
            ORDER BY d.state, d.name
        """))
        stores = result.fetchall()

    print(f"Found {len(stores)} Sweed stores to scrape\n")

    total_products = 0
    total_stores = 0

    for dispensary_id, name, state, menu_url, metadata in stores:
        # Extract store_id from metadata
        store_id = None
        if metadata:
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    pass
            if isinstance(metadata, dict):
                store_id = metadata.get("store_id")

        if not store_id:
            print(f"  {state} - {name[:45]:45} -> No store_id")
            continue

        print(f"  {state} - {name[:45]:45} (ID: {store_id})", end=" ", flush=True)

        try:
            products = scrape_sweed_store(store_id, name, referer=menu_url)

            if products:
                with engine.connect() as conn:
                    saved = save_products(conn, dispensary_id, products, name)

                print(f"-> {saved} products")
                total_products += saved
                total_stores += 1
            else:
                print(f"-> 0 products")

            time.sleep(1)

        except Exception as e:
            print(f"-> Error: {e}")

    print(f"\n{'='*60}")
    print(f"TOTAL: {total_stores} stores, {total_products} products")
    print("="*60)


if __name__ == "__main__":
    main()
