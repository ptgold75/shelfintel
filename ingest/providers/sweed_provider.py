# ingest/providers/sweed_provider.py
"""
Sweed menu provider - fetches all products from Sweed-powered dispensary sites.

Requires store_id which can be:
1. Passed explicitly via provider_metadata in the dispensary record
2. Discovered via discover_sweed.py and stored in provider_metadata

Usage:
    items = fetch_menu_items(menu_url, store_id="12345")
    # or
    items = fetch_menu_items(menu_url, provider_metadata={"store_id": "12345"})
"""

from __future__ import annotations
import json
import re
from typing import Any, Dict, Iterable, List, Optional

from ingest.providers.sweed_api import (
    get_categories,
    fetch_all_products_for_category,
    normalize_sweed_product,
)


def _extract_store_id_from_metadata(provider_metadata: Optional[Dict[str, Any]]) -> Optional[str]:
    """Extract store_id from provider_metadata JSON."""
    if not provider_metadata:
        return None
    if isinstance(provider_metadata, str):
        try:
            provider_metadata = json.loads(provider_metadata)
        except (json.JSONDecodeError, TypeError):
            return None
    return provider_metadata.get("store_id") or provider_metadata.get("storeId")


def _infer_sale_type(menu_url: str) -> str:
    """Infer sale type from URL patterns."""
    url_lower = menu_url.lower()
    if "medical" in url_lower or "med" in url_lower:
        return "Medical"
    return "Recreational"


def fetch_menu_items(
    menu_url: str,
    store_id: Optional[str] = None,
    provider_metadata: Optional[Dict[str, Any]] = None,
    sale_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch all menu items from a Sweed-powered dispensary.
    
    Args:
        menu_url: The dispensary menu URL
        store_id: Sweed store ID (required - pass directly or via provider_metadata)
        provider_metadata: Dict containing store_id and other config
        sale_type: "Recreational" or "Medical" (auto-detected if not provided)
    
    Returns:
        List of normalized menu items ready for RawMenuItem insertion
    """
    # Resolve store_id
    resolved_store_id = store_id or _extract_store_id_from_metadata(provider_metadata)
    
    if not resolved_store_id:
        raise ValueError(
            "store_id is required for Sweed provider. "
            "Run discover_sweed.py on the menu URL and store the result in dispensary.provider_metadata"
        )
    
    # Resolve sale type
    resolved_sale_type = sale_type or _infer_sale_type(menu_url)
    
    # Step 1: Get all categories
    categories = get_categories(store_id=resolved_store_id, sale_type=resolved_sale_type)
    
    if not categories:
        # Try fetching without category filters (some stores return all products)
        all_products = fetch_all_products_for_category(
            store_id=resolved_store_id,
            category_or_filters={},  # Empty filters = all products
            sale_type=resolved_sale_type,
            page_size=60,
        )
        return [_to_raw_item(normalize_sweed_product(p)) for p in all_products]
    
    # Step 2: Fetch products for each category
    all_items: List[Dict[str, Any]] = []
    seen_ids: set = set()
    
    for cat in categories:
        # Categories can be dicts with 'id'/'filter' or just category objects
        cat_id = None
        cat_name = None
        cat_filter = None
        
        if isinstance(cat, dict):
            cat_id = cat.get("id") or cat.get("categoryId") or cat.get("category_id")
            cat_name = cat.get("name") or cat.get("categoryName")
            cat_filter = cat.get("filter") or cat.get("filters")
            
            # If filter is present, use it directly
            if cat_filter and isinstance(cat_filter, dict):
                pass  # Use cat_filter as-is
            elif cat_id:
                cat_filter = {"category": [int(cat_id)]}
            else:
                continue  # Skip if we can't figure out how to query this category
        else:
            # Might be just an ID
            cat_id = cat
            cat_filter = {"category": [int(cat)]}
        
        products = fetch_all_products_for_category(
            store_id=resolved_store_id,
            category_or_filters=cat_filter,
            sale_type=resolved_sale_type,
            page_size=60,
        )
        
        for p in products:
            pid = p.get("id") or p.get("productId")
            if pid and str(pid) in seen_ids:
                continue
            if pid:
                seen_ids.add(str(pid))
            
            normalized = normalize_sweed_product(p, category_name=cat_name)
            all_items.append(_to_raw_item(normalized))
    
    return all_items


def _to_raw_item(normalized: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert normalized Sweed product to the format expected by run_scrape.py.
    
    Expected keys: name, category, brand, price, discount_price, discount_text, 
                   provider_product_id, raw
    """
    return {
        "name": normalized.get("name"),
        "category": normalized.get("category"),
        "brand": normalized.get("brand"),
        "price": normalized.get("price"),
        "discount_price": normalized.get("discount_price"),
        "discount_text": normalized.get("discount_text"),
        "provider_product_id": normalized.get("provider_product_id"),
        "raw": normalized.get("raw", {}),
    }
