# core/state_license_data.py
"""State-level cannabis license data for market intelligence."""

from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum


class LicenseType(Enum):
    RETAIL = "Retail"
    RETAIL_DELIVERY = "Retail (Delivery)"
    CULTIVATION = "Cultivation"
    MANUFACTURING = "Manufacturing"
    DISTRIBUTION = "Distribution"
    TESTING = "Testing Laboratory"
    MICROBUSINESS = "Microbusiness"
    EVENTS = "Events"
    PROCESSING = "Processing"
    TRANSPORT = "Transport"


class LicenseStatus(Enum):
    ACTIVE = "Active"
    PROVISIONAL = "Provisional"
    EXPIRED = "Expired"
    SURRENDERED = "Surrendered"
    SUSPENDED = "Suspended"
    REVOKED = "Revoked"
    PENDING = "Pending"


@dataclass
class LicenseBreakdown:
    """License counts by type."""
    retail: int = 0
    retail_delivery: int = 0
    cultivation: int = 0
    manufacturing: int = 0
    distribution: int = 0
    testing: int = 0
    microbusiness: int = 0
    events: int = 0
    transport: int = 0
    total: int = 0


@dataclass
class StateLicenseData:
    """Complete license data for a state."""
    state: str
    state_abbrev: str
    regulatory_body: str
    regulatory_website: str
    last_updated: datetime

    # License counts
    total_licenses: int
    active_licenses: int
    provisional_licenses: int

    # Breakdown by type
    license_breakdown: LicenseBreakdown

    # Geographic data
    counties_with_licenses: int
    cities_with_licenses: int
    jurisdictions_allowing: int
    jurisdictions_banning: int

    # Top counties/cities
    top_counties: Dict[str, int]  # county: license_count
    top_cities: Dict[str, int]    # city: license_count

    # Notes and context
    notes: List[str]
    data_sources: List[str]


# California License Data (Updated January 2026)
CALIFORNIA_LICENSE_DATA = StateLicenseData(
    state="California",
    state_abbrev="CA",
    regulatory_body="Department of Cannabis Control (DCC)",
    regulatory_website="https://www.cannabis.ca.gov/",
    last_updated=datetime(2026, 1, 13),

    # License counts (as of June 2025 data + user note)
    total_licenses=8252,
    active_licenses=8252,
    provisional_licenses=0,  # Provisional licenses ended Jan 1, 2026

    license_breakdown=LicenseBreakdown(
        retail=1450,           # User confirmed: 1,450 retail cannabis licenses
        retail_delivery=285,   # Non-storefront retailers
        cultivation=4711,      # Largest category
        manufacturing=559,     # 599 per detailed report, 559 per June 2025
        distribution=927,
        testing=23,
        microbusiness=364,
        events=35,
        transport=132,
        total=8252
    ),

    # Geographic data
    counties_with_licenses=28,  # For manufacturing; more for cultivation
    cities_with_licenses=167,   # 31% of 539 jurisdictions allow retail
    jurisdictions_allowing=167,  # 31% of 539
    jurisdictions_banning=372,   # 69% of 539 ban some or all licenses

    # Top counties for manufacturing
    top_counties={
        "Alameda": 114,        # 19% of manufacturing
        "Los Angeles": 90,     # 15%
        "Riverside": 84,       # 14%
        "Humboldt": 60,        # 10% (cultivation hub)
        "Monterey": 42,        # 7%
        "San Diego": 35,
        "Santa Barbara": 30,
        "Mendocino": 28,       # Cultivation hub
        "Sacramento": 25,
        "San Francisco": 20
    },

    # Top cities for licenses
    top_cities={
        "Oakland": 97,         # Most manufacturing licenses
        "Cathedral City": 32,
        "Los Angeles": 180,    # Total across types
        "San Francisco": 85,
        "San Diego": 75,
        "Sacramento": 60,
        "Palm Springs": 28,
        "Desert Hot Springs": 45,  # Manufacturing hub
        "Santa Rosa": 35,
        "Long Beach": 30
    },

    notes=[
        "California has the largest legal cannabis market in the United States",
        "1,450 retail cannabis licenses (storefront dispensaries) - rest are smoke shops",
        "Provisional licenses ended January 1, 2025 (no more renewals)",
        "All provisional licenses became ineffective January 1, 2026",
        "69% of jurisdictions (cities/counties) ban some or all cannabis licenses",
        "Cultivation dominated by Humboldt, Mendocino, and Trinity counties",
        "Manufacturing concentrated in Oakland (16% of all mfg licenses)",
        "19 different cultivation license types based on canopy size and light type",
        "Local control means each city/county sets its own rules",
        "Track-and-trace system (Metrc) required for all licensees"
    ],

    data_sources=[
        "https://www.cannabis.ca.gov/resources/data-dashboard/license-report/",
        "https://search.cannabis.ca.gov/",
        "https://www.newcannabisventures.com/detailed-look-at-599-california-cannabis-manufacturing-licenses/",
        "California Department of Cannabis Control - License Search Tool"
    ]
)


