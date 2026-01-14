#!/usr/bin/env python3
"""
Look up menu URLs for California cannabis retailers.

This script searches for dispensary menu URLs from:
- Weedmaps
- Leafly
- Dutchie
- Jane/iHeartJane
- Direct website searches
"""

import os
import sys
import re
import time
import json
import requests
from urllib.parse import quote_plus
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import get_engine
from sqlalchemy import text


@dataclass
class MenuURLResult:
    """Result of menu URL lookup."""
    license_number: str
    business_name: str
    dba_name: Optional[str]
    city: str
    weedmaps_url: Optional[str] = None
    leafly_url: Optional[str] = None
    dutchie_url: Optional[str] = None
    jane_url: Optional[str] = None
    website_url: Optional[str] = None


# Known dispensary chain URL patterns
CHAIN_URL_PATTERNS = {
    # MSOs
    "curaleaf": "https://curaleaf.com/shop/{state}/{city}",
    "trulieve": "https://www.trulieve.com/dispensaries/{state}/{city}",
    "rise": "https://risecannabis.com/dispensary/{state}/{city}",
    "zen leaf": "https://zenleafdispensaries.com/locations/{city}-{state}",
    "ascend": "https://awholdings.com/dispensaries/{state}/{city}",
    "the botanist": "https://shopbotanist.com/{state}/{city}",
    "cookies": "https://cookies.co/stores",
    "stiiizy": "https://www.stiiizy.com/pages/stores",

    # California chains
    "harborside": "https://www.shopharborside.com",
    "airfield supply": "https://airfieldsupplyco.com",
    "connected cannabis": "https://connectedcannabis.com/locations",
    "the apothecarium": "https://apothecarium.com",
    "march and ash": "https://marchandash.com",
    "embarc": "https://www.goembarc.com/stores",
    "la kush": "https://lakushla.com",
    "sweet flower": "https://sweetflower.com",
    "medmen": "https://www.medmen.com/stores",
    "planet 13": "https://planet13dispensary.com",

    # Weedmaps embedded menus
    "nug": "weedmaps",
    "flor": "weedmaps",
    "ohana": "weedmaps",
}


def normalize_name(name: str) -> str:
    """Normalize business name for matching."""
    name = name.lower()
    # Remove common suffixes
    name = re.sub(r'\s*(llc|inc|corp|dispensary|cannabis|collective|wellness|therapeutics|group)\s*', ' ', name)
    # Remove special characters
    name = re.sub(r'[^\w\s]', '', name)
    # Normalize whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def get_weedmaps_slug(name: str, city: str) -> str:
    """Generate potential Weedmaps URL slug."""
    # Weedmaps URLs are like: weedmaps.com/dispensaries/dispensary-name-city
    slug = f"{normalize_name(name)}-{city.lower()}"
    slug = re.sub(r'[^\w]+', '-', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug


def get_leafly_slug(name: str) -> str:
    """Generate potential Leafly URL slug."""
    slug = normalize_name(name)
    slug = re.sub(r'[^\w]+', '-', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug


def check_chain_match(business_name: str, dba_name: Optional[str]) -> Optional[str]:
    """Check if business matches a known chain and return URL pattern."""
    names_to_check = [business_name.lower()]
    if dba_name:
        names_to_check.append(dba_name.lower())

    for name in names_to_check:
        for chain, url_pattern in CHAIN_URL_PATTERNS.items():
            if chain in name:
                return url_pattern

    return None


def generate_menu_urls(business_name: str, dba_name: Optional[str], city: str) -> Dict[str, str]:
    """Generate potential menu URLs for a dispensary."""
    urls = {}

    # Use DBA name if available, otherwise business name
    display_name = dba_name if dba_name else business_name

    # Weedmaps URL
    wm_slug = get_weedmaps_slug(display_name, city)
    urls['weedmaps'] = f"https://weedmaps.com/dispensaries/{wm_slug}"

    # Leafly URL
    leafly_slug = get_leafly_slug(display_name)
    urls['leafly'] = f"https://www.leafly.com/dispensary-info/{leafly_slug}"

    # Check for chain match
    chain_url = check_chain_match(business_name, dba_name)
    if chain_url and chain_url != "weedmaps":
        urls['chain'] = chain_url

    return urls


def get_ca_retailers_without_urls(limit: int = 100) -> List[Dict]:
    """Get California retailers that don't have menu URLs yet."""
    engine = get_engine()

    with engine.connect() as conn:
        # Get retailers without menu URLs
        result = conn.execute(text("""
            SELECT
                cl.license_number,
                cl.business_name,
                cl.dba_name,
                cl.premise_city,
                cl.premise_county,
                cl.premise_address
            FROM california_license cl
            WHERE cl.license_type LIKE '%Retailer%'
            AND cl.license_status = 'Active'
            ORDER BY cl.premise_county, cl.business_name
            LIMIT :limit
        """), {"limit": limit})

        return [dict(row._mapping) for row in result]


def update_license_with_url(license_number: str, menu_url: str, menu_provider: str):
    """Update a California license with menu URL."""
    engine = get_engine()

    with engine.connect() as conn:
        # Add menu_url column if it doesn't exist
        conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                              WHERE table_name = 'california_license'
                              AND column_name = 'menu_url') THEN
                    ALTER TABLE california_license ADD COLUMN menu_url TEXT;
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


def print_sample_urls():
    """Print sample generated URLs for verification."""
    retailers = get_ca_retailers_without_urls(20)

    print("\nSample Generated Menu URLs:")
    print("=" * 80)

    for r in retailers:
        name = r['dba_name'] or r['business_name']
        city = r['premise_city']

        print(f"\n{name} ({city})")

        urls = generate_menu_urls(r['business_name'], r['dba_name'], city)
        for source, url in urls.items():
            print(f"  {source}: {url}")

        chain = check_chain_match(r['business_name'], r['dba_name'])
        if chain:
            print(f"  [Chain detected: {chain}]")


def export_for_manual_lookup(output_path: str, limit: int = 1208):
    """Export retailers to CSV for manual URL lookup."""
    retailers = get_ca_retailers_without_urls(limit)

    import csv

    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'license_number', 'business_name', 'dba_name', 'city', 'county',
            'weedmaps_url', 'leafly_url', 'verified_url', 'menu_provider'
        ])

        for r in retailers:
            urls = generate_menu_urls(r['business_name'], r['dba_name'], r['premise_city'])
            writer.writerow([
                r['license_number'],
                r['business_name'],
                r['dba_name'] or '',
                r['premise_city'],
                r['premise_county'],
                urls.get('weedmaps', ''),
                urls.get('leafly', ''),
                '',  # For manual verification
                ''   # Menu provider
            ])

    print(f"Exported {len(retailers)} retailers to {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Look up menu URLs for CA retailers")
    parser.add_argument('--sample', action='store_true', help="Show sample generated URLs")
    parser.add_argument('--export', type=str, help="Export to CSV for manual lookup")
    parser.add_argument('--limit', type=int, default=100, help="Limit number of retailers")

    args = parser.parse_args()

    if args.sample:
        print_sample_urls()
    elif args.export:
        export_for_manual_lookup(args.export, args.limit)
    else:
        print("""
California Menu URL Lookup

Usage:
  --sample              Show sample generated URLs for verification
  --export FILE.csv     Export retailers to CSV for manual URL lookup
  --limit N             Limit number of retailers (default: 100)

Example:
  python scripts/lookup_ca_menu_urls.py --sample
  python scripts/lookup_ca_menu_urls.py --export data/ca_retailers_urls.csv --limit 1208
        """)
