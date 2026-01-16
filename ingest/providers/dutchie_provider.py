# ingest/providers/dutchie_provider.py
"""
Dutchie menu provider - fetches all products from Dutchie-powered dispensary sites.

Requires retailer_id which can be:
1. Passed explicitly via provider_metadata in the dispensary record
2. Discovered via discover_sweed.py and stored in provider_metadata
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ingest.providers.dutchie import DutchieProvider


def _extract_retailer_id(
    provider_metadata: Optional[Dict[str, Any]]
) -> Optional[str]:
    """Extract retailer_id from provider_metadata JSON."""
    if not provider_metadata:
        return None

    if isinstance(provider_metadata, str):
        try:
            provider_metadata = json.loads(provider_metadata)
        except (json.JSONDecodeError, TypeError):
            return None

    return (
        provider_metadata.get("retailer_id")
        or provider_metadata.get("retailerId")
        or provider_metadata.get("dispensary_id")
        or provider_metadata.get("dispensaryId")
    )


def _extract_api_base(
    provider_metadata: Optional[Dict[str, Any]]
) -> Optional[str]:
    """Extract API base URL from provider_metadata."""
    if not provider_metadata:
        return None

    if isinstance(provider_metadata, str):
        try:
            provider_metadata = json.loads(provider_metadata)
        except (json.JSONDecodeError, TypeError):
            return None

    return provider_metadata.get("api_base")


def _infer_menu_type(menu_url: str) -> str:
    """Infer menu type from URL patterns."""
    url_lower = (menu_url or "").lower()
    if "medical" in url_lower or "med" in url_lower:
        return "MEDICAL"
    return "RECREATIONAL"


def _extract_dutchie_slug(menu_url: str) -> str:
    """Extract Dutchie slug from menu URL.

    Examples:
        https://dutchie.com/dispensary/crofton-maryland -> crofton-maryland
        https://example.com/order -> empty string
    """
    import re
    match = re.search(r'dutchie\.com/dispensary/([^/?#]+)', menu_url or "")
    if match:
        return match.group(1)
    return ""


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
    retailer_id: Optional[str] = None,
    provider_metadata: Optional[Dict[str, Any]] = None,
    menu_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch all menu items from a Dutchie-powered dispensary.

    Args:
        menu_url: Dispensary menu URL
        retailer_id: Dutchie retailer ID (optional if in provider_metadata)
        provider_metadata: Dict containing retailer_id and other config
        menu_type: "RECREATIONAL" or "MEDICAL" (auto-detected if not provided)

    Returns:
        List of menu items ready for RawMenuItem insertion
    """
    resolved_retailer_id = retailer_id or _extract_retailer_id(provider_metadata)
    if not resolved_retailer_id:
        raise ValueError(
            "retailer_id is required for Dutchie provider. "
            "Run discover_sweed.py and store the result in dispensary.provider_metadata."
        )

    api_base = _extract_api_base(provider_metadata)
    resolved_menu_type = menu_type or _infer_menu_type(menu_url)

    # Extract Dutchie slug from URL for Playwright fallback
    dutchie_slug = _extract_dutchie_slug(menu_url)

    # Create provider instance with proxy enabled
    provider = DutchieProvider(
        dispensary_id=dutchie_slug,  # Used for Playwright URL construction
        retailer_id=resolved_retailer_id,
        api_base=api_base,
        use_proxy=True,
    )

    # Map menu_type to pricing_type
    pricing_type = "med" if resolved_menu_type == "MEDICAL" else "rec"

    # Scrape and convert items - try regular first, fall back to Playwright
    all_items: List[Dict[str, Any]] = []
    for menu_item in provider.scrape(pricing_type=pricing_type):
        all_items.append(_to_raw_item(menu_item))

    # If regular scrape returned nothing, try Playwright for Cloudflare bypass
    if not all_items:
        print("Regular scrape returned 0 items, trying Playwright...")
        for menu_item in provider.scrape_with_playwright(pricing_type=pricing_type):
            all_items.append(_to_raw_item(menu_item))

    return all_items
