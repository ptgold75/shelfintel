#!/usr/bin/env python3
"""
Scrape California Cannabis Licenses from DCC

This script scrapes the California Department of Cannabis Control license database.
Data source: https://search.cannabis.ca.gov/

The DCC search portal has an export feature - this script automates that process
or can be used with Selenium/Playwright for full automation.
"""

import os
import sys
import json
import csv
import requests
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import get_engine
from sqlalchemy import text


@dataclass
class CaliforniaLicense:
    """California cannabis license record."""
    license_number: str
    business_name: str
    dba_name: Optional[str]
    license_type: str
    license_status: str

    # Address
    premise_address: str
    premise_city: str
    premise_county: str
    premise_state: str = "CA"
    premise_zip: str = ""

    # Dates
    issue_date: Optional[str] = None
    expiration_date: Optional[str] = None

    # Additional info
    adult_use: bool = False
    medicinal: bool = False

    # Metadata
    scraped_at: str = ""
    data_source: str = "DCC"


# License type mappings
LICENSE_TYPES = {
    # Retail
    "Retailer": "retail",
    "Retailer Nonstorefront": "retail_delivery",

    # Cultivation
    "Small Outdoor": "cultivation",
    "Small Indoor": "cultivation",
    "Small Mixed-Light Tier 1": "cultivation",
    "Small Mixed-Light Tier 2": "cultivation",
    "Medium Outdoor": "cultivation",
    "Medium Indoor": "cultivation",
    "Medium Mixed-Light Tier 1": "cultivation",
    "Medium Mixed-Light Tier 2": "cultivation",
    "Large Outdoor": "cultivation",
    "Large Indoor": "cultivation",
    "Large Mixed-Light Tier 1": "cultivation",
    "Large Mixed-Light Tier 2": "cultivation",
    "Specialty Cottage Outdoor": "cultivation",
    "Specialty Cottage Indoor": "cultivation",
    "Specialty Cottage Mixed-Light Tier 1": "cultivation",
    "Specialty Cottage Mixed-Light Tier 2": "cultivation",
    "Nursery": "cultivation",
    "Processor": "processing",

    # Manufacturing
    "Manufacturer Type 6": "manufacturing",  # Non-volatile
    "Manufacturer Type 7": "manufacturing",  # Volatile
    "Manufacturer Type N": "manufacturing",  # Infusion
    "Manufacturer Type P": "manufacturing",  # Packaging
    "Manufacturer Type S": "manufacturing",  # Shared facility

    # Distribution
    "Distributor": "distribution",
    "Distributor Transport Only": "transport",

    # Testing
    "Testing Laboratory": "testing",

    # Other
    "Microbusiness": "microbusiness",
    "Event Organizer": "events",
}


def parse_csv_export(csv_path: str) -> List[CaliforniaLicense]:
    """
    Parse a CSV export from the DCC license search portal.

    To get the CSV:
    1. Go to https://search.cannabis.ca.gov/
    2. Click "Advanced Search"
    3. Select license type or leave blank for all
    4. Click "Search"
    5. Click "Export" -> "All Data"
    6. Save the CSV file
    """
    licenses = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            # Handle the exact column names from DCC export
            license_number = row.get('licenseNumber', row.get('License Number', '')).strip()
            if not license_number:
                continue

            license = CaliforniaLicense(
                license_number=license_number,
                business_name=row.get('businessLegalName', row.get('Business Legal Name', '')).strip(),
                dba_name=row.get('businessDbaName', row.get('DBA', '')).strip() or None,
                license_type=row.get('licenseType', row.get('License Type', '')).strip(),
                license_status=row.get('licenseStatus', row.get('License Status', '')).strip(),
                premise_address=row.get('premiseStreetAddress', row.get('Premise Address', '')).strip(),
                premise_city=row.get('premiseCity', row.get('Premise City', '')).strip(),
                premise_county=row.get('premiseCounty', row.get('Premise County', '')).strip(),
                premise_zip=row.get('premiseZipCode', row.get('Premise Zip', '')).strip(),
                issue_date=row.get('issueDate', row.get('Issue Date', '')).strip() or None,
                expiration_date=row.get('expirationDate', row.get('Expiration Date', '')).strip() or None,
                adult_use='Adult-Use' in row.get('licenseDesignation', row.get('License Designation', '')),
                medicinal='Medicinal' in row.get('licenseDesignation', row.get('License Designation', '')),
                scraped_at=datetime.now().isoformat(),
                data_source="DCC Export"
            )

            # Clean up "Data Not Available" values
            if license.dba_name == "Data Not Available":
                license.dba_name = None

            licenses.append(license)

    return licenses


