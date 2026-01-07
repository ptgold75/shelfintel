# core/size_utils.py
"""Size normalization utilities for cannabis products."""

import re
from typing import Optional, Tuple

# Standard size mappings (all normalized to grams)
FLOWER_SIZE_MAP = {
    # 1 gram
    '1g': 1.0, '1 g': 1.0, '1gram': 1.0, '1 gram': 1.0, 'gram': 1.0,
    # 3.5 grams / eighth
    '3.5g': 3.5, '3.5 g': 3.5, '3.5gram': 3.5, '3.5 gram': 3.5, '3.5grams': 3.5,
    'eighth': 3.5, '1/8': 3.5, '1/8oz': 3.5, '1/8 oz': 3.5, '⅛': 3.5,
    '8th': 3.5, 'an eighth': 3.5,
    # 7 grams / quarter
    '7g': 7.0, '7 g': 7.0, '7gram': 7.0, '7 gram': 7.0, '7grams': 7.0,
    'quarter': 7.0, '1/4': 7.0, '1/4oz': 7.0, '1/4 oz': 7.0, 'q oz': 7.0,
    '¼': 7.0, 'quarter oz': 7.0, 'quarter ounce': 7.0,
    # 14 grams / half ounce
    '14g': 14.0, '14 g': 14.0, '14gram': 14.0, '14 gram': 14.0, '14grams': 14.0,
    'half': 14.0, 'half oz': 14.0, 'half ounce': 14.0, '1/2': 14.0,
    '1/2oz': 14.0, '1/2 oz': 14.0, '½': 14.0, 'half o': 14.0,
    # 28 grams / ounce
    '28g': 28.0, '28 g': 28.0, '28gram': 28.0, '28 gram': 28.0, '28grams': 28.0,
    'ounce': 28.0, 'oz': 28.0, '1oz': 28.0, '1 oz': 28.0, 'full oz': 28.0,
    'zip': 28.0, 'o': 28.0,
}

# Vape/cartridge sizes (in mg)
VAPE_SIZE_MAP = {
    # 300mg
    '300mg': 300, '300 mg': 300, '.3g': 300, '0.3g': 300, '.3 g': 300,
    # 500mg / half gram
    '500mg': 500, '500 mg': 500, '.5g': 500, '0.5g': 500, '.5 g': 500,
    'half gram': 500, 'half g': 500, '1/2g': 500, '1/2 g': 500,
    # 1000mg / full gram
    '1000mg': 1000, '1000 mg': 1000, '1g': 1000, '1 g': 1000,
    'full gram': 1000, 'gram': 1000, '1gram': 1000,
    # 2000mg / 2 gram
    '2000mg': 2000, '2000 mg': 2000, '2g': 2000, '2 g': 2000,
    '2gram': 2000, '2 gram': 2000,
}

# Edible sizes (in mg THC)
EDIBLE_SIZE_MAP = {
    '5mg': 5, '10mg': 10, '20mg': 20, '25mg': 25, '50mg': 50,
    '100mg': 100, '200mg': 200, '250mg': 250, '500mg': 500, '1000mg': 1000,
}

def normalize_flower_size(name: str) -> Tuple[Optional[float], str]:
    """
    Extract and normalize flower size from product name.

    Returns:
        Tuple of (grams as float, display string)
        e.g., (3.5, "3.5g (1/8oz)")
    """
    if not name:
        return None, "Unknown"

    name_lower = name.lower()

    # Try exact matches first
    for pattern, grams in sorted(FLOWER_SIZE_MAP.items(), key=lambda x: -len(x[0])):
        if pattern in name_lower:
            return grams, _format_flower_size(grams)

    # Try regex patterns
    # Match patterns like "3.5g", "14 g", "28grams"
    gram_match = re.search(r'(\d+\.?\d*)\s*(?:g(?:ram)?s?)\b', name_lower)
    if gram_match:
        grams = float(gram_match.group(1))
        if grams in [1, 3.5, 7, 14, 28]:
            return grams, _format_flower_size(grams)
        return grams, f"{grams}g"

    # Match fraction patterns like "1/8 oz", "1/4oz"
    frac_match = re.search(r'(\d)/(\d)\s*(?:oz|ounce)?', name_lower)
    if frac_match:
        num, denom = int(frac_match.group(1)), int(frac_match.group(2))
        oz = num / denom
        grams = oz * 28
        return grams, _format_flower_size(grams)

    return None, "Unknown"

def _format_flower_size(grams: float) -> str:
    """Format flower size as standard display string."""
    if grams == 1:
        return "1g"
    elif grams == 3.5:
        return "3.5g (1/8oz)"
    elif grams == 7:
        return "7g (1/4oz)"
    elif grams == 14:
        return "14g (1/2oz)"
    elif grams == 28:
        return "28g (1oz)"
    else:
        return f"{grams}g"

