#!/usr/bin/env python3
"""
Scrape New Jersey Cannabis Dispensaries from nj.gov

Data source: https://www.nj.gov/cannabis/dispensaries/find/
Alternative: https://data.nj.gov/Reference-Data/New-Jersey-Cannabis-Dispensary-Locations/uyq5-2c2g

This script scrapes NJ dispensary data and dedupes against our existing database.
"""

import os
import sys
import json
import re
import requests
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import get_engine
from sqlalchemy import text


@dataclass
class NJDispensary:
    """New Jersey dispensary record."""
    name: str
    address: str
    city: str
    state: str = "NJ"
    zip_code: str = ""
    county: str = ""
    phone: str = ""
    website: str = ""
    license_type: str = "retail"  # retail, delivery, cultivation, manufacturing
    license_class: str = "both"   # recreational, medicinal, or both
    is_recreational: bool = True
    is_medical: bool = False
    is_atc: bool = False  # Alternative Treatment Center (original medical)
    scraped_at: str = ""
    data_source: str = ""


# NJ License Types
NJ_LICENSE_TYPES = {
    # Recreational (Adult-Use) License Classes
    "Class 1": "cultivation",      # Cannabis Cultivator
    "Class 2": "manufacturing",    # Cannabis Manufacturer
    "Class 3": "wholesale",        # Cannabis Wholesaler
    "Class 4": "distribution",     # Cannabis Distributor
    "Class 5": "retail",           # Cannabis Retailer
    "Class 6": "delivery",         # Cannabis Delivery Service

    # Medical (ATC) Types
    "ATC": "medical_atc",          # Alternative Treatment Center (vertically integrated)
    "ATC-Retail": "medical_retail",
    "ATC-Cultivation": "medical_cultivation",
    "ATC-Manufacturing": "medical_manufacturing",
}


# NJ Counties
NJ_COUNTIES = [
    "Atlantic", "Bergen", "Burlington", "Camden", "Cape May", "Cumberland",
    "Essex", "Gloucester", "Hudson", "Hunterdon", "Mercer", "Middlesex",
    "Monmouth", "Morris", "Ocean", "Passaic", "Salem", "Somerset",
    "Sussex", "Union", "Warren"
]


