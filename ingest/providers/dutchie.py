# ingest/providers/dutchie.py
"""Dutchie provider - scrapes dispensaries using Dutchie's GraphQL API via Playwright."""

import asyncio
import json
import urllib.parse
import requests
from typing import Generator, Optional, Dict, Any, List
from .base import BaseProvider, MenuItem

# Proxy and rate limiting support
try:
    from ingest.proxy_config import get_proxies_dict, get_rate_limiter
    PROXY_AVAILABLE = True
except ImportError:
    PROXY_AVAILABLE = False

# Playwright for Cloudflare bypass
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class DutchieProvider(BaseProvider):
    """Provider for Dutchie-powered dispensaries.

    Dutchie uses a GraphQL API with persisted queries for menu data.
    Endpoint: dutchie.com/api-4/graphql
    """

    name = "dutchie"

    # API endpoints
    API_BASE = "https://dutchie.com/api-4/graphql"

    # Persisted query hash for FilteredProducts
    FILTERED_PRODUCTS_HASH = "c3dda0418c4b423ed26a38d011b50a2b8c9a1f8bde74b45f93420d60d2c50ae1"

    # Product categories
    CATEGORIES = ["Flower", "Vaporizers", "Edible", "Concentrate", "Pre-Rolls", "Tincture", "Topicals", "Accessories"]

    def __init__(
        self,
        dispensary_id: str,
        retailer_id: str,
        api_base: Optional[str] = None,
        use_proxy: bool = True
    ):
        super().__init__(dispensary_id)
        self.retailer_id = retailer_id
        self.api_base = api_base or self.API_BASE
        self.use_proxy = use_proxy and PROXY_AVAILABLE
        self.rate_limiter = get_rate_limiter("dutchie") if PROXY_AVAILABLE else None

    def _get_headers(self) -> dict:
        return {
            "accept": "application/json",
            "content-type": "application/json",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "origin": "https://dutchie.com",
            "referer": "https://dutchie.com/",
        }

    def _fetch_products(
        self,
        category: Optional[str] = None,
        page: int = 0,
        per_page: int = 100,
        pricing_type: str = "rec"
    ) -> Optional[Dict[str, Any]]:
        """Fetch products using persisted query."""
        if self.rate_limiter:
            self.rate_limiter.wait()

        # Build variables
        variables = {
            "includeEnterpriseSpecials": False,
            "productsFilter": {
                "dispensaryId": self.retailer_id,
                "pricingType": pricing_type,
                "strainTypes": [],
                "subcategories": [],
                "Status": "Active",
                "types": [category] if category else [],
                "useCache": True,
                "isDefaultSort": True,
                "sortBy": "popularSortIdx",
                "sortDirection": 1,
                "bypassOnlineThresholds": False,
                "isKioskMenu": False,
                "removeProductsBelowOptionThresholds": True,
            },
            "page": page,
            "perPage": per_page,
        }

        # Build extensions
        extensions = {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": self.FILTERED_PRODUCTS_HASH,
            }
        }

        # Build URL with query params
        params = {
            "operationName": "FilteredProducts",
            "variables": json.dumps(variables, separators=(",", ":")),
            "extensions": json.dumps(extensions, separators=(",", ":")),
        }

        url = f"{self.api_base}?{urllib.parse.urlencode(params)}"

        proxies = None
        if self.use_proxy:
            proxies = get_proxies_dict(force_rotate=False)

        try:
            resp = requests.get(
                url,
                headers=self._get_headers(),
                proxies=proxies,
                timeout=30
            )
            if resp.status_code == 200:
                return resp.json()
            else:
                print(f"Dutchie API error: {resp.status_code} - {resp.text[:500]}")
        except Exception as e:
            print(f"Dutchie request error: {e}")
        return None

    def scrape(self, pricing_type: str = "rec") -> Generator[MenuItem, None, None]:
        """Scrape all products from this dispensary.

        Args:
            pricing_type: "rec" for recreational, "med" for medical
        """
        seen_ids = set()

        # Scrape each category
        for category in self.CATEGORIES:
            page = 0
            while True:
                result = self._fetch_products(
                    category=category,
                    page=page,
                    per_page=100,
                    pricing_type=pricing_type
                )

                if not result:
                    break

                products = result.get("data", {}).get("filteredProducts", {}).get("products", [])

                if not products:
                    break

                new_products = 0
                for product in products:
                    product_id = product.get("_id", product.get("id", ""))
                    if product_id and product_id not in seen_ids:
                        seen_ids.add(product_id)
                        new_products += 1
                        yield from self._parse_product(product, category, pricing_type)

                if new_products == 0 or len(products) < 100:
                    break

                page += 1

    def _parse_product(self, product: dict, category: str, pricing_type: str) -> Generator[MenuItem, None, None]:
        """Parse a Dutchie product into MenuItem(s).

        Args:
            product: Raw product data from API
            category: Product category
            pricing_type: "rec" for recreational, "med" for medical
        """
        product_id = product.get("_id", product.get("id", ""))
        name = product.get("Name") or product.get("cName") or "Unknown"

        # Brand info
        brand_info = product.get("brand", {})
        brand_name = brand_info.get("name") if isinstance(brand_info, dict) else None

        # Category and subcategory
        cat = product.get("type") or category
        subcategory = product.get("subcategory")

        # Strain type
        strain_type = product.get("strainType")

        # THC/CBD
        thc = product.get("THCContent") or product.get("THC")
        cbd = product.get("CBDContent") or product.get("CBD")

        # Images
        image = product.get("Image")
        images = product.get("images", [])

        # Map pricing_type to menu_type
        menu_type = "medical" if pricing_type == "med" else "recreational"

        # Get prices based on pricing type
        if pricing_type == "rec":
            prices = product.get("recPrices", product.get("Prices", []))
            special_prices = product.get("recSpecialPrices", [])
        else:
            prices = product.get("medicalPrices", product.get("Prices", []))
            special_prices = product.get("medicalSpecialPrices", [])

        # Options (weight variants)
        options = product.get("Options", [])

        if not options or not prices:
            # Product without options - use first price if available
            price = prices[0] if prices else None
            special = special_prices[0] if special_prices else None

            raw_json = {
                "productId": product_id,
                "name": name,
                "brand": brand_name,
                "brandId": product.get("brandId"),
                "category": cat,
                "subcategory": subcategory,
                "strainType": strain_type,
                "thc": thc,
                "cbd": cbd,
                "image": image,
                "images": images,
                "weight": product.get("weight"),
                "menuType": menu_type,
            }

            yield MenuItem(
                provider_product_id=str(product_id),
                raw_name=name,
                raw_brand=brand_name,
                raw_category=cat,
                raw_price=float(price) if price else None,
                raw_discount_price=float(special) if special and special != price else None,
                raw_json=raw_json,
                menu_type=menu_type
            )
        else:
            # Create MenuItem for each option (weight variant)
            for i, option in enumerate(options):
                price = prices[i] if i < len(prices) else None
                special = special_prices[i] if i < len(special_prices) else None

                # Full name with weight option
                full_name = f"{name} - {option}" if option else name

                raw_json = {
                    "productId": product_id,
                    "optionIndex": i,
                    "name": name,
                    "option": option,
                    "brand": brand_name,
                    "brandId": product.get("brandId"),
                    "category": cat,
                    "subcategory": subcategory,
                    "strainType": strain_type,
                    "thc": thc,
                    "cbd": cbd,
                    "image": image,
                    "images": images,
                    "menuType": menu_type,
                }

                yield MenuItem(
                    provider_product_id=f"{product_id}_{i}",
                    raw_name=full_name,
                    raw_brand=brand_name,
                    raw_category=cat,
                    raw_price=float(price) if price else None,
                    raw_discount_price=float(special) if special and special != price else None,
                    raw_json=raw_json,
                    menu_type=menu_type
                )

    def scrape_both_menus(self) -> Generator[MenuItem, None, None]:
        """Scrape both recreational and medical menus.

        This is useful for comparing prices/availability between menu types.
        """
        # Scrape recreational menu
        yield from self.scrape(pricing_type="rec")

        # Scrape medical menu
        yield from self.scrape(pricing_type="med")

    def scrape_with_playwright(self, pricing_type: str = "rec") -> Generator[MenuItem, None, None]:
        """Scrape using Playwright to bypass Cloudflare."""
        if not PLAYWRIGHT_AVAILABLE:
            print("Playwright not available. Install with: pip install playwright")
            return

        # Run async scrape
        products = asyncio.run(self._playwright_scrape(pricing_type))

        seen_ids = set()
        for product in products:
            product_id = product.get("_id", product.get("id", ""))
            if product_id and product_id not in seen_ids:
                seen_ids.add(product_id)
                category = product.get("type", "Unknown")
                yield from self._parse_product(product, category, pricing_type)

    async def _playwright_scrape(self, pricing_type: str) -> List[dict]:
        """Use Playwright to scrape Dutchie menu."""
        all_products = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )

            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )

            page = await context.new_page()
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

            async def handle_response(response):
                if response.status == 200 and "FilteredProducts" in response.url:
                    try:
                        body = await response.json()
                        products = body.get("data", {}).get("filteredProducts", {}).get("products", [])
                        all_products.extend(products)
                    except:
                        pass

            page.on("response", handle_response)

            try:
                # Navigate to dispensary page
                slug = self._get_slug()
                url = f"https://dutchie.com/dispensary/{slug}"
                await page.goto(url, timeout=60000)
                await asyncio.sleep(5)

                # Close any age gate modal
                try:
                    age_button = await page.query_selector('button:has-text("Yes")')
                    if age_button:
                        await age_button.click()
                        await asyncio.sleep(2)
                except:
                    pass

                # Wait for products to load
                await asyncio.sleep(5)

                print(f"Captured {len(all_products)} products via Playwright")

            except Exception as e:
                print(f"Playwright scrape error: {e}")

            await browser.close()

        return all_products

    def _get_slug(self) -> str:
        """Get Dutchie slug from dispensary_id."""
        # The dispensary_id might be the slug or we derive it
        return self.dispensary_id.replace(" ", "-").lower()
