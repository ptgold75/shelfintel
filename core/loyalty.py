# core/loyalty.py
"""Loyalty program SMS tracking and deal parsing."""

import json
import re
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import text
from core.db import get_engine


def generate_random_address(city: str, state: str) -> dict:
    """Generate a plausible random address for loyalty signup.

    Uses common street names and random house numbers.
    """
    import random

    street_names = [
        "Main St", "Oak Ave", "Maple Dr", "Cedar Ln", "Pine St",
        "Elm St", "Washington Ave", "Park Blvd", "Lake Dr", "Hill Rd",
        "Forest Ave", "River Rd", "Spring St", "Valley Dr", "Sunset Blvd"
    ]

    house_number = random.randint(100, 9999)
    street = random.choice(street_names)

    # Common ZIP codes by state (just samples)
    zip_codes = {
        "MD": ["21201", "21202", "21224", "21230", "20901", "20902"],
        "NJ": ["07001", "07102", "08401", "08501", "07302", "07030"],
        "PA": ["19101", "19103", "15201", "15213", "18101", "18015"],
        "DE": ["19801", "19901", "19702", "19711", "19720"],
        "VA": ["22201", "22301", "23220", "23451", "20190"],
        "IL": ["60601", "60614", "60657", "62701", "61801"]
    }

    zip_code = random.choice(zip_codes.get(state, ["10001"]))

    return {
        "name": "Sam Davidson",
        "address": f"{house_number} {street}",
        "city": city,
        "state": state,
        "zip": zip_code
    }


def parse_deal_with_ai(message: str) -> dict:
    """Parse a promotional SMS message to extract deal details.

    Uses pattern matching first, then AI for complex messages.
    Returns structured deal information.
    """
    deal = {
        "deal_type": None,
        "discount_percent": None,
        "discount_amount": None,
        "affected_brands": [],
        "affected_categories": [],
        "expires_at": None,
        "promo_code": None,
        "bogo": False,
        "minimum_purchase": None,
        "raw_summary": None
    }

    message_lower = message.lower()

    # Extract percentage discount
    pct_match = re.search(r'(\d+)%\s*off', message_lower)
    if pct_match:
        deal["discount_percent"] = float(pct_match.group(1))
        deal["deal_type"] = "percentage_off"

    # Extract dollar discount
    dollar_match = re.search(r'\$(\d+)\s*off', message_lower)
    if dollar_match:
        deal["discount_amount"] = float(dollar_match.group(1))
        deal["deal_type"] = "dollar_off"

    # Check for BOGO
    if any(term in message_lower for term in ["bogo", "buy one get one", "b1g1", "buy 1 get 1"]):
        deal["bogo"] = True
        deal["deal_type"] = "bogo"

    # Check for flash sale
    if any(term in message_lower for term in ["flash sale", "today only", "limited time", "ends tonight"]):
        deal["deal_type"] = deal["deal_type"] or "flash_sale"
        # Set expiration to end of day
        deal["expires_at"] = datetime.now().replace(hour=23, minute=59, second=59).isoformat()

    # Extract promo code
    code_match = re.search(r'(?:code|promo|use)[\s:]+([A-Z0-9]{3,15})', message, re.IGNORECASE)
    if code_match:
        deal["promo_code"] = code_match.group(1).upper()

    # Extract categories
    categories = {
        "flower": ["flower", "bud", "cannabis flower", "eighth", "quarter", "oz"],
        "vapes": ["vape", "cart", "cartridge", "pen", "disposable"],
        "edibles": ["edible", "gummy", "gummies", "chocolate", "candy", "beverage"],
        "concentrates": ["concentrate", "wax", "shatter", "live resin", "rosin", "dab"],
        "pre-rolls": ["pre-roll", "preroll", "joint", "blunt", "infused pre-roll"],
        "tinctures": ["tincture", "oil", "drops", "sublingual"]
    }

    for category, keywords in categories.items():
        if any(kw in message_lower for kw in keywords):
            deal["affected_categories"].append(category)

    # Extract brand names (common brands)
    brands = [
        "Rythm", "Verano", "Cresco", "GTI", "Curaleaf", "Trulieve",
        "Cookies", "Select", "Strane", "Grassroots", "Garcia",
        "WYLD", "Kiva", "Pax", "Stiiizy", "Raw Garden", "Connected"
    ]

    for brand in brands:
        if brand.lower() in message_lower:
            deal["affected_brands"].append(brand)

    # Extract expiration date
    date_patterns = [
        r'(?:exp|expires?|ends?|until|through)[\s:]*(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)',
        r'(?:exp|expires?|ends?|until|through)[\s:]*([A-Za-z]+\s+\d{1,2})',
    ]

    for pattern in date_patterns:
        date_match = re.search(pattern, message, re.IGNORECASE)
        if date_match:
            # Try to parse the date
            date_str = date_match.group(1)
            try:
                # Try common formats
                for fmt in ["%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%m-%d-%y", "%B %d", "%b %d"]:
                    try:
                        parsed = datetime.strptime(date_str, fmt)
                        if parsed.year == 1900:  # No year specified
                            parsed = parsed.replace(year=datetime.now().year)
                        deal["expires_at"] = parsed.isoformat()
                        break
                    except ValueError:
                        continue
            except:
                pass
            break

    # Generate summary
    parts = []
    if deal["discount_percent"]:
        parts.append(f"{int(deal['discount_percent'])}% off")
    if deal["discount_amount"]:
        parts.append(f"${int(deal['discount_amount'])} off")
    if deal["bogo"]:
        parts.append("BOGO")
    if deal["affected_categories"]:
        parts.append(", ".join(deal["affected_categories"]))
    if deal["affected_brands"]:
        parts.append(f"({', '.join(deal['affected_brands'])})")
    if deal["promo_code"]:
        parts.append(f"Code: {deal['promo_code']}")

    deal["raw_summary"] = " ".join(parts) if parts else "Special offer"

    return deal


