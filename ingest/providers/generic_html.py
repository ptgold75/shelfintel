import requests
from bs4 import BeautifulSoup

def fetch_menu_items(menu_url: str):
    r = requests.get(menu_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    candidates = soup.select("h3, h2, .product-name")
    items = []
    for el in candidates[:200]:
        name = el.get_text(strip=True)
        if not name or len(name) < 3:
            continue
        items.append({
            "provider_product_id": None,
            "name": name,
            "category": None,
            "brand": None,
            "price": None,
            "discount_price": None,
            "discount_text": None,
            "raw": {"source": "generic_html"}
        })
    return items