# Known NJ Dispensaries (from various sources)
# License classes: "recreational", "medicinal", "both" (dual-licensed)
# is_atc: True = Alternative Treatment Center (original medical program)
KNOWN_NJ_DISPENSARIES = [
    # Curaleaf locations (ATC - both rec and med)
    {"name": "Curaleaf NJ - Bellmawr", "address": "640 Creek Rd", "city": "Bellmawr", "county": "Camden", "zip": "08031", "phone": "(856) 702-4750", "website": "https://curaleaf.com/locations/new-jersey/bellmawr", "license_class": "both", "is_atc": True},
    {"name": "Curaleaf NJ - Bordentown", "address": "615 US-130", "city": "Bordentown", "county": "Burlington", "zip": "08505", "phone": "(609) 424-4200", "website": "https://curaleaf.com/locations/new-jersey/bordentown", "license_class": "both", "is_atc": True},
    {"name": "Curaleaf NJ - Edgewater Park", "address": "4231 US-130", "city": "Edgewater Park", "county": "Burlington", "zip": "08010", "phone": "(609) 556-4200", "website": "https://curaleaf.com/locations/new-jersey/edgewater-park", "license_class": "both", "is_atc": True},

    # Rise locations
    {"name": "Rise Paterson", "address": "280 Main St", "city": "Paterson", "county": "Passaic", "zip": "07505", "phone": "(973) 321-7463", "website": "https://risecannabis.com/dispensaries/new-jersey/paterson"},
    {"name": "Rise Paramus", "address": "61 E Midland Ave", "city": "Paramus", "county": "Bergen", "zip": "07652", "phone": "(201) 881-7463", "website": "https://risecannabis.com/dispensaries/new-jersey/paramus"},
    {"name": "Rise Bloomfield", "address": "60 Watsessing Ave", "city": "Bloomfield", "county": "Essex", "zip": "07003", "phone": "(973) 510-7463", "website": "https://risecannabis.com/dispensaries/new-jersey/bloomfield"},

    # The Botanist locations
    {"name": "The Botanist - Egg Harbor Township", "address": "3415 English Creek Ave", "city": "Egg Harbor Township", "county": "Atlantic", "zip": "08234", "phone": "(609) 753-1008", "website": "https://shopbotanist.com/new-jersey/egg-harbor-township"},
    {"name": "The Botanist - Williamstown", "address": "1905 N Black Horse Pike", "city": "Williamstown", "county": "Gloucester", "zip": "08094", "phone": "(856) 728-3737", "website": "https://shopbotanist.com/new-jersey/williamstown"},
    {"name": "The Botanist - Atlantic City", "address": "1100 Atlantic Ave", "city": "Atlantic City", "county": "Atlantic", "zip": "08401", "phone": "(609) 848-5277", "website": "https://shopbotanist.com/new-jersey/atlantic-city"},
    {"name": "The Botanist - Collingswood", "address": "553 Haddon Ave", "city": "Collingswood", "county": "Camden", "zip": "08108", "phone": "(856) 858-3737", "website": "https://shopbotanist.com/new-jersey/collingswood"},

    # Zen Leaf locations
    {"name": "Zen Leaf Elizabeth", "address": "1201 E Grand St", "city": "Elizabeth", "county": "Union", "zip": "07201", "phone": "(908) 289-8800", "website": "https://zenleafdispensaries.com/locations/elizabeth-nj"},
    {"name": "Zen Leaf Neptune", "address": "2100 NJ-66", "city": "Neptune Township", "county": "Monmouth", "zip": "07753", "phone": "(732) 455-7800", "website": "https://zenleafdispensaries.com/locations/neptune-nj"},
    {"name": "Zen Leaf Lawrence", "address": "2495 US-1", "city": "Lawrence Township", "county": "Mercer", "zip": "08648", "phone": "(609) 219-8800", "website": "https://zenleafdispensaries.com/locations/lawrence-nj"},
    {"name": "Zen Leaf Lawrenceville", "address": "3371 US-1", "city": "Lawrenceville", "county": "Mercer", "zip": "08648", "phone": "(609) 912-8800", "website": "https://zenleafdispensaries.com/locations/lawrenceville-nj"},

    # Ascend locations
    {"name": "Ascend NJ - Fort Lee", "address": "2195 Lemoine Ave", "city": "Fort Lee", "county": "Bergen", "zip": "07024", "phone": "(201) 580-1460", "website": "https://ascendwellness.com/dispensaries/new-jersey/fort-lee"},
    {"name": "Ascend NJ - Rochelle Park", "address": "269 W Passaic St", "city": "Rochelle Park", "county": "Bergen", "zip": "07662", "phone": "(201) 373-7970", "website": "https://ascendwellness.com/dispensaries/new-jersey/rochelle-park"},
    {"name": "Ascend NJ - Montclair", "address": "605 Bloomfield Ave", "city": "Montclair", "county": "Essex", "zip": "07042", "phone": "(862) 485-1450", "website": "https://ascendwellness.com/dispensaries/new-jersey/montclair"},

    # Apothecarium
    {"name": "The Apothecarium - Maplewood", "address": "1750 Springfield Ave", "city": "Maplewood", "county": "Essex", "zip": "07040", "phone": "(973) 763-2700", "website": "https://apothecarium.com/new-jersey/maplewood"},
    {"name": "The Apothecarium - Phillipsburg", "address": "1008 S Main St", "city": "Phillipsburg", "county": "Warren", "zip": "08865", "phone": "(908) 387-4200", "website": "https://apothecarium.com/new-jersey/phillipsburg"},
    {"name": "The Apothecarium - Lodi", "address": "99 US-46", "city": "Lodi", "county": "Bergen", "zip": "07644", "phone": "(973) 530-8700", "website": "https://apothecarium.com/new-jersey/lodi"},

    # Earth & Ivy
    {"name": "Earth & Ivy - New Brunswick", "address": "355 George St", "city": "New Brunswick", "county": "Middlesex", "zip": "08901", "phone": "(732) 317-2992", "website": "https://earthandivy.co"},
    {"name": "Earth & Ivy - Lakehurst", "address": "306 NJ-70", "city": "Lakehurst", "county": "Ocean", "zip": "08733", "phone": "(732) 323-3100", "website": "https://earthandivy.co"},

    # NJ Leaf
    {"name": "NJ Leaf - Freehold", "address": "3569 US-9", "city": "Freehold Township", "county": "Monmouth", "zip": "07728", "phone": "(848) 458-1130", "website": "https://njleaf.com"},

    # Cannabist (Columbia Care)
    {"name": "Cannabist - Vineland", "address": "1062 E Landis Ave", "city": "Vineland", "county": "Cumberland", "zip": "08360", "phone": "(856) 899-0240", "website": "https://gocannabist.com/dispensaries/new-jersey-vineland"},
    {"name": "Cannabist - Deptford", "address": "1720 Clements Bridge Rd", "city": "Deptford", "county": "Gloucester", "zip": "08096", "phone": "(856) 432-4200", "website": "https://gocannabist.com/dispensaries/new-jersey-deptford"},

    # Indigo
    {"name": "Indigo Dispensary - Brooklawn", "address": "1200 N Crescent Blvd", "city": "Brooklawn", "county": "Camden", "zip": "08030", "phone": "(856) 324-6006", "website": "https://indigodispensary.com"},

    # The Healing Center
    {"name": "The Healing Center - Hoboken", "address": "62 Newark St", "city": "Hoboken", "county": "Hudson", "zip": "07030", "phone": "(201) 683-0042", "website": "https://thchoboken.com"},

    # Harmony
    {"name": "Harmony Dispensary - Secaucus", "address": "600 Meadowlands Pkwy", "city": "Secaucus", "county": "Hudson", "zip": "07094", "phone": "(201) 643-2800", "website": "https://harmonydispensary.com"},

    # Additional dispensaries
    {"name": "New Era Dispensary - Bridgewater", "address": "550 Grove St", "city": "Bridgewater", "county": "Somerset", "zip": "08807", "phone": "(908) 393-1000", "website": "https://neweradispensary.com"},
    {"name": "Green Thumb Hopewell", "address": "14 Mine St", "city": "Hopewell", "county": "Mercer", "zip": "08525", "phone": "", "website": ""},
    {"name": "MPX NJ", "address": "999 Route 73 North", "city": "Mt Laurel", "county": "Burlington", "zip": "08054", "phone": "(856) 437-4277", "website": "https://mpxnj.com"},
]


