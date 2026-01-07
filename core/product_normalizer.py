# core/product_normalizer.py
"""Product normalization for deduplication and standardization."""

import re
from typing import Optional, Tuple, Dict
from dataclasses import dataclass

@dataclass
class NormalizedProduct:
    """Normalized product representation."""
    base_name: str          # Strain/product name without size (e.g., "Pineapple Express")
    brand: str              # Brand name
    category: str           # Normalized category
    size_value: Optional[float]  # Numeric size (grams or mg)
    size_unit: str          # "g" or "mg"
    size_display: str       # Human readable (e.g., "3.5g (1/8oz)")
    form_factor: str        # "flower", "cart", "disposable", "edible", "preroll", etc.
    pack_count: int         # For multi-packs (default 1)
    normalized_key: str     # Unique key for deduplication

# Patterns to remove from product names to get base name
SIZE_PATTERNS = [
    r'\s*[-|]\s*\d+\.?\d*\s*(?:g|mg|gram|oz|ounce)s?\b',  # "- 3.5g", "| 500mg"
    r'\s*\[\s*\d+\.?\d*\s*(?:g|mg)\s*\]',                  # "[3.5g]", "[500mg]"
    r'\s*\(\s*\d+\.?\d*\s*(?:g|mg)\s*\)',                  # "(3.5g)", "(500mg)"
    r'\s*\d+\.?\d*\s*(?:g|mg|gram)s?\s*$',                 # trailing "3.5g", "500mg"
    r'\s*(?:1/8|1/4|1/2|eighth|quarter|half)\s*(?:oz|ounce)?\s*$',  # "1/8 oz"
    r'\s*\[\s*\d+\s*(?:pk|ct|pc|pack)\s*\]',              # "[10pk]"
    r'\s*\(\s*\d+\s*(?:pk|ct|pc|pack)\s*\)',              # "(5pk)"
    r'\s*\d+\s*(?:pk|ct|pc|pack)\s*$',                    # "10pk"
    r'\s*x\s*\d+\s*$',                                     # "x10"
]

# Patterns indicating vape form factor
DISPOSABLE_PATTERNS = [
    'disposable', 'all-in-one', 'all in one', 'aio', 'pod',
    'vape pen', 'pen vape', 'rechargeable'
]
CARTRIDGE_PATTERNS = ['cart', 'cartridge', '510']

# Category normalization mapping
CATEGORY_MAP = {
    # Flower variations
    'flower': 'Flower',
    'buds': 'Flower',
    'bud': 'Flower',
    'indica': 'Flower',
    'sativa': 'Flower',
    'hybrid': 'Flower',

    # Pre-roll variations
    'pre-roll': 'Pre-Rolls',
    'pre-rolls': 'Pre-Rolls',
    'preroll': 'Pre-Rolls',
    'prerolls': 'Pre-Rolls',
    'pre roll': 'Pre-Rolls',
    'pre rolls': 'Pre-Rolls',
    'joints': 'Pre-Rolls',
    'joint': 'Pre-Rolls',
    'blunts': 'Pre-Rolls',
    'blunt': 'Pre-Rolls',

    # Vape variations
    'vape': 'Vaporizers',
    'vapes': 'Vaporizers',
    'vaporizer': 'Vaporizers',
    'vaporizers': 'Vaporizers',
    'cartridge': 'Vaporizers',
    'cartridges': 'Vaporizers',
    'cart': 'Vaporizers',
    'carts': 'Vaporizers',
    '510 cartridges': 'Vaporizers',
    'disposable': 'Vaporizers',
    'disposables': 'Vaporizers',
    'pods': 'Vaporizers',

    # Concentrate variations
    'concentrate': 'Concentrates',
    'concentrates': 'Concentrates',
    'extract': 'Concentrates',
    'extracts': 'Concentrates',
    'wax': 'Concentrates',
    'shatter': 'Concentrates',
    'live resin': 'Concentrates',
    'rosin': 'Concentrates',
    'badder': 'Concentrates',
    'budder': 'Concentrates',
    'sauce': 'Concentrates',
    'diamonds': 'Concentrates',
    'rso': 'Concentrates',

    # Edible variations
    'edible': 'Edibles',
    'edibles': 'Edibles',
    'gummies': 'Edibles',
    'gummy': 'Edibles',
    'chocolate': 'Edibles',
    'chocolates': 'Edibles',
    'candy': 'Edibles',
    'mints': 'Edibles',
    'drinks': 'Edibles',
    'beverages': 'Edibles',
    'capsules': 'Edibles',

    # Tincture variations
    'tincture': 'Tinctures',
    'tinctures': 'Tinctures',
    'sublingual': 'Tinctures',
    'oil': 'Tinctures',

    # Topical variations
    'topical': 'Topicals',
    'topicals': 'Topicals',
    'balm': 'Topicals',
    'lotion': 'Topicals',
    'cream': 'Topicals',
    'patch': 'Topicals',
    'patches': 'Topicals',

    # Accessories (to be filtered out of main calculations)
    'accessory': 'Accessories',
    'accessories': 'Accessories',
    'gear': 'Accessories',
    'merchandise': 'Accessories',
    'merch': 'Accessories',
    'apparel': 'Accessories',
    'battery': 'Accessories',
    'batteries': 'Accessories',
    'grinder': 'Accessories',
    'grinders': 'Accessories',
    'papers': 'Accessories',
    'pipe': 'Accessories',
    'pipes': 'Accessories',
    'bong': 'Accessories',
    'bongs': 'Accessories',
}

