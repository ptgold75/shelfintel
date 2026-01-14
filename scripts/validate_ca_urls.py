#!/usr/bin/env python3
"""
Validate and import California dispensary menu URLs.

Checks Weedmaps URLs and saves valid ones to the database.
"""

import os
import sys
import re
import time
import requests
from typing import Optional, List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import get_engine
from sqlalchemy import text


def normalize_name(name: str) -> str:
    """Normalize business name for URL generation."""
    name = name.lower()
    name = re.sub(r'\s*(llc|inc|corp|dispensary|cannabis|collective|wellness|therapeutics|group)\s*', ' ', name)
    name = re.sub(r'\[.*?\]', '', name)  # Remove bracketed text like [Equity Retailer]
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def generate_weedmaps_slugs(name: str, city: str) -> List[str]:
    """Generate multiple potential Weedmaps URL slugs."""
    slugs = []
    normalized = normalize_name(name)
    city_lower = city.lower().replace(' ', '-')

    # Try different combinations
    base_slug = re.sub(r'[^\w]+', '-', normalized).strip('-')

    slugs.append(f"{base_slug}-{city_lower}")  # name-city
    slugs.append(base_slug)  # just name
    slugs.append(f"{base_slug}-california")  # name-california

    # If name has "the", try without
    if base_slug.startswith('the-'):
        slugs.append(base_slug[4:] + f"-{city_lower}")
        slugs.append(base_slug[4:])

    return slugs


def check_weedmaps_url(slug: str, timeout: int = 5) -> Tuple[bool, Optional[str]]:
    """Check if a Weedmaps URL exists."""
    url = f"https://weedmaps.com/dispensaries/{slug}"

    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        if response.status_code == 200:
            return True, url
        return False, None
    except:
        return False, None


def find_weedmaps_url(name: str, city: str) -> Optional[str]:
    """Try to find a valid Weedmaps URL for a dispensary."""
    slugs = generate_weedmaps_slugs(name, city)

    for slug in slugs:
        exists, url = check_weedmaps_url(slug)
        if exists:
            return url
        time.sleep(0.1)  # Rate limit

    return None


def get_ca_retailers(limit: int = 100, offset: int = 0) -> List[Dict]:
    """Get California retailers from database."""
    engine = get_engine()

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                license_number,
                business_name,
                dba_name,
                premise_city,
                premise_county
            FROM california_license
            WHERE license_type LIKE '%Retailer%'
            AND license_status = 'Active'
            ORDER BY premise_county, business_name
            LIMIT :limit OFFSET :offset
        """), {"limit": limit, "offset": offset})

        return [dict(row._mapping) for row in result]


def update_license_url(license_number: str, menu_url: str, menu_provider: str = "weedmaps"):
    """Update a license with its menu URL."""
    engine = get_engine()

    with engine.connect() as conn:
        # Ensure columns exist
        conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                              WHERE table_name = 'california_license' AND column_name = 'menu_url') THEN
                    ALTER TABLE california_license ADD COLUMN menu_url TEXT;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                              WHERE table_name = 'california_license' AND column_name = 'menu_provider') THEN
                    ALTER TABLE california_license ADD COLUMN menu_provider VARCHAR(50);
                END IF;
            END $$;
        """))

        conn.execute(text("""
            UPDATE california_license
            SET menu_url = :url, menu_provider = :provider, updated_at = NOW()
            WHERE license_number = :license_number
        """), {"url": menu_url, "provider": menu_provider, "license_number": license_number})

        conn.commit()


def validate_batch(retailers: List[Dict], verbose: bool = True) -> Tuple[int, int]:
    """Validate URLs for a batch of retailers."""
    found = 0
    not_found = 0

    for r in retailers:
        name = r['dba_name'] or r['business_name']
        city = r['premise_city']

        url = find_weedmaps_url(name, city)

        if url:
            found += 1
            update_license_url(r['license_number'], url, "weedmaps")
            if verbose:
                print(f"  ✓ {name} ({city}): {url}")
        else:
            not_found += 1
            if verbose:
                print(f"  ✗ {name} ({city}): Not found")

    return found, not_found


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Validate CA dispensary Weedmaps URLs")
    parser.add_argument('--limit', type=int, default=50, help="Number of retailers to check")
    parser.add_argument('--offset', type=int, default=0, help="Starting offset")
    parser.add_argument('--quiet', action='store_true', help="Less verbose output")

    args = parser.parse_args()

    print(f"Validating Weedmaps URLs for {args.limit} California retailers (offset: {args.offset})...")
    print()

    retailers = get_ca_retailers(args.limit, args.offset)

    if not retailers:
        print("No retailers found.")
        return

    found, not_found = validate_batch(retailers, verbose=not args.quiet)

    print()
    print(f"Results: {found} found, {not_found} not found ({found/(found+not_found)*100:.1f}% hit rate)")


if __name__ == "__main__":
    main()