def save_to_database(licenses: List[CaliforniaLicense]):
    """Save license data to the database."""
    engine = get_engine()

    with engine.connect() as conn:
        # Create table if not exists
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS california_license (
                license_id SERIAL PRIMARY KEY,
                license_number VARCHAR(50) UNIQUE NOT NULL,
                business_name VARCHAR(255),
                dba_name VARCHAR(255),
                license_type VARCHAR(100),
                license_type_normalized VARCHAR(50),
                license_status VARCHAR(50),
                premise_address VARCHAR(500),
                premise_city VARCHAR(100),
                premise_county VARCHAR(100),
                premise_state VARCHAR(2) DEFAULT 'CA',
                premise_zip VARCHAR(20),
                issue_date DATE,
                expiration_date DATE,
                adult_use BOOLEAN DEFAULT false,
                medicinal BOOLEAN DEFAULT false,
                scraped_at TIMESTAMP,
                data_source VARCHAR(100),
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.commit()

        # Insert/update licenses
        for lic in licenses:
            normalized_type = LICENSE_TYPES.get(lic.license_type, 'other')

            conn.execute(text("""
                INSERT INTO california_license (
                    license_number, business_name, dba_name, license_type,
                    license_type_normalized, license_status,
                    premise_address, premise_city, premise_county, premise_zip,
                    issue_date, expiration_date, adult_use, medicinal,
                    scraped_at, data_source
                ) VALUES (
                    :license_number, :business_name, :dba_name, :license_type,
                    :normalized_type, :license_status,
                    :address, :city, :county, :zip,
                    :issue_date, :expiration_date, :adult_use, :medicinal,
                    :scraped_at, :data_source
                )
                ON CONFLICT (license_number) DO UPDATE SET
                    business_name = EXCLUDED.business_name,
                    dba_name = EXCLUDED.dba_name,
                    license_type = EXCLUDED.license_type,
                    license_type_normalized = EXCLUDED.license_type_normalized,
                    license_status = EXCLUDED.license_status,
                    premise_address = EXCLUDED.premise_address,
                    premise_city = EXCLUDED.premise_city,
                    premise_county = EXCLUDED.premise_county,
                    premise_zip = EXCLUDED.premise_zip,
                    issue_date = EXCLUDED.issue_date,
                    expiration_date = EXCLUDED.expiration_date,
                    adult_use = EXCLUDED.adult_use,
                    medicinal = EXCLUDED.medicinal,
                    scraped_at = EXCLUDED.scraped_at,
                    updated_at = NOW()
            """), {
                "license_number": lic.license_number,
                "business_name": lic.business_name,
                "dba_name": lic.dba_name,
                "license_type": lic.license_type,
                "normalized_type": normalized_type,
                "license_status": lic.license_status,
                "address": lic.premise_address,
                "city": lic.premise_city,
                "county": lic.premise_county,
                "zip": lic.premise_zip,
                "issue_date": lic.issue_date if lic.issue_date else None,
                "expiration_date": lic.expiration_date if lic.expiration_date else None,
                "adult_use": lic.adult_use,
                "medicinal": lic.medicinal,
                "scraped_at": lic.scraped_at,
                "data_source": lic.data_source
            })

        conn.commit()

    print(f"Saved {len(licenses)} licenses to database")


def save_to_json(licenses: List[CaliforniaLicense], output_path: str):
    """Save licenses to JSON file."""
    data = [asdict(lic) for lic in licenses]

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"Saved {len(licenses)} licenses to {output_path}")


