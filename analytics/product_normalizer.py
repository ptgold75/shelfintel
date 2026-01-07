# analytics/product_normalizer.py
"""Product Normalization and Deduplication System.

Cannabis products are often listed with inconsistent naming conventions across
dispensaries. This module standardizes product data to enable accurate analytics.

Common issues:
- "Blue Dream 3.5g" vs "Blue Dream - 3.5 grams" vs "BLUE DREAM 1/8"
- Brand names with/without spaces: "Green Thumb" vs "GreenThumb"
- Size variations: "3.5g", "3.5 g", "1/8 oz", "eighth", "1/8th"
- Category inconsistencies: "Flower", "FLOWER", "flower", "Flowers"
"""

import re
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
import json

# Size normalization mappings
SIZE_PATTERNS = [
    # Grams
    (r'(\d+(?:\.\d+)?)\s*(?:g|gram|grams)\b', lambda m: f"{float(m.group(1))}g"),
    (r'(\d+(?:\.\d+)?)\s*(?:mg|milligram|milligrams)\b', lambda m: f"{float(m.group(1))}mg"),
    # Fractions to grams (flower)
    (r'\b(?:1/8|eighth|1/8th|⅛)\b', lambda m: "3.5g"),
    (r'\b(?:1/4|quarter|1/4th|¼)\b', lambda m: "7g"),
    (r'\b(?:1/2|half|1/2th|½)\b', lambda m: "14g"),
    (r'\b(?:oz|ounce)\b', lambda m: "28g"),
    # Counts
    (r'(\d+)\s*(?:pk|pack|ct|count|pc|pcs|pieces)\b', lambda m: f"{m.group(1)}pk"),
    # Cartridge sizes
    (r'(\d+(?:\.\d+)?)\s*(?:ml)\b', lambda m: f"{float(m.group(1))}ml"),
]

# Category normalization
CATEGORY_MAP = {
    'flower': 'Flower',
    'flowers': 'Flower',
    'buds': 'Flower',
    'pre-roll': 'Pre-Roll',
    'pre-rolls': 'Pre-Roll',
    'preroll': 'Pre-Roll',
    'prerolls': 'Pre-Roll',
    'joint': 'Pre-Roll',
    'joints': 'Pre-Roll',
    'vape': 'Vaporizer',
    'vapes': 'Vaporizer',
    'vaporizer': 'Vaporizer',
    'vaporizers': 'Vaporizer',
    'cartridge': 'Vaporizer',
    'cartridges': 'Vaporizer',
    'cart': 'Vaporizer',
    'carts': 'Vaporizer',
    'concentrate': 'Concentrate',
    'concentrates': 'Concentrate',
    'extract': 'Concentrate',
    'extracts': 'Concentrate',
    'wax': 'Concentrate',
    'shatter': 'Concentrate',
    'live resin': 'Concentrate',
    'rosin': 'Concentrate',
    'badder': 'Concentrate',
    'budder': 'Concentrate',
    'edible': 'Edible',
    'edibles': 'Edible',
    'gummy': 'Edible',
    'gummies': 'Edible',
    'chocolate': 'Edible',
    'tincture': 'Tincture',
    'tinctures': 'Tincture',
    'topical': 'Topical',
    'topicals': 'Topical',
    'accessory': 'Accessory',
    'accessories': 'Accessory',
    'gear': 'Accessory',
}

# Common brand name variations to standardize
BRAND_CORRECTIONS = {
    'culta cannabis': 'Culta',
    'evermore cannabis': 'Evermore',
    'grassroots cannabis': 'Grassroots',
    'select elite': 'Select',
    'cresco labs': 'Cresco',
    'gti': 'Green Thumb Industries',
    'rythm': 'Rhythm',  # Common misspelling
}


@dataclass
class NormalizedProduct:
    """A product with normalized attributes."""
    original_name: str
    normalized_name: str
    brand: str
    normalized_brand: str
    category: str
    normalized_category: str
    size: Optional[str]
    normalized_size: Optional[str]
    strain: Optional[str]
    match_key: str  # Key for matching duplicates
    dispensary_id: str
    dispensary_name: str
    price: Optional[float]
    raw_data: dict = field(default_factory=dict)


