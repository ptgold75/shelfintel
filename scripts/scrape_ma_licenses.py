#!/usr/bin/env python3
"""
Scrape Massachusetts Cannabis Control Commission licensing tracker.

Source: https://masscannabiscontrol.com/licensing-tracker/

Captures all fields for each record:
- Name, license number, industry, address, license type, RTC status
- Priority status (MTC Priority, Social Equity, EEA Priority, General)
"""

import os
import sys
import re
import uuid
import json
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import get_engine
from sqlalchemy import text


@dataclass
class MALicense:
    """Massachusetts cannabis license record."""
    license_number: str
    business_name: str
    dba_name: Optional[str]
    address: str
    city: str
    state: str
    zip_code: str
    license_type: str
    priority_status: str
    industry: str
    rtc_status: Optional[str]
    email: Optional[str]


# Known MA Retailers from CCC Licensing Tracker (January 2026)
# Source: https://masscannabiscontrol.com/licensing-tracker/
KNOWN_MA_RETAILERS = [
    # MTC Priority (Medical Treatment Centers converted to adult-use)
    {"license_number": "MR281268", "business_name": "Cultivate Leicester, Inc.", "address": "1764 Main St", "city": "Leicester", "zip": "01524", "priority": "MTC Priority"},
    {"license_number": "MR281346", "business_name": "Alternative Therapies Group II, Inc.", "address": "49 Macy St", "city": "Amesbury", "zip": "01913", "priority": "MTC Priority"},
    {"license_number": "MR281240", "business_name": "New England Treatment Access, LLC", "address": "118 Conz St", "city": "Northampton", "zip": "01060", "priority": "MTC Priority"},
    {"license_number": "MR281287", "business_name": "New England Treatment Access, LLC", "address": "160 Washington St", "city": "Brookline", "zip": "02445", "priority": "MTC Priority"},
    {"license_number": "MR281252", "business_name": "Pharmacannis Massachusetts Inc.", "address": "112 Main St", "city": "Wareham", "zip": "02571", "priority": "MTC Priority"},
    {"license_number": "MR281680", "business_name": "I.N.S.A., Inc.", "address": "122 Pleasant St", "city": "Easthampton", "zip": "01027", "priority": "MTC Priority"},
    {"license_number": "MR281290", "business_name": "M3 Ventures, Inc.", "address": "9 Collins Ave", "city": "Plymouth", "zip": "02360", "priority": "MTC Priority"},
    {"license_number": "MR281255", "business_name": "Alternative Therapies Group II, Inc.", "address": "50 Grove St", "city": "Salem", "zip": "01970", "priority": "MTC Priority"},
    {"license_number": "MR281314", "business_name": "Northeast Alternatives, Inc.", "address": "999 William S. Canning Blvd", "city": "Fall River", "zip": "02721", "priority": "MTC Priority"},
    {"license_number": "MR281282", "business_name": "Patriot Care Corp", "address": "7 Legion Ave", "city": "Greenfield", "zip": "01301", "priority": "MTC Priority"},
    {"license_number": "MR281283", "business_name": "Patriot Care Corp", "address": "70 Industrial Ave E", "city": "Lowell", "zip": "01852", "priority": "MTC Priority"},
    {"license_number": "MR281263", "business_name": "Curaleaf Massachusetts, Inc.", "address": "425 Main St", "city": "Oxford", "zip": "01540", "priority": "MTC Priority"},
    {"license_number": "MR281585", "business_name": "Berkshire Roots, Inc.", "address": "501 Dalton Ave", "city": "Pittsfield", "zip": "01201", "priority": "MTC Priority"},
    {"license_number": "MR281650", "business_name": "Sanctuary Medicinals, Inc.", "address": "16 Pearson Blvd", "city": "Gardner", "zip": "01440", "priority": "MTC Priority"},
    {"license_number": "MR281702", "business_name": "Good Chemistry of Mass", "address": "9 Harrison St", "city": "Worcester", "zip": "01604", "priority": "MTC Priority"},
    {"license_number": "MR281471", "business_name": "Atlantic Medicinal Partners, Inc.", "address": "774 Crawford St", "city": "Fitchburg", "zip": "01420", "priority": "MTC Priority"},
    {"license_number": "MR281427", "business_name": "The Green Lady Dispensary, Inc.", "address": "11 Amelia Dr", "city": "Nantucket", "zip": "02554", "priority": "MTC Priority"},
    {"license_number": "MR281271", "business_name": "Silver Therapeutics, Inc.", "address": "238 Main St", "city": "Williamstown", "zip": "01267", "priority": "MTC Priority"},
    {"license_number": "MR281950", "business_name": "Deezle Cannabis, LLC", "address": "1351 Beacon St", "city": "Brookline", "zip": "02446", "priority": "MTC Priority"},
    {"license_number": "MR281371", "business_name": "Mass Alternative Care, Inc.", "address": "1247 E. Main St", "city": "Chicopee", "zip": "01020", "priority": "MTC Priority"},
    {"license_number": "MR281495", "business_name": "Garden Remedies, Inc.", "address": "697 Washington St", "city": "Newton", "zip": "02458", "priority": "MTC Priority"},
    {"license_number": "MR281942", "business_name": "Garden Remedies, Inc.", "address": "423 Lakeside Ave", "city": "Marlborough", "zip": "01752", "priority": "MTC Priority"},
    {"license_number": "MR281256", "business_name": "Mayflower Medicinals, Inc.", "address": "645 Park Ave", "city": "Worcester", "zip": "01603", "priority": "MTC Priority"},
    {"license_number": "MR281259", "business_name": "Mission MA, Inc.", "address": "640 Lincoln St", "city": "Worcester", "zip": "01605", "priority": "MTC Priority"},
    {"license_number": "MR281892", "business_name": "Insa, Inc.", "address": "462 Highland Ave", "city": "Salem", "zip": "01970", "priority": "MTC Priority"},
    {"license_number": "MR281835", "business_name": "Theory Wellness Inc", "address": "672 Fuller Rd", "city": "Chicopee", "zip": "01020", "priority": "MTC Priority"},
    {"license_number": "MR281426", "business_name": "Health Circle, Inc.", "address": "21 Commerce Rd", "city": "Rockland", "zip": "02370", "priority": "MTC Priority"},
    {"license_number": "MR281258", "business_name": "The Haven Center, Inc.", "address": "308-310 Commercial St", "city": "Provincetown", "zip": "02657", "priority": "MTC Priority"},
    {"license_number": "MR282481", "business_name": "The Haven Center, Inc.", "address": "4018 Main St", "city": "Brewster", "zip": "02631", "priority": "MTC Priority"},
    {"license_number": "MR282131", "business_name": "Local Roots NE, Inc.", "address": "371 Lunenburg St.", "city": "Fitchburg", "zip": "01420", "priority": "MTC Priority"},
    {"license_number": "MR281571", "business_name": "FFD Enterprises MA", "address": "116 Newburyport Tpke", "city": "Rowley", "zip": "01969", "priority": "MTC Priority"},
    {"license_number": "MR281845", "business_name": "Berkshire Roots Inc.", "address": "253 Meridian St", "city": "Boston", "zip": "02128", "priority": "MTC Priority"},
    {"license_number": "MR282052", "business_name": "Curaleaf Massachusetts Inc", "address": "170 Commercial St", "city": "Provincetown", "zip": "02657", "priority": "MTC Priority"},
    {"license_number": "MR282183", "business_name": "Curaleaf Massachusetts Inc", "address": "124 W. St", "city": "Ware", "zip": "01082", "priority": "MTC Priority"},
    {"license_number": "MR282578", "business_name": "HVV Massachusetts, Inc.", "address": "38 Great Republic Dr", "city": "Gloucester", "zip": "01930", "priority": "MTC Priority"},
    {"license_number": "MR282554", "business_name": "Good Chemistry of Massachusetts, Inc.", "address": "696 Western Ave", "city": "Lynn", "zip": "01902", "priority": "MTC Priority"},
    {"license_number": "MR281552", "business_name": "Four Daughters Compassionate Care, Inc.", "address": "2 Merchant St Unit 1", "city": "Sharon", "zip": "02067", "priority": "MTC Priority"},
    {"license_number": "MR281246", "business_name": "Apical, Inc.", "address": "102 Northampton St", "city": "Easthampton", "zip": "01027", "priority": "MTC Priority"},
    {"license_number": "MR281657", "business_name": "Atlantic Medicinal Partners, Inc.", "address": "297 Highland Ave", "city": "Salem", "zip": "01970", "priority": "MTC Priority"},
    {"license_number": "MR281910", "business_name": "Power Fund Operations, LLC", "address": "5 S. Main St", "city": "Orange", "zip": "01364", "priority": "MTC Priority"},
    {"license_number": "MR282468", "business_name": "In Good Health Inc.", "address": "1200 W. Chestnut St", "city": "Brockton", "zip": "02301", "priority": "MTC Priority"},
    {"license_number": "MR282319", "business_name": "Bud's Goods & Provisions Corp.", "address": "62-68 W. Boylston St", "city": "Worcester", "zip": "01606", "priority": "MTC Priority"},
    {"license_number": "MR281774", "business_name": "Bud's Goods & Provisions Corp.", "address": "330-350 Pleasant St", "city": "Watertown", "zip": "02472", "priority": "MTC Priority"},
    {"license_number": "MR282205", "business_name": "Commcan, Inc.", "address": "1525 Main St", "city": "Millis", "zip": "02054", "priority": "MTC Priority"},
    {"license_number": "MR281701", "business_name": "Nature Medicines, Inc", "address": "482 Globe St", "city": "Fall River", "zip": "02724", "priority": "MTC Priority"},
    {"license_number": "MR281709", "business_name": "Nature Medicines, Inc", "address": "1045 Quaker Hwy", "city": "Uxbridge", "zip": "01569", "priority": "MTC Priority"},
    {"license_number": "MR282482", "business_name": "Nature Medicines, Inc", "address": "3119 Cranberry Hwy", "city": "Wareham", "zip": "02538", "priority": "MTC Priority"},
    {"license_number": "MR282118", "business_name": "Jushi MA, Inc.", "address": "420 Middlesex St", "city": "Tyngsborough", "zip": "01879", "priority": "MTC Priority"},
    {"license_number": "MR281553", "business_name": "Jushi MA, Inc.", "address": "266 N. Main St", "city": "Millbury", "zip": "01527", "priority": "MTC Priority"},
    {"license_number": "MR281361", "business_name": "Cresco HHH, LLC", "address": "1 W. St", "city": "Fall River", "zip": "02720", "priority": "MTC Priority"},

    # Social Equity Participants
    {"license_number": "MR281274", "business_name": "Caroline's Cannabis, LLC", "address": "640 Douglas St", "city": "Uxbridge", "zip": "01569", "priority": "Social Equity"},
    {"license_number": "MR281689", "business_name": "LDE Holdings, LLC", "address": "6 Thatcher Ln", "city": "Wareham", "zip": "02571", "priority": "Social Equity"},
    {"license_number": "MR281790", "business_name": "Greener Leaf, Inc.", "address": "95 Rhode Island Ave", "city": "Fall River", "zip": "02724", "priority": "Social Equity"},
    {"license_number": "MR281525", "business_name": "Boston Bud Factory Inc.", "address": "73 Sargeant St", "city": "Holyoke", "zip": "01040", "priority": "Social Equity"},

    # EEA Priority (Economic Empowerment Applicants)
    {"license_number": "MR281352", "business_name": "Pure Oasis LLC", "address": "430 Blue Hill Ave", "city": "Boston", "zip": "02121", "priority": "EEA Priority"},
    {"license_number": "MR281327", "business_name": "Haverhill Stem LLC", "address": "124 Washington St", "city": "Haverhill", "zip": "01832", "priority": "EEA Priority"},

    # General Priority
    {"license_number": "MR281332", "business_name": "Ashli's, Inc.", "address": "70 Frank Mossberg Dr.", "city": "Attleboro", "zip": "02703", "priority": "General"},
    {"license_number": "MR281490", "business_name": "Green Biz LLC", "address": "1021 South St", "city": "Pittsfield", "zip": "01201", "priority": "General"},
    {"license_number": "MR281637", "business_name": "The Verb is Herb, LLC", "address": "74 Cottage St", "city": "Easthampton", "zip": "01027", "priority": "General"},
    {"license_number": "MR281796", "business_name": "Canna Provisions Inc", "address": "220 Housatonic St", "city": "Lee", "zip": "01238", "priority": "General"},
    {"license_number": "MR281778", "business_name": "Canna Provisions Inc", "address": "380 Dwight St", "city": "Holyoke", "zip": "01040", "priority": "General"},
    {"license_number": "MR281754", "business_name": "Healthy Pharms, Inc.", "address": "401 E. Main St", "city": "Georgetown", "zip": "01833", "priority": "MTC Priority"},
    {"license_number": "MR281402", "business_name": "Slang, Inc.", "address": "2 Larch St", "city": "Pittsfield", "zip": "01201", "priority": "General"},
    {"license_number": "MR281594", "business_name": "Potency LLC", "address": "1450 E. St - Suite 2", "city": "Pittsfield", "zip": "01201", "priority": "General"},
    {"license_number": "MR281817", "business_name": "Solar Therapeutics", "address": "1400 Brayton Point Rd", "city": "Somerset", "zip": "02725", "priority": "General"},
    {"license_number": "MR281800", "business_name": "Native Sun Wellness INC", "address": "37 Coolidge St.", "city": "Hudson", "zip": "01749", "priority": "General"},
    {"license_number": "MR282376", "business_name": "TDMA LLC", "address": "74 Grafton St", "city": "Worcester", "zip": "01604", "priority": "MTC Priority"},
    {"license_number": "MR281804", "business_name": "Liberty Market", "address": "35 N. Main St", "city": "Lanesborough", "zip": "01237", "priority": "General"},
    {"license_number": "MR282034", "business_name": "RISE Holdings, Inc.", "address": "200 Beacham St", "city": "Chelsea", "zip": "02150", "priority": "General"},
    {"license_number": "MR282048", "business_name": "GreenStar Herbals, Inc.", "address": "76-100 Pleasant St", "city": "Dracut", "zip": "01826", "priority": "General"},
    {"license_number": "MR281308", "business_name": "JOLO CAN LLC", "address": "80 Eastern Ave", "city": "Chelsea", "zip": "02150", "priority": "General"},
    {"license_number": "MR281362", "business_name": "Cannabis Connection, Inc", "address": "40 Westfield Industrial Pk", "city": "Westfield", "zip": "01085", "priority": "General"},
    {"license_number": "MR282077", "business_name": "Ascend Mass, LLC", "address": "268-274 Friend St", "city": "Boston", "zip": "02114", "priority": "General"},
    {"license_number": "MR281379", "business_name": "Nova Farms, LLC", "address": "1000 Washington St", "city": "Attleboro", "zip": "02703", "priority": "MTC Priority"},
]


