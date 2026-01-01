# ingest/discover_sweed.py
"""
Dispensary URL discovery - detects provider type and extracts configuration.

Supports:
- Sweed (most common)
- Future: Dutchie, Jane, iHeartJane, etc.

Usage:
    python ingest/discover_sweed.py --url "https://www.gleaf.com/stores/maryland/rockville/shop"
    python ingest/discover_sweed.py --file urls.txt --out results.jsonl
"""

import argparse
import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

# Provider detection hints
SWEED_HINTS = ["sweed", "sweedpos", "stocktype=default", "/shop/", "/menu/"]
DUTCHIE_HINTS = ["dutchie", "dutchie-plus", "embed.dutchie"]
JANE_HINTS = ["iheartjane", "jane.com", "jane-embed"]

# Sweed API endpoints to capture
SWEED_API_PATTERNS = [
    "sweedpos.com/_api/proxy/Products/GetProductCategoryList",
    "sweedpos.com/_api/proxy/Products/GetProductList",
    "sweedpos.com/api/Product",
]


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
            score += 0.25
    
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


def discover_one(url: str, timeout_ms: int = 45000) -> Dict[str, Any]:
    """
    Discover provider type and configuration for a dispensary URL.
    
    Returns dict with:
        - url: Original URL
        - provider: "sweed", "dutchie", "jane", or "unknown"
        - confidence: 0.0-1.0
        - extracted: {store_id, tenant_id, menu_category_id, api_base}
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
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = context.new_page()
        
        def on_request(req):
            ru = req.url
            if any(pattern in ru for pattern in SWEED_API_PATTERNS):
                headers = dict(req.headers)
                matched_requests.append({
                    "url": ru,
                    "method": req.method,
                    "post_data": (req.post_data or "")[:4000],
                    "headers": headers,
                })
        
        def on_response(resp):
            ru = resp.url
            if any(pattern in ru for pattern in SWEED_API_PATTERNS):
                try:
                    body = resp.text()[:8000]
                except:
                    body = None
                matched_responses.append({
                    "url": ru,
                    "status": resp.status,
                    "body": body,
                })
        
        page.on("request", on_request)
        page.on("response", on_response)
        
        try:
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            html = page.content()
            
            # Score providers
            sweed_score = _looks_like_sweed(url, html)
            dutchie_score = _looks_like_dutchie(url, html)
            
            if sweed_score > dutchie_score and sweed_score > 0.2:
                result["provider"] = "sweed"
                result["confidence"] = sweed_score
                result["signals"].append(f"html_heuristics:{sweed_score:.2f}")
            elif dutchie_score > 0.2:
                result["provider"] = "dutchie"
                result["confidence"] = dutchie_score
                result["signals"].append(f"dutchie_heuristics:{dutchie_score:.2f}")
            
            # Process captured requests
            if matched_requests:
                result["signals"].append(f"api_calls_captured:{len(matched_requests)}")
                result["network_samples"] = [r["url"] for r in matched_requests[:10]]
                result["payload_samples"] = [r["post_data"] for r in matched_requests[:3] if r["post_data"]]
                result["header_samples"] = [r["headers"] for r in matched_requests[:3]]
                
                # Extract API base
                parsed = urlparse(matched_requests[0]["url"])
                result["extracted"]["api_base"] = f"{parsed.scheme}://{parsed.netloc}"
                
                # Boost confidence for Sweed
                result["provider"] = "sweed"
                result["confidence"] = max(result["confidence"], 0.8)
            
            # Process responses
            if matched_responses:
                result["signals"].append(f"api_responses:{len(matched_responses)}")
                result["response_samples"] = [
                    {"url": r["url"], "status": r["status"], "body": (r["body"] or "")[:2000]}
                    for r in matched_responses[:3]
                ]
            
            # Extract IDs from all captured data
            all_texts = (
                [r["post_data"] for r in matched_requests] +
                [r.get("body") for r in matched_responses]
            )
            all_headers = [r["headers"] for r in matched_requests]
            
            store_id = _extract_store_id(all_texts, all_headers)
            tenant_id = _extract_tenant_id(all_texts, all_headers)
            
            if store_id:
                result["extracted"]["store_id"] = store_id
                result["signals"].append(f"store_id_found:{store_id}")
                result["confidence"] = max(result["confidence"], 0.95)
            
            if tenant_id:
                result["extracted"]["tenant_id"] = tenant_id
                result["signals"].append(f"tenant_id_found:{tenant_id}")
            
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
    args = parser.parse_args()
    
    if args.url:
        urls = [args.url.strip()]
    elif args.file:
        with open(args.file, "r") as f:
            urls = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
    else:
        raise SystemExit("Provide --url or --file")
    
    results = []
    for u in urls:
        print(f"Discovering: {u}")
        res = discover_one(u, timeout_ms=args.timeout)
        results.append(res)
        print(f"  Provider: {res['provider']} ({res['confidence']:.0%})")
        print(f"  Store ID: {res['extracted'].get('store_id')}")
    
    with open(args.out, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    
    print(f"\nWrote {len(results)} results to {args.out}")


if __name__ == "__main__":
    main()