# Manufacturing License Detail (California)
CALIFORNIA_MANUFACTURING = {
    "total": 599,
    "by_type": {
        "extraction_volatile": 150,      # Type 7 - butane, propane
        "extraction_nonvolatile": 371,   # Type 6 - CO2, ethanol, mechanical
        "infusion": 55,
        "packaging_labeling": 23
    },
    "by_use": {
        "adult_use": 257,
        "medicinal": 342
    },
    "by_county": {
        "Alameda": 114,
        "Los Angeles": 90,
        "Riverside": 84,
        "Humboldt": 60,
        "Monterey": 42
    },
    "unique_entities": 351,  # 599 licenses held by 351 companies
    "notes": "Most holders maintain 1-2 strategically paired licenses"
}


# Cultivation License Types (California)
CALIFORNIA_CULTIVATION_TYPES = [
    # Outdoor
    {"type": "Outdoor - Small", "canopy_sqft": "up to 5,000", "code": "Type 1"},
    {"type": "Outdoor - Small", "canopy_sqft": "5,001-10,000", "code": "Type 1A"},
    {"type": "Outdoor - Medium", "canopy_sqft": "10,001+", "code": "Type 2"},
    {"type": "Outdoor - Large", "canopy_sqft": "1+ acre", "code": "Type 5"},

    # Indoor
    {"type": "Indoor - Small", "canopy_sqft": "up to 5,000", "code": "Type 1C"},
    {"type": "Indoor - Medium", "canopy_sqft": "5,001-10,000", "code": "Type 2A"},
    {"type": "Indoor - Large", "canopy_sqft": "10,001-22,000", "code": "Type 3"},
    {"type": "Indoor - Large", "canopy_sqft": "22,001+", "code": "Type 5A"},

    # Mixed Light
    {"type": "Mixed Light - Small Tier 1", "canopy_sqft": "up to 5,000", "code": "Type 1B"},
    {"type": "Mixed Light - Small Tier 2", "canopy_sqft": "up to 5,000", "code": "Type 1D"},
    {"type": "Mixed Light - Medium", "canopy_sqft": "5,001-10,000", "code": "Type 2B"},
    {"type": "Mixed Light - Large", "canopy_sqft": "10,001-22,000", "code": "Type 3A/3B"},
    {"type": "Mixed Light - Large", "canopy_sqft": "22,001+", "code": "Type 5B"},

    # Special
    {"type": "Nursery", "canopy_sqft": "varies", "code": "Type 4"},
    {"type": "Processor", "canopy_sqft": "N/A", "code": "Processor"}
]


# Major California Cannabis Brands/Companies
CALIFORNIA_MAJOR_COMPANIES = [
    # MSOs with CA presence
    {"name": "Curaleaf", "type": "MSO", "licenses": ["retail", "cultivation", "manufacturing"]},
    {"name": "Trulieve", "type": "MSO", "licenses": ["retail", "cultivation"]},
    {"name": "Cookies", "type": "Brand/Retail", "hq": "San Francisco", "licenses": ["retail", "manufacturing"]},
    {"name": "Connected Cannabis", "type": "Vertically Integrated", "hq": "Sacramento", "licenses": ["retail", "cultivation", "manufacturing", "distribution"]},
    {"name": "Caliva", "type": "Single-State Operator", "hq": "San Jose", "licenses": ["retail", "cultivation", "manufacturing", "distribution"]},

    # Major Brands
    {"name": "Stiiizy", "type": "Brand", "category": "Vapes", "hq": "Los Angeles"},
    {"name": "Raw Garden", "type": "Brand", "category": "Concentrates/Vapes", "hq": "Santa Barbara"},
    {"name": "Jetty Extracts", "type": "Brand", "category": "Extracts", "hq": "Oakland"},
    {"name": "AbsoluteXtracts (ABX)", "type": "Brand", "category": "Vapes", "hq": "Santa Rosa"},
    {"name": "Kiva Confections", "type": "Brand", "category": "Edibles", "hq": "Oakland"},
    {"name": "Papa & Barkley", "type": "Brand", "category": "Topicals/Tinctures", "hq": "Eureka"},
    {"name": "Garden Society", "type": "Brand", "category": "Edibles", "hq": "Sonoma"},
    {"name": "PAX Labs", "type": "Brand/Device", "category": "Vaporizers", "hq": "San Francisco"},
    {"name": "Alien Labs", "type": "Brand", "category": "Flower/Concentrates", "hq": "Sacramento"},
    {"name": "710 Labs", "type": "Brand", "category": "Concentrates", "hq": "Los Angeles"},
    {"name": "Fig Farms", "type": "Brand", "category": "Flower", "hq": "Mendocino"},
    {"name": "Glass House Brands", "type": "Cultivator/Brand", "category": "Flower", "hq": "Long Beach"},
    {"name": "Lowell Farms", "type": "Brand/Cultivator", "category": "Flower/Pre-rolls", "hq": "Santa Barbara"},

    # Distributors
    {"name": "Nabis", "type": "Distributor", "hq": "Oakland"},
    {"name": "Herbl", "type": "Distributor", "hq": "Oakland"},
    {"name": "KGB Reserve", "type": "Distributor", "hq": "Oakland"},
]


def get_state_license_data(state_abbrev: str) -> Optional[StateLicenseData]:
    """Get license data for a state."""
    data_map = {
        "CA": CALIFORNIA_LICENSE_DATA
    }
    return data_map.get(state_abbrev.upper())


def get_all_states_with_data() -> List[str]:
    """Get list of states with license data."""
    return ["CA"]  # Expand as we add more states
