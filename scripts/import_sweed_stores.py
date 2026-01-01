# scripts/import_sweed_stores.py
"""Import all discovered Sweed stores into the database."""

import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.db import get_session
from core.models import Dispensary


def main():
    # Load discovered stores
    with open("sweed_stores_discovered.json") as f:
        stores = json.load(f)
    
    print(f"Found {len(stores)} stores in discovery file")
    
    db = get_session()
    
    # Get existing store IDs to avoid duplicates
    existing = db.query(Dispensary).filter(
        Dispensary.menu_provider == "sweed"
    ).all()
    
    existing_store_ids = set()
    for d in existing:
        if d.provider_metadata:
            try:
                meta = json.loads(d.provider_metadata)
                if meta.get("store_id"):
                    existing_store_ids.add(str(meta["store_id"]))
            except:
                pass
    
    print(f"Already have {len(existing_store_ids)} Sweed stores in database")
    
    added = 0
    skipped = 0
    
    for store in stores:
        store_id = str(store["store_id"])
        
        if store_id in existing_store_ids:
            skipped += 1
            continue
        
        disp = Dispensary(
            name=f"Sweed Store #{store_id}",
            state="XX",  # Unknown - update later
            menu_url=f"https://sweedpos.com/store/{store_id}",  # Placeholder
            menu_provider="sweed",
            provider_metadata=json.dumps({"store_id": store_id}),
            is_active=True,
        )
        db.add(disp)
        added += 1
        print(f"  ✅ Added store #{store_id}")
    
    db.commit()
    db.close()
    
    print(f"\n{'='*40}")
    print(f"✅ Added: {added}")
    print(f"⏭️ Skipped (already exist): {skipped}")
    print(f"📊 Total Sweed stores in DB: {len(existing_store_ids) + added}")


if __name__ == "__main__":
    main()
