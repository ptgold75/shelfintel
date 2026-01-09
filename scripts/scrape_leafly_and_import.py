#!/usr/bin/env python3
"""Scrape dispensaries from Leafly and import them into the database."""

import requests
from bs4 import BeautifulSoup
import json
import time
import uuid
import re
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg://postgres:Tattershall2020@db.trteltlgtmcggdbrqwdw.supabase.co:5432/postgres"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

# All legal cannabis states
STATES = [
    ('florida', 'FL'),
    ('massachusetts', 'MA'),
    ('new-york', 'NY'),
    ('missouri', 'MO'),
    ('maine', 'ME'),
    ('minnesota', 'MN'),
    ('pennsylvania', 'PA'),
    ('ohio', 'OH'),
    ('virginia', 'VA'),
    ('connecticut', 'CT'),
    ('delaware', 'DE'),
    ('rhode-island', 'RI'),
    ('vermont', 'VT'),
    ('new-hampshire', 'NH'),
    ('arkansas', 'AR'),
    ('louisiana', 'LA'),
    ('oklahoma', 'OK'),
    ('texas', 'TX'),
    ('utah', 'UT'),
    ('west-virginia', 'WV'),
    ('north-dakota', 'ND'),
    ('south-dakota', 'SD'),
    ('montana', 'MT'),
    ('alaska', 'AK'),
    ('washington', 'WA'),
    ('oregon', 'OR'),
    ('hawaii', 'HI'),
    ('kentucky', 'KY'),
]


def get_engine():
    return create_engine(DATABASE_URL)


def clean_dispensary_name(name):
    """Clean up dispensary name by removing extra info."""
    # Remove common suffixes
    patterns = [
        r'(MED|REC)?\s*\d+\.\d+\(\d+\)',  # Ratings like "4.5(12)"
        r'Open until \d+[ap]m \w+',  # Hours
        r'\d+\.?\d*\s*mi away',  # Distance
        r'(Medical|Recreational)\s*Cannabis.*',
        r'\s*-\s*$',
    ]

    for pattern in patterns:
        name = re.sub(pattern, '', name, flags=re.IGNORECASE)

    # Clean up
    name = name.strip()
    name = re.sub(r'\s+', ' ', name)

    return name


def scrape_leafly_state(state_slug, state_abbrev, max_pages=5):
    """Scrape dispensaries from Leafly for a state."""
    dispensaries = []
    page = 0

    while page < max_pages:
        url = f"https://www.leafly.com/dispensaries/{state_slug}"
        if page > 0:
            url += f"?page={page}"

        print(f"  Fetching page {page}...", end=" ", flush=True)

        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code != 200:
                print(f"HTTP {resp.status_code}")
                break

            soup = BeautifulSoup(resp.text, 'html.parser')

            # Find dispensary links
            links = soup.find_all('a', href=lambda x: x and '/dispensary-info/' in x)

            if not links:
                print("no more")
                break

            seen = set()
            page_count = 0

            for link in links:
                href = link.get('href', '')
                if href in seen or not href:
                    continue
                seen.add(href)

                # Get name from link text
                name_raw = link.get_text(strip=True)
                if not name_raw or len(name_raw) < 3:
                    continue

                name = clean_dispensary_name(name_raw)
                if not name or len(name) < 3:
                    continue

                full_url = f"https://www.leafly.com{href}" if not href.startswith('http') else href

                # Extract slug for menu URL
                slug = href.split('/dispensary-info/')[-1].rstrip('/')

                dispensaries.append({
                    'name': name,
                    'leafly_url': full_url,
                    'leafly_slug': slug,
                    'state': state_abbrev,
                })
                page_count += 1

            print(f"{page_count} dispensaries")

            if page_count < 20:  # Likely last page
                break

            page += 1
            time.sleep(1)

        except Exception as e:
            print(f"Error: {e}")
            break

    return dispensaries


def import_to_database(dispensaries, engine):
    """Import dispensaries into the database."""
    with engine.connect() as conn:
        # Get existing dispensaries
        result = conn.execute(text("""
            SELECT name, state FROM dispensary WHERE is_active = true
        """))
        existing = set((r[0].lower(), r[1]) for r in result)

        added = 0
        skipped = 0

        for d in dispensaries:
            key = (d['name'].lower(), d['state'])
            if key in existing:
                skipped += 1
                continue

            try:
                dispensary_id = str(uuid.uuid4())
                conn.execute(text("""
                    INSERT INTO dispensary (dispensary_id, name, state, menu_url, menu_provider, is_active, source)
                    VALUES (:id, :name, :state, :url, 'leafly', true, 'leafly_scrape')
                    ON CONFLICT DO NOTHING
                """), {
                    "id": dispensary_id,
                    "name": d['name'],
                    "state": d['state'],
                    "url": d['leafly_url'],
                })
                added += 1
            except Exception as e:
                print(f"  Error adding {d['name']}: {e}")

        conn.commit()

    return added, skipped


def main():
    print("="*60)
    print("LEAFLY DISPENSARY SCRAPER & IMPORTER")
    print("="*60)

    engine = get_engine()

    total_found = 0
    total_added = 0
    total_skipped = 0

    for state_slug, state_abbrev in STATES:
        print(f"\n{state_abbrev} ({state_slug}):")

        dispensaries = scrape_leafly_state(state_slug, state_abbrev)
        total_found += len(dispensaries)

        if dispensaries:
            added, skipped = import_to_database(dispensaries, engine)
            total_added += added
            total_skipped += skipped
            print(f"  -> Added: {added}, Skipped: {skipped}")

        time.sleep(2)

    print(f"\n{'='*60}")
    print(f"TOTAL: Found {total_found}, Added {total_added}, Skipped {total_skipped}")
    print("="*60)


if __name__ == "__main__":
    main()
