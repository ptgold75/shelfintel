# ingest/providers/sweed_api.py
"""
Sweed POS API client for fetching dispensary menu data.

The Sweed API requires a store_id header to identify the dispensary.
This can be discovered using discover_sweed.py.

API Base: https://web-ui-production.sweedpos.com/_api/proxy
"""

import json
import time
from typing import Any, Dict, List, Optional

import requests

SWEED_BASE = "https://web-ui-production.sweedpos.com/_api/proxy"
DEFAULT_TIMEOUT = 30


def _headers(store_id: str, sale_type: str = "Recreational", referer: Optional[str] = None) -> Dict[str, str]:
    """Build headers for Sweed API requests."""
    h = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "storeid": str(store_id),
        "saletype": sale_type,
        "ssr": "false",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    if referer:
        h["referer"] = referer
        h["origin"] = referer.split("/")[0] + "//" + referer.split("/")[2]
    return h


def get_categories(
    store_id: str,
    sale_type: str = "Recreational",
    referer: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch product categories for a store.
    
    Returns list of category objects. Structure varies by store config.
    """
    url = f"{SWEED_BASE}/Products/GetProductCategoryList"
    payload = {"saleType": sale_type}
    
    try:
        r = requests.post(
            url,
            headers=_headers(store_id, sale_type, referer),
            json=payload,
            timeout=DEFAULT_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        
        # Handle various response shapes
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ["data", "result", "items", "categories", "list"]:
                if isinstance(data.get(key), list):
                    return data[key]
        
        return []
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to get categories: {e}")


def get_product_list(
    store_id: str,
    filters: Dict[str, Any],
    sale_type: str = "Recreational",
    page: int = 1,
    page_size: int = 60,
    sorting_method_id: int = 7,
    search_term: str = "",
    referer: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch a page of products.
    
    Args:
        store_id: Sweed store identifier
        filters: Category/filter dict, e.g., {"category": [495364]}
        sale_type: "Recreational" or "Medical"
        page: Page number (1-indexed)
        page_size: Items per page (max typically 60)
        sorting_method_id: Sort order (7 = default/popular)
    
    Returns raw API response dict.
    """
    url = f"{SWEED_BASE}/Products/GetProductList"
    
    payload = {
        "filters": filters,
        "page": page,
        "pageSize": page_size,
        "sortingMethodId": sorting_method_id,
        "searchTerm": search_term,
        "saleType": sale_type,
        "platformOs": "web",
        "sourcePage": 1,
    }
    
    r = requests.post(
        url,
        headers=_headers(store_id, sale_type, referer),
        json=payload,
        timeout=DEFAULT_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def _extract_products(resp: Any) -> List[Dict[str, Any]]:
    """Extract product list from API response."""
    if not isinstance(resp, dict):
        return []
    
    # Most common: products under "list" key
    if isinstance(resp.get("list"), list):
        return resp["list"]
    
    # Alternative shapes
    for key in ["products", "items", "data", "result"]:
        v = resp.get(key)
        if isinstance(v, list):
            return v
        if isinstance(v, dict):
            for subkey in ["list", "items", "products", "data"]:
                if isinstance(v.get(subkey), list):
                    return v[subkey]
    
    return []


def fetch_all_products_for_category(
    store_id: str,
    category_or_filters: Any,
    sale_type: str = "Recreational",
    page_size: int = 60,
    max_pages: int = 100,
    polite_delay_s: float = 0.15,
    referer: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch all products for a category, handling pagination.
    
    Args:
        store_id: Sweed store ID
        category_or_filters: Either:
            - int: category ID → becomes {"category": [id]}
            - dict: filters object to use directly
        sale_type: "Recreational" or "Medical"
        page_size: Items per page
        max_pages: Safety limit to prevent infinite loops
        polite_delay_s: Delay between requests
    
    Returns list of raw product dicts from API.
    """
    # Normalize filters
    if isinstance(category_or_filters, dict):
        filters = category_or_filters
    elif category_or_filters is not None:
        filters = {"category": [int(category_or_filters)]}
    else:
        filters = {}
    
    all_products: List[Dict[str, Any]] = []
    seen_ids: set = set()
    
    page = 1
    while page <= max_pages:
        try:
            resp = get_product_list(
                store_id=store_id,
                filters=filters,
                sale_type=sale_type,
                page=page,
                page_size=page_size,
                referer=referer,
            )
        except Exception as e:
            print(f"  Warning: Error on page {page}: {e}")
            break
        
        products = _extract_products(resp)
        
        if not products:
            break
        
        # Dedupe by product ID
        new_count = 0
        for p in products:
            pid = p.get("id") or p.get("productId") or p.get("ProductId")
            key = str(pid) if pid else json.dumps(p, sort_keys=True)[:200]
            
            if key not in seen_ids:
                seen_ids.add(key)
                all_products.append(p)
                new_count += 1
        
        # Stop if no new products (hit end or duplicate page)
        if new_count == 0:
            break
        
        # Stop if fewer than page_size returned (last page)
        if len(products) < page_size:
            break
        
        page += 1
        if polite_delay_s > 0:
            time.sleep(polite_delay_s)
    
    return all_products


def normalize_sweed_product(p: Dict[str, Any], category_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Convert Sweed product JSON to standardized format.
    
    Returns dict with keys:
        - provider_product_id
        - name
        - category
        - brand
        - price
        - discount_price
        - discount_text
        - raw (original JSON)
    """
    # Name
    name = p.get("name") or p.get("productName") or ""
    
    # Brand - can be string or object
    brand = None
    brand_val = p.get("brand")
    if isinstance(brand_val, dict):
        brand = brand_val.get("name")
    elif isinstance(brand_val, str):
        brand = brand_val
    
    # Category - can be string or object, or use passed-in name
    category = category_name
    if not category:
        cat_val = p.get("category")
        if isinstance(cat_val, dict):
            category = cat_val.get("name")
        elif isinstance(cat_val, str):
            category = cat_val
    
    # Pricing - typically in variants array
    price = None
    discount_price = None
    discount_text = None
    
    variants = p.get("variants") or []
    if isinstance(variants, list) and variants:
        v0 = variants[0]
        
        # Regular price
        for key in ["price", "basePrice", "regularPrice", "unitPrice"]:
            val = v0.get(key)
            if isinstance(val, (int, float)) and val > 0:
                price = float(val)
                break
        
        # Discount price
        for key in ["discountPrice", "salePrice", "finalPrice", "specialPrice"]:
            val = v0.get(key)
            if isinstance(val, (int, float)) and val > 0:
                discount_price = float(val)
                break
        
        # Discount text
        discount_text = v0.get("discountText") or v0.get("promoText")
    
    # If no variants, try top-level price
    if price is None:
        for key in ["price", "basePrice", "unitPrice"]:
            val = p.get(key)
            if isinstance(val, (int, float)) and val > 0:
                price = float(val)
                break
    
    return {
        "provider_product_id": str(p.get("id")) if p.get("id") is not None else None,
        "name": name,
        "category": category,
        "brand": brand,
        "price": price,
        "discount_price": discount_price,
        "discount_text": discount_text,
        "raw": p,
    }


# =============================================================================
# CLI for testing
# =============================================================================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Sweed API")
    parser.add_argument("--store-id", required=True, help="Sweed store ID")
    parser.add_argument("--sale-type", default="Recreational", help="Recreational or Medical")
    parser.add_argument("--categories", action="store_true", help="Fetch categories")
    parser.add_argument("--products", action="store_true", help="Fetch all products")
    args = parser.parse_args()
    
    if args.categories:
        print("Fetching categories...")
        cats = get_categories(args.store_id, args.sale_type)
        print(f"Found {len(cats)} categories:")
        for c in cats[:10]:
            print(f"  {c}")
    
    if args.products:
        print("Fetching all products...")
        products = fetch_all_products_for_category(
            store_id=args.store_id,
            category_or_filters={},  # Empty = all
            sale_type=args.sale_type,
        )
        print(f"Found {len(products)} products")
        
        # Sample output
        for p in products[:5]:
            norm = normalize_sweed_product(p)
            print(f"  {norm['brand']} - {norm['name']}: ${norm['price']}")
