"""
Smoke Shop / CBD Store Scraper

Handles common e-commerce platforms used by smoke/CBD/hemp shops:
- Shopify stores
- WooCommerce (WordPress)
- Square Online
- Generic product pages

Product categories tracked:
- CBD (oils, gummies, topicals)
- Delta-8 THC
- Delta-9 THC (hemp-derived)
- THCA flower/products
- HHC
- Kratom
- Mushroom supplements
- Vapes/Hardware
"""

import requests
from bs4 import BeautifulSoup
import re
import json
from typing import List, Dict, Optional

# Common smoke shop product categories
SMOKE_SHOP_CATEGORIES = {
    'cbd_oil': ['cbd oil', 'cbd tincture', 'full spectrum', 'broad spectrum'],
    'cbd_edible': ['cbd gummies', 'cbd edibles', 'cbd candy', 'cbd chocolate'],
    'cbd_topical': ['cbd cream', 'cbd lotion', 'cbd balm', 'cbd salve', 'cbd roll-on'],
    'delta8': ['delta 8', 'delta-8', 'd8', 'delta eight'],
    'delta9': ['delta 9', 'delta-9', 'd9', 'hemp derived thc'],
    'thca': ['thca', 'thc-a', 'thca flower', 'thca diamond'],
    'hhc': ['hhc', 'hexahydrocannabinol'],
    'kratom': ['kratom', 'mitragyna'],
    'mushroom': ['mushroom', 'shroom', 'amanita', 'psilocybin'],
    'vape': ['vape', 'cartridge', 'cart', 'disposable', 'pod'],
    'flower': ['flower', 'bud', 'pre-roll', 'hemp flower'],
    'accessory': ['grinder', 'pipe', 'bong', 'papers', 'rolling'],
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def detect_category(product_name: str) -> Optional[str]:
    """Detect product category from name"""
    name_lower = product_name.lower()
    for category, keywords in SMOKE_SHOP_CATEGORIES.items():
        for keyword in keywords:
            if keyword in name_lower:
                return category
    return None


def extract_price(text: str) -> Optional[float]:
    """Extract price from text"""
    if not text:
        return None
    match = re.search(r'\$?(\d+\.?\d*)', text.replace(',', ''))
    if match:
        try:
            return float(match.group(1))
        except:
            pass
    return None


def fetch_shopify_products(base_url: str) -> List[Dict]:
    """Fetch products from Shopify store via products.json endpoint"""
    items = []

    # Try products.json endpoint
    products_url = base_url.rstrip('/') + '/products.json'
    try:
        r = requests.get(products_url, headers=HEADERS, timeout=30)
        if r.status_code == 200:
            data = r.json()
            for product in data.get('products', []):
                name = product.get('title', '')
                brand = product.get('vendor', '')
                category = detect_category(name) or product.get('product_type', '')

                # Get first variant price
                variants = product.get('variants', [])
                price = None
                if variants:
                    price = extract_price(variants[0].get('price', ''))

                items.append({
                    "provider_product_id": str(product.get('id', '')),
                    "name": name,
                    "category": category,
                    "brand": brand,
                    "price": price,
                    "discount_price": None,
                    "discount_text": None,
                    "raw": {
                        "source": "shopify",
                        "product_type": product.get('product_type'),
                        "tags": product.get('tags', []),
                        "variants_count": len(variants)
                    }
                })
    except Exception as e:
        print(f"Shopify JSON failed: {e}")

    return items


def fetch_woocommerce_products(base_url: str) -> List[Dict]:
    """Fetch products from WooCommerce store"""
    items = []

    # Try wp-json endpoint
    api_url = base_url.rstrip('/') + '/wp-json/wc/store/products'
    try:
        r = requests.get(api_url, headers=HEADERS, timeout=30)
        if r.status_code == 200:
            products = r.json()
            for product in products:
                name = product.get('name', '')
                price_html = product.get('price_html', '')
                price = extract_price(product.get('prices', {}).get('price', ''))

                items.append({
                    "provider_product_id": str(product.get('id', '')),
                    "name": name,
                    "category": detect_category(name),
                    "brand": None,
                    "price": price / 100 if price and price > 100 else price,  # WooCommerce often uses cents
                    "discount_price": None,
                    "discount_text": None,
                    "raw": {"source": "woocommerce"}
                })
    except Exception as e:
        print(f"WooCommerce API failed: {e}")

    return items


def fetch_generic_html(menu_url: str) -> List[Dict]:
    """Generic HTML scraper for product pages"""
    items = []

    try:
        r = requests.get(menu_url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')

        # Common product selectors
        product_selectors = [
            '.product',
            '.product-item',
            '.product-card',
            '[data-product]',
            '.woocommerce-loop-product__title',
            '.shopify-product',
            'article.product',
        ]

        products = []
        for selector in product_selectors:
            products = soup.select(selector)
            if products:
                break

        # If no products found, try finding by common patterns
        if not products:
            # Look for h2/h3 with price nearby
            for heading in soup.find_all(['h2', 'h3', 'h4']):
                name = heading.get_text(strip=True)
                if len(name) < 3 or len(name) > 200:
                    continue

                # Look for price in parent or siblings
                parent = heading.parent
                price_text = parent.get_text() if parent else ''
                price = extract_price(price_text)

                if detect_category(name):  # Only add if it matches a smoke shop category
                    items.append({
                        "provider_product_id": None,
                        "name": name,
                        "category": detect_category(name),
                        "brand": None,
                        "price": price,
                        "discount_price": None,
                        "discount_text": None,
                        "raw": {"source": "generic_html"}
                    })
        else:
            for product in products[:200]:
                # Extract name
                name_el = product.select_one('.product-title, .product-name, h2, h3, a')
                name = name_el.get_text(strip=True) if name_el else ''

                if not name or len(name) < 3:
                    continue

                # Extract price
                price_el = product.select_one('.price, .product-price, [data-price]')
                price = extract_price(price_el.get_text() if price_el else '')

                items.append({
                    "provider_product_id": None,
                    "name": name,
                    "category": detect_category(name),
                    "brand": None,
                    "price": price,
                    "discount_price": None,
                    "discount_text": None,
                    "raw": {"source": "generic_html"}
                })

    except Exception as e:
        print(f"Generic HTML failed: {e}")

    return items


def fetch_menu_items(menu_url: str) -> List[Dict]:
    """
    Main entry point - detects platform and fetches products accordingly
    """
    if not menu_url:
        return []

    menu_url = menu_url.strip()

    # Try Shopify first (most common for CBD stores)
    items = fetch_shopify_products(menu_url)
    if items:
        return items

    # Try WooCommerce
    items = fetch_woocommerce_products(menu_url)
    if items:
        return items

    # Fall back to generic HTML
    return fetch_generic_html(menu_url)


# For testing
if __name__ == "__main__":
    test_urls = [
        "https://shopcbdkratom.com/",
        "https://cbdamericanshaman.com/",
    ]

    for url in test_urls:
        print(f"\n{'='*60}")
        print(f"Testing: {url}")
        items = fetch_menu_items(url)
        print(f"Found {len(items)} products")
        for item in items[:5]:
            print(f"  - {item['name'][:50]} | {item['category']} | ${item['price']}")
