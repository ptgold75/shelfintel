#!/usr/bin/env python3
"""Add new NJ Sweed stores to database and scrape them."""

import json
import psycopg2
import uuid
from datetime import datetime

# Database connection
conn = psycopg2.connect(
    host='db.trteltlgtmcggdbrqwdw.supabase.co',
    database='postgres',
    user='postgres',
    password='Tattershall2020',
    port='5432',
    sslmode='require'
)

# Load discovered stores
with open('/Users/gleaf/shelfintel/sweed_stores_info.json') as f:
    data = json.load(f)

# Current stores in DB
existing_store_ids = {'128', '129', '130', '552', '553', '554', '555'}

# NJ stores to add
nj_stores = [s for s in data['stores'] if s.get('state') == 'New Jersey']

# Exclude test stores and duplicates
test_keywords = ['test', 'autotest', 'metrc']
valid_stores = []
seen_addresses = set()

for s in nj_stores:
    name = s.get('name', '').lower()
    addr = s.get('address', '')

    if any(k in name for k in test_keywords):
        continue
    if str(s['store_id']) in existing_store_ids:
        continue
    if addr in seen_addresses:
        continue
    seen_addresses.add(addr)
    valid_stores.append(s)

print(f"Adding {len(valid_stores)} new NJ stores...")

cur = conn.cursor()

for store in valid_stores:
    # Determine API base (production for non-Curaleaf)
    api_base = "https://web-ui-production.sweedpos.com"

    provider_metadata = {
        "provider": "sweed",
        "store_id": str(store['store_id']),
        "api_base": api_base,
        "sale_types": store.get('sale_types', []),
        "url": store.get('url'),
        "lat": store.get('lat'),
        "lng": store.get('lng')
    }

    # Generate new UUID
    dispensary_id = str(uuid.uuid4())

    try:
        cur.execute('''
            INSERT INTO dispensary (dispensary_id, name, city, state, address, is_active, provider_metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (
            dispensary_id,
            store['name'],
            store['city'],
            'NJ',
            store.get('address'),
            True,
            json.dumps(provider_metadata)
        ))
        print(f"  Added: {store['name']} - {store['city']} (store_id: {store['store_id']})")
    except Exception as e:
        print(f"  Error adding {store['name']}: {e}")
        conn.rollback()

conn.commit()
cur.close()
conn.close()

print("\nDone! Now run scraper to collect products.")
