# core/category_utils.py
"""Category normalization utilities for consistent reporting."""

# Mapping of raw category names to normalized names
CATEGORY_MAPPING = {
    # Flower
    'flower': 'Flower',
    'Flower': 'Flower',
    'Infused Flower': 'Flower',

    # Edibles
    'edible': 'Edibles',
    'Edible': 'Edibles',
    'Edibles': 'Edibles',
    'Beverages': 'Edibles',

    # Vapes/Carts
    'vape': 'Vapes',
    'Vapes': 'Vapes',
    'Vaporizers': 'Vapes',
    'Cartridges': 'Vapes',
    'All In One Cartridges': 'Vapes',

    # Pre-Rolls
    'pre-roll': 'Pre-Rolls',
    'Pre-Rolls': 'Pre-Rolls',
    'Infused Pre-Rolls': 'Pre-Rolls',

    # Concentrates
    'extract': 'Concentrates',
    'Concentrate': 'Concentrates',
    'Concentrates': 'Concentrates',

    # Accessories
    'gear': 'Accessories',
    'Accessories': 'Accessories',
    'Smoking Devices': 'Accessories',
    'merch': 'Accessories',
    'Apparel': 'Accessories',
    'Ancillary': 'Accessories',

    # Topicals
    'topical': 'Topicals',
    'Topicals': 'Topicals',

    # Tinctures
    'tincture': 'Tinctures',
    'Tinctures': 'Tinctures',

    # CBD
    'Hemp CBD': 'CBD',
    'CBD': 'CBD',
}

# Canonical category order for display
CATEGORY_ORDER = [
    'Flower',
    'Pre-Rolls',
    'Vapes',
    'Edibles',
    'Concentrates',
    'Topicals',
    'Tinctures',
    'Accessories',
    'CBD',
    'Other'
]


def normalize_category(raw_category: str) -> str:
    """Normalize a category name to its canonical form.

    Args:
        raw_category: The raw category string from scrape

    Returns:
        Normalized category name
    """
    if not raw_category:
        return 'Other'

    # Check direct mapping first
    if raw_category in CATEGORY_MAPPING:
        return CATEGORY_MAPPING[raw_category]

    # Try case-insensitive lookup
    raw_lower = raw_category.lower()
    for key, value in CATEGORY_MAPPING.items():
        if key.lower() == raw_lower:
            return value

    # Fuzzy matching for common patterns
    if 'flower' in raw_lower:
        return 'Flower'
    if 'edible' in raw_lower or 'gumm' in raw_lower or 'chocolate' in raw_lower:
        return 'Edibles'
    if 'vape' in raw_lower or 'cart' in raw_lower or 'pod' in raw_lower:
        return 'Vapes'
    if 'pre-roll' in raw_lower or 'preroll' in raw_lower or 'joint' in raw_lower:
        return 'Pre-Rolls'
    if 'concentrate' in raw_lower or 'extract' in raw_lower or 'wax' in raw_lower or 'shatter' in raw_lower:
        return 'Concentrates'
    if 'topical' in raw_lower or 'lotion' in raw_lower or 'balm' in raw_lower:
        return 'Topicals'
    if 'tincture' in raw_lower:
        return 'Tinctures'
    if 'accessor' in raw_lower or 'gear' in raw_lower or 'merch' in raw_lower:
        return 'Accessories'
    if 'cbd' in raw_lower or 'hemp' in raw_lower:
        return 'CBD'

    return 'Other'


def get_normalized_category_sql() -> str:
    """Return a SQL CASE statement for category normalization.

    Use this in SQL queries for consistent category grouping.
    Uses ILIKE for fuzzy matching to catch variations.

    IMPORTANT: Check product name first to override miscategorized items.
    E.g., "Ice Widow 14g" marked as "Vapes" is clearly Flower.
    """
    return """
    CASE
        -- Override: Flower weights in name = Flower (regardless of category)
        WHEN raw_name ~* '(^|\\s)(28|14|7|3\\.5)\\s*g($|\\s|\\))' THEN 'Flower'
        WHEN raw_name ILIKE '%quarter%' OR raw_name ILIKE '%eighth%' OR raw_name ILIKE '%half oz%' THEN 'Flower'

        -- Standard category matching
        WHEN raw_category ILIKE '%flower%' OR raw_category ILIKE '%bud%' THEN 'Flower'
        WHEN raw_category ILIKE '%pre-roll%' OR raw_category ILIKE '%preroll%' OR raw_category ILIKE '%pre roll%' OR raw_category ILIKE '%joint%' THEN 'Pre-Rolls'
        WHEN raw_category ILIKE '%vape%' OR raw_category ILIKE '%cart%' OR raw_category ILIKE '%pod%' THEN 'Vapes'
        WHEN raw_category ILIKE '%edible%' OR raw_category ILIKE '%gumm%' OR raw_category ILIKE '%chocolate%' OR raw_category ILIKE '%beverage%' OR raw_category ILIKE '%drink%' OR raw_category ILIKE '%candy%' THEN 'Edibles'
        WHEN raw_category ILIKE '%concentrate%' OR raw_category ILIKE '%extract%' OR raw_category ILIKE '%dab%' OR raw_category ILIKE '%wax%' OR raw_category ILIKE '%shatter%' OR raw_category ILIKE '%rosin%' OR raw_category ILIKE '%resin%' THEN 'Concentrates'
        WHEN raw_category ILIKE '%topical%' OR raw_category ILIKE '%cream%' OR raw_category ILIKE '%balm%' OR raw_category ILIKE '%lotion%' OR raw_category ILIKE '%salve%' THEN 'Topicals'
        WHEN raw_category ILIKE '%tincture%' OR raw_category ILIKE '%oil%' OR raw_category ILIKE '%sublingual%' OR raw_category ILIKE '%rso%' THEN 'Tinctures'
        WHEN raw_category ILIKE '%accessor%' OR raw_category ILIKE '%gear%' OR raw_category ILIKE '%pipe%' OR raw_category ILIKE '%paper%' OR raw_category ILIKE '%grinder%' OR raw_category ILIKE '%merch%' OR raw_category ILIKE '%apparel%' THEN 'Accessories'
        WHEN raw_category ILIKE '%cbd%' OR raw_category ILIKE '%hemp%' THEN 'CBD'
        ELSE 'Other'
    END
    """
