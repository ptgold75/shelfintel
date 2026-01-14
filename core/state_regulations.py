"""
State Cannabis Regulations Data Module
Updated: January 2026
Source: DISA, NCSL, MJBizDaily
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class LegalStatus(Enum):
    FULLY_LEGAL = "Fully Legal (Recreational)"
    MEDICAL_DECRIM = "Medical & Decriminalized"
    MEDICAL_ONLY = "Medical Only"
    CBD_ONLY = "CBD/Low-THC Only"
    DECRIMINALIZED = "Decriminalized Only"
    ILLEGAL = "Fully Illegal"


@dataclass
class StateRegulation:
    state: str
    abbreviation: str
    status: LegalStatus
    medical_year: Optional[int] = None  # Year medical was legalized
    recreational_year: Optional[int] = None  # Year recreational was legalized
    dispensary_count: Optional[int] = None
    notes: str = ""
    license_types: List[str] = None

    def __post_init__(self):
        if self.license_types is None:
            self.license_types = []


# Complete US State Regulations (as of January 2026)
STATE_REGULATIONS: Dict[str, StateRegulation] = {
    # Fully Legal (Recreational)
    "AK": StateRegulation("Alaska", "AK", LegalStatus.FULLY_LEGAL, 1998, 2014,
                          notes="First state to decriminalize (1975). Home cultivation allowed."),
    "AZ": StateRegulation("Arizona", "AZ", LegalStatus.FULLY_LEGAL, 2010, 2020,
                          notes="Prop 207 passed 2020. Vertical integration common."),
    "CA": StateRegulation("California", "CA", LegalStatus.FULLY_LEGAL, 1996, 2016,
                          notes="Largest cannabis market. Prop 64. Complex local regulations."),
    "CO": StateRegulation("Colorado", "CO", LegalStatus.FULLY_LEGAL, 2000, 2012,
                          notes="First recreational sales Jan 2014. Mature market."),
    "CT": StateRegulation("Connecticut", "CT", LegalStatus.FULLY_LEGAL, 2012, 2021,
                          notes="Social equity focus. Sales began Jan 2023."),
    "DE": StateRegulation("Delaware", "DE", LegalStatus.FULLY_LEGAL, 2011, 2023,
                          notes="No home cultivation. Sales expected 2024."),
    "DC": StateRegulation("District of Columbia", "DC", LegalStatus.FULLY_LEGAL, 2010, 2014,
                          notes="Initiative 71. No commercial sales due to Congress."),
    "IL": StateRegulation("Illinois", "IL", LegalStatus.FULLY_LEGAL, 2013, 2019, 43,
                          notes="First state to legalize via legislature. Social equity program."),
    "ME": StateRegulation("Maine", "ME", LegalStatus.FULLY_LEGAL, 1999, 2016,
                          notes="Delayed implementation. Sales began 2020."),
    "MD": StateRegulation("Maryland", "MD", LegalStatus.FULLY_LEGAL, 2013, 2022, 88,
                          notes="Question 4 passed 2022. Rec sales July 2023. 112 dispensaries."),
    "MA": StateRegulation("Massachusetts", "MA", LegalStatus.FULLY_LEGAL, 2012, 2016,
                          notes="First East Coast rec sales. Social equity focus."),
    "MI": StateRegulation("Michigan", "MI", LegalStatus.FULLY_LEGAL, 2008, 2018,
                          notes="Large market. Home cultivation allowed."),
    "MN": StateRegulation("Minnesota", "MN", LegalStatus.FULLY_LEGAL, 2014, 2023,
                          notes="Rec sales began 2025. Social equity provisions."),
    "MO": StateRegulation("Missouri", "MO", LegalStatus.FULLY_LEGAL, 2018, 2022,
                          notes="Amendment 3 passed 2022. Expungement provisions."),
    "MT": StateRegulation("Montana", "MT", LegalStatus.FULLY_LEGAL, 2004, 2020,
                          notes="I-190 passed. Sales began Jan 2022."),
    "NV": StateRegulation("Nevada", "NV", LegalStatus.FULLY_LEGAL, 2000, 2016,
                          notes="Tourism-driven market. Las Vegas hub."),
    "NJ": StateRegulation("New Jersey", "NJ", LegalStatus.FULLY_LEGAL, 2010, 2020, 15,
                          notes="Question 1 passed. Limited licenses. No home grow."),
    "NM": StateRegulation("New Mexico", "NM", LegalStatus.FULLY_LEGAL, 2007, 2021,
                          notes="Cannabis Regulation Act. Sales began April 2022."),
    "NY": StateRegulation("New York", "NY", LegalStatus.FULLY_LEGAL, 2014, 2021,
                          notes="MRTA passed. Delayed rollout. Social equity focus."),
    "OH": StateRegulation("Ohio", "OH", LegalStatus.FULLY_LEGAL, 2016, 2023,
                          notes="Issue 2 passed Nov 2023. Implementation ongoing."),
    "OR": StateRegulation("Oregon", "OR", LegalStatus.FULLY_LEGAL, 1998, 2014,
                          notes="Measure 91. Oversupply issues. Price compression."),
    "RI": StateRegulation("Rhode Island", "RI", LegalStatus.FULLY_LEGAL, 2006, 2022,
                          notes="Cannabis Act passed. Sales began Dec 2022."),
    "VT": StateRegulation("Vermont", "VT", LegalStatus.FULLY_LEGAL, 2004, 2018,
                          notes="First state to legalize via legislature (no sales initially)."),
    "VA": StateRegulation("Virginia", "VA", LegalStatus.FULLY_LEGAL, 2020, 2021,
                          notes="Possession legal, NO commercial sales yet. Expected 2024-2025."),
    "WA": StateRegulation("Washington", "WA", LegalStatus.FULLY_LEGAL, 1998, 2012,
                          notes="I-502. No home cultivation. Mature market."),

    # Medical & Decriminalized
    "HI": StateRegulation("Hawaii", "HI", LegalStatus.MEDICAL_DECRIM, 2000,
                          notes="Inter-island transport restrictions. Limited dispensaries."),
    "LA": StateRegulation("Louisiana", "LA", LegalStatus.MEDICAL_DECRIM, 2015,
                          notes="Pharmacy-based model. Smokable flower added 2022."),
    "MS": StateRegulation("Mississippi", "MS", LegalStatus.MEDICAL_DECRIM, 2022,
                          notes="Initiative 65 struck down, then SB 2095 passed."),
    "NE": StateRegulation("Nebraska", "NE", LegalStatus.MEDICAL_DECRIM, 2024,
                          notes="Medical passed Nov 2024. Implementation pending."),
    "NH": StateRegulation("New Hampshire", "NH", LegalStatus.MEDICAL_DECRIM, 2013,
                          notes="Alternative Treatment Centers. Decrim since 2017."),
    "ND": StateRegulation("North Dakota", "ND", LegalStatus.MEDICAL_DECRIM, 2016,
                          notes="Measure 5 passed. Rec failed 2022 & 2024."),

    # Medical Only
    "AL": StateRegulation("Alabama", "AL", LegalStatus.MEDICAL_ONLY, 2021,
                          notes="Darren Wesley 'Ato' Hall Compassion Act. No smokable."),
    "AR": StateRegulation("Arkansas", "AR", LegalStatus.MEDICAL_ONLY, 2016,
                          notes="Issue 6 passed. Rec failed 2022."),
    "FL": StateRegulation("Florida", "FL", LegalStatus.MEDICAL_ONLY, 2016,
                          notes="Amendment 2. Vertical integration. Rec failed 2024 (56%)."),
    "KY": StateRegulation("Kentucky", "KY", LegalStatus.MEDICAL_ONLY, 2023,
                          notes="SB 47 signed. Sales expected 2025."),
    "OK": StateRegulation("Oklahoma", "OK", LegalStatus.MEDICAL_ONLY, 2018,
                          notes="SQ 788. Very liberal program. Oversupply issues."),
    "PA": StateRegulation("Pennsylvania", "PA", LegalStatus.MEDICAL_ONLY, 2016,
                          notes="Act 16. Vertical integration. Rec bills pending."),
    "SD": StateRegulation("South Dakota", "SD", LegalStatus.MEDICAL_ONLY, 2020,
                          notes="IM 26 (medical). Rec Amendment A struck down."),
    "UT": StateRegulation("Utah", "UT", LegalStatus.MEDICAL_ONLY, 2018,
                          notes="Prop 2 passed, modified by legislature."),
    "WV": StateRegulation("West Virginia", "WV", LegalStatus.MEDICAL_ONLY, 2017,
                          notes="SB 386. Slow implementation. Sales began 2022."),

    # CBD/Low-THC Only
    "GA": StateRegulation("Georgia", "GA", LegalStatus.CBD_ONLY,
                          notes="Haleigh's Hope Act. Low-THC oil only. No in-state production initially."),
    "IN": StateRegulation("Indiana", "IN", LegalStatus.CBD_ONLY,
                          notes="CBD with 0.3% THC only (hemp-derived)."),
    "IA": StateRegulation("Iowa", "IA", LegalStatus.CBD_ONLY, 2014,
                          notes="SF 2360. 3% THC cap. Limited conditions."),
    "TN": StateRegulation("Tennessee", "TN", LegalStatus.CBD_ONLY,
                          notes="Limited CBD program. Bills for medical pending."),
    "TX": StateRegulation("Texas", "TX", LegalStatus.CBD_ONLY, 2015,
                          notes="Compassionate Use Program. 1% THC cap expanded."),
    "WI": StateRegulation("Wisconsin", "WI", LegalStatus.CBD_ONLY,
                          notes="Lydia's Law. Very limited CBD program."),

    # Decriminalized Only
    "NC": StateRegulation("North Carolina", "NC", LegalStatus.DECRIMINALIZED,
                          notes="Decrim for small amounts. No medical program."),

    # Fully Illegal
    "ID": StateRegulation("Idaho", "ID", LegalStatus.ILLEGAL,
                          notes="Constitutional amendment banning. Strictest state."),
    "KS": StateRegulation("Kansas", "KS", LegalStatus.ILLEGAL,
                          notes="No medical or decrim. CBD from hemp only."),
    "SC": StateRegulation("South Carolina", "SC", LegalStatus.ILLEGAL,
                          notes="CBD limited. Medical bills have failed."),
    "WY": StateRegulation("Wyoming", "WY", LegalStatus.ILLEGAL,
                          notes="No medical program. Hemp CBD allowed."),
}

# Color mappings for visualization
STATUS_COLORS = {
    LegalStatus.FULLY_LEGAL: "#2E7D32",      # Green
    LegalStatus.MEDICAL_DECRIM: "#66BB6A",   # Light Green
    LegalStatus.MEDICAL_ONLY: "#42A5F5",     # Blue
    LegalStatus.CBD_ONLY: "#FFA726",         # Orange
    LegalStatus.DECRIMINALIZED: "#FFEE58",   # Yellow
    LegalStatus.ILLEGAL: "#EF5350",          # Red
}

STATUS_LABELS = {
    LegalStatus.FULLY_LEGAL: "Recreational",
    LegalStatus.MEDICAL_DECRIM: "Medical+Decrim",
    LegalStatus.MEDICAL_ONLY: "Medical Only",
    LegalStatus.CBD_ONLY: "CBD Only",
    LegalStatus.DECRIMINALIZED: "Decriminalized",
    LegalStatus.ILLEGAL: "Illegal",
}


def get_states_by_status(status: LegalStatus) -> List[StateRegulation]:
    """Get all states with a specific legal status."""
    return [s for s in STATE_REGULATIONS.values() if s.status == status]


def get_state_regulation(abbreviation: str) -> Optional[StateRegulation]:
    """Get regulation info for a specific state."""
    return STATE_REGULATIONS.get(abbreviation.upper())


def get_status_summary() -> Dict[str, int]:
    """Get count of states by legal status."""
    summary = {}
    for status in LegalStatus:
        summary[status.value] = len(get_states_by_status(status))
    return summary


def get_all_recreational_states() -> List[str]:
    """Get list of states with recreational cannabis."""
    return [s.abbreviation for s in STATE_REGULATIONS.values()
            if s.status == LegalStatus.FULLY_LEGAL]


def get_all_medical_states() -> List[str]:
    """Get list of states with medical cannabis (including recreational)."""
    medical_statuses = [LegalStatus.FULLY_LEGAL, LegalStatus.MEDICAL_DECRIM, LegalStatus.MEDICAL_ONLY]
    return [s.abbreviation for s in STATE_REGULATIONS.values()
            if s.status in medical_statuses]


# 2026 Ballot initiatives
UPCOMING_BALLOTS = {
    "FL": {
        "year": 2026,
        "type": "Recreational",
        "description": "Adult-use legalization. 21+, up to 2oz possession.",
        "status": "Qualified for ballot"
    },
    "ID": {
        "year": 2026,
        "type": "Medical",
        "description": "Medical marijuana legalization for substantial health conditions.",
        "status": "Petition filed"
    },
    "NE": {
        "year": 2026,
        "type": "Recreational",
        "description": "Adult-use for 21+.",
        "status": "Petition filed"
    },
    "OK": {
        "year": 2026,
        "type": "Recreational",
        "description": "SQ 837. 21+, up to 8oz, home cultivation of 12 plants.",
        "status": "Petition filed"
    },
}
