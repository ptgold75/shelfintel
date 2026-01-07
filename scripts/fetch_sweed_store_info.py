#!/usr/bin/env python3
"""Fetch store info for all discovered Sweed store IDs."""

import json
import requests
import time
from pathlib import Path

# Load discovered store IDs
discovered_file = Path(__file__).parent.parent / "sweed_stores_discovered.json"
with open(discovered_file) as f:
    discovered = json.load(f)

store_ids = sorted([d["store_id"] for d in discovered])
print(f"Found {len(store_ids)} store IDs to fetch")

# Sweed API endpoint
API_BASE = "https://web-ui-production.sweedpos.com/_api/proxy/Store/GetStoreInfo"

# Headers
headers = {
    "Content-Type": "application/json",
    "Accept": "*/*",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

stores = []
errors = []

for i, store_id in enumerate(store_ids):
    try:
        # Make request with store ID header
        req_headers = {**headers, "storeid": str(store_id)}
        resp = requests.post(API_BASE, headers=req_headers, json={}, timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            store_info = {
                "store_id": store_id,
                "name": data.get("name"),
                "address": data.get("contacts", {}).get("address"),
                "city": data.get("location", {}).get("city", {}).get("name"),
                "state": data.get("location", {}).get("region", {}).get("name"),
                "zip": data.get("location", {}).get("zipCode"),
                "sale_types": data.get("saleTypes", []),
                "url": data.get("url"),
                "lat": data.get("location", {}).get("coords", {}).get("lat"),
                "lng": data.get("location", {}).get("coords", {}).get("lng")
            }
            stores.append(store_info)
            print(f"[{i+1}/{len(store_ids)}] {store_id}: {store_info['name']} - {store_info['city']}, {store_info['state']}")
        else:
            errors.append({"store_id": store_id, "status": resp.status_code})
            print(f"[{i+1}/{len(store_ids)}] {store_id}: ERROR {resp.status_code}")

        # Rate limiting
        time.sleep(0.3)

    except Exception as e:
        errors.append({"store_id": store_id, "error": str(e)})
        print(f"[{i+1}/{len(store_ids)}] {store_id}: EXCEPTION {e}")

# Save results
output_file = Path(__file__).parent.parent / "sweed_stores_info.json"
with open(output_file, "w") as f:
    json.dump({
        "stores": stores,
        "errors": errors,
        "total_discovered": len(store_ids),
        "total_fetched": len(stores)
    }, f, indent=2)

print(f"\nDone! Fetched {len(stores)} stores, {len(errors)} errors")
print(f"Results saved to {output_file}")

# Print summary by state
from collections import Counter
states = Counter([s["state"] for s in stores if s.get("state")])
print("\nStores by state:")
for state, count in states.most_common():
    print(f"  {state}: {count}")
