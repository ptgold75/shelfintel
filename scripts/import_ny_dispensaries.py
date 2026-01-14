#!/usr/bin/env python3
"""
Import New York dispensary licenses from NY Open Data Portal.

Source: https://data.ny.gov/Economic-Development/Current-OCM-Licenses/jskf-tt3q
"""

import os
import sys
import json
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import get_engine
from sqlalchemy import text


@dataclass
class NYDispensary:
    """NY dispensary license record."""
    license_number: str
    business_name: str
    trade_name: Optional[str]
    address: str
    city: str
    state: str
    zip_code: str
    license_type: str
    license_status: str


def fetch_ny_licenses(license_type: str = None, limit: int = 5000) -> List[Dict]:
    """Fetch NY OCM licenses from Socrata API."""
    base_url = "https://data.ny.gov/resource/jskf-tt3q.json"

    params = {
        "$limit": limit,
        "$order": "license_number"
    }

    if license_type:
        params["license_type"] = license_type

    try:
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching NY licenses: {e}")
        return []


def parse_license(record: Dict) -> Optional[NYDispensary]:
    """Parse a license record from API response."""
    # Required fields - NY uses entity_name, not business_name
    license_number = record.get('license_number', '').strip()
    if not license_number:
        return None

    business_name = record.get('entity_name', '').strip()
    if not business_name:
        return None

    return NYDispensary(
        license_number=license_number,
        business_name=business_name,
        trade_name=record.get('dba', '').strip() or None,  # NY uses 'dba' not 'trade_name'
        address=record.get('address_line_1', '').strip(),  # NY uses 'address_line_1'
        city=record.get('city', '').strip(),
        state='NY',
        zip_code=record.get('zip_code', '').strip(),
        license_type=record.get('license_type', '').strip(),
        license_status=record.get('license_status', '').strip()
    )


def get_existing_dispensaries() -> Dict[str, str]:
    """Get existing NY dispensaries from database (name -> dispensary_id)."""
    engine = get_engine()

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT dispensary_id, LOWER(name) as name
            FROM dispensary
            WHERE state = 'NY'
        """))
        return {row.name: row.dispensary_id for row in result}


def normalize_name(name: str) -> str:
    """Normalize name for matching."""
    import re
    name = name.lower()
    name = re.sub(r'\s*(llc|inc|corp|company|co\.?)[\s,]*$', '', name)
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def update_dispensary_license_status(dispensary_id: str, is_licensed: bool):
    """Update a dispensary's license verification status."""
    engine = get_engine()

    with engine.connect() as conn:
        if is_licensed:
            conn.execute(text("""
                UPDATE dispensary
                SET store_type = 'dispensary',
                    discovery_confidence = 1.0,
                    updated_at = NOW()
                WHERE dispensary_id = :id
            """), {"id": dispensary_id})
        else:
            conn.execute(text("""
                UPDATE dispensary
                SET store_type = CASE
                    WHEN store_type IS NULL OR store_type = 'unknown' THEN 'unverified'
                    ELSE store_type
                END,
                updated_at = NOW()
                WHERE dispensary_id = :id
            """), {"id": dispensary_id})
        conn.commit()


def insert_dispensary(disp: NYDispensary) -> Optional[str]:
    """Insert a new dispensary from license data."""
    engine = get_engine()

    import uuid
    dispensary_id = str(uuid.uuid4())

    # Use trade name if available, otherwise business name
    display_name = disp.trade_name if disp.trade_name else disp.business_name

    with engine.connect() as conn:
        try:
            conn.execute(text("""
                INSERT INTO dispensary (
                    dispensary_id, name, address, city, state, zip,
                    store_type, discovery_confidence, is_active, created_at, updated_at
                ) VALUES (
                    :id, :name, :address, :city, 'NY', :zip,
                    'dispensary', 1.0, true, NOW(), NOW()
                )
                ON CONFLICT (dispensary_id) DO NOTHING
            """), {
                "id": dispensary_id,
                "name": display_name,
                "address": disp.address,
                "city": disp.city,
                "zip": disp.zip_code
            })
            conn.commit()
            return dispensary_id
        except Exception as e:
            print(f"  Error inserting {display_name}: {e}")
            return None


def import_ny_retail_dispensaries(dry_run: bool = True):
    """Import NY adult-use retail dispensary licenses."""
    print("Fetching NY OCM licenses from Open Data Portal...")

    # Fetch adult-use retail dispensaries
    all_licenses = fetch_ny_licenses()

    if not all_licenses:
        print("No licenses fetched. Check network connection.")
        return

    print(f"Fetched {len(all_licenses)} total licenses")

    # Filter for retail dispensaries (both regular and conditional)
    retail_licenses = []
    retail_types = [
        'Adult-Use Retail Dispensary License',
        'Adult-Use Conditional Retail Dispensary License',
        'Conditional Adult-Use Retail Dispensary License',
        'Adult-Use Registered Organization Dispensary License',
    ]
    for record in all_licenses:
        license_type = record.get('license_type', '')
        if any(rt in license_type for rt in retail_types):
            parsed = parse_license(record)
            if parsed and parsed.license_status == 'Active':
                retail_licenses.append(parsed)

    print(f"Found {len(retail_licenses)} active retail dispensary licenses")

    # Get existing dispensaries
    existing = get_existing_dispensaries()
    print(f"Found {len(existing)} existing NY dispensaries in database")

    # Track results
    matched = 0
    added = 0
    not_matched = []

    print("\nProcessing licenses...")

    for disp in retail_licenses:
        display_name = disp.trade_name if disp.trade_name else disp.business_name
        norm_name = normalize_name(display_name)

        # Try to match against existing
        found = False
        for existing_name, existing_id in existing.items():
            if norm_name in existing_name or existing_name in norm_name:
                if not dry_run:
                    update_dispensary_license_status(existing_id, True)
                matched += 1
                found = True
                break

        if not found:
            # Check if we should add it
            if not dry_run:
                new_id = insert_dispensary(disp)
                if new_id:
                    added += 1
                    print(f"  + Added: {display_name} ({disp.city})")
            else:
                not_matched.append(disp)
                added += 1  # Count for dry run

    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Total active retail licenses: {len(retail_licenses)}")
    print(f"  Matched to existing records: {matched}")
    print(f"  {'Would add' if dry_run else 'Added'} new records: {added}")

    if dry_run:
        print("\n[DRY RUN - no changes made. Use --apply to import]")

        # Show sample of unmatched
        if not_matched[:10]:
            print("\nSample of unmatched licenses:")
            for d in not_matched[:10]:
                name = d.trade_name if d.trade_name else d.business_name
                print(f"  - {name} ({d.city})")

    # Also export the full licensed list
    print("\nExporting licensed dispensary list...")
    export_licensed_list(retail_licenses)


