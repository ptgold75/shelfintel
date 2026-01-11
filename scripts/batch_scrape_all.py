#!/usr/bin/env python3
"""
Batch scraper for all dispensaries by provider type.

Usage:
    python scripts/batch_scrape_all.py --provider sweed --state MD
    python scripts/batch_scrape_all.py --provider dutchie --limit 50
    python scripts/batch_scrape_all.py --provider leafly --state CA --limit 100
    python scripts/batch_scrape_all.py --all-providers --state MD
"""

import os
import sys
import argparse
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from core.db import get_engine, get_session
from core.models import Dispensary


def get_unscraped_dispensaries(provider=None, state=None, limit=None):
    """Get dispensaries that haven't been scraped yet."""
    engine = get_engine()

    query = """
        WITH scraped AS (
            SELECT DISTINCT dispensary_id FROM raw_menu_item
        )
        SELECT d.dispensary_id, d.name, d.state, d.menu_provider, d.menu_url
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

    query += " ORDER BY d.state, d.name"

    if limit:
        query += f" LIMIT {int(limit)}"

    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        return [dict(row._mapping) for row in result]


def run_scrape(dispensary_id):
    """Run scrape for a single dispensary using run_scrape.py logic."""
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
    parser = argparse.ArgumentParser(description="Batch scrape dispensaries")
    parser.add_argument("--provider", help="Filter by provider (sweed, dutchie, jane, leafly)")
    parser.add_argument("--state", help="Filter by state (e.g., MD, NJ)")
    parser.add_argument("--limit", type=int, help="Limit number of dispensaries")
    parser.add_argument("--all-providers", action="store_true", help="Scrape all supported providers")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between scrapes (seconds)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be scraped without scraping")
    args = parser.parse_args()

    # Get supported providers
    supported_providers = ["sweed", "dutchie", "jane", "leafly"]

    if args.all_providers:
        providers = supported_providers
    elif args.provider:
        providers = [args.provider]
    else:
        # Default: show stats and exit
        print("=== Unscraped Dispensaries by Provider ===\n")
        for p in supported_providers:
            disps = get_unscraped_dispensaries(provider=p, state=args.state)
            print(f"  {p:12} | {len(disps):>6,} remaining")
        print("\nUse --provider or --all-providers to start scraping")
        return

    total_success = 0
    total_failed = 0

    for provider in providers:
        dispensaries = get_unscraped_dispensaries(
            provider=provider,
            state=args.state,
            limit=args.limit
        )

        if not dispensaries:
            print(f"\nNo unscraped {provider} dispensaries found")
            continue

        print(f"\n{'='*60}")
        print(f"Scraping {len(dispensaries)} {provider.upper()} dispensaries")
        if args.state:
            print(f"State filter: {args.state}")
        print(f"{'='*60}")

        if args.dry_run:
            for d in dispensaries[:20]:
                print(f"  Would scrape: {d['state']} | {d['name'][:40]}")
            if len(dispensaries) > 20:
                print(f"  ... and {len(dispensaries) - 20} more")
            continue

        for i, d in enumerate(dispensaries, 1):
            print(f"\n[{i}/{len(dispensaries)}] {d['state']} | {d['name']}")
            print(f"  URL: {d['menu_url'][:60]}...")

            result = run_scrape(d['dispensary_id'])

            if result.get("status") == "success":
                total_success += 1
                print(f"  ✅ Success: {result.get('items', 0)} items")
            else:
                total_failed += 1
                print(f"  ❌ Failed: {result.get('error', 'Unknown error')[:100]}")

            # Delay between scrapes
            if i < len(dispensaries):
                time.sleep(args.delay)

    # Summary
    print(f"\n{'='*60}")
    print("BATCH SCRAPE SUMMARY")
    print(f"{'='*60}")
    print(f"  Success: {total_success}")
    print(f"  Failed:  {total_failed}")
    print(f"  Total:   {total_success + total_failed}")


if __name__ == "__main__":
    main()
