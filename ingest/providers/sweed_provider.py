from typing import Any, Dict, List

from ingest.providers.sweed_api import (
    get_categories,
    fetch_all_products_for_category,
    normalize_sweed_product,
)

def fetch_menu_items(menu_url: str, store_id: str | None = None) -> List[Dict[str, Any]]:
    """
    Full catalog ingestion using Sweed API.
    Menu availability (not vault inventory).
    """

    # TEMP: hardcoded until we add store_id to dispensary table
    if store_id is None:
        store_id = "376"  # gLeaf Rockville

    categories = get_categories(store_id)
    items: List[Dict[str, Any]] = []

    for c in categories:
        category_name = c.get("name")
        filters = c.get("filter") or {}

        products = fetch_all_products_for_category(
            store_id=store_id,
            category_or_filters=filters,
            page_size=24,
            max_pages=200,
        )

        for p in products:
            items.append(
                normalize_sweed_product(p, category_name=category_name)
            )

    return items
