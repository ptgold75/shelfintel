# ingest/providers/sweed.py
"""Sweed POS provider - scrapes dispensaries using Sweed platform."""

import requests
from typing import Generator
from .base import BaseProvider, MenuItem

class SweedProvider(BaseProvider):
    """Provider for Sweed POS dispensaries."""
    
    name = "sweed"
    
    BASE_URL = "https://web-ui-production.sweedpos.com/_api/proxy"
    
    def __init__(self, dispensary_id: str, store_id: str):
        super().__init__(dispensary_id)
        self.store_id = store_id
    
    def _get_headers(self, sale_type: str = "Recreational") -> dict:
        return {
            "accept": "application/json",
            "content-type": "application/json",
            "storeid": str(self.store_id),
            "saletype": sale_type,
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
    
    def _get_categories(self) -> list:
        """Fetch all product categories for this store."""
        url = f"{self.BASE_URL}/Products/GetProductCategoryList"
        try:
            resp = requests.get(url, headers=self._get_headers(), timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("productCategoryList", [])
        except Exception as e:
            print(f"Error fetching categories: {e}")
        return []
    
    def _get_products(self, category: str, page: int = 1, page_size: int = 100) -> dict:
        """Fetch products for a specific category."""
        url = f"{self.BASE_URL}/Products/GetProductList"
        payload = {
            "categoryName": category,
            "page": page,
            "pageSize": page_size,
            "sortDirection": "asc",
            "sortExpression": "Name"
        }
        try:
            resp = requests.post(url, headers=self._get_headers(), json=payload, timeout=30)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"Error fetching products: {e}")
        return {}
    
    def scrape(self) -> Generator[MenuItem, None, None]:
        """Scrape all products from this dispensary."""
        categories = self._get_categories()
        
        for category in categories:
            cat_name = category.get("categoryName", "Unknown")
            page = 1
            
            while True:
                data = self._get_products(cat_name, page=page)
                products = data.get("productList", [])
                
                if not products:
                    break
                
                for product in products:
                    # Extract price info
                    price = None
                    weights = product.get("weightPriceList", [])
                    if weights:
                        price = weights[0].get("price")
                    
                    # Get discount/sale price if available
                    discount_price = None
                    discount_text = None
                    if weights and weights[0].get("discountPrice"):
                        discount_price = weights[0].get("discountPrice")
                    if product.get("discountText"):
                        discount_text = product.get("discountText")
                    
                    # Get description
                    description = product.get("description", "")
                    
                    # Build raw JSON with all useful fields
                    raw_json = {
                        "productId": product.get("productId"),
                        "name": product.get("productName"),
                        "brand": product.get("brandName"),
                        "category": cat_name,
                        "subcategory": product.get("subCategoryName"),
                        "description": description,
                        "thc": product.get("thc"),
                        "cbd": product.get("cbd"),
                        "strain": product.get("strain"),
                        "strainType": product.get("strainType"),
                        "weights": weights,
                        "imageUrl": product.get("imageUrl"),
                        "labResults": product.get("labResults"),
                    }
                    
                    yield MenuItem(
                        provider_product_id=str(product.get("productId", "")),
                        raw_name=product.get("productName", "Unknown"),
                        raw_brand=product.get("brandName"),
                        raw_category=cat_name,
                        raw_price=price,
                        raw_discount_price=discount_price,
                        raw_discount_text=discount_text,
                        raw_json=raw_json
                    )
                
                # Check for more pages
                total_count = data.get("totalCount", 0)
                if page * 100 >= total_count:
                    break
                page += 1