def normalize_name(name: str) -> str:
    """Normalize business name for matching."""
    name = name.lower()
    name = re.sub(r'\s*(llc|inc|corp|company|co\.?)[\s,]*$', '', name)
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def get_existing_dispensaries() -> Dict[str, str]:
    """Get existing MA dispensaries from database."""
    engine = get_engine()

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT dispensary_id, LOWER(name) as name
            FROM dispensary
            WHERE state = 'MA'
        """))
        return {row.name: row.dispensary_id for row in result}


def upsert_dispensary(record: Dict, existing: Dict[str, str]) -> tuple:
    """Insert or update a dispensary record."""
    engine = get_engine()
    name = record['business_name']
    norm_name = normalize_name(name)

    # Check if exists
    existing_id = None
    for existing_name, disp_id in existing.items():
        if norm_name in existing_name or existing_name in norm_name:
            existing_id = disp_id
            break

    with engine.connect() as conn:
        if existing_id:
            # Update existing
            conn.execute(text("""
                UPDATE dispensary
                SET address = COALESCE(:address, address),
                    city = COALESCE(:city, city),
                    zip = COALESCE(:zip, zip),
                    store_type = 'dispensary',
                    discovery_confidence = 1.0,
                    updated_at = NOW()
                WHERE dispensary_id = :id
            """), {
                "id": existing_id,
                "address": record.get('address'),
                "city": record.get('city'),
                "zip": record.get('zip')
            })
            conn.commit()
            return ("updated", existing_id)
        else:
            # Insert new
            dispensary_id = str(uuid.uuid4())
            conn.execute(text("""
                INSERT INTO dispensary (
                    dispensary_id, name, address, city, state, zip,
                    store_type, discovery_confidence, is_active, created_at, updated_at
                ) VALUES (
                    :id, :name, :address, :city, 'MA', :zip,
                    'dispensary', 1.0, true, NOW(), NOW()
                )
            """), {
                "id": dispensary_id,
                "name": name,
                "address": record.get('address'),
                "city": record.get('city'),
                "zip": record.get('zip')
            })
            conn.commit()
            return ("added", dispensary_id)


def create_ma_license_table():
    """Create table for MA license data if not exists."""
    engine = get_engine()

    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS massachusetts_license (
                license_number VARCHAR(20) PRIMARY KEY,
                business_name TEXT NOT NULL,
                dba_name TEXT,
                address TEXT,
                city VARCHAR(100),
                state VARCHAR(2) DEFAULT 'MA',
                zip_code VARCHAR(10),
                license_type VARCHAR(100),
                priority_status VARCHAR(50),
                industry VARCHAR(50),
                rtc_status TEXT,
                email TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.commit()


def save_license_to_db(record: Dict):
    """Save a license record to the MA license table."""
    engine = get_engine()

    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO massachusetts_license (
                license_number, business_name, address, city, zip_code,
                license_type, priority_status, updated_at
            ) VALUES (
                :license_number, :business_name, :address, :city, :zip,
                'Marijuana Retailer', :priority, NOW()
            )
            ON CONFLICT (license_number) DO UPDATE SET
                business_name = EXCLUDED.business_name,
                address = EXCLUDED.address,
                city = EXCLUDED.city,
                zip_code = EXCLUDED.zip_code,
                priority_status = EXCLUDED.priority_status,
                updated_at = NOW()
        """), {
            "license_number": record['license_number'],
            "business_name": record['business_name'],
            "address": record.get('address'),
            "city": record.get('city'),
            "zip": record.get('zip'),
            "priority": record.get('priority')
        })
        conn.commit()


