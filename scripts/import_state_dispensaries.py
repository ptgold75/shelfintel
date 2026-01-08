#!/usr/bin/env python3
"""Import dispensary data from state databases."""

import json
import uuid
import psycopg2
from psycopg2.extras import execute_values

# Database connection
conn = psycopg2.connect(
    host='db.trteltlgtmcggdbrqwdw.supabase.co',
    database='postgres',
    user='postgres',
    password='Tattershall2020',
    port='5432',
    sslmode='require'
)


def get_existing_dispensaries(state):
    """Get existing dispensaries for a state."""
    cur = conn.cursor()
    cur.execute("""
        SELECT name, address, city FROM dispensary WHERE state = %s
    """, (state,))
    existing = set()
    for row in cur.fetchall():
        # Create a key for matching
        name = (row[0] or '').lower().strip()
        addr = (row[1] or '').lower().strip()
        existing.add((name, addr))
    cur.close()
    return existing


def import_il_dispensaries(json_file):
    """Import IL dispensaries from parsed PDF data."""
    print("\n" + "="*60)
    print("Importing Illinois Dispensaries")
    print("="*60)

    with open(json_file) as f:
        dispensaries = json.load(f)

    existing = get_existing_dispensaries('IL')
    print(f"Existing IL dispensaries: {len(existing)}")

    cur = conn.cursor()
    added = 0
    skipped = 0

    for d in dispensaries:
        name = d.get('name', '').strip()
        address = d.get('address', '').strip()
        phone = d.get('phone', '').strip()

        # Parse city from address (format: "Street City, IL ZIPCODE")
        city = ''
        if ', IL' in address:
            parts = address.split(', IL')
            addr_parts = parts[0].rsplit(' ', 1)
            if len(addr_parts) > 1:
                city = addr_parts[-1]
                address = addr_parts[0]

        # Check if exists
        key = (name.lower(), address.lower())
        if key in existing:
            skipped += 1
            continue

        # Insert
        try:
            dispensary_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO dispensary (dispensary_id, name, address, city, state, phone, is_active, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (dispensary_id, name, address, city, 'IL', phone, True, 'state_database'))
            added += 1
            print(f"  Added: {name} - {city}")
        except Exception as e:
            print(f"  Error adding {name}: {e}")
            conn.rollback()

    conn.commit()
    cur.close()

    print(f"\nAdded: {added}, Skipped (existing): {skipped}")
    return added


def import_leafly_dispensaries(json_file, state):
    """Import dispensaries from Leafly scrape."""
    print(f"\n{'='*60}")
    print(f"Importing {state} Dispensaries from Leafly")
    print("="*60)

    with open(json_file) as f:
        dispensaries = json.load(f)

    existing = get_existing_dispensaries(state)
    print(f"Existing {state} dispensaries: {len(existing)}")

    cur = conn.cursor()
    added = 0
    skipped = 0

    for d in dispensaries:
        name = d.get('name', '').strip()
        address = d.get('address', '').strip()
        url = d.get('url', '').strip()

        # Skip if no valid name
        if not name or len(name) < 3:
            continue

        # Check if exists (by name only for Leafly since addresses may differ)
        name_lower = name.lower()
        if any(name_lower in existing_name for existing_name, _ in existing):
            skipped += 1
            continue

        # Parse city from address
        city = ''
        if address:
            parts = address.split(',')
            if len(parts) >= 2:
                city = parts[-2].strip().split()[-1] if len(parts[-2].strip().split()) > 1 else parts[-2].strip()

        # Insert
        try:
            dispensary_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO dispensary (dispensary_id, name, address, city, state, menu_url, is_active, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (dispensary_id, name, address, city, state, url, True, 'leafly'))
            added += 1
            print(f"  Added: {name}")
        except Exception as e:
            print(f"  Error adding {name}: {e}")
            conn.rollback()

    conn.commit()
    cur.close()

    print(f"\nAdded: {added}, Skipped (existing): {skipped}")
    return added


if __name__ == '__main__':
    # Import IL from state database
    try:
        import_il_dispensaries('/tmp/il_dispensaries.json')
    except FileNotFoundError:
        print("IL dispensaries file not found")

    # Import NJ from Leafly
    try:
        import_leafly_dispensaries('leafly_nj_dispensaries.json', 'NJ')
    except FileNotFoundError:
        print("NJ Leafly file not found")

    conn.close()
    print("\nDone!")
