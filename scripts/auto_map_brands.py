#!/usr/bin/env python3
"""
Auto-map brands by searching for parent company information.
Uses web search to find brand ownership for Maryland cannabis brands.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from core.db import get_engine
import time
import re

# Known brand mappings for Maryland market (from research)
# Only exact matches to avoid false positives
KNOWN_MAPPINGS = {
    # GTI (Green Thumb Industries)
    "GTI": ["RYTHM", "DOGWALKERS", "&SHINE", "INCREDIBLES", "BEBOE", "GOOD GREEN"],

    # Verano Holdings
    "VERANO": ["VERANO", "VERANO RESERVE", "SAVVY", "AVEXIA", "ENCORE", "ENCORE EDIBLES", "MUV", "EXTRA SAVVY"],

    # Cresco Labs
    "CRESCO LABS": ["CRESCO", "CRESCO LABS", "HIGH SUPPLY", "GOOD NEWS", "MINDY'S", "REMEDI", "WONDER WELLNESS", "WONDER WELLNESS CO."],

    # Curaleaf
    "CURALEAF": ["CURALEAF", "SELECT", "GRASSROOTS"],

    # Trulieve
    "TRULIEVE": ["TRULIEVE", "CULTIVAR COLLECTION", "MODERN FLOWER"],

    # Cookies
    "COOKIES": ["COOKIES", "LEMONNADE", "GRANDIFLORA", "POWERZZZUP"],

    # Ascend Wellness Holdings (AWH)
    "ASCEND WELLNESS": ["OZONE", "OZONE RESERVE", "SIMPLY HERB", "COMMON GROUND"],

    # Columbia Care / Cannabist
    "COLUMBIA CARE": ["SEED & STRAIN", "CLASSIX", "PRESS", "AMBER"],

    # CULTA (Maryland local)
    "CULTA": ["CULTA", "DOSIDOS", "POOCHIE LOVE"],

    # Curio Wellness (Maryland local)
    "CURIO WELLNESS": ["CURIO", "CURIO WELLNESS", "FAR OUT", "STRANE"],

    # Evermore Cannabis (Maryland local)
    "EVERMORE": ["EVERMORE", "EVERMORE CANNABIS", "EVERMORE CANNABIS COMPANY"],

    # Sunmed (Maryland)
    "SUNMED": ["SUNMED", "SUN MED", "SUNMED GROWERS", "SUNMED LABS"],

    # Nature's Heritage
    "NATURE'S HERITAGE": ["NATURE'S HERITAGE", "NATURES HERITAGE"],

    # District Cannabis (Maryland/DC)
    "DISTRICT CANNABIS": ["DISTRICT CANNABIS", "DISTRICT CANNABIS CO", "DC CANNABIS"],

    # gLeaf (Maryland)
    "GLEAF": ["GLEAF", "G LEAF"],

    # Holistic Industries
    "HOLISTIC INDUSTRIES": ["LIBERTY"],

    # HMS Health (Maryland)
    "HMS HEALTH": ["GARCIA HAND PICKED"],

    # Kind Tree / TerrAscend
    "TERRASCEND": ["KIND TREE", "KINDTREE", "ILERA", "GAGE"],

    # 1937 Farms
    "1937 FARMS": ["1937", "1937 FARMS"],

    # Harvest (now Trulieve)
    "HARVEST/TRULIEVE": ["HARVEST", "ROLL ONE"],

    # Vireo Health
    "VIREO": ["VIREO", "1906"],

    # Wana Brands
    "WANA": ["WANA", "WANA BRANDS", "WANA QUICK"],

    # KIVA Confections
    "KIVA": ["KIVA", "PETRA", "LOST FARM", "LOST FARMS", "CAMINO"],

    # Wyld
    "WYLD": ["WYLD"],

    # PharmaCann
    "PHARMACANN": ["MATTER", "MATTER."],

    # Jushi Holdings
    "JUSHI": ["THE BANK", "SÈCHE"],

    # AYR Wellness
    "AYR WELLNESS": ["KYND", "LEVIA", "ENTOURAGE"],

    # Tikun Olam
    "TIKUN OLAM": ["TIKUN"],

    # Fade Co.
    "FADE CO.": ["FADE CO", "FADE CO."],

    # Hellavated
    "HELLAVATED": ["HELLAVATED"],

    # Betty's Eddies
    "BETTY'S EDDIES": ["BETTY'S EDDIES", "BETTYS EDDIES"],

    # Dixie Brands
    "DIXIE": ["DIXIE", "DIXIE ELIXIRS"],

    # Cheeba Chews
    "CHEEBA CHEWS": ["CHEEBA CHEWS"],

    # Mary's Medicinals
    "MARY'S MEDICINALS": ["MARY'S MEDICINALS", "MARYS MEDICINALS"],

    # Dosist
    "DOSIST": ["DOSIST"],

    # PAX Labs
    "PAX LABS": ["PAX"],

    # STIIIZY
    "STIIIZY": ["STIIIZY", "STIIZY"],

    # Raw Garden
    "RAW GARDEN": ["RAW GARDEN"],

    # Lowell Herb Co.
    "LOWELL": ["LOWELL", "LOWELL HERB", "LOWELL FARMS"],

    # Old Pal
    "OLD PAL": ["OLD PAL", "OLD PAL CANNABIS"],

    # Alien Labs / Connected
    "ALIEN LABS": ["ALIEN LABS", "CONNECTED"],

    # 710 Labs (independent)
    "710 LABS": ["710 LABS"],

    # Green Dot Labs (independent)
    "GREEN DOT LABS": ["GREEN DOT LABS"],

    # Aeriz
    "AERIZ": ["AERIZ"],

    # Rev Clinics
    "REV CLINICS": ["REV CLINICS", "REV"],

    # Revolution
    "REVOLUTION": ["REVOLUTION", "REV"],

    # Bedford Grow
    "BEDFORD GROW": ["BEDFORD GROW"],

    # Floracal
    "FLORACAL": ["FLORACAL"],

    # Pure Beauty
    "PURE BEAUTY": ["PURE BEAUTY"],

    # CANN
    "CANN": ["CANN"],

    # Bloom County
    "BLOOM COUNTY": ["BLOOM COUNTY"],
}


def get_unmapped_brands(min_products: int = 5):
    """Get brands that need mapping."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT brand_upper as brand, product_count
            FROM (
                SELECT UPPER(r.raw_brand) as brand_upper, COUNT(*) as product_count
                FROM raw_menu_item r
                JOIN dispensary d ON r.dispensary_id = d.dispensary_id
                WHERE r.raw_brand IS NOT NULL AND r.raw_brand != ''
                GROUP BY UPPER(r.raw_brand)
                HAVING COUNT(*) >= :min_products
            ) brands
            LEFT JOIN brand_hierarchy bh ON brands.brand_upper = UPPER(bh.child_brand)
            WHERE bh.child_brand IS NULL
            ORDER BY product_count DESC
        """), {"min_products": min_products})
        return [(row[0], row[1]) for row in result]


def add_mapping(master_brand: str, child_brand: str, notes: str = None):
    """Add a brand mapping."""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO brand_hierarchy (master_brand, child_brand, notes)
            VALUES (:master, :child, :notes)
            ON CONFLICT (child_brand) DO UPDATE SET
                master_brand = EXCLUDED.master_brand,
                notes = EXCLUDED.notes,
                updated_at = NOW()
        """), {"master": master_brand.upper(), "child": child_brand.upper(), "notes": notes})
        conn.commit()