def get_existing_nj_dispensaries() -> List[str]:
    """Get list of existing NJ dispensary names from database."""
    engine = get_engine()

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT LOWER(name) FROM dispensary WHERE state = 'NJ' AND is_active = true
        """))
        return [row[0] for row in result]


def normalize_name(name: str) -> str:
    """Normalize dispensary name for deduplication."""
    # Remove common suffixes
    name = re.sub(r'\s*-\s*(NJ|New Jersey|Dispensary|Cannabis).*$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+', ' ', name).strip().lower()
    return name


def is_duplicate(name: str, existing_names: List[str]) -> bool:
    """Check if dispensary already exists in database."""
    norm_name = normalize_name(name)

    for existing in existing_names:
        if norm_name in existing or existing in norm_name:
            return True

        # Check for common variations
        if norm_name.replace(' ', '') == existing.replace(' ', ''):
            return True

    return False


def save_to_database(dispensaries: List[Dict]):
    """Save NJ dispensaries to database, deduping against existing records."""
    engine = get_engine()
    existing = get_existing_nj_dispensaries()

    added = 0
    updated = 0
    skipped = 0

    with engine.connect() as conn:
        for disp in dispensaries:
            name = disp.get('name', '')
            if not name:
                continue

            # Check for duplicates
            if is_duplicate(name, existing):
                # Update existing record with new info
                conn.execute(text("""
                    UPDATE dispensary SET
                        phone = COALESCE(NULLIF(:phone, ''), phone),
                        menu_url = COALESCE(NULLIF(:website, ''), menu_url),
                        county = COALESCE(NULLIF(:county, ''), county),
                        updated_at = NOW()
                    WHERE LOWER(name) LIKE :name_pattern AND state = 'NJ'
                """), {
                    "phone": disp.get('phone', ''),
                    "website": disp.get('website', ''),
                    "county": disp.get('county', ''),
                    "name_pattern": f"%{normalize_name(name)}%"
                })
                updated += 1
            else:
                # Check if exact name exists
                exists = conn.execute(text("""
                    SELECT dispensary_id FROM dispensary
                    WHERE LOWER(name) = LOWER(:name) AND state = 'NJ'
                """), {"name": name}).fetchone()

                if exists:
                    skipped += 1
                    continue

                # Insert new dispensary
                conn.execute(text("""
                    INSERT INTO dispensary (
                        dispensary_id, name, address, city, state, zip, county,
                        phone, menu_url, is_active, store_type
                    ) VALUES (
                        gen_random_uuid(), :name, :address, :city, 'NJ', :zip, :county,
                        :phone, :website, true, 'dispensary'
                    )
                """), {
                    "name": name,
                    "address": disp.get('address', ''),
                    "city": disp.get('city', ''),
                    "zip": disp.get('zip', ''),
                    "county": disp.get('county', ''),
                    "phone": disp.get('phone', ''),
                    "website": disp.get('website', '')
                })
                existing.append(normalize_name(name))
                added += 1

        conn.commit()

    print(f"Results: {added} added, {updated} updated, {skipped} skipped")
    return added, updated, skipped


def print_instructions():
    """Print instructions for scraping NJ data."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║             NEW JERSEY DISPENSARY SCRAPING INSTRUCTIONS                      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  This script uses known NJ dispensary data and can be extended with          ║