def export_licensed_list(dispensaries: List[NYDispensary]):
    """Export the licensed dispensary list to a Python file for verification."""
    output_path = os.path.join(
        os.path.dirname(__file__),
        'ny_licensed_dispensaries.py'
    )

    with open(output_path, 'w') as f:
        f.write('"""\n')
        f.write('Official NY OCM Licensed Dispensaries\n')
        f.write('Source: https://data.ny.gov/Economic-Development/Current-OCM-Licenses/jskf-tt3q\n')
        f.write(f'Generated: {__import__("datetime").datetime.now().isoformat()}\n')
        f.write('"""\n\n')
        f.write('NY_LICENSED_DISPENSARIES = [\n')

        for d in sorted(dispensaries, key=lambda x: (x.city, x.business_name)):
            name = d.trade_name if d.trade_name else d.business_name
            # Escape quotes in names
            name = name.replace('"', '\\"')
            address = d.address.replace('"', '\\"') if d.address else ''
            city = d.city.replace('"', '\\"') if d.city else ''

            f.write(f'    {{"name": "{name}", "address": "{address}", "city": "{city}", "zip": "{d.zip_code}"}},\n')

        f.write(']\n')

    print(f"Exported {len(dispensaries)} licensed dispensaries to {output_path}")


def mark_unlicensed_as_smoke_shops(dry_run: bool = True):
    """Mark NY dispensaries that aren't in licensed list as smoke shops."""
    # First, get the licensed list
    all_licenses = fetch_ny_licenses()
    retail_types = [
        'Adult-Use Retail Dispensary License',
        'Adult-Use Conditional Retail Dispensary License',
        'Conditional Adult-Use Retail Dispensary License',
        'Adult-Use Registered Organization Dispensary License',
    ]
    retail_licenses = []
    for record in all_licenses:
        license_type = record.get('license_type', '')
        if any(rt in license_type for rt in retail_types):
            parsed = parse_license(record)
            if parsed and parsed.license_status == 'Active':
                retail_licenses.append(parsed)

    # Build set of licensed names (normalized)
    licensed_names = set()
    for d in retail_licenses:
        if d.trade_name:
            licensed_names.add(normalize_name(d.trade_name))
        licensed_names.add(normalize_name(d.business_name))

    print(f"Built set of {len(licensed_names)} licensed dispensary names")

    # Get all NY dispensaries from database
    engine = get_engine()

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT dispensary_id, name, city, store_type
            FROM dispensary
            WHERE state = 'NY' AND is_active = true
        """))
        db_dispensaries = [dict(row._mapping) for row in result]

    print(f"Checking {len(db_dispensaries)} NY dispensaries in database...")

    smoke_shop_count = 0
    verified_count = 0

    for d in db_dispensaries:
        name = d['name'] or ''
        norm_name = normalize_name(name)

        # Check if name matches any licensed name
        is_licensed = False
        for lic_name in licensed_names:
            if norm_name in lic_name or lic_name in norm_name:
                is_licensed = True
                break

        if is_licensed:
            verified_count += 1
            if not dry_run:
                update_dispensary_license_status(d['dispensary_id'], True)
        else:
            # Check if it looks like a smoke shop
            name_lower = name.lower()
            if any(kw in name_lower for kw in ['smoke', 'tobacco', 'vape', 'cigar', 'hookah']):
                smoke_shop_count += 1
                if not dry_run:
                    with engine.connect() as conn:
                        conn.execute(text("""
                            UPDATE dispensary
                            SET store_type = 'smoke_shop', updated_at = NOW()
                            WHERE dispensary_id = :id
                        """), {"id": d['dispensary_id']})
                        conn.commit()

    print("\n" + "=" * 60)
    print("Verification Summary:")
    print(f"  Verified as licensed: {verified_count}")
    print(f"  Identified as smoke shops: {smoke_shop_count}")
    print(f"  Remaining unverified: {len(db_dispensaries) - verified_count - smoke_shop_count}")

    if dry_run:
        print("\n[DRY RUN - no changes made. Use --apply to update database]")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Import NY dispensary licenses from Open Data Portal")
    parser.add_argument('--apply', action='store_true', help="Apply changes to database")
    parser.add_argument('--verify', action='store_true', help="Verify existing dispensaries and mark smoke shops")

    args = parser.parse_args()

    if args.verify:
        mark_unlicensed_as_smoke_shops(dry_run=not args.apply)
    else:
        import_ny_retail_dispensaries(dry_run=not args.apply)
