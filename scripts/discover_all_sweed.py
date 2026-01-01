# scripts/discover_all_sweed.py
"""Discover all Sweed stores by trying IDs 1-1000"""

import json
import time
import requests
from pathlib import Path

SWEED_BASE = "https://web-ui-production.sweedpos.com/_api/proxy"

def try_store(store_id: int) -> dict | None:
    """Try to fetch categories for a store ID. Returns store info if valid."""
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "storeid": str(store_id),
        "saletype": "Recreational",
        "user-agent": "Mozilla/5.0",
    }
    
    try:
        r = requests.post(
            f"{SWEED_BASE}/Products/GetProductCategoryList",
            headers=headers,
            json={"saleType": "Recreational"},
            timeout=10,
        )
        
        if r.status_code == 200:
            data = r.json()
            # Check if we got actual data back
            if data and (isinstance(data, list) or (isinstance(data, dict) and data.get("data"))):
                return {"store_id": store_id, "response_sample": str(data)[:500]}
        
        return None
    except Exception as e:
        return None

def main():
    print("🔍 Discovering Sweed stores (IDs 1-1000)...")
    print("This will take ~15-20 minutes\n")
    
    found = []
    
    for store_id in range(1, 1001):
        result = try_store(store_id)
        
        if result:
            found.append(result)
            print(f"✅ Found store ID: {store_id}")
        elif store_id % 50 == 0:
            print(f"   Checked {store_id}/1000... ({len(found)} found so far)")
        
        time.sleep(0.1)  # Be polite
    
    # Save results
    output_file = Path("sweed_stores_discovered.json")
    with open(output_file, "w") as f:
        json.dump(found, f, indent=2)
    
    print(f"\n✅ Done! Found {len(found)} stores")
    print(f"📄 Saved to {output_file}")
    
    # Print summary
    print("\nStore IDs found:")
    for s in found:
        print(f"  - {s['store_id']}")

if __name__ == "__main__":
    main()