def get_summary_stats(licenses: List[CaliforniaLicense]) -> Dict:
    """Get summary statistics from license data."""
    stats = {
        "total": len(licenses),
        "by_type": {},
        "by_status": {},
        "by_county": {},
        "by_city": {},
        "retail_count": 0,
        "cultivation_count": 0,
        "manufacturing_count": 0,
        "distribution_count": 0,
    }

    for lic in licenses:
        # By type
        stats["by_type"][lic.license_type] = stats["by_type"].get(lic.license_type, 0) + 1

        # By status
        stats["by_status"][lic.license_status] = stats["by_status"].get(lic.license_status, 0) + 1

        # By county
        county = lic.premise_county or "Unknown"
        stats["by_county"][county] = stats["by_county"].get(county, 0) + 1

        # By city
        city = lic.premise_city or "Unknown"
        stats["by_city"][city] = stats["by_city"].get(city, 0) + 1

        # Normalized counts
        normalized = LICENSE_TYPES.get(lic.license_type, 'other')
        if normalized == 'retail' or normalized == 'retail_delivery':
            stats["retail_count"] += 1
        elif normalized == 'cultivation':
            stats["cultivation_count"] += 1
        elif normalized == 'manufacturing':
            stats["manufacturing_count"] += 1
        elif normalized == 'distribution':
            stats["distribution_count"] += 1

    return stats


def print_instructions():
    """Print instructions for manually exporting data."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║          CALIFORNIA CANNABIS LICENSE DATA EXPORT INSTRUCTIONS                ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  The DCC license search portal requires JavaScript and has an export feature.║
║  Follow these steps to download the complete license database:               ║
║                                                                              ║
║  1. Go to: https://search.cannabis.ca.gov/                                   ║
║                                                                              ║
║  2. Click "Advanced Search" button                                           ║
║                                                                              ║
║  3. Leave all fields blank to get ALL licenses, or filter by:                ║
║     - License Type (Retailer, Cultivator, Manufacturer, etc.)                ║
║     - License Status (Active, Expired, etc.)                                 ║
║     - County                                                                 ║
║     - City                                                                   ║
║                                                                              ║
║  4. Click "Search"                                                           ║
║                                                                              ║
║  5. Click "Export" button (top right of results)                             ║
║                                                                              ║
║  6. Select "All Data" to get complete records                                ║
║                                                                              ║
║  7. Save the CSV file to: /Users/gleaf/shelfintel/data/ca_licenses.csv       ║
║                                                                              ║
║  8. Run this script with the CSV path:                                       ║
║     python scripts/scrape_california_licenses.py data/ca_licenses.csv        ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  RECOMMENDED: Export by license type to get complete data:                   ║
║  - Export all Retailers (should be ~1,450)                                   ║
║  - Export all Cultivators (should be ~4,700)                                 ║
║  - Export all Manufacturers (should be ~560)                                 ║
║  - Export all Distributors (should be ~930)                                  ║
║  - Export all Microbusinesses (should be ~365)                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_instructions()
        sys.exit(0)

    csv_path = sys.argv[1]

    if not os.path.exists(csv_path):
        print(f"Error: File not found: {csv_path}")
        print_instructions()
        sys.exit(1)

    print(f"Parsing CSV: {csv_path}")
    licenses = parse_csv_export(csv_path)

    print(f"\nFound {len(licenses)} licenses")

    # Get stats
    stats = get_summary_stats(licenses)

    print(f"\nSummary:")
    print(f"  Total licenses: {stats['total']:,}")
    print(f"  Retail: {stats['retail_count']:,}")
    print(f"  Cultivation: {stats['cultivation_count']:,}")
    print(f"  Manufacturing: {stats['manufacturing_count']:,}")
    print(f"  Distribution: {stats['distribution_count']:,}")

    print(f"\nTop 10 counties:")
    sorted_counties = sorted(stats['by_county'].items(), key=lambda x: x[1], reverse=True)[:10]
    for county, count in sorted_counties:
        print(f"  {county}: {count:,}")

    print(f"\nTop 10 cities:")
    sorted_cities = sorted(stats['by_city'].items(), key=lambda x: x[1], reverse=True)[:10]
    for city, count in sorted_cities:
        print(f"  {city}: {count:,}")

    # Save to database
    save_to_database(licenses)

    # Save to JSON backup
    json_path = csv_path.replace('.csv', '.json')
    save_to_json(licenses, json_path)

    print("\nDone!")