def find_best_match(brand: str) -> tuple:
    """Find the best master brand match for a given brand - EXACT MATCHES ONLY."""
    brand_upper = brand.upper().strip()

    # Only do exact matches to avoid false positives
    for master, children in KNOWN_MAPPINGS.items():
        for child in children:
            if brand_upper == child.upper():
                return master, f"Exact match: {child}"

    return None, None


def auto_map_brands(dry_run: bool = True, min_products: int = 10):
    """Auto-map brands using known mappings."""
    unmapped = get_unmapped_brands(min_products)
    print(f"\nFound {len(unmapped)} unmapped brands with {min_products}+ products\n")

    mapped_count = 0
    not_found = []

    for brand, count in unmapped:
        master, reason = find_best_match(brand)

        if master:
            mapped_count += 1
            if dry_run:
                print(f"[DRY RUN] Would map: {brand} ({count} products) -> {master} ({reason})")
            else:
                add_mapping(master, brand, f"Auto-mapped: {reason}")
                print(f"[MAPPED] {brand} ({count} products) -> {master} ({reason})")
        else:
            not_found.append((brand, count))

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Total unmapped brands: {len(unmapped)}")
    print(f"  Successfully matched: {mapped_count}")
    print(f"  Could not match: {len(not_found)}")

    if not_found:
        print(f"\nBrands that need manual mapping (top 50):")
        for brand, count in sorted(not_found, key=lambda x: -x[1])[:50]:
            print(f"  - {brand} ({count} products)")

    return mapped_count, not_found


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Auto-map cannabis brands to parent companies")
    parser.add_argument("--apply", action="store_true", help="Actually apply mappings (default is dry run)")
    parser.add_argument("--min-products", type=int, default=10, help="Minimum product count to consider")
    args = parser.parse_args()

    print("Cannabis Brand Auto-Mapping")
    print("="*60)

    if args.apply:
        print("MODE: APPLYING CHANGES")
    else:
        print("MODE: DRY RUN (use --apply to actually map)")

    mapped, not_found = auto_map_brands(dry_run=not args.apply, min_products=args.min_products)