# Categories that should be excluded from main product counts
ACCESSORY_CATEGORIES = {'Accessories', 'accessories', 'gear', 'merchandise', 'apparel'}


def normalize_category(raw_category: str) -> str:
    """Normalize category to standard form."""
    if not raw_category:
        return "Other"

    cat_lower = raw_category.lower().strip()
    return CATEGORY_MAP.get(cat_lower, raw_category)


def is_accessory(raw_category: str) -> bool:
    """Check if category is an accessory (should be filtered from main calculations)."""
    if not raw_category:
        return False

    normalized = normalize_category(raw_category)
    return normalized == 'Accessories' or raw_category.lower() in ACCESSORY_CATEGORIES


# Common brand name variations to normalize
BRAND_ALIASES = {
    'curio': 'Curio Wellness',
    'curio wellness': 'Curio Wellness',
    'nature\'s heritage': 'Nature\'s Heritage',
    'natures heritage': 'Nature\'s Heritage',
    'district cannabis': 'District Cannabis',
    'district': 'District Cannabis',
    'grassroots': 'Grassroots',
    'grass roots': 'Grassroots',
    'rythm': 'RYTHM',
    'rhythm': 'RYTHM',
    'strane': 'Strane',
    'kind tree': 'Kind Tree',
    'kindtree': 'Kind Tree',
    '&shine': '&Shine',
    'and shine': '&Shine',
    'evermore': 'Evermore',
    'culta': 'Culta',
    'sunmed': 'SunMed',
    'sun med': 'SunMed',
    'gleaf': 'gLeaf',
    'g leaf': 'gLeaf',
}


def extract_base_name(raw_name: str, brand: str = None) -> str:
    """
    Extract the base product name without size/weight info.
    E.g., "Pineapple Express 3.5g" -> "Pineapple Express"
    """
    if not raw_name:
        return ""

    name = raw_name.strip()

    # Remove brand prefix if present
    if brand:
        brand_lower = brand.lower()
        name_lower = name.lower()
        if name_lower.startswith(brand_lower):
            name = name[len(brand):].strip()
            # Remove common separators after brand
            name = re.sub(r'^[\s\-|:]+', '', name)

    # Remove size patterns
    for pattern in SIZE_PATTERNS:
        name = re.sub(pattern, '', name, flags=re.IGNORECASE)

    # Remove common suffixes
    name = re.sub(r'\s*[-|]+\s*$', '', name)  # Trailing dashes/pipes
    name = re.sub(r'\s+', ' ', name).strip()   # Normalize whitespace

    # Remove "ADD TO CART" or similar button text that got scraped
    name = re.sub(r'\s*ADD TO CART\s*$', '', name, flags=re.IGNORECASE)

    return name


