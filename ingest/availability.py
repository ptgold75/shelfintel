from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import select

from core.models import RawMenuItem, MenuItemState, MenuItemEvent


def utcnow():
    return datetime.now(timezone.utc)


def update_availability(session, *, dispensary_id: str, scrape_run_id: str) -> dict:
    """
    Derive availability state + events from immutable raw_menu_item rows for a scrape_run.

    Uses provider_product_id as the stable SKU key.
    Returns a stats dict for logging/UI.
    """

    # Load all items seen in this scrape (must have provider_product_id)
    rows = session.execute(
        select(
            RawMenuItem.provider_product_id,
            RawMenuItem.raw_name,
            RawMenuItem.raw_category,
            RawMenuItem.raw_brand,
        ).where(
            RawMenuItem.scrape_run_id == scrape_run_id,
            RawMenuItem.dispensary_id == dispensary_id,
            RawMenuItem.provider_product_id.is_not(None),
        )
    ).all()

    # Deduplicate by provider_product_id (keep last occurrence)
    seen_meta = {}
    for r in rows:
        if r.provider_product_id:
            seen_meta[r.provider_product_id] = r

    seen_ids = set(seen_meta.keys())
    now = utcnow()

    # Existing states for this dispensary
    existing_states = session.execute(
        select(MenuItemState).where(MenuItemState.dispensary_id == dispensary_id)
    ).scalars().all()

    state_by_id = {s.provider_product_id: s for s in existing_states}

    appeared_events = 0
    disappeared_events = 0
    new_states = 0
    listed_updates = 0

    # 1) Mark all seen IDs as currently listed (create or update)
    for pid in seen_ids:
        meta = seen_meta[pid]

        if pid not in state_by_id:
            # First time ever seen (for this dispensary)
            s = MenuItemState(
                dispensary_id=dispensary_id,
                provider_product_id=pid,
                raw_name=getattr(meta, "raw_name", None),
                raw_category=getattr(meta, "raw_category", None),
                raw_brand=getattr(meta, "raw_brand", None),
                first_seen_at=now,
                last_seen_at=now,
                currently_listed=1,
                last_missing_at=None,
            )
            session.add(s)
            new_states += 1

            session.add(
                MenuItemEvent(
                    dispensary_id=dispensary_id,
                    scrape_run_id=scrape_run_id,
                    provider_product_id=pid,
                    event_type="appeared",
                    event_at=now,
                    raw_name=getattr(meta, "raw_name", None),
                    raw_category=getattr(meta, "raw_category", None),
                    raw_brand=getattr(meta, "raw_brand", None),
                )
            )
            appeared_events += 1
        else:
            s = state_by_id[pid]
            was_listed = bool(s.currently_listed)

            s.last_seen_at = now
            s.currently_listed = 1
            s.raw_name = getattr(meta, "raw_name", s.raw_name)
            s.raw_category = getattr(meta, "raw_category", s.raw_category)
            s.raw_brand = getattr(meta, "raw_brand", s.raw_brand)

            listed_updates += 1

            if not was_listed:
                s.last_missing_at = None
                session.add(
                    MenuItemEvent(
                        dispensary_id=dispensary_id,
                        scrape_run_id=scrape_run_id,
                        provider_product_id=pid,
                        event_type="appeared",
                        event_at=now,
                        raw_name=getattr(meta, "raw_name", None),
                        raw_category=getattr(meta, "raw_category", None),
                        raw_brand=getattr(meta, "raw_brand", None),
                    )
                )
                appeared_events += 1

    # 2) Anything previously listed but not seen now => disappeared
    for s in existing_states:
        if bool(s.currently_listed) and (s.provider_product_id not in seen_ids):
            s.currently_listed = 0
            s.last_missing_at = now

            session.add(
                MenuItemEvent(
                    dispensary_id=dispensary_id,
                    scrape_run_id=scrape_run_id,
                    provider_product_id=s.provider_product_id,
                    event_type="disappeared",
                    event_at=now,
                    raw_name=s.raw_name,
                    raw_category=s.raw_category,
                    raw_brand=s.raw_brand,
                )
            )
            disappeared_events += 1

    return {
        "seen_in_scrape": len(seen_ids),
        "new_states": new_states,
        "listed_updates": listed_updates,
        "appeared_events": appeared_events,
        "disappeared_events": disappeared_events,
    }
