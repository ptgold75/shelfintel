# scripts/lookup_store_names.py
"""Look up store names from Weedmaps/Leafly."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import json
import time
from sqlalchemy import text
from core.db import get_engine

def search_weedmaps(query, lat=39.0, lng=-77.0):
    """Search Weedmaps for dispensary info."""
    url = "https://api-g.weedmaps.com/discovery/v2/listings"
    params = {
        "filter[any_retailer_services][]": "storefront",
        "filter[bounding_radius]": 50,
        "filter[bounding_latlng]": f"{lat},{lng}",
        "page_size": 20,
        "size": 20,
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        r = requests.get(url, params=params, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json().get('data', {}).get('listings', [])
    except:
        pass
    return []

def main():
    engine = get_engine()
    
    # Get stores without real names
    with engine.connect() as conn:
        stores = conn.execute(text("""
            SELECT dispensary_id, name, state, provider_metadata
            FROM dispensary 
            WHERE name LIKE 'Sweed Store #%'
            ORDER BY name
        """)).fetchall()
    
    print(f"Found {len(stores)} stores needing names")
    
    # For now, just list them
    for store in stores[:20]:
        print(f"  {store[1]} - State: {store[2] or 'Unknown'}")
    
    print("\nTo find names, we need to:")
    print("1. Visit each Sweed-powered dispensary website")
    print("2. Or scrape Weedmaps/Leafly directories")
    print("3. Or manually research each store ID")

if __name__ == "__main__":
    main()