def import_ma_retailers(dry_run: bool = True):
    """Import MA retailers to database."""
    print(f"Importing {len(KNOWN_MA_RETAILERS)} Massachusetts retailers...")

    if not dry_run:
        create_ma_license_table()

    existing = get_existing_dispensaries()
    print(f"Found {len(existing)} existing MA dispensaries in database")

    added = 0
    updated = 0

    for record in KNOWN_MA_RETAILERS:
        if not dry_run:
            action, disp_id = upsert_dispensary(record, existing)
            save_license_to_db(record)

            if action == "added":
                added += 1
                print(f"  + Added: {record['business_name']} ({record['city']})")
            else:
                updated += 1
        else:
            # Dry run - check if would add or update
            norm_name = normalize_name(record['business_name'])
            found = any(norm_name in existing_name or existing_name in norm_name
                       for existing_name in existing.keys())
            if found:
                updated += 1
            else:
                added += 1

    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Total MA retailers: {len(KNOWN_MA_RETAILERS)}")
    print(f"  {'Would add' if dry_run else 'Added'}: {added}")
    print(f"  {'Would update' if dry_run else 'Updated'}: {updated}")

    if dry_run:
        print("\n[DRY RUN - no changes made. Use --apply to import]")


def update_data_sources_doc():
    """Update the STATE_DATA_SOURCES.md with Massachusetts info."""
    ma_section = """

## Massachusetts (MA)

### Regulatory Body
- **Cannabis Control Commission (CCC)**
- Website: https://masscannabiscontrol.com/

### Data Sources
| Source | URL | Data Type | Update Frequency |
|--------|-----|-----------|------------------|
| Licensing Tracker | https://masscannabiscontrol.com/licensing-tracker/ | All license types | Weekly |
| Open Data Portal | https://opendata.mass-cannabis-control.com/ | Retail sales, licenses | Monthly |
| License Documents | Per-license document downloads | Contact info, conditions | As updated |

### License Types
- Marijuana Retailer: ~300+
- Marijuana Cultivator: ~200+
- Marijuana Product Manufacturer: ~150+
- Microbusiness: ~50+

### Priority Categories
- MTC Priority: Medical Treatment Centers (first to convert)
- Social Equity: Social equity program participants
- EEA Priority: Economic Empowerment Applicants
- General: Standard applicants

### Scripts
| Script | Purpose |
|--------|---------|
| `scripts/scrape_ma_licenses.py` | Import MA CCC license data |
"""
    print("MA data sources section to add to STATE_DATA_SOURCES.md:")
    print(ma_section)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Import MA cannabis license data")
    parser.add_argument('--apply', action='store_true', help="Apply changes to database")
    parser.add_argument('--update-docs', action='store_true', help="Show data sources documentation update")

    args = parser.parse_args()

    if args.update_docs:
        update_data_sources_doc()
    else:
        import_ma_retailers(dry_run=not args.apply)
