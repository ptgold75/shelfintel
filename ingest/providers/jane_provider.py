# ingest/providers/jane_provider.py
"""
iHeartJane menu provider - fetches all products from Jane-powered dispensary sites.

Requires jane_store_id which can be:
1. Passed explicitly via provider_metadata in the dispensary record
2. Discovered via discover_sweed.py and stored in provider_metadata
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ingest.providers.jane import JaneProvider


def _extract_store_id(
    provider_metadata: Optional[Dict[str, Any]]
) -> Optional[str]:
    """Extract jane_store_id from provider_metadata JSON."""
    if not provider_metadata:
        return None

    if isinstance(provider_metadata, str):
        try:
            provider_metadata = json.loads(provider_metadata)
        except (json.JSONDecodeError, TypeError):
            return None

    return (
        provider_metadata.get("jane_store_id")
        or provider_metadata.get("store_id")
        or provider_metadata.get("storeId")
    )


def _to_raw_item(menu_item) -> Dict[str, Any]:
    """Convert MenuItem to the format expected by run_scrape.py."""
    return {
        "name": menu_item.raw_name,
        "category": menu_item.raw_category,
        "brand": menu_item.raw_brand,
        "price": menu_item.raw_price,
        "discount_price": menu_item.raw_discount_price,
        "discount_text": menu_item.raw_discount_text,
        "provider_product_id": menu_item.provider_product_id,
        "raw": menu_item.raw_json,
    }


def fetch_menu_items(
    *,
    menu_url: str,
    store_id: Optional[str] = None,
    provider_metadata: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch all menu items from a Jane-powered dispensary.

    Uses a multi-tier approach:
    1. REST API (fastest, but often blocked by Cloudflare)
    2. Algolia search (alternative API, also may be blocked)
    3. Playwright with proxy (headless browser, bypasses Cloudflare)

    Args:
        menu_url: Dispensary menu URL
        store_id: Jane store ID (optional if in provider_metadata)
        provider_metadata: Dict containing jane_store_id and other config

    Returns:
        List of menu items ready for RawMenuItem insertion
    """
    resolved_store_id = store_id or _extract_store_id(provider_metadata)
    if not resolved_store_id:
        raise ValueError(
            "jane_store_id is required for Jane provider. "
            "Run discover_sweed.py and store the result in dispensary.provider_metadata."
        )

    # Create provider instance with proxy enabled
    provider = JaneProvider(
        dispensary_id="",  # Not needed for scraping
        store_id=resolved_store_id,
        use_proxy=True,  # Enable proxy for Cloudflare bypass
        menu_url=menu_url,  # Pass the actual dispensary URL for Playwright fallback
    )

    # Scrape and convert items (REST API + Algolia fallback)
    all_items: List[Dict[str, Any]] = []
    for menu_item in provider.scrape():
        all_items.append(_to_raw_item(menu_item))

    # If no items found, try Playwright with proxy to bypass Cloudflare
    if not all_items:
        print(f"REST/Algolia returned no products, trying Playwright for store {resolved_store_id}...")
        for menu_item in provider.scrape_with_playwright():
            all_items.append(_to_raw_item(menu_item))

    return all_items