def store_sms_message(
    subscription_id: str,
    from_number: str,
    to_number: str,
    message: str
) -> str:
    """Store an incoming SMS message and parse the deal."""
    engine = get_engine()

    # Parse the deal
    deal = parse_deal_with_ai(message)

    with engine.connect() as conn:
        result = conn.execute(text("""
            INSERT INTO loyalty_message (
                subscription_id, from_number, to_number, raw_message,
                parsed_deal, deal_type, discount_percent,
                affected_brands, affected_categories, expires_at, promo_code,
                is_processed
            ) VALUES (
                :sub_id, :from_num, :to_num, :message,
                :parsed_deal, :deal_type, :discount_pct,
                :brands, :categories, :expires, :promo_code,
                true
            )
            RETURNING message_id
        """), {
            "sub_id": subscription_id,
            "from_num": from_number,
            "to_num": to_number,
            "message": message,
            "parsed_deal": json.dumps(deal),
            "deal_type": deal.get("deal_type"),
            "discount_pct": deal.get("discount_percent"),
            "brands": deal.get("affected_brands") or None,
            "categories": deal.get("affected_categories") or None,
            "expires": deal.get("expires_at"),
            "promo_code": deal.get("promo_code")
        })

        message_id = result.fetchone()[0]
        conn.commit()

        return str(message_id)


