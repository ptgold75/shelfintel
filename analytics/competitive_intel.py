# analytics/competitive_intel.py
"""Competitive Intelligence Analytics for Dispensary Owners.

Provides insights into:
- Product gaps (what competitors carry that you don't)
- Price comparisons vs competitors, county, and state averages
- Brand distribution analysis
- Category mix comparisons
- Market positioning insights
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
import json
import math


@dataclass
class ProductInfo:
    """Represents a product for comparison."""
    name: str
    brand: str
    category: str
    subcategory: Optional[str]
    price: float
    discount_price: Optional[float]
    dispensary_id: str
    dispensary_name: str


@dataclass
class PriceComparison:
    """Price comparison results."""
    product_name: str
    brand: str
    category: str
    your_price: float
    competitor_price: Optional[float] = None
    county_avg: Optional[float] = None
    state_avg: Optional[float] = None
    price_position: str = "unknown"  # "below", "at", "above"
    savings_vs_competitor: Optional[float] = None
    savings_vs_county: Optional[float] = None
    savings_vs_state: Optional[float] = None


@dataclass
class ProductGap:
    """A product carried by competitors but not by you."""
    product_name: str
    brand: str
    category: str
    carried_by: List[str]  # List of competitor names
    avg_price: float
    min_price: float
    max_price: float
    popularity_score: int  # Number of competitors carrying it


@dataclass
class CompetitiveReport:
    """Full competitive intelligence report."""
    dispensary_name: str
    dispensary_county: str
    comparison_type: str  # "competitor", "county", "state"

    # Product analysis
    your_product_count: int = 0
    your_brand_count: int = 0
    your_category_breakdown: Dict[str, int] = field(default_factory=dict)

    # Competitor/market stats
    comparison_product_count: int = 0
    comparison_brand_count: int = 0
    comparison_category_breakdown: Dict[str, int] = field(default_factory=dict)

    # Gaps and opportunities
    product_gaps: List[ProductGap] = field(default_factory=list)
    brand_gaps: List[str] = field(default_factory=list)

    # Price analysis
    price_comparisons: List[PriceComparison] = field(default_factory=list)
    avg_price_vs_market: float = 0.0  # Percentage difference

    # Category insights
    underrepresented_categories: List[Tuple[str, float]] = field(default_factory=list)
    overrepresented_categories: List[Tuple[str, float]] = field(default_factory=list)


class CompetitiveIntelligence:
    """Competitive intelligence engine for dispensary analysis."""

    def __init__(self, menu_data_path: Optional[str] = None, licensee_data_path: Optional[str] = None):
        """Initialize with paths to scraped menu data and licensee database.

        Args:
            menu_data_path: Path to scraped menu data (JSON)
            licensee_data_path: Path to MD licensee database
        """
        self.menu_data_path = menu_data_path
        self.licensee_data_path = licensee_data_path or "data/md_licensees.json"

        # Data stores
        self._dispensaries: Dict[str, dict] = {}  # dispensary_id -> info
        self._products: Dict[str, List[ProductInfo]] = defaultdict(list)  # dispensary_id -> products
        self._county_products: Dict[str, List[ProductInfo]] = defaultdict(list)  # county -> products
        self._all_products: List[ProductInfo] = []

        self._loaded = False

    def load_licensee_data(self):
        """Load dispensary information from licensee database."""
        try:
            with open(self.licensee_data_path) as f:
                data = json.load(f)

            for disp in data.get('dispensaries', []):
                disp_id = disp.get('license_number', '')
                self._dispensaries[disp_id] = {
                    'name': disp.get('trade_name') or disp.get('location_name'),
                    'legal_name': disp.get('legal_name'),
                    'county': disp.get('county'),
                    'region': disp.get('region'),
                    'address': disp.get('address'),
                    'lat': disp.get('lat'),
                    'lng': disp.get('lng')
                }
        except Exception as e:
            print(f"Error loading licensee data: {e}")

    def load_menu_data(self, menu_data: Dict[str, List[dict]]):
        """Load scraped menu data.

        Args:
            menu_data: Dict mapping dispensary_id to list of product dicts
        """
        for disp_id, products in menu_data.items():
            disp_info = self._dispensaries.get(disp_id, {})
            disp_name = disp_info.get('name', disp_id)
            county = disp_info.get('county', 'Unknown')

            for prod in products:
                price = prod.get('raw_price') or prod.get('price')
                if not price:
                    continue

                product = ProductInfo(
                    name=prod.get('raw_name') or prod.get('name', 'Unknown'),
                    brand=prod.get('raw_brand') or prod.get('brand', 'Unknown'),
                    category=prod.get('raw_category') or prod.get('category', 'Unknown'),
                    subcategory=prod.get('subcategory'),
                    price=float(price),
                    discount_price=float(prod.get('raw_discount_price')) if prod.get('raw_discount_price') else None,
                    dispensary_id=disp_id,
                    dispensary_name=disp_name
                )

                self._products[disp_id].append(product)
                self._county_products[county].append(product)
                self._all_products.append(product)

        self._loaded = True

    def get_nearby_competitors(self, dispensary_id: str, radius_miles: float = 10.0) -> List[str]:
        """Find dispensaries within a radius of the given dispensary.

        Args:
            dispensary_id: License number of the dispensary
            radius_miles: Search radius in miles

        Returns:
            List of competitor dispensary IDs
        """
        if dispensary_id not in self._dispensaries:
            return []

        my_info = self._dispensaries[dispensary_id]
        my_lat, my_lng = my_info.get('lat'), my_info.get('lng')

        if not my_lat or not my_lng:
            # Fall back to same county
            return self.get_county_competitors(dispensary_id)

        competitors = []
        for comp_id, comp_info in self._dispensaries.items():
            if comp_id == dispensary_id:
                continue

            comp_lat, comp_lng = comp_info.get('lat'), comp_info.get('lng')
            if not comp_lat or not comp_lng:
                continue

            distance = self._haversine_distance(my_lat, my_lng, comp_lat, comp_lng)
            if distance <= radius_miles:
                competitors.append(comp_id)

        return competitors

    def get_county_competitors(self, dispensary_id: str) -> List[str]:
        """Get all dispensaries in the same county.

        Args:
            dispensary_id: License number of the dispensary

        Returns:
            List of competitor dispensary IDs in same county
        """
        if dispensary_id not in self._dispensaries:
            return []

        my_county = self._dispensaries[dispensary_id].get('county')

        return [
            disp_id for disp_id, info in self._dispensaries.items()
            if info.get('county') == my_county and disp_id != dispensary_id
        ]

    def _haversine_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two points in miles."""
        R = 3959  # Earth's radius in miles

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)

        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        return R * c

    def find_product_gaps(
        self,
        dispensary_id: str,
        competitor_ids: Optional[List[str]] = None,
        min_competitors: int = 1
    ) -> List[ProductGap]:
        """Find products carried by competitors but not by you.

        Args:
            dispensary_id: Your dispensary's license number
            competitor_ids: List of competitor IDs to compare against (or None for county)
            min_competitors: Minimum number of competitors carrying the product

        Returns:
            List of ProductGap objects sorted by popularity
        """
        my_products = self._products.get(dispensary_id, [])
        my_product_keys = {self._product_key(p) for p in my_products}

        # Get competitor products
        if competitor_ids:
            competitor_products = []
            for comp_id in competitor_ids:
                competitor_products.extend(self._products.get(comp_id, []))
        else:
            # Use county
            my_county = self._dispensaries.get(dispensary_id, {}).get('county')
            competitor_products = [
                p for p in self._county_products.get(my_county, [])
                if p.dispensary_id != dispensary_id
            ]

        # Find gaps
        gap_products = defaultdict(lambda: {
            'brand': '',
            'category': '',
            'carried_by': set(),
            'prices': []
        })

        for prod in competitor_products:
            key = self._product_key(prod)
            if key not in my_product_keys:
                gap_products[key]['brand'] = prod.brand
                gap_products[key]['category'] = prod.category
                gap_products[key]['carried_by'].add(prod.dispensary_name)
                gap_products[key]['prices'].append(prod.price)

        # Convert to ProductGap objects
        gaps = []
        for product_name, info in gap_products.items():
            if len(info['carried_by']) >= min_competitors:
                prices = info['prices']
                gaps.append(ProductGap(
                    product_name=product_name,
                    brand=info['brand'],
                    category=info['category'],
                    carried_by=list(info['carried_by']),
                    avg_price=sum(prices) / len(prices),
                    min_price=min(prices),
                    max_price=max(prices),
                    popularity_score=len(info['carried_by'])
                ))

        # Sort by popularity
        gaps.sort(key=lambda x: -x.popularity_score)
        return gaps

    def find_brand_gaps(
        self,
        dispensary_id: str,
        competitor_ids: Optional[List[str]] = None
    ) -> List[Tuple[str, int, List[str]]]:
        """Find brands carried by competitors but not by you.

        Returns:
            List of (brand_name, competitor_count, [competitor_names])
        """
        my_products = self._products.get(dispensary_id, [])
        my_brands = {p.brand for p in my_products if p.brand}

        # Get competitor brands
        if competitor_ids:
            competitor_products = []
            for comp_id in competitor_ids:
                competitor_products.extend(self._products.get(comp_id, []))
        else:
            my_county = self._dispensaries.get(dispensary_id, {}).get('county')
            competitor_products = [
                p for p in self._county_products.get(my_county, [])
                if p.dispensary_id != dispensary_id
            ]

        brand_carriers = defaultdict(set)
        for prod in competitor_products:
            if prod.brand and prod.brand not in my_brands:
                brand_carriers[prod.brand].add(prod.dispensary_name)

        result = [
            (brand, len(carriers), list(carriers))
            for brand, carriers in brand_carriers.items()
        ]
        result.sort(key=lambda x: -x[1])
        return result

    def compare_prices(
        self,
        dispensary_id: str,
        competitor_ids: Optional[List[str]] = None,
        category: Optional[str] = None
    ) -> List[PriceComparison]:
        """Compare your prices to competitors, county, and state averages.

        Args:
            dispensary_id: Your dispensary ID
            competitor_ids: Specific competitors to compare against
            category: Optional category filter

        Returns:
            List of PriceComparison objects
        """
        my_products = self._products.get(dispensary_id, [])
        if category:
            my_products = [p for p in my_products if p.category.lower() == category.lower()]

        my_county = self._dispensaries.get(dispensary_id, {}).get('county')

        comparisons = []
        for prod in my_products:
            key = self._product_key(prod)

            # Find competitor prices
            comp_prices = []
            if competitor_ids:
                for comp_id in competitor_ids:
                    for comp_prod in self._products.get(comp_id, []):
                        if self._product_key(comp_prod) == key:
                            comp_prices.append(comp_prod.price)

            # Find county prices
            county_prices = [
                p.price for p in self._county_products.get(my_county, [])
                if self._product_key(p) == key and p.dispensary_id != dispensary_id
            ]

            # Find state prices
            state_prices = [
                p.price for p in self._all_products
                if self._product_key(p) == key and p.dispensary_id != dispensary_id
            ]

            comp_avg = sum(comp_prices) / len(comp_prices) if comp_prices else None
            county_avg = sum(county_prices) / len(county_prices) if county_prices else None
            state_avg = sum(state_prices) / len(state_prices) if state_prices else None

            # Determine price position
            reference = comp_avg or county_avg or state_avg
            if reference:
                diff_pct = ((prod.price - reference) / reference) * 100
                if diff_pct < -5:
                    position = "below"
                elif diff_pct > 5:
                    position = "above"
                else:
                    position = "at"
            else:
                position = "unknown"

            comparisons.append(PriceComparison(
                product_name=prod.name,
                brand=prod.brand,
                category=prod.category,
                your_price=prod.price,
                competitor_price=comp_avg,
                county_avg=county_avg,
                state_avg=state_avg,
                price_position=position,
                savings_vs_competitor=(comp_avg - prod.price) if comp_avg else None,
                savings_vs_county=(county_avg - prod.price) if county_avg else None,
                savings_vs_state=(state_avg - prod.price) if state_avg else None
            ))

        return comparisons

    def compare_category_mix(
        self,
        dispensary_id: str,
        competitor_ids: Optional[List[str]] = None
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Compare your category distribution to competitors.

        Returns:
            (your_category_pct, competitor_category_pct)
        """
        my_products = self._products.get(dispensary_id, [])

        if competitor_ids:
            comp_products = []
            for comp_id in competitor_ids:
                comp_products.extend(self._products.get(comp_id, []))
        else:
            my_county = self._dispensaries.get(dispensary_id, {}).get('county')
            comp_products = [
                p for p in self._county_products.get(my_county, [])
                if p.dispensary_id != dispensary_id
            ]

        def get_category_pcts(products):
            cat_counts = defaultdict(int)
            for p in products:
                cat_counts[p.category] += 1
            total = len(products) or 1
            return {cat: (count / total) * 100 for cat, count in cat_counts.items()}

        return get_category_pcts(my_products), get_category_pcts(comp_products)

    def generate_report(
        self,
        dispensary_id: str,
        competitor_ids: Optional[List[str]] = None,
        comparison_type: str = "competitor"
    ) -> CompetitiveReport:
        """Generate a full competitive intelligence report.

        Args:
            dispensary_id: Your dispensary ID
            competitor_ids: Specific competitors (or None for county comparison)
            comparison_type: "competitor", "county", or "state"
        """
        disp_info = self._dispensaries.get(dispensary_id, {})
        my_products = self._products.get(dispensary_id, [])

        report = CompetitiveReport(
            dispensary_name=disp_info.get('name', dispensary_id),
            dispensary_county=disp_info.get('county', 'Unknown'),
            comparison_type=comparison_type
        )

        # Your stats
        report.your_product_count = len(my_products)
        report.your_brand_count = len({p.brand for p in my_products})
        for p in my_products:
            report.your_category_breakdown[p.category] = report.your_category_breakdown.get(p.category, 0) + 1

        # Get comparison products
        if comparison_type == "state":
            comp_products = [p for p in self._all_products if p.dispensary_id != dispensary_id]
        elif comparison_type == "county" or not competitor_ids:
            comp_products = [
                p for p in self._county_products.get(disp_info.get('county'), [])
                if p.dispensary_id != dispensary_id
            ]
        else:
            comp_products = []
            for comp_id in competitor_ids:
                comp_products.extend(self._products.get(comp_id, []))

        # Comparison stats
        report.comparison_product_count = len(comp_products)
        report.comparison_brand_count = len({p.brand for p in comp_products})
        for p in comp_products:
            report.comparison_category_breakdown[p.category] = report.comparison_category_breakdown.get(p.category, 0) + 1

        # Product gaps
        report.product_gaps = self.find_product_gaps(dispensary_id, competitor_ids)[:50]

        # Brand gaps
        brand_gaps = self.find_brand_gaps(dispensary_id, competitor_ids)
        report.brand_gaps = [b[0] for b in brand_gaps[:20]]

        # Price comparisons
        report.price_comparisons = self.compare_prices(dispensary_id, competitor_ids)

        # Calculate average price difference
        price_diffs = []
        for pc in report.price_comparisons:
            ref = pc.competitor_price or pc.county_avg or pc.state_avg
            if ref:
                price_diffs.append(((pc.your_price - ref) / ref) * 100)
        report.avg_price_vs_market = sum(price_diffs) / len(price_diffs) if price_diffs else 0

        # Category analysis
        my_cat_pct, comp_cat_pct = self.compare_category_mix(dispensary_id, competitor_ids)
        for cat in set(my_cat_pct.keys()) | set(comp_cat_pct.keys()):
            my_pct = my_cat_pct.get(cat, 0)
            comp_pct = comp_cat_pct.get(cat, 0)
            diff = my_pct - comp_pct
            if diff < -5:
                report.underrepresented_categories.append((cat, diff))
            elif diff > 5:
                report.overrepresented_categories.append((cat, diff))

        report.underrepresented_categories.sort(key=lambda x: x[1])
        report.overrepresented_categories.sort(key=lambda x: -x[1])

        return report

    def _product_key(self, product: ProductInfo) -> str:
        """Generate a unique key for product matching."""
        # Normalize the product name for matching
        name = product.name.lower().strip()
        brand = (product.brand or '').lower().strip()
        return f"{brand}:{name}"

    def print_report(self, report: CompetitiveReport):
        """Print a formatted competitive intelligence report."""
        print("\n" + "=" * 70)
        print(f"COMPETITIVE INTELLIGENCE REPORT")
        print(f"Dispensary: {report.dispensary_name}")
        print(f"County: {report.dispensary_county}")
        print(f"Comparison: {report.comparison_type.upper()}")
        print("=" * 70)

        print(f"\n📊 INVENTORY COMPARISON")
        print(f"   {'Metric':<25} {'You':>10} {'Market':>10}")
        print(f"   {'-'*45}")
        print(f"   {'Product Count':<25} {report.your_product_count:>10} {report.comparison_product_count:>10}")
        print(f"   {'Brand Count':<25} {report.your_brand_count:>10} {report.comparison_brand_count:>10}")

        print(f"\n💰 PRICE POSITIONING")
        if report.avg_price_vs_market > 2:
            print(f"   Your prices are {report.avg_price_vs_market:.1f}% ABOVE market average")
        elif report.avg_price_vs_market < -2:
            print(f"   Your prices are {abs(report.avg_price_vs_market):.1f}% BELOW market average")
        else:
            print(f"   Your prices are AT market average ({report.avg_price_vs_market:+.1f}%)")

        if report.product_gaps:
            print(f"\n🔍 TOP PRODUCT GAPS (carried by competitors, not by you)")
            for gap in report.product_gaps[:10]:
                print(f"   • {gap.product_name[:40]:<40}")
                print(f"     Brand: {gap.brand} | Avg Price: ${gap.avg_price:.2f} | Carried by {gap.popularity_score} competitor(s)")

        if report.brand_gaps:
            print(f"\n🏷️  BRAND GAPS (brands you don't carry)")
            print(f"   {', '.join(report.brand_gaps[:10])}")

        if report.underrepresented_categories:
            print(f"\n📉 UNDERREPRESENTED CATEGORIES (vs market)")
            for cat, diff in report.underrepresented_categories[:5]:
                print(f"   • {cat}: {diff:+.1f}% vs market")

        if report.overrepresented_categories:
            print(f"\n📈 OVERREPRESENTED CATEGORIES (vs market)")
            for cat, diff in report.overrepresented_categories[:5]:
                print(f"   • {cat}: {diff:+.1f}% vs market")

        print("\n" + "=" * 70 + "\n")


# Example usage
def demo():
    """Demonstrate competitive intelligence features."""
    ci = CompetitiveIntelligence()
    ci.load_licensee_data()

    # Simulate some menu data for demo
    sample_menu_data = {
        "DA-23-00052": [  # Thrive Annapolis
            {"raw_name": "Blue Dream 3.5g", "raw_brand": "Culta", "raw_category": "Flower", "raw_price": 45.00},
            {"raw_name": "OG Kush 3.5g", "raw_brand": "Evermore", "raw_category": "Flower", "raw_price": 50.00},
            {"raw_name": "Gummy Bears 10pk", "raw_brand": "Dixie", "raw_category": "Edible", "raw_price": 25.00},
        ],
        "DA-23-00109": [  # Green Point Millersville
            {"raw_name": "Blue Dream 3.5g", "raw_brand": "Culta", "raw_category": "Flower", "raw_price": 48.00},
            {"raw_name": "Sour Diesel 3.5g", "raw_brand": "Culta", "raw_category": "Flower", "raw_price": 45.00},
            {"raw_name": "Vape Cart 0.5g", "raw_brand": "Select", "raw_category": "Vaporizers", "raw_price": 35.00},
        ]
    }

    ci.load_menu_data(sample_menu_data)

    # Generate report for Thrive Annapolis
    report = ci.generate_report("DA-23-00052", comparison_type="county")
    ci.print_report(report)


if __name__ == "__main__":
    demo()
