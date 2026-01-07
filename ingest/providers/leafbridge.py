# ingest/providers/leafbridge.py
"""LeafBridge provider - scrapes dispensaries using LeafBridge/Dutchie WordPress integration."""

import requests
import re
from typing import Generator, Optional, Dict, Any, List
from .base import BaseProvider, MenuItem

# Proxy and rate limiting support
try:
    from ingest.proxy_config import get_proxies_dict, get_rate_limiter
    PROXY_AVAILABLE = True
except ImportError:
    PROXY_AVAILABLE = False


class LeafBridgeProvider(BaseProvider):
    """Provider for LeafBridge-powered dispensaries.

    LeafBridge is a WordPress plugin that integrates with Dutchie's backend
    for cannabis menu display and ordering. It's used by chains like:
    - Health for Life (Terrabis)
    - Ethos Cannabis
    - Remedy Maryland
    - Story Cannabis

    The API is accessed via WordPress AJAX endpoints.
    """

    name = "leafbridge"

    # Product categories
    CATEGORIES = [
        "flower", "pre-rolls", "vaporizers", "concentrates",
        "edibles", "tinctures", "topicals", "accessories"
    ]

    def __init__(
        self,
        dispensary_id: str,
        retailer_id: str,
        base_url: str,
        use_proxy: bool = False
    ):
        """Initialize LeafBridge provider.

        Args:
            dispensary_id: Human-readable dispensary identifier
            retailer_id: LeafBridge/Dutchie retailer UUID
            base_url: Base URL of the dispensary website (e.g., https://healthforlifedispensaries.com)
            use_proxy: Whether to use proxy for requests
        """
        super().__init__(dispensary_id)
        self.retailer_id = retailer_id
        self.base_url = base_url.rstrip('/')
        self.use_proxy = use_proxy and PROXY_AVAILABLE
        self.rate_limiter = get_rate_limiter("leafbridge") if PROXY_AVAILABLE else None

    def _get_headers(self) -> dict:
        return {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "origin": self.base_url,
            "referer": f"{self.base_url}/",
        }

    def _fetch_products(
        self,
        category: Optional[str] = None,
        page: int = 1,
        per_page: int = 100,
        menu_type: str = "recreational"
    ) -> Optional[Dict[str, Any]]:
        """Fetch products via LeafBridge AJAX endpoint.

        Args:
            category: Product category filter
            page: Page number (1-indexed)
            per_page: Products per page
            menu_type: "recreational" or "medical"
        """
        if self.rate_limiter:
            self.rate_limiter.wait()

        # LeafBridge uses WordPress AJAX
        ajax_url = f"{self.base_url}/wp-admin/admin-ajax.php"

        # Build form data for AJAX request
        data = {
            "action": "leafbridge_get_products",
            "retailer_id": self.retailer_id,
            "page": page,
            "per_page": per_page,
            "menu_type": "MEDICAL" if menu_type == "medical" else "RECREATIONAL",
        }

        if category:
            data["category"] = category.upper()

        proxies = None
        if self.use_proxy:
            proxies = get_proxies_dict(force_rotate=False)

        try:
            resp = requests.post(
                ajax_url,
                headers=self._get_headers(),
                data=data,
                proxies=proxies,
                timeout=30
            )
            if resp.status_code == 200:
                return resp.json()
            else:
                print(f"LeafBridge AJAX error: {resp.status_code}")
        except Exception as e:
            print(f"LeafBridge request error: {e}")

        return None

    def _fetch_products_via_api(
        self,
        category: Optional[str] = None,
        menu_type: str = "recreational"
    ) -> Optional[List[Dict]]:
        """Alternative: Fetch products via Dutchie's embedded API.

        LeafBridge often proxies to Dutchie's API. This method attempts
        to fetch directly from Dutchie using the retailer_id.
        """
        if self.rate_limiter:
            self.rate_limiter.wait()

        # Dutchie embedded menu API
        api_url = "https://dutchie.com/graphql"

        # GraphQL query for menu products
        query = """
        query GetRetailerProducts($retailerId: ID!, $menuType: MenuType, $category: String) {
            retailer(id: $retailerId) {
                id
                name
                menuProducts(menuType: $menuType, category: $category) {
                    products {
                        id
                        name
                        brand {
                            name
                        }
                        category
                        subcategory
                        strainType
                        THCContent {
                            value
                            unit
                        }
                        CBDContent {
                            value
                            unit
                        }
                        prices
                        specialPrices
                        image
                        description
                        options
                    }
                }
            }
        }
        """

        variables = {
            "retailerId": self.retailer_id,
            "menuType": "MEDICAL" if menu_type == "medical" else "RECREATIONAL",
        }
        if category:
            variables["category"] = category

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        }

        proxies = None
        if self.use_proxy:
            proxies = get_proxies_dict(force_rotate=False)

        try:
            resp = requests.post(
                api_url,
                headers=headers,
                json={"query": query, "variables": variables},
                proxies=proxies,
                timeout=30
            )
            if resp.status_code == 200:
                data = resp.json()
                products = data.get("data", {}).get("retailer", {}).get("menuProducts", {}).get("products", [])
                return products
        except Exception as e:
            print(f"Dutchie API error: {e}")

        return None

    def _scrape_page(self, url: str) -> List[Dict]:
        """Scrape product data directly from a dispensary page.

        This fallback method parses the HTML for embedded product JSON.
        """
        if self.rate_limiter:
            self.rate_limiter.wait()

        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        }

        proxies = None
        if self.use_proxy:
            proxies = get_proxies_dict(force_rotate=False)

        try:
            resp = requests.get(url, headers=headers, proxies=proxies, timeout=30)
            if resp.status_code == 200:
                # Look for embedded JSON in script tags or data attributes
                # LeafBridge often embeds product data in the page
                products = []

                # Pattern 1: Look for leafbridge product data
                pattern = r'leafbridge_products\s*=\s*(\[.*?\]);'
                match = re.search(pattern, resp.text, re.DOTALL)
                if match:
                    import json
                    try:
                        products = json.loads(match.group(1))
                    except:
                        pass

                return products
        except Exception as e:
            print(f"Page scrape error: {e}")

        return []

    def scrape(self, menu_type: str = "recreational") -> Generator[MenuItem, None, None]:
        """Scrape all products from this dispensary.

        Args:
            menu_type: "recreational" or "medical"
        """
        seen_ids = set()

        # Try AJAX endpoint first
        for category in self.CATEGORIES:
            page = 1
            while True:
                result = self._fetch_products(
                    category=category,
                    page=page,
                    per_page=100,
                    menu_type=menu_type
                )

                if not result:
                    break

                products = result.get("products", result.get("data", []))

                if not products:
                    break

                new_products = 0
                for product in products:
                    product_id = str(product.get("id", product.get("product_id", "")))
                    if product_id and product_id not in seen_ids:
                        seen_ids.add(product_id)
                        new_products += 1
                        yield from self._parse_product(product, category, menu_type)

                if new_products == 0 or len(products) < 100:
                    break

                page += 1

        # If no products found via AJAX, try Dutchie API directly
        if not seen_ids:
            print(f"AJAX returned no products, trying Dutchie API for {self.dispensary_id}")
            for category in self.CATEGORIES:
                products = self._fetch_products_via_api(category=category, menu_type=menu_type)
                if products:
                    for product in products:
                        product_id = str(product.get("id", ""))
                        if product_id and product_id not in seen_ids:
                            seen_ids.add(product_id)
                            yield from self._parse_dutchie_product(product, category, menu_type)

    def scrape_both_menus(self) -> Generator[MenuItem, None, None]:
        """Scrape both recreational and medical menus."""
        yield from self.scrape(menu_type="recreational")
        yield from self.scrape(menu_type="medical")

    def _parse_product(self, product: dict, category: str, menu_type: str) -> Generator[MenuItem, None, None]:
        """Parse a LeafBridge product into MenuItem(s).

        Args:
            product: Raw product data
            category: Product category
            menu_type: "recreational" or "medical"
        """
        product_id = product.get("id", product.get("product_id", ""))
        name = product.get("name", product.get("product_name", "Unknown"))

        # Brand info
        brand = product.get("brand", product.get("brand_name", ""))
        if isinstance(brand, dict):
            brand = brand.get("name", "")

        # Category
        cat = product.get("category", category)
        subcategory = product.get("subcategory", product.get("sub_category"))

        # Strain type
        strain_type = product.get("strain_type", product.get("strainType"))

        # THC/CBD
        thc = product.get("thc", product.get("THCContent"))
        cbd = product.get("cbd", product.get("CBDContent"))
        if isinstance(thc, dict):
            thc = thc.get("value")
        if isinstance(cbd, dict):
            cbd = cbd.get("value")

        # Price info
        price = product.get("price", product.get("prices"))
        if isinstance(price, list) and price:
            price = price[0]

        special_price = product.get("special_price", product.get("specialPrices"))
        if isinstance(special_price, list) and special_price:
            special_price = special_price[0]

        # Image
        image = product.get("image", product.get("image_url", product.get("photo_url")))

        # Description
        description = product.get("description", "")

        # Variants/options
        options = product.get("options", product.get("variants", []))

        raw_json = {
            "productId": product_id,
            "name": name,
            "brand": brand,
            "category": cat,
            "subcategory": subcategory,
            "strainType": strain_type,
            "thc": thc,
            "cbd": cbd,
            "image": image,
            "description": description,
            "menuType": menu_type,
        }

        if not options:
            yield MenuItem(
                provider_product_id=str(product_id),
                raw_name=name,
                raw_brand=brand,
                raw_category=cat,
                raw_price=float(price) if price else None,
                raw_discount_price=float(special_price) if special_price and special_price != price else None,
                raw_description=description,
                raw_json=raw_json,
                menu_type=menu_type
            )
        else:
            # Create MenuItem for each variant
            for i, option in enumerate(options):
                if isinstance(option, dict):
                    option_name = option.get("name", option.get("weight", ""))
                    option_price = option.get("price", price)
                    option_special = option.get("special_price", special_price)
                else:
                    option_name = str(option)
                    option_price = price
                    option_special = special_price

                full_name = f"{name} - {option_name}" if option_name else name

                variant_json = raw_json.copy()
                variant_json["option"] = option_name
                variant_json["optionIndex"] = i

                yield MenuItem(
                    provider_product_id=f"{product_id}_{i}",
                    raw_name=full_name,
                    raw_brand=brand,
                    raw_category=cat,
                    raw_price=float(option_price) if option_price else None,
                    raw_discount_price=float(option_special) if option_special and option_special != option_price else None,
                    raw_description=description,
                    raw_json=variant_json,
                    menu_type=menu_type
                )

    def _parse_dutchie_product(self, product: dict, category: str, menu_type: str) -> Generator[MenuItem, None, None]:
        """Parse a Dutchie API product into MenuItem(s)."""
        # Dutchie products have a slightly different structure
        product_id = product.get("id", "")
        name = product.get("name", "Unknown")

        brand = product.get("brand", {})
        brand_name = brand.get("name", "") if isinstance(brand, dict) else brand

        cat = product.get("category", category)
        subcategory = product.get("subcategory")
        strain_type = product.get("strainType")

        thc_content = product.get("THCContent", {})
        thc = thc_content.get("value") if isinstance(thc_content, dict) else thc_content

        cbd_content = product.get("CBDContent", {})
        cbd = cbd_content.get("value") if isinstance(cbd_content, dict) else cbd_content

        prices = product.get("prices", [])
        special_prices = product.get("specialPrices", [])
        options = product.get("options", [])

        image = product.get("image")
        description = product.get("description", "")

        raw_json = {
            "productId": product_id,
            "name": name,
            "brand": brand_name,
            "category": cat,
            "subcategory": subcategory,
            "strainType": strain_type,
            "thc": thc,
            "cbd": cbd,
            "image": image,
            "description": description,
            "menuType": menu_type,
        }

        if not options or not prices:
            price = prices[0] if prices else None
            special = special_prices[0] if special_prices else None

            yield MenuItem(
                provider_product_id=str(product_id),
                raw_name=name,
                raw_brand=brand_name,
                raw_category=cat,
                raw_price=float(price) if price else None,
                raw_discount_price=float(special) if special and special != price else None,
                raw_description=description,
                raw_json=raw_json,
                menu_type=menu_type
            )
        else:
            for i, option in enumerate(options):
                price = prices[i] if i < len(prices) else None
                special = special_prices[i] if i < len(special_prices) else None

                full_name = f"{name} - {option}" if option else name

                variant_json = raw_json.copy()
                variant_json["option"] = option
                variant_json["optionIndex"] = i

                yield MenuItem(
                    provider_product_id=f"{product_id}_{i}",
                    raw_name=full_name,
                    raw_brand=brand_name,
                    raw_category=cat,
                    raw_price=float(price) if price else None,
                    raw_discount_price=float(special) if special and special != price else None,
                    raw_description=description,
                    raw_json=variant_json,
                    menu_type=menu_type
                )
