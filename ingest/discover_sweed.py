# ingest/discover_sweed.py
"""
Dispensary URL discovery - detects provider type and extracts configuration.

Supports:
- Sweed
- Dutchie (GraphQL API)
- iHeartJane (REST API)

Usage:
    python ingest/discover_sweed.py --url "https://www.gleaf.com/stores/maryland/rockville/shop"
    python ingest/discover_sweed.py --file urls.txt --out results.jsonl
"""

import argparse
import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, parse_qs

from playwright.sync_api import sync_playwright

# Proxy support
try:
    from ingest.proxy_config import get_playwright_proxy
    PROXY_AVAILABLE = True
except ImportError:
    PROXY_AVAILABLE = False

# Provider detection hints (HTML/URL patterns)
SWEED_HINTS = ["sweed", "sweedpos", "stocktype=default"]
DUTCHIE_HINTS = ["dutchie", "dutchie-plus", "embed.dutchie", "dutchie.com"]
JANE_HINTS = ["iheartjane", "jane.com", "jane-embed", "api.iheartjane"]

# API endpoint patterns by provider
SWEED_API_PATTERNS = [
    "sweedpos.com/_api/proxy/Products/GetProductCategoryList",
    "sweedpos.com/_api/proxy/Products/GetProductList",
    "sweedpos.com/api/Product",
]

DUTCHIE_API_PATTERNS = [
    "dutchie.com/graphql",
    "plus.dutchie.com/plus",
    "dutchie.com/embedded-menu",
    "api.dutchie.com",
]

JANE_API_PATTERNS = [
    "api.iheartjane.com/v1/stores",
    "api.iheartjane.com/v1/products",
    "iheartjane.com/embed",
    "api.iheartjane.com/v1/",
]

# All patterns for network capture
ALL_API_PATTERNS = SWEED_API_PATTERNS + DUTCHIE_API_PATTERNS + JANE_API_PATTERNS


def _looks_like_sweed(url: str, html: str) -> float:
    """Score how likely this is a Sweed site (0.0 - 1.0)."""
    score = 0.0
    combined = (url + " " + html).lower()
    
    for hint in SWEED_HINTS:
        if hint in combined:
            score += 0.15
    
    # Strong indicators
    if "sweedpos.com" in combined:
        score += 0.4
    if "web-ui-production.sweedpos.com" in combined:
        score += 0.3
    
    return min(score, 1.0)


def _looks_like_dutchie(url: str, html: str) -> float:
    """Score how likely this is a Dutchie site."""
    score = 0.0
    combined = (url + " " + html).lower()

    for hint in DUTCHIE_HINTS:
        if hint in combined:
            score += 0.2

    # Strong indicators
    if "dutchie.com/graphql" in combined:
        score += 0.4
    if "plus.dutchie.com" in combined:
        score += 0.3
    if "embedded-menu" in combined:
        score += 0.2

    return min(score, 1.0)


def _looks_like_jane(url: str, html: str) -> float:
    """Score how likely this is an iHeartJane site."""
    score = 0.0
    combined = (url + " " + html).lower()

    for hint in JANE_HINTS:
        if hint in combined:
            score += 0.2

    # Strong indicators
    if "api.iheartjane.com" in combined:
        score += 0.5
    if "/v1/stores/" in combined:
        score += 0.3

    return min(score, 1.0)


def _find_menu_category_id(url: str) -> Optional[str]:
    """Extract menu category ID from URL like /menu/flower-3763."""
    m = re.search(r"/menu/[^/]+-(\d+)", url)
    return m.group(1) if m else None


