#!/usr/bin/env python3
"""
Quick verification of NY dispensaries against licensed list.
Marks unlicensed stores with smoke-related names as smoke shops.
"""

import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import get_engine
from sqlalchemy import text

# Import the exported licensed list
scripts_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, scripts_dir)
from ny_licensed_dispensaries import NY_LICENSED_DISPENSARIES


def normalize_name(name: str) -> str:
    """Normalize name for matching."""
    name = name.lower()
    name = re.sub(r'\s*(llc|inc|corp|company|co\.?)[\s,]*$', '', name)
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def build_licensed_set():
    """Build set of normalized licensed names."""
    licensed = set()
    for d in NY_LICENSED_DISPENSARIES:
        licensed.add(normalize_name(d['name']))
    return licensed


def verify_and_update(dry_run: bool = True):
    """Verify NY dispensaries and mark smoke shops."""
    licensed_names = build_licensed_set()
    print(f"Built set of {len(licensed_names)} licensed dispensary names")

    engine = get_engine()

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT dispensary_id, name, city, store_type
            FROM dispensary
            WHERE state = 'NY' AND is_active = true
        """))
        dispensaries = [dict(row._mapping) for row in result]

    print(f"Checking {len(dispensaries)} NY dispensaries...")

    verified = 0
    smoke_shops = 0
    unverified = 0

    for d in dispensaries:
        name = d['name'] or ''
        norm_name = normalize_name(name)
        name_lower = name.lower()

        # Check if licensed
        is_licensed = False
        for lic_name in licensed_names:
            if norm_name == lic_name or norm_name in lic_name or lic_name in norm_name:
                is_licensed = True
                break

        if is_licensed:
            verified += 1
            if not dry_run:
                with engine.connect() as conn:
                    conn.execute(text("""
                        UPDATE dispensary
                        SET store_type = 'dispensary', discovery_confidence = 1.0, updated_at = NOW()
                        WHERE dispensary_id = :id
                    """), {"id": d['dispensary_id']})
                    conn.commit()
        elif any(kw in name_lower for kw in ['smoke', 'tobacco', 'vape', 'cigar', 'hookah', 'vapor']):
            smoke_shops += 1
            if not dry_run:
                with engine.connect() as conn:
                    conn.execute(text("""
                        UPDATE dispensary
                        SET store_type = 'smoke_shop', updated_at = NOW()
                        WHERE dispensary_id = :id
                    """), {"id": d['dispensary_id']})
                    conn.commit()
        else:
            unverified += 1

    print("\n" + "=" * 60)
    print("Verification Summary:")
    print(f"  Verified as licensed: {verified}")
    print(f"  Marked as smoke shops: {smoke_shops}")
    print(f"  Remaining unverified: {unverified}")

    if dry_run:
        print("\n[DRY RUN - no changes made. Use --apply to update]")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    verify_and_update(dry_run=not args.apply)
