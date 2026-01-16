# ingest/providers/curaleaf_provider.py
"""
Curaleaf menu provider - fetches products using saved authentication cookies.

Requires manual cookie setup via scripts/curaleaf_manual_auth.py first.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

# Proxy and rate limiting support
try:
    from ingest.proxy_config import get_playwright_proxy, get_rate_limiter
    PROXY_AVAILABLE = True
except ImportError:
    PROXY_AVAILABLE = False

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

COOKIE_FILE = "data/curaleaf_cookies.json"


def _load_cookies() -> Optional[List[dict]]:
    """Load saved cookies from file."""
    if not os.path.exists(COOKIE_FILE):
        print(f"  Warning: Cookie file not found: {COOKIE_FILE}")
        print(f"  Run 'python scripts/curaleaf_manual_auth.py' first")
        return None

    with open(COOKIE_FILE, 'r') as f:
        cookies = json.load(f)

    # Check expiration
    now = datetime.now().timestamp()
    valid_cookies = []
    expired = 0

    for c in cookies:
        exp = c.get('expires', -1)
        if exp == -1 or exp > now:
            valid_cookies.append(c)
        else:
            expired += 1

    if expired > 0:
        print(f"  Warning: {expired} cookies have expired")

    if not valid_cookies:
        print("  Error: All cookies expired. Re-run manual auth.")
        return None

    return valid_cookies


def _extract_store_url(provider_metadata: Optional[Dict[str, Any]]) -> Optional[str]:
    """Extract Curaleaf store URL from provider_metadata."""
    if not provider_metadata:
        return None

    if isinstance(provider_metadata, str):
        try:
            provider_metadata = json.loads(provider_metadata)
        except (json.JSONDecodeError, TypeError):
            return None

    return provider_metadata.get("curaleaf_store_url") or provider_metadata.get("store_url")


def _parse_product(item: dict) -> Dict[str, Any]:
    """Parse Curaleaf product into standard format."""
    name = item.get('name', '')

    # Brand
    brand = ''
    brand_obj = item.get('brand')
    if brand_obj:
        if isinstance(brand_obj, dict):
            brand = brand_obj.get('name', '')
        else:
            brand = str(brand_obj)

    # Category
    category = item.get('category', '') or item.get('type', '')
    if isinstance(category, dict):
        category = category.get('name', '')

    # Price - try various fields
    price = None
    if item.get('price'):
        price = item['price']
    elif item.get('variants'):
        variants = item['variants']
        if variants and isinstance(variants, list):
            price = variants[0].get('price') or variants[0].get('priceRec')
    elif item.get('prices'):
        prices = item['prices']
        if isinstance(prices, dict):
            price = prices.get('rec') or prices.get('med') or prices.get('default')

    # THC/CBD
    thc = item.get('thcContent') or item.get('thc')
    cbd = item.get('cbdContent') or item.get('cbd')

    return {
        'name': name,
        'brand': brand,
        'category': category,
        'price': float(price) if price else None,
        'provider_product_id': str(item.get('id') or item.get('productId') or ''),
        'raw': {
            'thc': str(thc) if thc else None,
            'cbd': str(cbd) if cbd else None,
        },
    }


async def _scrape_store(context, url: str) -> List[dict]:
    """Scrape a single Curaleaf store."""
    products = {}

    page = await context.new_page()

    async def capture_response(response):
        if response.status == 200:
            try:
                ct = response.headers.get('content-type', '')
                if 'json' in ct:
                    data = await response.json()

                    def extract(obj, depth=0):
                        if depth > 8 or not obj:
                            return
                        if isinstance(obj, dict):
                            # Look for product-like objects
                            if obj.get('name') and (obj.get('price') or obj.get('variants') or obj.get('thcContent')):
                                pid = obj.get('id') or obj.get('productId') or str(len(products))
                                products[pid] = obj
                            for v in obj.values():
                                extract(v, depth + 1)
                        elif isinstance(obj, list):
                            for item in obj:
                                extract(item, depth + 1)

                    extract(data)
            except:
                pass

    page.on("response", capture_response)

    try:
        await page.goto(url, timeout=45000, wait_until="networkidle")
        await asyncio.sleep(2)

        # Check if we passed age gate
        if 'age-gate' in page.url:
            print(f"    Cookies expired - redirected to age gate")
            await page.close()
            return []

        # Scroll to load more products
        for _ in range(15):
            await page.evaluate("window.scrollBy(0, 600)")
            await asyncio.sleep(0.3)

        # Click through category tabs
        categories = ['Flower', 'Pre-Rolls', 'Vaporizers', 'Edibles', 'Concentrates', 'Tinctures']
        for cat in categories:
            try:
                cat_btn = page.locator(f"button:has-text('{cat}'), a:has-text('{cat}')")
                if await cat_btn.count() > 0:
                    await cat_btn.first.click()
                    await asyncio.sleep(1)
                    for _ in range(5):
                        await page.evaluate("window.scrollBy(0, 600)")
                        await asyncio.sleep(0.2)
            except:
                pass

    except Exception as e:
        print(f"    Error: {e}")
    finally:
        await page.close()

    return list(products.values())


async def _scrape_with_playwright(menu_url: str) -> List[dict]:
    """Scrape Curaleaf using Playwright with saved cookies."""
    cookies = _load_cookies()
    if not cookies:
        return []

    # Get proxy config
    proxy_config = None
    if PROXY_AVAILABLE:
        proxy_config = get_playwright_proxy(force_rotate=True)
        if proxy_config:
            print(f"  Using proxy: {proxy_config['server']}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            proxy=proxy_config,
        )

        # Add saved cookies
        await context.add_cookies(cookies)

        products = await _scrape_store(context, menu_url)

        await browser.close()

    return products


def fetch_menu_items(
    *,
    menu_url: str,
    provider_metadata: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch all menu items from a Curaleaf dispensary.

    Args:
        menu_url: Curaleaf store URL
        provider_metadata: Optional dict with curaleaf_store_url override

    Returns:
        List of menu items ready for RawMenuItem insertion
    """
    if not PLAYWRIGHT_AVAILABLE:
        print("  Playwright not available. Install with: pip install playwright")
        return []

    # Get the store URL
    store_url = _extract_store_url(provider_metadata) or menu_url
    if not store_url:
        raise ValueError("menu_url or curaleaf_store_url in provider_metadata is required")

    # Rate limit
    if PROXY_AVAILABLE:
        rate_limiter = get_rate_limiter("curaleaf")
        rate_limiter.wait()

    # Scrape with Playwright
    raw_products = asyncio.run(_scrape_with_playwright(store_url))

    # Parse products
    all_items = []
    for product in raw_products:
        parsed = _parse_product(product)
        if parsed['name']:
            all_items.append(parsed)

    return all_items
