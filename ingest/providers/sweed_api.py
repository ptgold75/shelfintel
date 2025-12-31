import json
import time
from typing import Any, Dict, List, Optional

import requests

SWEED_BASE = "https://web-ui-production.sweedpos.com/_api/proxy"

def _headers(store_id: str, sale_type: str = "Recreational") -> Dict[str, str]:
    # These headers mirror what the browser sends. storeid is the key requirement.
    return {
        "accept": "*/*",
        "content-type": "application/json",
        "referer": "https://www.gleaf.com/",
        "storeid": str(store_id),
        "saletype": sale_type,
        # x-cookie not strictly required in many cases; omit unless needed
        "ssr": "false",
        "user-agent": "Mozilla/5.0",
    }

def get_categories(store_id: str, sale_type: str = "Recreational") -> List[Dict[str, Any]]:
    url = f"{SWEED_BASE}/Products/GetProductCategoryList"
    payload = {"saleType": sale_type}
    r = requests.post(url, headers=_headers(store_id, sale_type), json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    # shape varies; try common forms
    if isinstance(data, dict):
        for k in ["data", "result", "items", "categories"]:
            if isinstance(data.get(k), list):
                return data[k]
    if isinstance(data, list):
        return data
    return []

def get_product_list(
    store_id: str,
    filters: Dict[str, Any],
    sale_type: str = "Recreational",
    page: int = 1,
    page_size: int = 24,
    sorting_method_id: int = 7,
    search_term: str = "",
    platform_os: str = "web",
    source_page: int = 1,
) -> Dict[str, Any]:
    url = f"{SWEED_BASE}/Products/GetProductList"
    payload: Dict[str, Any] = {
        "filters": filters,
        "page": page,
        "pageSize": page_size,
        "sortingMethodId": sorting_method_id,
        "searchTerm": search_term,
        "saleType": sale_type,
        "platformOs": platform_os,
        "sourcePage": source_page,
    }
    r = requests.post(url, headers=_headers(store_id, sale_type), json=payload, timeout=30)
    r.raise_for_status()
    return r.json()

def _extract_products(resp: Any) -> List[Dict[str, Any]]:
    """Sweed GetProductList returns products under key 'list'."""
    if isinstance(resp, dict):
        if isinstance(resp.get("list"), list):
            return resp["list"]

        # fallback shapes (just in case)
        for k in ["products", "items", "data", "result"]:
            v = resp.get(k)
            if isinstance(v, list):
                return v
            if isinstance(v, dict):
                for kk in ["list", "items", "products", "data"]:
                    if isinstance(v.get(kk), list):
                        return v[kk]
    return []

def fetch_all_products_for_category(
    store_id: str,
    category_or_filters,
    sale_type: str = "Recreational",
    page_size: int = 24,
    max_pages: int = 100,
    polite_delay_s: float = 0.15,
) -> List[Dict[str, Any]]:
    """
    Fetches all pages via GetProductList.

    category_or_filters:
      - int category id (e.g., 495364)
      - OR a dict filters object (e.g., {"category":[495364]}) from GetProductCategoryList["filter"]
    """
    all_products: List[Dict[str, Any]] = []
    seen_ids = set()

    # Accept either an int category id or a full filters dict
    if isinstance(category_or_filters, dict):
        filters = category_or_filters
    else:
        filters = {"category": [int(category_or_filters)]}

    page = 1
    while page <= max_pages:
        resp = get_product_list(
            store_id=store_id,
            sale_type=sale_type,
            filters=filters,
            page=page,
            page_size=page_size,
        )
        products = _extract_products(resp)

        if not products:
            break

        new_count = 0
        for p in products:
            pid = p.get("id") or p.get("productId") or p.get("ProductId")
            key = str(pid) if pid is not None else json.dumps(p, sort_keys=True)[:200]
            if key in seen_ids:
                continue
            seen_ids.add(key)
            all_products.append(p)
            new_count += 1

        if new_count == 0:
            break

        page += 1
        time.sleep(polite_delay_s)

    return all_products

def normalize_sweed_product(p: Dict[str, Any], category_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Converts Sweed product JSON to your internal item format.
    Pull price/discount from variants when available.
    """
    name = p.get("name")
    brand = None
    if isinstance(p.get("brand"), dict):
        brand = p["brand"].get("name")
    elif isinstance(p.get("brand"), str):
        brand = p["brand"]

    category = category_name or (p.get("category", {}).get("name") if isinstance(p.get("category"), dict) else p.get("category"))

    # pricing: often in variants
    price = None
    discount_price = None
    discount_text = None

    variants = p.get("variants") or []
    if isinstance(variants, list) and variants:
        v0 = variants[0]
        # try common fields
        for k in ["price", "basePrice", "regularPrice"]:
            if isinstance(v0.get(k), (int, float)):
                price = float(v0[k]); break
        for k in ["discountPrice", "salePrice", "finalPrice"]:
            if isinstance(v0.get(k), (int, float)):
                discount_price = float(v0[k]); break
        if v0.get("discountText"):
            discount_text = v0.get("discountText")

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
