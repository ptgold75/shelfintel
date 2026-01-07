# ingest/run_scrape.py
"""
Main scrape orchestrator - fetches menu items from all active dispensaries.

Usage:
    python ingest/run_scrape.py              # Scrape all active dispensaries
    python ingest/run_scrape.py --disp-id X  # Scrape specific dispensary
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone

# Force project root onto path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.db import get_session
from core.models import Dispensary, ScrapeRun, RawMenuItem
from ingest.availability import update_availability

# Provider imports
from ingest.providers.generic_html import fetch_menu_items as fetch_generic
from ingest.providers.gleaf_playwright import fetch_menu_items as fetch_gleaf
from ingest.providers.sweed_provider import fetch_menu_items as fetch_sweed
from ingest.providers.dutchie_provider import fetch_menu_items as fetch_dutchie
from ingest.providers.jane_provider import fetch_menu_items as fetch_jane


def _parse_provider_metadata(disp: Dispensary) -> dict:
    """Parse provider_metadata JSON from dispensary record."""
    if not disp.provider_metadata:
        return {}
    try:
        return json.loads(disp.provider_metadata)
    except (json.JSONDecodeError, TypeError):
        return {}


def fetch_items(disp: Dispensary) -> list:
    """Route to appropriate provider based on dispensary config."""
    provider = (disp.menu_provider or "").lower()
    metadata = _parse_provider_metadata(disp)

    print(f"  Provider: {provider}")
    print(f"  Metadata: {metadata}")

    if provider in ["sweed", "sweed_api"]:
        return fetch_sweed(
            menu_url=disp.menu_url,
            provider_metadata=metadata,
        )

    if provider == "dutchie":
        return fetch_dutchie(
            menu_url=disp.menu_url,
            provider_metadata=metadata,
        )

    if provider in ["jane", "iheartjane"]:
        return fetch_jane(
            menu_url=disp.menu_url,
            provider_metadata=metadata,
        )

    if provider == "gleaf":
        return fetch_gleaf(disp.menu_url)

    # Fallback to generic HTML scraper
    return fetch_generic(disp.menu_url)


def scrape_dispensary(db, disp: Dispensary) -> dict:
    """
    Scrape a single dispensary and update availability.
    Returns stats dict.
    """
    print(f"\n{'='*60}")
    print(f"Scraping: {disp.name}")
    print(f"  URL: {disp.menu_url}")
    
    # Create scrape run record
    scrape = ScrapeRun(
        dispensary_id=disp.dispensary_id,
        status="started",
        started_at=datetime.now(timezone.utc),
    )
    db.add(scrape)
    db.commit()
    
    try:
        items = fetch_items(disp)
        print(f"  Items fetched: {len(items)}")
        
        # Insert raw items
        for it in items:
            db.add(RawMenuItem(
                scrape_run_id=scrape.scrape_run_id,
                dispensary_id=disp.dispensary_id,
                raw_name=it.get("name"),
                raw_category=it.get("category"),
                raw_brand=it.get("brand"),
                raw_price=it.get("price"),
                raw_discount_price=it.get("discount_price"),
                raw_discount_text=it.get("discount_text"),
                provider_product_id=it.get("provider_product_id"),
                raw_json=json.dumps(it.get("raw", {})),
            ))
        db.commit()
        
        # Update availability tracking
        stats = update_availability(
            db,
            dispensary_id=disp.dispensary_id,
            scrape_run_id=scrape.scrape_run_id,
        )
        db.commit()
        
        # Mark success
        scrape.status = "success"
        scrape.records_found = len(items)
        scrape.finished_at = datetime.now(timezone.utc)
        db.commit()
        
        print(f"  ✅ Success: {len(items)} items")
        print(f"  Availability: {stats}")
        
        return {"status": "success", "items": len(items), "availability": stats}
        
    except Exception as e:
        scrape.status = "fail"
        scrape.error_message = str(e)[:2000]
        scrape.finished_at = datetime.now(timezone.utc)
        db.commit()
        
        print(f"  ❌ Failed: {e}")
        return {"status": "fail", "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Run menu scrapes")
    parser.add_argument("--disp-id", help="Specific dispensary ID to scrape")
    parser.add_argument("--all", action="store_true", help="Scrape all active dispensaries")
    args = parser.parse_args()
    
    db = get_session()
    
    # Build query
    query = db.query(Dispensary).filter(
        Dispensary.menu_url.isnot(None),
        Dispensary.is_active == True,
    )
    
    if args.disp_id:
        query = query.filter(Dispensary.dispensary_id == args.disp_id)
    
    dispensaries = query.all()
    
    if not dispensaries:
        print("❌ No active dispensaries with menu_url found.")
        return
    
    print(f"Found {len(dispensaries)} dispensary(ies) to scrape")
    
    results = []
    for disp in dispensaries:
        result = scrape_dispensary(db, disp)
        results.append({"name": disp.name, **result})
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    success = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "fail")
    print(f"Success: {success}, Failed: {failed}")
    
    for r in results:
        status_icon = "✅" if r["status"] == "success" else "❌"
        print(f"  {status_icon} {r['name']}: {r.get('items', 0)} items")


if __name__ == "__main__":
    main()

# Update analytics summaries after scraping
try:
    from scripts.update_analytics_summary import update_summaries
    update_summaries()
except Exception as e:
    print(f"Warning: Could not update summaries: {e}")
