#!/usr/bin/env python3
"""
Discover store IDs and scrape dispensaries in one go.

Usage:
    python scripts/discover_and_scrape.py --provider sweed --state MD --limit 5
    python scripts/discover_and_scrape.py --provider dutchie --state MD
"""

import os
import sys
import json
import argparse
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from core.db import get_engine, get_session
from core.models import Dispensary

# Import discovery function
from ingest.discover_sweed import discover_one


def get_unscraped_dispensaries(provider=None, state=None, limit=None, needs_discovery=False):
    """Get dispensaries that haven't been scraped yet."""
    engine = get_engine()

    query = """
        WITH scraped AS (
            SELECT DISTINCT dispensary_id FROM raw_menu_item
        )
        SELECT d.dispensary_id, d.name, d.state, d.menu_provider, d.menu_url, d.provider_metadata
        FROM dispensary d
        LEFT JOIN scraped s ON d.dispensary_id = s.dispensary_id
        WHERE d.is_active = true
          AND d.menu_url IS NOT NULL
          AND d.menu_url <> ''
          AND s.dispensary_id IS NULL
    """

    params = {}

    if provider:
        query += " AND LOWER(d.menu_provider) = :provider"
        params["provider"] = provider.lower()

    if state:
        query += " AND d.state = :state"
        params["state"] = state.upper()

    if needs_discovery:
        # Only get dispensaries that don't have store_id in metadata
        query += " AND (d.provider_metadata IS NULL OR d.provider_metadata NOT LIKE '%store_id%')"

    query += " ORDER BY d.state, d.name"

    if limit:
        query += f" LIMIT {int(limit)}"

    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        return [dict(row._mapping) for row in result]


def discover_and_update(dispensary_id, menu_url):
    """Discover store_id and update the dispensary record."""
    print(f"  Discovering store_id from {menu_url[:50]}...")

    try:
        result = discover_one(menu_url, timeout_ms=60000, use_proxy=True)

        provider = result.get("provider", "unknown")
        extracted = result.get("extracted", {})

        print(f"  Detected provider: {provider} (confidence: {result.get('confidence', 0):.0%})")

        # Build metadata based on provider
        metadata = {}

        if provider == "sweed" and extracted.get("store_id"):
            metadata["store_id"] = extracted["store_id"]
            print(f"  Found store_id: {metadata['store_id']}")
        elif provider == "dutchie" and extracted.get("retailer_id"):
            metadata["retailer_id"] = extracted["retailer_id"]
            print(f"  Found retailer_id: {metadata['retailer_id']}")
        elif provider == "jane" and extracted.get("jane_store_id"):
            metadata["store_id"] = extracted["jane_store_id"]
            print(f"  Found jane_store_id: {metadata['store_id']}")

        if extracted.get("api_base"):
            metadata["api_base"] = extracted["api_base"]

        if metadata:
            # Update the dispensary record
            engine = get_engine()
            with engine.connect() as conn:
                conn.execute(text("""
                    UPDATE dispensary
                    SET provider_metadata = :metadata,
                        menu_provider = :provider
                    WHERE dispensary_id = :disp_id
                """), {
                    "metadata": json.dumps(metadata),
                    "provider": provider,
                    "disp_id": str(dispensary_id)
                })
                conn.commit()
            print(f"  Updated dispensary with metadata")
            return True, metadata
        else:
            print(f"  No store_id found - signals: {result.get('signals', [])[:3]}")
            return False, {}

    except Exception as e:
        print(f"  Discovery failed: {e}")
        return False, {}


def run_scrape(dispensary_id):
    """Run scrape for a single dispensary."""
    from ingest.run_scrape import scrape_dispensary

    db = get_session()
    try:
        disp = db.query(Dispensary).filter(
            Dispensary.dispensary_id == dispensary_id
        ).first()

        if not disp:
            return {"status": "error", "error": "Dispensary not found"}

        result = scrape_dispensary(db, disp)
        return result
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Discover and scrape dispensaries")
    parser.add_argument("--provider", help="Filter by provider (sweed, dutchie, jane)")
    parser.add_argument("--state", help="Filter by state (e.g., MD, NJ)")
    parser.add_argument("--limit", type=int, help="Limit number of dispensaries")
    parser.add_argument("--delay", type=float, default=3.0, help="Delay between operations (seconds)")
    parser.add_argument("--discover-only", action="store_true", help="Only discover, don't scrape")
    parser.add_argument("--scrape-only", action="store_true", help="Only scrape (skip discovery)")
    args = parser.parse_args()

    if not args.provider:
        print("Please specify --provider (sweed, dutchie, jane)")
        return

    # Get unscraped dispensaries
    needs_discovery = not args.scrape_only
    dispensaries = get_unscraped_dispensaries(
        provider=args.provider,
        state=args.state,
        limit=args.limit,
        needs_discovery=needs_discovery
    )

    if not dispensaries:
        print(f"No unscraped {args.provider} dispensaries found")
        if args.state:
            print(f"(state filter: {args.state})")
        return

    print(f"\n{'='*60}")
    print(f"Processing {len(dispensaries)} {args.provider.upper()} dispensaries")
    if args.state:
        print(f"State filter: {args.state}")
    print(f"{'='*60}")

    discovered = 0
    scraped_success = 0
    scraped_failed = 0

    for i, d in enumerate(dispensaries, 1):
        print(f"\n[{i}/{len(dispensaries)}] {d['state']} | {d['name']}")

        # Step 1: Discover store_id if needed
        if not args.scrape_only:
            has_metadata = d.get('provider_metadata') and 'store_id' in str(d.get('provider_metadata', ''))

            if not has_metadata:
                success, metadata = discover_and_update(d['dispensary_id'], d['menu_url'])
                if success:
                    discovered += 1
                    time.sleep(args.delay)
                else:
                    print(f"  Skipping scrape - no store_id discovered")
                    continue
            else:
                print(f"  Already has metadata, skipping discovery")

        if args.discover_only:
            continue

        # Step 2: Scrape
        print(f"  Scraping...")
        result = run_scrape(d['dispensary_id'])

        if result.get("status") == "success":
            scraped_success += 1
            print(f"  ✅ Success: {result.get('items', 0)} items")
        else:
            scraped_failed += 1
            error = result.get('error', 'Unknown error')
            print(f"  ❌ Failed: {error[:80]}")

        time.sleep(args.delay)

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    if not args.scrape_only:
        print(f"  Discovered: {discovered}")
    if not args.discover_only:
        print(f"  Scraped successfully: {scraped_success}")
        print(f"  Scrape failed: {scraped_failed}")


if __name__ == "__main__":
    main()