def extract_size_from_description(description: str) -> Tuple[Optional[float], str, str]:
    """
    Extract size from product description when not in name.
    Used as fallback when extract_size returns None.
    """
    if not description:
        return None, "", ""

    desc_lower = description.lower()

    # Look for explicit size mentions
    # Try gram patterns first
    g_match = re.search(r'(\d+\.?\d*)\s*g(?:ram)?s?\b', desc_lower)
    if g_match:
        grams = float(g_match.group(1))
        if grams <= 28:  # Reasonable flower/pre-roll size
            return grams, "g", f"{grams}g"

    # Try mg patterns
    mg_match = re.search(r'(\d{2,4})\s*mg', desc_lower)
    if mg_match:
        mg = int(mg_match.group(1))
        return mg, "mg", f"{mg}mg"

    # Try pack count
    pack_match = re.search(r'(\d+)\s*(?:pk|pack|count|piece)', desc_lower)
    if pack_match:
        count = int(pack_match.group(1))
        return count, "pk", f"{count}pk"

    return None, "", ""


def extract_size(raw_name: str, category: str) -> Tuple[Optional[float], str, str]:
    """
    Extract size information from product name.

    Returns:
        (numeric_value, unit, display_string)
        e.g., (3.5, "g", "3.5g (1/8oz)")
    """
    if not raw_name:
        return None, "", "Unknown"

    name_lower = raw_name.lower()
    cat_lower = (category or '').lower()

    # Check for mg sizes first (vapes, edibles)
    mg_match = re.search(r'(\d{2,4})\s*mg', name_lower)
    if mg_match:
        mg = int(mg_match.group(1))
        if mg in [300, 500, 1000, 2000]:
            displays = {300: "300mg (0.3g)", 500: "500mg (0.5g)",
                       1000: "1000mg (1g)", 2000: "2000mg (2g)"}
            return mg, "mg", displays.get(mg, f"{mg}mg")
        return mg, "mg", f"{mg}mg"

    # Check for gram sizes
    g_match = re.search(r'(\d+\.?\d*)\s*g(?:ram)?s?\b', name_lower)
    if g_match:
        grams = float(g_match.group(1))
        displays = {1.0: "1g", 3.5: "3.5g (1/8oz)", 7.0: "7g (1/4oz)",
                   14.0: "14g (1/2oz)", 28.0: "28g (1oz)", 0.5: "0.5g",
                   2.0: "2g"}
        return grams, "g", displays.get(grams, f"{grams}g")

    # Check fraction patterns
    frac_patterns = [
        (r'1/8\s*(?:oz)?', 3.5), (r'eighth', 3.5),
        (r'1/4\s*(?:oz)?', 7.0), (r'quarter', 7.0),
        (r'1/2\s*(?:oz)?', 14.0), (r'half\s*(?:oz)?', 14.0),
        (r'(?:full\s+)?oz(?:ounce)?', 28.0),
    ]
    for pattern, grams in frac_patterns:
        if re.search(pattern, name_lower):
            displays = {3.5: "3.5g (1/8oz)", 7.0: "7g (1/4oz)",
                       14.0: "14g (1/2oz)", 28.0: "28g (1oz)"}
            return grams, "g", displays.get(grams, f"{grams}g")

    return None, "", "Unknown"


def extract_pack_count(raw_name: str) -> int:
    """Extract pack count from product name (default 1)."""
    if not raw_name:
        return 1

    match = re.search(r'(\d+)\s*(?:pk|pack|ct|count|pc|piece)', raw_name.lower())
    if match:
        return int(match.group(1))

    # Check for [10pk] style
    bracket_match = re.search(r'\[\s*(\d+)\s*(?:pk|ct)?\s*\]', raw_name.lower())
    if bracket_match:
        return int(bracket_match.group(1))

    return 1


def extract_form_factor(raw_name: str, category: str) -> str:
    """
    Determine the form factor of the product.
    Returns: "flower", "cart", "disposable", "preroll", "edible", "concentrate", "tincture", "topical"
    """
    name_lower = raw_name.lower() if raw_name else ""
    cat_lower = (category or '').lower()

    # Check vape type first
    if 'vape' in cat_lower or 'cart' in cat_lower or 'vaporizer' in cat_lower:
        for pattern in DISPOSABLE_PATTERNS:
            if pattern in name_lower:
                return "disposable"
        for pattern in CARTRIDGE_PATTERNS:
            if pattern in name_lower:
                return "cart"
        # Default to cart if category is vape
        return "cart"

    # Check other categories
    if 'flower' in cat_lower or 'bud' in cat_lower:
        return "flower"
    if 'pre-roll' in cat_lower or 'preroll' in cat_lower or 'pre roll' in cat_lower:
        return "preroll"
    if 'edible' in cat_lower or 'gumm' in cat_lower or 'chocolate' in cat_lower:
        return "edible"
    if 'concentrate' in cat_lower or 'extract' in cat_lower or 'wax' in cat_lower:
        return "concentrate"
    if 'tincture' in cat_lower:
        return "tincture"
    if 'topical' in cat_lower:
        return "topical"

    return "other"