def normalize_vape_size(name: str) -> Tuple[Optional[int], str]:
    """
    Extract and normalize vape/cartridge size from product name.

    Returns:
        Tuple of (mg as int, display string)
        e.g., (500, "500mg (0.5g)")
    """
    if not name:
        return None, "Unknown"

    name_lower = name.lower()

    # Check for disposable vs cartridge
    is_disposable = any(x in name_lower for x in ['disposable', 'all-in-one', 'all in one', 'aio', 'pod'])
    prefix = "Disp " if is_disposable else "Cart "

    # Try exact matches first
    for pattern, mg in sorted(VAPE_SIZE_MAP.items(), key=lambda x: -len(x[0])):
        if pattern in name_lower:
            return mg, prefix + _format_vape_size(mg)

    # Try regex patterns
    # Match mg patterns like "500mg", "1000 mg"
    mg_match = re.search(r'(\d{3,4})\s*mg', name_lower)
    if mg_match:
        mg = int(mg_match.group(1))
        return mg, prefix + _format_vape_size(mg)

    # Match gram patterns for vapes like "1g", ".5g", "2g"
    g_match = re.search(r'(\d*\.?\d+)\s*g(?:ram)?(?!\s*(?:ummy|el))', name_lower)  # Avoid matching "gummy"
    if g_match:
        grams = float(g_match.group(1))
        mg = int(grams * 1000)
        if mg in [300, 500, 1000, 2000]:
            return mg, prefix + _format_vape_size(mg)

    return None, prefix + "Unknown"

def _format_vape_size(mg: int) -> str:
    """Format vape size as standard display string."""
    if mg == 300:
        return "300mg (0.3g)"
    elif mg == 500:
        return "500mg (0.5g)"
    elif mg == 1000:
        return "1000mg (1g)"
    elif mg == 2000:
        return "2000mg (2g)"
    else:
        return f"{mg}mg"

def normalize_preroll_size(name: str) -> Tuple[Optional[float], Optional[int], str]:
    """
    Extract and normalize pre-roll size from product name.

    Returns:
        Tuple of (grams per joint, pack count, display string)
        e.g., (1.0, 5, "1g (5pk)")
    """
    if not name:
        return None, None, "Unknown"

    name_lower = name.lower()

    # Extract pack count
    pack_match = re.search(r'(\d+)\s*(?:pk|pack|ct|count|pc|x)', name_lower)
    pack_count = int(pack_match.group(1)) if pack_match else 1

    # Extract per-joint size
    grams = None

    # Match patterns like "1g", ".5g", "2g"
    g_match = re.search(r'(\d*\.?\d+)\s*g(?:ram)?', name_lower)
    if g_match:
        grams = float(g_match.group(1))

    # Common size keywords
    if grams is None:
        if 'half gram' in name_lower or 'half g' in name_lower:
            grams = 0.5
        elif 'full gram' in name_lower:
            grams = 1.0

    # Format display string
    if grams and pack_count > 1:
        return grams, pack_count, f"{grams}g ({pack_count}pk)"
    elif grams:
        return grams, pack_count, f"{grams}g"
    elif pack_count > 1:
        return None, pack_count, f"({pack_count}pk)"

    return None, None, "Unknown"

def normalize_edible_size(name: str) -> Tuple[Optional[int], Optional[int], str]:
    """
    Extract and normalize edible size from product name.

    Returns:
        Tuple of (mg per piece, piece count, display string)
        e.g., (10, 10, "10mg x10 (100mg total)")
    """
    if not name:
        return None, None, "Unknown"

    name_lower = name.lower()

    # Try to find total mg
    total_match = re.search(r'(\d{2,4})\s*mg', name_lower)
    total_mg = int(total_match.group(1)) if total_match else None

    # Try to find piece count
    count_match = re.search(r'(\d+)\s*(?:pc|piece|ct|count|pack|pk|x\d)', name_lower)
    piece_count = int(count_match.group(1)) if count_match else None

    # Calculate per-piece if we have both
    if total_mg and piece_count and piece_count > 1:
        per_piece = total_mg // piece_count
        return per_piece, piece_count, f"{per_piece}mg x{piece_count} ({total_mg}mg)"
    elif total_mg:
        return total_mg, 1, f"{total_mg}mg"

    return None, None, "Unknown"

