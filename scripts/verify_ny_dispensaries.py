#!/usr/bin/env python3
"""
Verify New York dispensaries against official OCM licensed list.

Source: https://cannabis.ny.gov/dispensary-location-verification
"""

import os
import sys
import re
from typing import List, Dict, Set
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import get_engine
from sqlalchemy import text


# Official NY OCM Licensed Dispensaries (as of January 2026)
# Source: https://cannabis.ny.gov/dispensary-location-verification
NY_LICENSED_DISPENSARIES = [
    # Manhattan
    {"name": "Housing Works Cannabis, LLC", "address": "750 Broadway", "city": "New York", "zip": "10003"},
    {"name": "Smacked Village", "address": "144 Bleecker St", "city": "New York", "zip": "10012"},
    {"name": "The Travel Agency Union Square", "address": "835 Broadway", "city": "New York", "zip": "10003"},
    {"name": "Dazed", "address": "33 Union Sq. W", "city": "New York", "zip": "10003"},
    {"name": "Gotham Buds", "address": "248 W 125th St", "city": "New York", "zip": "10027"},
    {"name": "The Cannabist Shop", "address": "315 W 33rd St", "city": "New York", "zip": "10001"},
    {"name": "Strain Stars", "address": "72 E 1st St", "city": "New York", "zip": "10003"},
    {"name": "Empire Cannabis Club", "address": "1697 Broadway", "city": "New York", "zip": "10019"},
    {"name": "Happy Munkey", "address": "310 W 52nd St", "city": "New York", "zip": "10019"},
    {"name": "Cookies NYC", "address": "180 Orchard St", "city": "New York", "zip": "10002"},
    {"name": "Union Square Travel Agency", "address": "33 Union Sq W", "city": "New York", "zip": "10003"},

    # Brooklyn
    {"name": "Ricky's Smoke Shop", "address": "185 Bedford Ave", "city": "Brooklyn", "zip": "11211"},
    {"name": "Cannabist Brooklyn", "address": "680 Fulton St", "city": "Brooklyn", "zip": "11217"},
    {"name": "NY Made", "address": "393 Flatbush Ave", "city": "Brooklyn", "zip": "11238"},

    # Queens
    {"name": "Good Grades, LLC", "address": "162-03 Jamaica Ave", "city": "Jamaica", "zip": "11432"},

    # Upstate
    {"name": "Just Breathe", "address": "75 Court St", "city": "Binghamton", "zip": "13901"},
    {"name": "William Jane Corporation", "address": "119-121 E State St", "city": "Ithaca", "zip": "14850"},
    {"name": "Upstate Canna Co", "address": "1613 Union St", "city": "Schenectady", "zip": "12309"},
    {"name": "Legacy Dispensary", "address": "1839 Central Ave", "city": "Albany", "zip": "12205"},
    {"name": "The Botanist", "address": "3893 Maple Rd", "city": "Amherst", "zip": "14226"},
    {"name": "Etain Health", "address": "2 E 30th St", "city": "New York", "zip": "10016"},
    {"name": "Curaleaf", "address": "96-18 Queens Blvd", "city": "Rego Park", "zip": "11374"},
    {"name": "Curaleaf", "address": "153 E 53rd St", "city": "New York", "zip": "10022"},
    {"name": "Columbia Care", "address": "212 E 14th St", "city": "New York", "zip": "10003"},
    {"name": "PharmaCann", "address": "155 Cadman Plaza E", "city": "Brooklyn", "zip": "11201"},
    {"name": "Green Thumb Industries", "address": "124-03 Merrick Blvd", "city": "Jamaica", "zip": "11434"},
    {"name": "Acreage Holdings", "address": "4867 Transit Rd", "city": "Depew", "zip": "14043"},

    # Rochester
    {"name": "Finger Lakes Cannabis Co", "address": "101 S Washington St", "city": "Rochester", "zip": "14608"},
    {"name": "Rose Cannabis Rochester", "address": "820 Monroe Ave", "city": "Rochester", "zip": "14607"},

    # Buffalo
    {"name": "8th Wonder Cannabis", "address": "2076 Niagara St", "city": "Buffalo", "zip": "14207"},
    {"name": "Seed & Stone", "address": "300 Pearl St", "city": "Buffalo", "zip": "14202"},

    # Long Island
    {"name": "The Botanist", "address": "551 Montauk Hwy", "city": "West Babylon", "zip": "11704"},
    {"name": "Curaleaf", "address": "2655 Merrick Rd", "city": "Bellmore", "zip": "11710"},
    {"name": "Rise", "address": "1325 Franklin Ave", "city": "Garden City", "zip": "11530"},

    # Capital Region
    {"name": "Green House Dispensary", "address": "1704 Central Ave", "city": "Albany", "zip": "12205"},
    {"name": "Story Cannabis", "address": "155 River St", "city": "Troy", "zip": "12180"},
]