@dataclass
class ProductCluster:
    """A cluster of products that are likely the same item."""
    canonical_name: str
    canonical_brand: str
    canonical_category: str
    canonical_size: Optional[str]
    match_key: str
    products: List[NormalizedProduct] = field(default_factory=list)
    dispensary_count: int = 0
    avg_price: float = 0.0
    price_range: Tuple[float, float] = (0.0, 0.0)
    confidence: float = 0.0  # How confident we are these are the same product


class ProductNormalizer:
    """Normalizes and deduplicates cannabis product data."""

    def __init__(self):
        self._products: List[NormalizedProduct] = []
        self._clusters: Dict[str, ProductCluster] = {}
        self._brand_aliases: Dict[str, str] = {}  # alias -> canonical

    def normalize_text(self, text: str) -> str:
        """Basic text normalization."""
        if not text:
            return ""
        # Lowercase, strip, collapse whitespace
        text = re.sub(r'\s+', ' ', text.lower().strip())
        # Remove special characters except essential ones
        text = re.sub(r'[^\w\s\-\./]', '', text)
        return text

    def extract_size(self, name: str) -> Tuple[str, Optional[str]]:
        """Extract and normalize size from product name.

        Returns:
            (name_without_size, normalized_size)
        """
        name_lower = name.lower()
        normalized_size = None

        for pattern, normalizer in SIZE_PATTERNS:
            match = re.search(pattern, name_lower, re.IGNORECASE)
            if match:
                normalized_size = normalizer(match)
                # Remove size from name
                name = re.sub(pattern, '', name, flags=re.IGNORECASE).strip()
                break

        return name.strip(' -'), normalized_size

    def normalize_brand(self, brand: str) -> str:
        """Normalize brand name."""
        if not brand:
            return ""

        normalized = self.normalize_text(brand)

        # Check known corrections
        if normalized in BRAND_CORRECTIONS:
            return BRAND_CORRECTIONS[normalized]

        # Check aliases
        if normalized in self._brand_aliases:
            return self._brand_aliases[normalized]

        # Title case
        return brand.strip().title()

    def normalize_category(self, category: str) -> str:
        """Normalize category name."""
        if not category:
            return "Other"

        normalized = self.normalize_text(category)

        # Check mapping
        for key, value in CATEGORY_MAP.items():
            if key in normalized:
                return value

        return category.strip().title()

    def create_match_key(
        self,
        brand: str,
        name: str,
        category: str,
        size: Optional[str]
    ) -> str:
        """Create a key for matching similar products.

        The key combines normalized brand, name, category, and size to
        identify products that should be considered the same.
        """
        parts = [
            self.normalize_text(brand) if brand else "unknown",
            self.normalize_text(name),
            self.normalize_category(category).lower(),
        ]
        if size:
            parts.append(size.lower())

        return "|".join(parts)

    def normalize_product(
        self,
        name: str,
        brand: str,
        category: str,
        dispensary_id: str,
        dispensary_name: str,
        price: Optional[float] = None,
        raw_data: Optional[dict] = None
    ) -> NormalizedProduct:
        """Normalize a single product."""
        # Extract size from name
        name_without_size, normalized_size = self.extract_size(name)

        # Normalize brand
        normalized_brand = self.normalize_brand(brand)

        # Normalize category
        normalized_category = self.normalize_category(category)

        # Create normalized name (without size, title case)
        normalized_name = name_without_size.strip().title()
        normalized_name = re.sub(r'\s+', ' ', normalized_name)

        # Create match key
        match_key = self.create_match_key(
            normalized_brand,
            normalized_name,
            normalized_category,
            normalized_size
        )

        return NormalizedProduct(
            original_name=name,
            normalized_name=normalized_name,
            brand=brand,
            normalized_brand=normalized_brand,
            category=category,
            normalized_category=normalized_category,
            size=self.extract_size(name)[1],  # Original extracted size
            normalized_size=normalized_size,
            strain=None,  # TODO: Extract strain from name
            match_key=match_key,
            dispensary_id=dispensary_id,
            dispensary_name=dispensary_name,
            price=price,
            raw_data=raw_data or {}
        )

    def add_product(self, product: NormalizedProduct):
        """Add a normalized product to the collection."""
        self._products.append(product)

        # Add to cluster
        if product.match_key not in self._clusters:
            self._clusters[product.match_key] = ProductCluster(
                canonical_name=product.normalized_name,
                canonical_brand=product.normalized_brand,
                canonical_category=product.normalized_category,
                canonical_size=product.normalized_size,
                match_key=product.match_key,
                products=[]
            )

        self._clusters[product.match_key].products.append(product)

    def process_products(self, products: List[dict]) -> List[NormalizedProduct]:
        """Process a list of raw products and normalize them.

        Args:
            products: List of dicts with keys: name, brand, category,
                     dispensary_id, dispensary_name, price
        """
        normalized = []
        for p in products:
            norm = self.normalize_product(
                name=p.get('name', ''),
                brand=p.get('brand', ''),
                category=p.get('category', ''),
                dispensary_id=p.get('dispensary_id', ''),
                dispensary_name=p.get('dispensary_name', ''),
                price=p.get('price'),
                raw_data=p
            )
            self.add_product(norm)
            normalized.append(norm)

        return normalized

    def compute_cluster_stats(self):
        """Compute statistics for all clusters."""
        for cluster in self._clusters.values():
            products = cluster.products
            cluster.dispensary_count = len(set(p.dispensary_id for p in products))

            prices = [p.price for p in products if p.price and p.price > 0]
            if prices:
                cluster.avg_price = sum(prices) / len(prices)
                cluster.price_range = (min(prices), max(prices))

            # Confidence based on consistency
            # Higher if same brand across all, lower if names vary significantly
            brands = set(p.normalized_brand for p in products)
            names = set(p.normalized_name for p in products)

            brand_consistency = 1.0 if len(brands) == 1 else 0.5
            name_consistency = 1.0 / len(names) if names else 0.0

            cluster.confidence = (brand_consistency + name_consistency) / 2

    def find_potential_duplicates(
        self,
        min_dispensaries: int = 2,
        min_confidence: float = 0.5
    ) -> List[ProductCluster]:
        """Find clusters that might be duplicates needing review.

        Returns clusters where the same product appears in multiple
        dispensaries with slightly different names.
        """
        self.compute_cluster_stats()

        duplicates = []
        for cluster in self._clusters.values():
            if cluster.dispensary_count >= min_dispensaries:
                # Check if there are naming variations
                names = set(p.original_name for p in cluster.products)
                if len(names) > 1:  # Multiple name variations
                    duplicates.append(cluster)

        # Sort by dispensary count (most widespread first)
        duplicates.sort(key=lambda c: -c.dispensary_count)
        return duplicates

    def find_fuzzy_matches(
        self,
        product: NormalizedProduct,
        threshold: float = 0.8
    ) -> List[Tuple[NormalizedProduct, float]]:
        """Find products that fuzzy-match a given product.

        Uses simple character-based similarity. For production,
        consider using rapidfuzz or similar library.
        """
        matches = []
        target = product.normalized_name.lower()

        for other in self._products:
            if other == product:
                continue
            if other.normalized_category != product.normalized_category:
                continue
            if other.normalized_brand != product.normalized_brand:
                continue

            # Simple similarity score
            other_name = other.normalized_name.lower()
            similarity = self._simple_similarity(target, other_name)

            if similarity >= threshold:
                matches.append((other, similarity))

        matches.sort(key=lambda x: -x[1])
        return matches

    def _simple_similarity(self, a: str, b: str) -> float:
        """Simple string similarity based on common characters."""
        if not a or not b:
            return 0.0
        if a == b:
            return 1.0

        # Character overlap
        set_a, set_b = set(a), set(b)
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)

        jaccard = intersection / union if union else 0.0

        # Length similarity
        len_sim = min(len(a), len(b)) / max(len(a), len(b))

        return (jaccard + len_sim) / 2

    def get_deduplication_report(self) -> dict:
        """Generate a report on potential duplicate products."""
        self.compute_cluster_stats()

        total_raw = len(self._products)
        total_clusters = len(self._clusters)

        # Find high-confidence duplicates
        multi_name_clusters = [
            c for c in self._clusters.values()
            if len(set(p.original_name for p in c.products)) > 1
        ]

        # Estimate true unique products
        estimated_unique = total_clusters

        return {
            "total_raw_products": total_raw,
            "total_clusters": total_clusters,
            "estimated_unique_products": estimated_unique,
            "estimated_duplicates": total_raw - total_clusters,
            "duplicate_rate": (total_raw - total_clusters) / total_raw * 100 if total_raw else 0,
            "clusters_with_name_variations": len(multi_name_clusters),
            "top_duplicate_clusters": [
                {
                    "canonical_name": c.canonical_name,
                    "brand": c.canonical_brand,
                    "category": c.canonical_category,
                    "size": c.canonical_size,
                    "dispensary_count": c.dispensary_count,
                    "name_variations": list(set(p.original_name for p in c.products))[:5],
                    "avg_price": c.avg_price
                }
                for c in sorted(multi_name_clusters, key=lambda x: -x.dispensary_count)[:20]
            ]
        }

    def export_canonical_products(self) -> List[dict]:
        """Export canonical (deduplicated) product list."""
        self.compute_cluster_stats()

        canonical = []
        for cluster in self._clusters.values():
            canonical.append({
                "canonical_name": cluster.canonical_name,
                "brand": cluster.canonical_brand,
                "category": cluster.canonical_category,
                "size": cluster.canonical_size,
                "match_key": cluster.match_key,
                "dispensary_count": cluster.dispensary_count,
                "avg_price": round(cluster.avg_price, 2),
                "price_min": round(cluster.price_range[0], 2),
                "price_max": round(cluster.price_range[1], 2),
                "name_variations": list(set(p.original_name for p in cluster.products)),
                "dispensaries": list(set(p.dispensary_name for p in cluster.products))
            })

        return canonical