def get_normalized_size(name: str, category: str) -> Tuple[Optional[float], str]:
    """
    Get normalized size based on category.

    Returns:
        Tuple of (numeric value for sorting, display string)
    """
    cat_lower = (category or '').lower()

    if 'flower' in cat_lower or 'bud' in cat_lower:
        grams, display = normalize_flower_size(name)
        return grams, display

    elif 'vape' in cat_lower or 'cart' in cat_lower or 'vaporizer' in cat_lower:
        mg, display = normalize_vape_size(name)
        return mg / 1000 if mg else None, display  # Convert to grams for comparison

    elif 'pre-roll' in cat_lower or 'pre roll' in cat_lower or 'preroll' in cat_lower:
        grams, count, display = normalize_preroll_size(name)
        total = (grams or 0) * (count or 1)
        return total if total > 0 else None, display

    elif 'edible' in cat_lower or 'gumm' in cat_lower or 'chocolate' in cat_lower:
        mg, count, display = normalize_edible_size(name)
        return mg, display

    elif 'concentrate' in cat_lower or 'extract' in cat_lower or 'wax' in cat_lower:
        # Concentrates often use gram sizes like flower
        grams, display = normalize_flower_size(name)
        return grams, display

    return None, "N/A"

def get_size_sql_case() -> str:
    """
    Return SQL CASE statement for normalizing sizes in queries.
    This normalizes to grams for consistent sorting/grouping.
    """
    return """
    CASE
        -- Flower sizes (extract grams)
        WHEN raw_name ILIKE '%28g%' OR raw_name ILIKE '%28 g%' OR raw_name ILIKE '%1oz%' OR raw_name ILIKE '%ounce%' THEN 28.0
        WHEN raw_name ILIKE '%14g%' OR raw_name ILIKE '%14 g%' OR raw_name ILIKE '%half oz%' OR raw_name ILIKE '%1/2 oz%' OR raw_name ILIKE '%1/2oz%' THEN 14.0
        WHEN raw_name ILIKE '%7g%' OR raw_name ILIKE '%7 g%' OR raw_name ILIKE '%quarter%' OR raw_name ILIKE '%1/4 oz%' OR raw_name ILIKE '%1/4oz%' THEN 7.0
        WHEN raw_name ILIKE '%3.5g%' OR raw_name ILIKE '%3.5 g%' OR raw_name ILIKE '%eighth%' OR raw_name ILIKE '%1/8%' THEN 3.5
        WHEN raw_name ILIKE '%1g%' OR raw_name ILIKE '%1 g%' OR raw_name ILIKE '%gram%' THEN 1.0

        -- Vape sizes (convert to grams)
        WHEN raw_name ILIKE '%2000mg%' OR raw_name ILIKE '%2g%' THEN 2.0
        WHEN raw_name ILIKE '%1000mg%' OR raw_name ILIKE '%1g%' THEN 1.0
        WHEN raw_name ILIKE '%500mg%' OR raw_name ILIKE '%.5g%' OR raw_name ILIKE '%half gram%' THEN 0.5
        WHEN raw_name ILIKE '%300mg%' OR raw_name ILIKE '%.3g%' THEN 0.3

        ELSE NULL
    END
    """

def get_size_display_sql() -> str:
    """
    Return SQL CASE statement for size display strings.
    """
    return """
    CASE
        -- Flower
        WHEN raw_name ILIKE '%28g%' OR raw_name ILIKE '%28 g%' OR raw_name ILIKE '%1oz%' OR raw_name ILIKE '%ounce%' THEN '28g (1oz)'
        WHEN raw_name ILIKE '%14g%' OR raw_name ILIKE '%14 g%' OR raw_name ILIKE '%half oz%' OR raw_name ILIKE '%1/2%' THEN '14g (1/2oz)'
        WHEN raw_name ILIKE '%7g%' OR raw_name ILIKE '%7 g%' OR raw_name ILIKE '%quarter%' OR raw_name ILIKE '%1/4%' THEN '7g (1/4oz)'
        WHEN raw_name ILIKE '%3.5g%' OR raw_name ILIKE '%3.5 g%' OR raw_name ILIKE '%eighth%' OR raw_name ILIKE '%1/8%' THEN '3.5g (1/8oz)'
        WHEN raw_name ILIKE '%1g %' OR raw_name ILIKE '% 1g%' OR raw_name ILIKE '%gram%' THEN '1g'

        -- Vape
        WHEN raw_name ILIKE '%2000mg%' OR raw_name ILIKE '% 2g%' THEN '2000mg (2g)'
        WHEN raw_name ILIKE '%1000mg%' OR raw_name ILIKE '% 1g%' THEN '1000mg (1g)'
        WHEN raw_name ILIKE '%500mg%' OR raw_name ILIKE '%.5g%' OR raw_name ILIKE '%half gram%' THEN '500mg (0.5g)'
        WHEN raw_name ILIKE '%300mg%' OR raw_name ILIKE '%.3g%' THEN '300mg (0.3g)'

        ELSE 'Unknown'
    END
    """