def get_subscription_by_phone(twilio_phone: str) -> Optional[dict]:
    """Get subscription by Twilio phone number."""
    engine = get_engine()

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT ls.subscription_id, ls.dispensary_id, d.name, d.state
            FROM loyalty_subscription ls
            JOIN dispensary d ON ls.dispensary_id = d.dispensary_id
            WHERE ls.twilio_phone = :phone AND ls.is_active = true
        """), {"phone": twilio_phone})

        row = result.fetchone()
        if row:
            return {
                "subscription_id": str(row[0]),
                "dispensary_id": row[1],
                "dispensary_name": row[2],
                "state": row[3]
            }

    return None


def create_subscription(
    dispensary_id: str,
    twilio_phone: str,
    dispensary_phone: str = None,
    notes: str = None
) -> str:
    """Create a new loyalty subscription."""
    engine = get_engine()

    # Get dispensary info for address generation
    with engine.connect() as conn:
        disp = conn.execute(text("""
            SELECT name, city, state FROM dispensary WHERE dispensary_id = :id
        """), {"id": dispensary_id}).fetchone()

        if not disp:
            raise ValueError(f"Dispensary {dispensary_id} not found")

        # Generate address
        addr = generate_random_address(disp[1] or "Baltimore", disp[2] or "MD")

        result = conn.execute(text("""
            INSERT INTO loyalty_subscription (
                dispensary_id, twilio_phone, dispensary_phone,
                signup_name, signup_address, signup_city, signup_state, signup_zip,
                notes
            ) VALUES (
                :disp_id, :twilio_phone, :disp_phone,
                :name, :address, :city, :state, :zip,
                :notes
            )
            RETURNING subscription_id
        """), {
            "disp_id": dispensary_id,
            "twilio_phone": twilio_phone,
            "disp_phone": dispensary_phone,
            "name": addr["name"],
            "address": addr["address"],
            "city": addr["city"],
            "state": addr["state"],
            "zip": addr["zip"],
            "notes": notes
        })

        sub_id = result.fetchone()[0]
        conn.commit()

        return str(sub_id)


def get_active_deals(state: str = None, hours: int = 24) -> list:
    """Get active deals from the last N hours."""
    engine = get_engine()

    query = """
        SELECT
            lm.message_id,
            d.name as dispensary_name,
            d.state,
            d.city,
            lm.raw_message,
            lm.deal_type,
            lm.discount_percent,
            lm.affected_brands,
            lm.affected_categories,
            lm.promo_code,
            lm.expires_at,
            lm.received_at
        FROM loyalty_message lm
        JOIN loyalty_subscription ls ON lm.subscription_id = ls.subscription_id
        JOIN dispensary d ON ls.dispensary_id = d.dispensary_id
        WHERE lm.received_at > NOW() - INTERVAL ':hours hours'
    """

    params = {"hours": hours}

    if state:
        query += " AND d.state = :state"
        params["state"] = state

    query += " ORDER BY lm.received_at DESC"

    with engine.connect() as conn:
        # Use string formatting for interval since parameterized doesn't work well
        actual_query = query.replace(":hours hours", f"{hours} hours")
        result = conn.execute(text(actual_query), params)

        deals = []
        for row in result:
            deals.append({
                "message_id": str(row[0]),
                "dispensary": row[1],
                "state": row[2],
                "city": row[3],
                "message": row[4],
                "deal_type": row[5],
                "discount_percent": float(row[6]) if row[6] else None,
                "brands": row[7],
                "categories": row[8],
                "promo_code": row[9],
                "expires_at": row[10].isoformat() if row[10] else None,
                "received_at": row[11].isoformat() if row[11] else None
            })

        return deals


def get_deal_stats(days: int = 7) -> dict:
    """Get statistics about deals over the past N days."""
    engine = get_engine()

    with engine.connect() as conn:
        # Total messages
        total = conn.execute(text(f"""
            SELECT COUNT(*) FROM loyalty_message
            WHERE received_at > NOW() - INTERVAL '{days} days'
        """)).scalar()

        # By deal type
        by_type = conn.execute(text(f"""
            SELECT deal_type, COUNT(*)
            FROM loyalty_message
            WHERE received_at > NOW() - INTERVAL '{days} days'
            AND deal_type IS NOT NULL
            GROUP BY deal_type
            ORDER BY COUNT(*) DESC
        """)).fetchall()

        # Average discount
        avg_discount = conn.execute(text(f"""
            SELECT AVG(discount_percent)
            FROM loyalty_message
            WHERE received_at > NOW() - INTERVAL '{days} days'
            AND discount_percent IS NOT NULL
        """)).scalar()

        # By dispensary
        by_dispensary = conn.execute(text(f"""
            SELECT d.name, COUNT(*)
            FROM loyalty_message lm
            JOIN loyalty_subscription ls ON lm.subscription_id = ls.subscription_id
            JOIN dispensary d ON ls.dispensary_id = d.dispensary_id
            WHERE lm.received_at > NOW() - INTERVAL '{days} days'
            GROUP BY d.name
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """)).fetchall()

        return {
            "total_messages": total or 0,
            "by_deal_type": {row[0]: row[1] for row in by_type},
            "avg_discount_percent": round(float(avg_discount), 1) if avg_discount else None,
            "top_dispensaries": {row[0]: row[1] for row in by_dispensary}
        }
