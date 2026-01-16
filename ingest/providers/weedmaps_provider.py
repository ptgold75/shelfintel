# ingest/providers/weedmaps_provider.py
"""
Weedmaps menu provider - fetches all products from Weedmaps API.

Requires weedmaps_slug in provider_metadata.
"""

import json
import time
from typing import Any, Dict, List, Optional
import requests

# Proxy and rate limiting support
try:
    from ingest.proxy_config import get_proxies_dict, get_rate_limiter
    PROXY_AVAILABLE = True
except ImportError:
    PROXY_AVAILABLE = False


def _extract_slug(provider_metadata: Optional[Dict[str, Any]]) -> Optional[str]:
    """Extract weedmaps_slug from provider_metadata JSON."""
    if not provider_metadata:
        return None

    if isinstance(provider_metadata, str):
        try:
            provider_metadata = json.loads(provider_metadata)
        except (json.JSONDecodeError, TypeError):
            return None

    return (
        provider_metadata.get("weedmaps_slug")
        or provider_metadata.get("slug")
    )


def _parse_item(item: dict) -> Dict[str, Any]:
    """Parse a Weedmaps menu item into standard format."""
    name = item.get("name", "")

    # Extract brand
    brand = ""
    if item.get("brand"):
        if isinstance(item["brand"], dict):
            brand = item["brand"].get("name", "")
        else:
            brand = str(item["brand"])

    # Category
    category = ""
    if item.get("category"):
        if isinstance(item["category"], dict):
            category = item["category"].get("name", "")
        else:
            category = str(item["category"])

    # Map Weedmaps categories to standard categories
    category_map = {
        "Hybrid": "Flower",
        "Indica": "Flower",
        "Sativa": "Flower",
        "Pre-Roll": "Pre-Rolls",
        "Vape": "Vaporizers",
        "Concentrate": "Concentrates",
        "Edible": "Edibles",
        "Tincture": "Tinctures",
        "Topical": "Topicals",
        "Accessory": "Accessories",
    }
    category = category_map.get(category, category)

    # Price - get first available
    price = None
    prices = item.get("prices", {})
    if prices:
        for key in ["unit", "half_gram", "gram", "eighth", "quarter", "half_ounce", "ounce"]:
            if key in prices and prices[key]:
                price_data = prices[key]
                if isinstance(price_data, dict):
                    price = price_data.get("price")
                else:
                    price = price_data
                if price:
                    break

    if not price:
        price = item.get("price")

    return {
        "name": name,
        "brand": brand,
        "category": category,
        "price": float(price) if price else None,
        "provider_product_id": str(item.get("id", "")),
        "raw": item,
    }


def fetch_menu_items(
    *,
    menu_url: str,
    provider_metadata: Optional[Dict[str, Any]] = None,
    max_pages: int = 20,
) -> List[Dict[str, Any]]:
    """
    Fetch all menu items from a Weedmaps-powered dispensary.

    Args:
        menu_url: Dispensary menu URL (not used directly, slug from metadata)
        provider_metadata: Dict containing weedmaps_slug
        max_pages: Maximum number of pages to fetch

    Returns:
        List of menu items ready for RawMenuItem insertion
    """
    slug = _extract_slug(provider_metadata)
    if not slug:
        raise ValueError(
            "weedmaps_slug is required in provider_metadata for Weedmaps provider."
        )

    # Rate limiter
    rate_limiter = get_rate_limiter("weedmaps") if PROXY_AVAILABLE else None

    base_url = f"https://api-g.weedmaps.com/discovery/v1/listings/dispensaries/{slug}/menu_items"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json",
    }

    all_items = []
    page = 1
    page_size = 100

    while page <= max_pages:
        if rate_limiter:
            rate_limiter.wait()

        params = {
            "page_size": page_size,
            "page": page
        }

        # Get proxy
        proxies = None
        if PROXY_AVAILABLE:
            proxies = get_proxies_dict(force_rotate=False)

        try:
            r = requests.get(
                base_url,
                params=params,
                headers=headers,
                proxies=proxies,
                timeout=30
            )
            if r.status_code != 200:
                print(f"    Weedmaps page {page}: HTTP {r.status_code}")
                break

            data = r.json()
            items = data.get("data", {}).get("menu_items", [])

            if not items:
                break

            # Parse and add items
            for item in items:
                parsed = _parse_item(item)
                if parsed["name"]:
                    all_items.append(parsed)

            print(f"    Weedmaps page {page}: {len(items)} items (total: {len(all_items)})")

            # Check if more pages
            meta = data.get("meta", {})
            total = meta.get("total_count", 0)
            if len(all_items) >= total:
                break

            page += 1
            time.sleep(0.3)  # Additional rate limiting

        except Exception as e:
            print(f"    Weedmaps error on page {page}: {e}")
            break

    return all_items