def _extract_from_json(text: str, keys: List[str]) -> Optional[str]:
    """Try to extract a value from JSON-like text for any of the given keys."""
    for key in keys:
        # Try JSON parsing first
        patterns = [
            rf'"{key}"\s*:\s*"([^"]+)"',  # "key": "value"
            rf'"{key}"\s*:\s*(\d+)',       # "key": 123
            rf"'{key}'\s*:\s*'([^']+)'",   # 'key': 'value'
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                return m.group(1)
    return None


def _extract_store_id(texts: List[str], headers: List[Dict]) -> Optional[str]:
    """Extract store_id from request/response data."""
    # Check headers first (most reliable)
    for h in headers:
        for key in ["storeid", "store-id", "x-store-id", "locationid", "location-id"]:
            if key in h:
                return str(h[key])
    
    # Check text blobs (payloads, responses)
    combined = "\n".join(t or "" for t in texts)
    
    store_keys = ["storeId", "StoreId", "store_id", "locationId", "LocationId", "location_id"]
    result = _extract_from_json(combined, store_keys)
    if result:
        return result
    
    # URL parameter fallback
    m = re.search(r'[?&](?:store_?id|location_?id)=(\d+)', combined, re.IGNORECASE)
    if m:
        return m.group(1)
    
    return None


def _extract_tenant_id(texts: List[str], headers: List[Dict]) -> Optional[str]:
    """Extract tenant_id from request/response data."""
    for h in headers:
        for key in ["tenantid", "tenant-id", "x-tenant-id", "clientid", "client-id"]:
            if key in h:
                return str(h[key])

    combined = "\n".join(t or "" for t in texts)

    tenant_keys = ["tenantId", "TenantId", "tenant_id", "clientId", "ClientId", "client_id", "orgId", "customerId"]
    return _extract_from_json(combined, tenant_keys)


def _extract_dutchie_retailer_id(texts: List[str], urls: List[str]) -> Optional[str]:
    """Extract Dutchie retailer ID from GraphQL requests or URLs."""
    combined = "\n".join(t or "" for t in texts)
    all_urls = "\n".join(urls)

    # Check for retailerId in GraphQL variables
    retailer_keys = ["retailerId", "retailer_id", "dispensaryId", "dispensary_id"]
    result = _extract_from_json(combined, retailer_keys)
    if result:
        return result

    # Check embedded menu URL pattern: /embedded-menu/{retailer-slug}
    m = re.search(r'/embedded-menu/([a-z0-9-]+)', all_urls, re.IGNORECASE)
    if m:
        return m.group(1)

    # Check for retailer in URL path
    m = re.search(r'dutchie\.com/([a-z0-9-]+)(?:/|$)', all_urls, re.IGNORECASE)
    if m and m.group(1) not in ['graphql', 'plus', 'embedded-menu', 'api']:
        return m.group(1)

    return None


def _extract_jane_store_id(texts: List[str], urls: List[str]) -> Optional[str]:
    """Extract iHeartJane store ID from API requests."""
    # Check URLs for /v1/stores/{id} pattern
    for url in urls:
        m = re.search(r'/v1/stores/(\d+)', url)
        if m:
            return m.group(1)

    combined = "\n".join(t or "" for t in texts)

    # Check JSON responses for store_id
    jane_keys = ["store_id", "storeId", "id"]
    result = _extract_from_json(combined, jane_keys)
    if result and result.isdigit():
        return result

    return None


def _identify_provider_from_request(url: str) -> Optional[str]:
    """Identify which provider a request URL belongs to."""
    if any(p in url for p in SWEED_API_PATTERNS):
        return "sweed"
    if any(p in url for p in DUTCHIE_API_PATTERNS):
        return "dutchie"
    if any(p in url for p in JANE_API_PATTERNS):
        return "jane"
    return None


def discover_one(url: str, timeout_ms: int = 45000, use_proxy: bool = True) -> Dict[str, Any]:
    """
    Discover provider type and configuration for a dispensary URL.

    Returns dict with:
        - url: Original URL
        - provider: "sweed", "dutchie", "jane", or "unknown"
        - confidence: 0.0-1.0
        - extracted: {store_id, retailer_id, tenant_id, menu_category_id, api_base}
        - signals: List of detection signals
        - network_samples: Sample API URLs captured
    """
    result = {
        "url": url,
        "provider": "unknown",
        "confidence": 0.0,
        "signals": [],
        "extracted": {
            "menu_category_id": _find_menu_category_id(url),
            "store_id": None,
            "retailer_id": None,  # Dutchie
            "jane_store_id": None,  # iHeartJane
            "tenant_id": None,
            "api_base": None,
        },
        "network_samples": [],
        "payload_samples": [],
        "header_samples": [],
        "response_samples": [],
    }

    matched_requests: List[Dict] = []
    matched_responses: List[Dict] = []

    # Get proxy config if available and enabled
    proxy_config = None
    if use_proxy and PROXY_AVAILABLE:
        proxy_config = get_playwright_proxy(force_rotate=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # Create context with optional proxy
        context_options = {
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        if proxy_config:
            context_options["proxy"] = proxy_config
            result["signals"].append("using_proxy")

        context = browser.new_context(**context_options)
        page = context.new_page()

        def on_request(req):
            ru = req.url
            # Capture requests matching any provider pattern
            if any(pattern in ru for pattern in ALL_API_PATTERNS):
                headers = dict(req.headers)
                matched_requests.append({
                    "url": ru,
                    "method": req.method,
                    "post_data": (req.post_data or "")[:8000],
                    "headers": headers,
                    "provider": _identify_provider_from_request(ru),
                })

        def on_response(resp):
            ru = resp.url
            # Capture responses matching any provider pattern
            if any(pattern in ru for pattern in ALL_API_PATTERNS):
                try:
                    body = resp.text()[:16000]
                except:
                    body = None
                matched_responses.append({
                    "url": ru,
                    "status": resp.status,
                    "body": body,
                    "provider": _identify_provider_from_request(ru),
                })

        page.on("request", on_request)
        page.on("response", on_response)

        try:
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            html = page.content()

            # Score all providers
            sweed_score = _looks_like_sweed(url, html)
            dutchie_score = _looks_like_dutchie(url, html)
            jane_score = _looks_like_jane(url, html)

            # Determine provider from HTML heuristics
            scores = [
                ("sweed", sweed_score),
                ("dutchie", dutchie_score),
                ("jane", jane_score),
            ]
            best_provider, best_score = max(scores, key=lambda x: x[1])

            if best_score > 0.2:
                result["provider"] = best_provider
                result["confidence"] = best_score
                result["signals"].append(f"html_heuristics:{best_provider}:{best_score:.2f}")

            # Process captured requests - override provider based on actual API calls
            if matched_requests:
                result["signals"].append(f"api_calls_captured:{len(matched_requests)}")
                result["network_samples"] = [r["url"] for r in matched_requests[:15]]
                result["payload_samples"] = [r["post_data"] for r in matched_requests[:5] if r["post_data"]]
                result["header_samples"] = [r["headers"] for r in matched_requests[:5]]

                # Determine provider from captured requests
                provider_counts = {}
                for req in matched_requests:
                    p = req.get("provider")
                    if p:
                        provider_counts[p] = provider_counts.get(p, 0) + 1

                if provider_counts:
                    detected_provider = max(provider_counts, key=provider_counts.get)
                    result["provider"] = detected_provider
                    result["confidence"] = max(result["confidence"], 0.85)
                    result["signals"].append(f"api_detected:{detected_provider}:{provider_counts[detected_provider]}")

                # Extract API base from first request
                parsed = urlparse(matched_requests[0]["url"])
                result["extracted"]["api_base"] = f"{parsed.scheme}://{parsed.netloc}"

            # Process responses
            if matched_responses:
                result["signals"].append(f"api_responses:{len(matched_responses)}")
                result["response_samples"] = [
                    {"url": r["url"], "status": r["status"], "body": (r["body"] or "")[:4000]}
                    for r in matched_responses[:5]
                ]

            # Extract IDs based on provider type
            all_texts = (
                [r["post_data"] for r in matched_requests] +
                [r.get("body") for r in matched_responses]
            )
            all_urls = [r["url"] for r in matched_requests] + [r["url"] for r in matched_responses]
            all_headers = [r["headers"] for r in matched_requests]

            # Sweed IDs
            store_id = _extract_store_id(all_texts, all_headers)
            tenant_id = _extract_tenant_id(all_texts, all_headers)

            if store_id:
                result["extracted"]["store_id"] = store_id
                result["signals"].append(f"sweed_store_id:{store_id}")
                if result["provider"] == "sweed":
                    result["confidence"] = max(result["confidence"], 0.95)

            if tenant_id:
                result["extracted"]["tenant_id"] = tenant_id
                result["signals"].append(f"tenant_id:{tenant_id}")

            # Dutchie IDs
            retailer_id = _extract_dutchie_retailer_id(all_texts, all_urls)
            if retailer_id:
                result["extracted"]["retailer_id"] = retailer_id
                result["signals"].append(f"dutchie_retailer_id:{retailer_id}")
                if result["provider"] == "dutchie":
                    result["confidence"] = max(result["confidence"], 0.95)

            # Jane IDs
            jane_store_id = _extract_jane_store_id(all_texts, all_urls)
            if jane_store_id:
                result["extracted"]["jane_store_id"] = jane_store_id
                result["signals"].append(f"jane_store_id:{jane_store_id}")
                if result["provider"] == "jane":
                    result["confidence"] = max(result["confidence"], 0.95)

        except Exception as e:
            result["signals"].append(f"error:{type(e).__name__}:{str(e)[:100]}")
        finally:
            browser.close()

    return result


def main():
    parser = argparse.ArgumentParser(description="Discover dispensary URL configuration")
    parser.add_argument("--url", help="Single URL to discover")
    parser.add_argument("--file", help="Text file with URLs (one per line)")
    parser.add_argument("--out", default="discovery_results.jsonl", help="Output file")
    parser.add_argument("--timeout", type=int, default=45000, help="Timeout in ms")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    parser.add_argument("--no-proxy", action="store_true", help="Disable proxy usage")
    args = parser.parse_args()

    if args.url:
        urls = [args.url.strip()]
    elif args.file:
        with open(args.file, "r") as f:
            urls = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
    else:
        raise SystemExit("Provide --url or --file")

    use_proxy = not args.no_proxy

    results = []
    for u in urls:
        print(f"\nDiscovering: {u}")
        res = discover_one(u, timeout_ms=args.timeout, use_proxy=use_proxy)
        results.append(res)

        print(f"  Provider: {res['provider']} ({res['confidence']:.0%})")

        # Show provider-specific IDs
        extracted = res["extracted"]
        if res["provider"] == "sweed":
            print(f"  Sweed Store ID: {extracted.get('store_id')}")
        elif res["provider"] == "dutchie":
            print(f"  Dutchie Retailer ID: {extracted.get('retailer_id')}")
        elif res["provider"] == "jane":
            print(f"  Jane Store ID: {extracted.get('jane_store_id')}")

        if extracted.get("api_base"):
            print(f"  API Base: {extracted['api_base']}")

        if args.verbose:
            print(f"  Signals: {res['signals']}")
            if res["network_samples"]:
                print(f"  Network samples:")
                for ns in res["network_samples"][:5]:
                    print(f"    - {ns[:100]}...")

    with open(args.out, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    print(f"\n{'='*50}")
    print(f"Wrote {len(results)} results to {args.out}")

    # Summary by provider
    provider_counts = {}
    for r in results:
        p = r["provider"]
        provider_counts[p] = provider_counts.get(p, 0) + 1

    print("\nProvider breakdown:")
    for prov, count in sorted(provider_counts.items(), key=lambda x: -x[1]):
        print(f"  {prov}: {count}")


if __name__ == "__main__":
    main()