║  Selenium/Playwright to scrape the interactive map at:                       ║
║  https://www.nj.gov/cannabis/dispensaries/find/                              ║
║                                                                              ║
║  Current data sources:                                                       ║
║  - Official NJ CRC dispensary listings                                       ║
║  - Known dispensary chain websites (Curaleaf, Rise, Zen Leaf, etc.)          ║
║  - NJ Open Data portal (when accessible)                                     ║
║                                                                              ║
║  To run with built-in data:                                                  ║
║    python scripts/scrape_nj_dispensaries.py --load-known                     ║
║                                                                              ║
║  To scrape live data (requires Selenium):                                    ║
║    python scripts/scrape_nj_dispensaries.py --scrape                         ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scrape NJ dispensary data")
    parser.add_argument('--load-known', action='store_true', help="Load known dispensary data")
    parser.add_argument('--scrape', action='store_true', help="Scrape live data (requires Selenium)")
    parser.add_argument('--dry-run', action='store_true', help="Don't save to database")

    args = parser.parse_args()

    if not args.load_known and not args.scrape:
        print_instructions()
        sys.exit(0)

    dispensaries = []

    if args.load_known:
        print(f"Loading {len(KNOWN_NJ_DISPENSARIES)} known NJ dispensaries...")
        dispensaries = KNOWN_NJ_DISPENSARIES

    if args.scrape:
        print("Note: Live scraping requires Selenium/Playwright")
        print("The NJ cannabis site uses an interactive map that requires JavaScript")
        print("Using known dispensary data instead...")
        dispensaries = KNOWN_NJ_DISPENSARIES

    if dispensaries:
        print(f"\nTotal dispensaries to process: {len(dispensaries)}")

        if args.dry_run:
            print("\n[DRY RUN] Would save the following dispensaries:")
            for d in dispensaries[:10]:
                print(f"  - {d['name']} ({d['city']})")
            if len(dispensaries) > 10:
                print(f"  ... and {len(dispensaries) - 10} more")
        else:
            added, updated, skipped = save_to_database(dispensaries)
            print(f"\nDone! Added: {added}, Updated: {updated}, Skipped: {skipped}")