def demo():
    """Demonstrate the product normalizer."""
    normalizer = ProductNormalizer()

    # Sample products with naming variations
    sample_products = [
        {"name": "Blue Dream 3.5g", "brand": "Culta", "category": "Flower", "dispensary_id": "1", "dispensary_name": "Dispensary A", "price": 45.00},
        {"name": "Blue Dream - 3.5 grams", "brand": "Culta Cannabis", "category": "flower", "dispensary_id": "2", "dispensary_name": "Dispensary B", "price": 48.00},
        {"name": "BLUE DREAM 1/8", "brand": "Culta", "category": "FLOWER", "dispensary_id": "3", "dispensary_name": "Dispensary C", "price": 44.00},
        {"name": "Blue Dream Eighth", "brand": "culta", "category": "Flowers", "dispensary_id": "4", "dispensary_name": "Dispensary D", "price": 46.00},
        {"name": "OG Kush 3.5g", "brand": "Evermore", "category": "Flower", "dispensary_id": "1", "dispensary_name": "Dispensary A", "price": 50.00},
        {"name": "OG Kush - 3.5g", "brand": "Evermore Cannabis", "category": "flower", "dispensary_id": "2", "dispensary_name": "Dispensary B", "price": 52.00},
        {"name": "Select Elite Cart 0.5g", "brand": "Select", "category": "Vape", "dispensary_id": "1", "dispensary_name": "Dispensary A", "price": 35.00},
        {"name": "Select Elite Cartridge .5g", "brand": "Select Elite", "category": "Cartridge", "dispensary_id": "2", "dispensary_name": "Dispensary B", "price": 38.00},
    ]

    normalizer.process_products(sample_products)

    print("\n" + "="*70)
    print("PRODUCT NORMALIZATION REPORT")
    print("="*70)

    report = normalizer.get_deduplication_report()
    print(f"\nTotal Raw Products: {report['total_raw_products']}")
    print(f"Unique Products (Clusters): {report['total_clusters']}")
    print(f"Estimated Duplicates: {report['estimated_duplicates']}")
    print(f"Duplicate Rate: {report['duplicate_rate']:.1f}%")

    print(f"\nClusters with Name Variations: {report['clusters_with_name_variations']}")

    if report['top_duplicate_clusters']:
        print("\nTop Duplicate Clusters:")
        print("-"*70)
        for cluster in report['top_duplicate_clusters']:
            print(f"\n  {cluster['brand']} - {cluster['canonical_name']} ({cluster['size']})")
            print(f"  Category: {cluster['category']}")
            print(f"  Found in {cluster['dispensary_count']} dispensaries")
            print(f"  Avg Price: ${cluster['avg_price']:.2f}")
            print(f"  Name Variations:")
            for var in cluster['name_variations']:
                print(f"    - {var}")


if __name__ == "__main__":
    demo()