def normalize_brand(raw_brand: str) -> str:
    """Normalize brand name to standard form."""
    if not raw_brand:
        return ""

    brand_lower = raw_brand.lower().strip()
    return BRAND_ALIASES.get(brand_lower, raw_brand.strip())


def generate_normalized_key(base_name: str, brand: str, form_factor: str,
                           size_value: Optional[float], size_unit: str) -> str:
    """
    Generate a unique key for product deduplication.
    Format: brand|base_name|form_factor|size
    """
    parts = [
        normalize_brand(brand).lower(),
        base_name.lower().strip(),
        form_factor,
        f"{size_value}{size_unit}" if size_value else "unknown"
    ]
    return "|".join(parts)


def normalize_product(raw_name: str, raw_brand: str, raw_category: str,
                      raw_description: str = None) -> NormalizedProduct:
    """
    Fully normalize a product for deduplication and analysis.

    Args:
        raw_name: Product name
        raw_brand: Brand name
        raw_category: Product category
        raw_description: Optional product description (used as fallback for size)
    """
    brand = normalize_brand(raw_brand)
    base_name = extract_base_name(raw_name, brand)
    size_value, size_unit, size_display = extract_size(raw_name, raw_category)

    # Fallback: try to get size from description if not in name
    if size_value is None and raw_description:
        size_value, size_unit, size_display = extract_size_from_description(raw_description)

    form_factor = extract_form_factor(raw_name, raw_category)
    pack_count = extract_pack_count(raw_name)

    normalized_key = generate_normalized_key(base_name, brand, form_factor, size_value, size_unit)

    return NormalizedProduct(
        base_name=base_name,
        brand=brand,
        category=raw_category or "",
        size_value=size_value,
        size_unit=size_unit,
        size_display=size_display,
        form_factor=form_factor,
        pack_count=pack_count,
        normalized_key=normalized_key
    )


def get_unique_product_count_sql() -> str:
    """
    SQL to count unique products by normalizing names.
    Groups by brand + base product name (without size info).
    """
    return """
    WITH normalized AS (
        SELECT
            raw_brand,
            -- Extract base name by removing size patterns
            REGEXP_REPLACE(
                REGEXP_REPLACE(
                    REGEXP_REPLACE(
                        raw_name,
                        '\\s*[-|]\\s*\\d+\\.?\\d*\\s*(g|mg|gram)s?\\s*$', '', 'i'
                    ),
                    '\\s*\\[\\d+\\.?\\d*\\s*(g|mg)\\]', '', 'i'
                ),
                '\\s*\\d+\\.?\\d*\\s*(g|mg|gram)s?\\s*$', '', 'i'
            ) as base_name,
            dispensary_id
        FROM raw_menu_item
        WHERE raw_brand IS NOT NULL
    )
    SELECT
        raw_brand as brand,
        COUNT(DISTINCT base_name) as unique_products,
        COUNT(DISTINCT dispensary_id) as store_count
    FROM normalized
    GROUP BY raw_brand
    ORDER BY unique_products DESC
    """


# Test function
if __name__ == "__main__":
    test_products = [
        ("&Shine Pineapple Express All in One Vape Pen 2000mg", "&Shine", "Vapes"),
        ("Pineapple Express | 3.5g", "Curio Wellness", "Flower"),
        ("Pineapple Express 1/8 oz", "Curio", "Flower"),
        ("Baccio Gelato", "Savvy", "Flower"),
        ("Blue Dream Cart 500mg", "Select", "Vapes"),
        ("Blue Dream Disposable [1g]", "Select", "Vapes"),
        ("Elderberry Hibiscus [10pk] (100mg)", "Curio Wellness", "Edibles"),
    ]

    for raw_name, brand, category in test_products:
        result = normalize_product(raw_name, brand, category)
        print(f"\nInput: {raw_name}")
        print(f"  Base: {result.base_name}")
        print(f"  Size: {result.size_display}")
        print(f"  Form: {result.form_factor}")
        print(f"  Key:  {result.normalized_key}")