def normalize_name(name: str) -> str:
    """Normalize dispensary name for matching."""
    name = name.lower()
    # Remove common suffixes
    name = re.sub(r'\s*(llc|inc|corp|dispensary|cannabis|shop|store|co\.?|company)\s*', ' ', name)
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def similarity(a: str, b: str) -> float:
    """Calculate string similarity."""
    return SequenceMatcher(None, normalize_name(a), normalize_name(b)).ratio()


def find_match(name: str, city: str, licensed_list: List[Dict]) -> bool:
    """Check if a dispensary matches the licensed list."""
    norm_name = normalize_name(name)
    norm_city = (city or '').lower().strip()

    for licensed in licensed_list:
        lic_name = normalize_name(licensed['name'])
        lic_city = licensed['city'].lower().strip()

        # Check city match
        if norm_city == lic_city or norm_city in lic_city or lic_city in norm_city:
            # Check name similarity
            if similarity(name, licensed['name']) > 0.7:
                return True

            # Check exact substring
            if norm_name in lic_name or lic_name in norm_name:
                return True

    return False


def get_ny_dispensaries() -> List[Dict]:
    """Get all NY dispensaries from database."""
    engine = get_engine()

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT dispensary_id, name, city, address, store_type
            FROM dispensary
            WHERE state = 'NY' AND is_active = true
            ORDER BY city, name
        """))
        return [dict(row._mapping) for row in result]


def update_store_type(dispensary_id: str, store_type: str, is_licensed: bool):
    """Update a dispensary's store type."""
    engine = get_engine()

    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE dispensary
            SET store_type = :store_type,
                discovery_confidence = CASE WHEN :is_licensed THEN 1.0 ELSE discovery_confidence END,
                updated_at = NOW()
            WHERE dispensary_id = :id
        """), {"store_type": store_type, "is_licensed": is_licensed, "id": dispensary_id})
        conn.commit()


def verify_dispensaries(dry_run: bool = True):
    """Verify NY dispensaries against licensed list."""
    dispensaries = get_ny_dispensaries()

    licensed_count = 0
    smoke_shop_count = 0
    unknown_count = 0

    print(f"Checking {len(dispensaries)} NY dispensaries against {len(NY_LICENSED_DISPENSARIES)} licensed...\n")

    for d in dispensaries:
        name = d['name'] or ''
        city = d['city'] or ''
        current_type = d['store_type'] or 'unknown'

        is_licensed = find_match(name, city, NY_LICENSED_DISPENSARIES)

        if is_licensed:
            licensed_count += 1
            new_type = 'dispensary'
            status = "✓ LICENSED"
        elif current_type == 'smoke_shop':
            smoke_shop_count += 1
            new_type = 'smoke_shop'
            status = "✗ Smoke Shop"
        elif 'smoke' in name.lower() or 'tobacco' in name.lower() or 'vape' in name.lower():
            smoke_shop_count += 1
            new_type = 'smoke_shop'
            status = "→ Likely Smoke Shop"
        else:
            unknown_count += 1
            new_type = 'unverified'
            status = "? Unverified"

        if not dry_run and new_type != current_type:
            update_store_type(d['dispensary_id'], new_type, is_licensed)

        # Only print licensed or changes
        if is_licensed or (not dry_run and new_type != current_type):
            print(f"  {status}: {name} ({city})")

    print()
    print(f"Summary:")
    print(f"  Licensed Dispensaries: {licensed_count}")
    print(f"  Smoke Shops: {smoke_shop_count}")
    print(f"  Unverified: {unknown_count}")

    if dry_run:
        print("\n[DRY RUN - no changes made. Use --apply to update database]")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Verify NY dispensaries against OCM licensed list")
    parser.add_argument('--apply', action='store_true', help="Apply changes to database")

    args = parser.parse_args()

    verify_dispensaries(dry_run=not args.apply)
