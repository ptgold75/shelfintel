import os, sys, json, time, requests
from collections import Counter
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.db import get_session
from core.models import Dispensary

SWEED_BASE = "https://web-ui-production.sweedpos.com/_api/proxy"

def get_sample_products(store_id, count=20):
    headers = {"accept": "application/json", "content-type": "application/json", "storeid": store_id, "saletype": "Recreational", "user-agent": "Mozilla/5.0"}
    try:
        r = requests.post(f"{SWEED_BASE}/Products/GetProductList", headers=headers, json={"filters": {}, "page": 1, "pageSize": count, "saleType": "Recreational"}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            return data.get("list") or data.get("products") or data.get("data") or []
    except:
        pass
    return []

def main():
    db = get_session()
    stores = db.query(Dispensary).filter(Dispensary.menu_provider == "sweed", Dispensary.name.like("Sweed Store #%")).all()
    print(f"Found {len(stores)} unidentified Sweed stores")
    results = []
    for i, store in enumerate(stores):
        meta = json.loads(store.provider_metadata or "{}")
        store_id = meta.get("store_id")
        if not store_id: continue
        print(f"[{i+1}/{len(stores)}] Store #{store_id}...", end=" ")
        products = get_sample_products(store_id)
        brands = []
        for p in products:
            b = p.get("brand")
            if isinstance(b, dict):
                b = b.get("name")
            if b:
                brands.append(b)
        brand_counts = Counter(brands).most_common(5)
        results.append({"store_id": store_id, "product_count": len(products), "top_brands": brand_counts})
        if brand_counts:
            print(", ".join([f"{b[0]}({b[1]})" for b in brand_counts[:3]]))
        else:
            print("No products")
        time.sleep(0.15)
    with open("store_identification.csv", "w") as f:
        f.write("store_id,product_count,top_brands\n")
        for r in results:
            brands = "; ".join([f"{b[0]}({b[1]})" for b in r["top_brands"]])
            f.write(f'{r["store_id"]},{r["product_count"]},"{brands}"\n')
    print("Saved to store_identification.csv")
    db.close()

if __name__ == "__main__":
    main()
