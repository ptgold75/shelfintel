# ingest/availability.py
"""
Availability tracking - detects when products appear/disappear from menus.

Called after each scrape to update MenuItemState and create MenuItemEvent records.
"""

from datetime import datetime, timezone
from typing import Dict, Set

from sqlalchemy.orm import Session
from sqlalchemy import and_

from core.models import RawMenuItem, MenuItemState, MenuItemEvent


def update_availability(
    db: Session,
    dispensary_id: str,
    scrape_run_id: str,
) -> Dict[str, int]:
    """
    Update availability state based on the latest scrape.
    
    For each product in the scrape:
      - If new: create state record + "appeared" event
      - If existing: update last_seen_at
    
    For products in state but missing from scrape:
      - Mark as not currently_listed + "disappeared" event
    
    Returns dict with counts: {appeared, disappeared, unchanged}
    """
    now = datetime.now(timezone.utc)
    
    # Get all products from this scrape run
    scraped_items = db.query(RawMenuItem).filter(
        RawMenuItem.scrape_run_id == scrape_run_id,
        RawMenuItem.dispensary_id == dispensary_id,
    ).all()
    
    # Build set of provider_product_ids seen in this scrape
    seen_ids: Set[str] = set()
    scraped_by_id: Dict[str, RawMenuItem] = {}
    
    for item in scraped_items:
        if item.provider_product_id:
            seen_ids.add(item.provider_product_id)
            scraped_by_id[item.provider_product_id] = item
    
    # Get all existing state records for this dispensary
    existing_states = db.query(MenuItemState).filter(
        MenuItemState.dispensary_id == dispensary_id
    ).all()
    
    existing_by_id: Dict[str, MenuItemState] = {
        s.provider_product_id: s for s in existing_states
    }
    
    stats = {"appeared": 0, "disappeared": 0, "unchanged": 0}
    
    # Process scraped items
    for pid, item in scraped_by_id.items():
        if pid in existing_by_id:
            # Existing product - update last_seen
            state = existing_by_id[pid]
            state.last_seen_at = now
            state.updated_at = now
            
            # If it was marked as not listed, it's back
            if not state.currently_listed:
                state.currently_listed = True
                
                # Create "appeared" event (re-appeared)
                event = MenuItemEvent(
                    dispensary_id=dispensary_id,
                    scrape_run_id=scrape_run_id,
                    provider_product_id=pid,
                    event_type="appeared",
                    event_at=now,
                    raw_name=item.raw_name,
                    raw_category=item.raw_category,
                    raw_brand=item.raw_brand,
                )
                db.add(event)
                stats["appeared"] += 1
            else:
                stats["unchanged"] += 1
        else:
            # New product - create state + appeared event
            state = MenuItemState(
                dispensary_id=dispensary_id,
                provider_product_id=pid,
                raw_name=item.raw_name,
                raw_category=item.raw_category,
                raw_brand=item.raw_brand,
                first_seen_at=now,
                last_seen_at=now,
                currently_listed=True,
            )
            db.add(state)
            
            event = MenuItemEvent(
                dispensary_id=dispensary_id,
                scrape_run_id=scrape_run_id,
                provider_product_id=pid,
                event_type="appeared",
                event_at=now,
                raw_name=item.raw_name,
                raw_category=item.raw_category,
                raw_brand=item.raw_brand,
            )
            db.add(event)
            stats["appeared"] += 1
    
    # Check for disappeared products
    for pid, state in existing_by_id.items():
        if pid not in seen_ids and state.currently_listed:
            # Product was listed but not in this scrape - mark as disappeared
            state.currently_listed = False
            state.last_missing_at = now
            state.updated_at = now
            
            event = MenuItemEvent(
                dispensary_id=dispensary_id,
                scrape_run_id=scrape_run_id,
                provider_product_id=pid,
                event_type="disappeared",
                event_at=now,
                raw_name=state.raw_name,
                raw_category=state.raw_category,
                raw_brand=state.raw_brand,
            )
            db.add(event)
            stats["disappeared"] += 1
    
    return stats
