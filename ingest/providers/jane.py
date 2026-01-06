# ingest/providers/jane.py
"""iHeartJane provider - scrapes dispensaries using Jane's REST API and Algolia search."""

import re
import requests
from typing import Generator, Optional, List, Dict, Any
from .base import BaseProvider, MenuItem

# Proxy and rate limiting support
try:
    from ingest.proxy_config import get_proxies_dict, get_rate_limiter
    PROXY_AVAILABLE = True
except ImportError:
    PROXY_AVAILABLE = False


class JaneProvider(BaseProvider):
    """Provider for iHeartJane-powered dispensaries.

    iHeartJane uses multiple API patterns:
    1. Direct API: api.iheartjane.com/v1/stores/{store_id}/
    2. Algolia search: search.iheartjane.com for product queries
    3. Roots API (via retailer proxy): /api/jane/roots/store_operations_api/v1/stores/{store_id}/
    """

    name = "jane"

    # API endpoints
    BASE_URL = "https://api.iheartjane.com/v1"
    ALGOLIA_URL = "https://search.iheartjane.com/1/indexes"
    ALGOLIA_INDEX = "menu-products-production"

    # Algolia credentials (public, embedded in retailer JS bundles)
    ALGOLIA_APP_ID = "VFM4X0N23A"
    ALGOLIA_API_KEY = "11f0fcaee5ae875f14a915b07cb6ef27"

    def __init__(self, dispensary_id: str, store_id: str, use_proxy: bool = True, api_base: str = None):
        super().__init__(dispensary_id)
        self.store_id = store_id
        self.api_base = api_base or self.BASE_URL
        self.use_proxy = use_proxy and PROXY_AVAILABLE
        self.rate_limiter = get_rate_limiter("jane") if PROXY_AVAILABLE else None

    @staticmethod
    def extract_store_id_from_url(url: str) -> Optional[str]:
        """Extract Jane store ID from a dispensary URL.

        RISE URLs contain store ID: /dispensaries/maryland/bethesda/5476/
        """
        # Pattern: /dispensaries/{state}/{city}/{store_id}/
        match = re.search(r'/dispensaries/[^/]+/[^/]+/(\d+)/', url)
        if match:
            return match.group(1)

        # Alternative pattern: /stores/{store_id}
        match = re.search(r'/stores/(\d+)', url)
        if match:
            return match.group(1)

        return None

    def _get_headers(self) -> dict:
        return {
            "accept": "application/json",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "origin": "https://www.iheartjane.com",
            "referer": "https://www.iheartjane.com/",
        }

    def _get(self, endpoint: str, params: Optional[dict] = None) -> Optional[dict]:
        """Make a GET request to the Jane API."""
        # Apply rate limiting
        if self.rate_limiter:
            self.rate_limiter.wait()

        url = f"{self.BASE_URL}{endpoint}"

        # Get proxy if enabled
        proxies = None
        if self.use_proxy:
            proxies = get_proxies_dict(force_rotate=False)

        try:
            resp = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                proxies=proxies,
                timeout=30
            )
            if resp.status_code == 200:
                return resp.json()
            else:
                print(f"Jane API error: {resp.status_code} - {resp.text[:500]}")
        except Exception as e:
            print(f"Jane request error: {e}")
        return None

    def _algolia_search(
        self,
        query: str = "",
        page: int = 0,
        hits_per_page: int = 100,
        filters: Optional[str] = None,
        menu_type: str = "recreational"
    ) -> Optional[Dict[str, Any]]:
        """Search products using Algolia.

        Args:
            query: Search query (empty string for all products)
            page: Page number (0-indexed)
            hits_per_page: Number of results per page
            filters: Algolia filter string (e.g., "store_id:5476")
            menu_type: "recreational" or "medical" - filters by menu type
        """
        if self.rate_limiter:
            self.rate_limiter.wait()

        url = f"{self.ALGOLIA_URL}/{self.ALGOLIA_INDEX}/query"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Algolia-Application-Id": self.ALGOLIA_APP_ID,
            "X-Algolia-API-Key": self.ALGOLIA_API_KEY,
            "X-Algolia-Agent": "Algolia for JavaScript (4.20.0); Browser",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": "https://risecannabis.com",
            "Referer": "https://risecannabis.com/",
        }

        # Build filter string (Algolia uses = not :)
        filter_parts = [f"store_id = {self.store_id}"]

        # Skip menu type filter - just get all products for the store
        # Different stores have different field configurations

        if filters:
            filter_parts.append(filters)

        payload = {
            "query": query,
            "page": page,
            "hitsPerPage": hits_per_page,
            "filters": " AND ".join(filter_parts),
            "facets": ["*"],
        }

        proxies = None
        if self.use_proxy:
            proxies = get_proxies_dict(force_rotate=False)

        try:
            resp = requests.post(
                url,
                headers=headers,
                json=payload,
                proxies=proxies,
                timeout=30
            )
            if resp.status_code == 200:
                return resp.json()
            else:
                print(f"Algolia search error: {resp.status_code} - {resp.text[:500]}")
        except Exception as e:
            print(f"Algolia request error: {e}")
        return None

    def get_store_info(self) -> Optional[dict]:
        """Fetch store information."""
        return self._get(f"/stores/{self.store_id}")

    def get_products(
        self,
        page: int = 1,
        per_page: int = 100,
        category: Optional[str] = None,
        sort: str = "popular"
    ) -> Optional[dict]:
        """Fetch products for this store.

        Args:
            page: Page number (1-indexed)
            per_page: Number of products per page
            category: Filter by category (e.g., "flower", "vape", "edible")
            sort: Sort order ("popular", "price_asc", "price_desc", "name")
        """
        params = {
            "page": page,
            "per_page": per_page,
            "sort": sort,
        }
        if category:
            params["category"] = category

        return self._get(f"/stores/{self.store_id}/products", params=params)

    def get_menu_products(
        self,
        page: int = 1,
        per_page: int = 100
    ) -> Optional[dict]:
        """Fetch menu products for this store (alternative endpoint)."""
        params = {
            "page": page,
            "per_page": per_page,
        }
        return self._get(f"/stores/{self.store_id}/menu_products", params=params)

    def get_categories(self) -> List[str]:
        """Fetch available categories for this store."""
        # Try to get categories from store info
        store_info = self.get_store_info()
        if store_info:
            categories = store_info.get("categories", [])
            if categories:
                return [c.get("name") or c.get("key") for c in categories if c]

        # Fallback to common cannabis categories
        return [
            "flower",
            "vape",
            "edible",
            "concentrate",
            "pre-roll",
            "tincture",
            "topical",
            "accessory",
        ]

    def scrape(self, menu_type: str = "recreational") -> Generator[MenuItem, None, None]:
        """Scrape all products from this dispensary.

        Args:
            menu_type: "recreational" or "medical"
        """
        # Try REST API first
        products_found = False
        for item in self._scrape_rest_api(menu_type=menu_type):
            products_found = True
            yield item

        # If REST API didn't return products, try Algolia
        if not products_found:
            print(f"REST API returned no products, trying Algolia for store {self.store_id}")
            yield from self._scrape_algolia(menu_type=menu_type)

    def scrape_both_menus(self) -> Generator[MenuItem, None, None]:
        """Scrape both recreational and medical menus."""
        yield from self.scrape(menu_type="recreational")
        yield from self.scrape(menu_type="medical")

    def _scrape_rest_api(self, menu_type: str = "recreational") -> Generator[MenuItem, None, None]:
        """Scrape products using REST API endpoints.

        Args:
            menu_type: "recreational" or "medical"
        """
        page = 1
        seen_ids = set()

        while True:
            # Try the products endpoint first
            result = self.get_products(page=page, per_page=100)

            if not result:
                # Try alternative menu_products endpoint
                result = self.get_menu_products(page=page, per_page=100)

            if not result:
                break

            products = result.get("products", result.get("data", []))

            if not products:
                break

            new_products = 0
            for product in products:
                product_id = str(product.get("id", ""))
                if product_id and product_id not in seen_ids:
                    seen_ids.add(product_id)
                    new_products += 1
                    yield from self._parse_product(product, menu_type=menu_type)

            # Check if we've reached the end
            if new_products == 0:
                break

            # Check pagination info
            meta = result.get("meta", {})
            total_pages = meta.get("total_pages", 0)
            if total_pages and page >= total_pages:
                break

            page += 1

    def _scrape_algolia(self, menu_type: str = "recreational") -> Generator[MenuItem, None, None]:
        """Scrape products using Algolia search.

        Args:
            menu_type: "recreational" or "medical"
        """
        page = 0
        seen_ids = set()

        while True:
            result = self._algolia_search(query="", page=page, hits_per_page=100, menu_type=menu_type)

            if not result:
                break

            hits = result.get("hits", [])

            if not hits:
                break

            new_products = 0
            for hit in hits:
                product_id = str(hit.get("objectID", hit.get("id", "")))
                if product_id and product_id not in seen_ids:
                    seen_ids.add(product_id)
                    new_products += 1
                    yield from self._parse_algolia_hit(hit, menu_type=menu_type)

            # Check if we've reached the end
            if new_products == 0:
                break

            # Check pagination info
            nb_pages = result.get("nbPages", 0)
            if nb_pages and page >= nb_pages - 1:
                break

            page += 1

    def _parse_algolia_hit(self, hit: dict, menu_type: str = "recreational") -> Generator[MenuItem, None, None]:
        """Parse an Algolia hit into MenuItem(s).

        Args:
            hit: Algolia search result
            menu_type: "recreational" or "medical"
        """
        product_id = hit.get("objectID", hit.get("id", ""))
        name = hit.get("name", hit.get("product_name", "Unknown"))
        brand_name = hit.get("brand", hit.get("brand_name", ""))
        category = hit.get("kind", hit.get("category", hit.get("product_type", "")))
        description = hit.get("description", "")

        # Price information
        price = hit.get("price", hit.get("min_price"))
        special_price = hit.get("special_price", hit.get("discounted_price"))

        # Potency info
        thc = hit.get("percent_thc", hit.get("thc"))
        cbd = hit.get("percent_cbd", hit.get("cbd"))

        # Weight/size
        weight = hit.get("amount", hit.get("weight", hit.get("size")))

        raw_json = {
            "productId": product_id,
            "name": name,
            "brand": brand_name,
            "category": category,
            "subcategory": hit.get("subcategory", hit.get("root_subtype")),
            "description": description,
            "thc": thc,
            "cbd": cbd,
            "strain": hit.get("strain", hit.get("strain_name")),
            "strainType": hit.get("strain_type", hit.get("lineage", hit.get("category_type"))),
            "weight": weight,
            "weightUnit": hit.get("amount_unit", hit.get("weight_unit")),
            "image": hit.get("image_url", hit.get("photo_url")),
            "inStock": hit.get("in_stock", True),
            "storeId": hit.get("store_id"),
            "menuType": menu_type,
        }

        yield MenuItem(
            provider_product_id=str(product_id),
            raw_name=name,
            raw_brand=brand_name,
            raw_category=category,
            raw_price=float(price) if price else None,
            raw_discount_price=float(special_price) if special_price else None,
            raw_description=description,
            raw_json=raw_json,
            menu_type=menu_type
        )

    def _parse_product(self, product: dict, menu_type: str = "recreational") -> Generator[MenuItem, None, None]:
        """Parse a Jane product into MenuItem(s).

        Args:
            product: Raw product data from API
            menu_type: "recreational" or "medical"
        """
        product_id = product.get("id", "")
        name = product.get("name", "Unknown")
        brand = product.get("brand", {})
        brand_name = brand.get("name") if isinstance(brand, dict) else brand
        category = product.get("category") or product.get("kind") or product.get("product_type")
        description = product.get("description", "")

        # Price information
        price = product.get("price") or product.get("min_price")
        special_price = product.get("special_price") or product.get("discounted_price")

        # Potency info
        thc = product.get("thc") or product.get("thc_potency")
        cbd = product.get("cbd") or product.get("cbd_potency")

        # Variants/options (different sizes)
        variants = product.get("variants", product.get("options", []))

        if not variants:
            # Product without variants
            raw_json = {
                "productId": product_id,
                "name": name,
                "brand": brand_name,
                "category": category,
                "subcategory": product.get("subcategory"),
                "description": description,
                "thc": thc,
                "cbd": cbd,
                "strain": product.get("strain"),
                "strainType": product.get("strain_type") or product.get("lineage"),
                "weight": product.get("weight") or product.get("size"),
                "image": product.get("image_url") or product.get("photo_url"),
                "inStock": product.get("in_stock", True),
                "menuType": menu_type,
            }

            yield MenuItem(
                provider_product_id=str(product_id),
                raw_name=name,
                raw_brand=brand_name,
                raw_category=category,
                raw_price=float(price) if price else None,
                raw_discount_price=float(special_price) if special_price else None,
                raw_description=description,
                raw_json=raw_json,
                menu_type=menu_type
            )
        else:
            # Create a MenuItem for each variant
            for variant in variants:
                variant_id = variant.get("id", "")
                variant_name = variant.get("name") or variant.get("option") or variant.get("size")
                variant_price = variant.get("price", price)
                variant_special = variant.get("special_price") or variant.get("discounted_price")

                full_name = f"{name} - {variant_name}" if variant_name else name

                raw_json = {
                    "productId": product_id,
                    "variantId": variant_id,
                    "name": name,
                    "variantName": variant_name,
                    "brand": brand_name,
                    "category": category,
                    "subcategory": product.get("subcategory"),
                    "description": description,
                    "thc": thc,
                    "cbd": cbd,
                    "strain": product.get("strain"),
                    "strainType": product.get("strain_type") or product.get("lineage"),
                    "weight": variant.get("weight") or variant.get("size") or variant_name,
                    "image": product.get("image_url") or product.get("photo_url"),
                    "inStock": variant.get("in_stock", product.get("in_stock", True)),
                    "quantity": variant.get("quantity"),
                    "menuType": menu_type,
                }

                yield MenuItem(
                    provider_product_id=f"{product_id}_{variant_id}" if variant_id else str(product_id),
                    raw_name=full_name,
                    raw_brand=brand_name,
                    raw_category=category,
                    raw_price=float(variant_price) if variant_price else None,
                    raw_discount_price=float(variant_special) if variant_special else None,
                    raw_description=description,
                    raw_json=raw_json,
                    menu_type=menu_type
                )
