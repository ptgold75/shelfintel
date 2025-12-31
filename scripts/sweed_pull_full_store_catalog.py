from ingest.providers.sweed_api import get_categories, fetch_all_products_for_category

STORE_ID = "376"  # gLeaf Rockville

def main():
    cats = get_categories(STORE_ID)
    print("✅ Categories:", len(cats))

    all_products = {}
    for c in cats:
        name = c["name"]
        filters = c.get("filter") or {}
        prods = fetch_all_products_for_category(STORE_ID, filters, page_size=24, max_pages=120)
        print(f" - {name}: {len(prods)}")

        for p in prods:
            pid = p.get("id")
            if pid is not None:
                all_products[str(pid)] = p

    print("\n✅ Total unique products:", len(all_products))

if __name__ == "__main__":
    main()
