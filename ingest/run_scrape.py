import os, sys

# Force project root onto path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
from datetime import datetime, timezone

from core.db import get_session
from core.models import Dispensary, ScrapeRun, RawMenuItem

from ingest.availability import update_availability

from ingest.providers.generic_html import fetch_menu_items as fetch_generic
from ingest.providers.gleaf_playwright import fetch_menu_items as fetch_gleaf
from ingest.providers.sweed_provider import fetch_menu_items as fetch_sweed


def fetch_items(disp):
    provider = (disp.menu_provider or "").lower()

    # Preferred for gLeaf/Sweed sites: full catalog via API
    if provider in ["sweed", "sweed_api"]:
        return fetch_sweed(disp.menu_url)

    # Legacy browser automation
    if provider == "gleaf":
        return fetch_gleaf(disp.menu_url)

    return fetch_generic(disp.menu_url)


def main():
    db = get_session()

    disp = db.query(Dispensary).filter(Dispensary.menu_url.isnot(None)).first()
    if not disp:
        print("❌ No dispensary with a menu_url found.")
        return

    scrape = ScrapeRun(
        dispensary_id=disp.dispensary_id,
        status="started",
        started_at=datetime.now(timezone.utc),
    )
    db.add(scrape)
    db.commit()

    try:
        print("DEBUG provider =", disp.menu_provider)

        items = fetch_items(disp)

        print("DEBUG items fetched =", len(items))

        for it in items:
            db.add(
                RawMenuItem(
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
                )
            )

        # Commit raw items so availability logic can query them
        db.commit()

        stats = update_availability(
            db,
            dispensary_id=disp.dispensary_id,
            scrape_run_id=scrape.scrape_run_id,
        )
        db.commit()

        print("✅ Availability updated:", stats)

        scrape.status = "success"
        scrape.records_found = len(items)
        scrape.finished_at = datetime.now(timezone.utc)
        db.commit()

        print(f"✅ Scraped {len(items)} items for {disp.name} (provider={disp.menu_provider})")

    except Exception as e:
        scrape.status = "fail"
        scrape.error_message = str(e)
        scrape.finished_at = datetime.now(timezone.utc)
        db.commit()
        print("❌ Scrape failed:", e)
        raise


if __name__ == "__main__":
    main()
