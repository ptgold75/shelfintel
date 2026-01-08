#!/usr/bin/env python3
"""Scrape dispensary data from Leafly for a given state."""

import json
import re
import time
import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

def scrape_leafly_state(state_slug, state_abbrev):
    """Scrape all dispensaries for a state from Leafly."""
    dispensaries = []
    page = 0

    while True:
        url = f"https://www.leafly.com/dispensaries/{state_slug}"
        if page > 0:
            url += f"?page={page}"

        print(f"Fetching {url}...")

        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code != 200:
                print(f"  Error: {resp.status_code}")
                break

            soup = BeautifulSoup(resp.text, 'html.parser')

            # Find dispensary cards
            cards = soup.find_all('div', {'data-testid': 'dispensary-card'})
            if not cards:
                # Try alternative selectors
                cards = soup.find_all('a', href=re.compile(r'/dispensary-info/'))

            if not cards:
                print(f"  No more dispensaries found on page {page}")
                break

            for card in cards:
                try:
                    # Extract name
                    name_elem = card.find(['h2', 'h3', 'span'], class_=re.compile(r'name|title', re.I))
                    if not name_elem:
                        name_elem = card.find('a')
                    name = name_elem.get_text(strip=True) if name_elem else None

                    # Extract address
                    addr_elem = card.find(['p', 'span', 'div'], class_=re.compile(r'address|location', re.I))
                    address = addr_elem.get_text(strip=True) if addr_elem else None

                    # Extract rating
                    rating_elem = card.find(['span', 'div'], class_=re.compile(r'rating|star', re.I))
                    rating = rating_elem.get_text(strip=True) if rating_elem else None

                    # Get link
                    link_elem = card.find('a', href=True)
                    link = link_elem['href'] if link_elem else None
                    if link and not link.startswith('http'):
                        link = f"https://www.leafly.com{link}"

                    if name:
                        dispensaries.append({
                            'name': name,
                            'address': address,
                            'rating': rating,
                            'url': link,
                            'state': state_abbrev,
                            'source': 'leafly'
                        })
                except Exception as e:
                    print(f"  Error parsing card: {e}")
                    continue

            print(f"  Found {len(cards)} dispensaries on page {page}")

            # Check for next page
            next_btn = soup.find('a', {'aria-label': 'Next'}) or soup.find('button', text=re.compile(r'Next|Load More', re.I))
            if not next_btn or len(cards) < 20:
                break

            page += 1
            time.sleep(1)  # Be polite

        except Exception as e:
            print(f"  Error fetching page: {e}")
            break

    return dispensaries


def main():
    states = [
        ('new-jersey', 'NJ'),
        ('illinois', 'IL'),
        ('colorado', 'CO'),
        ('michigan', 'MI'),
        ('arizona', 'AZ'),
        ('nevada', 'NV'),
        ('california', 'CA'),
        ('connecticut', 'CT'),
        ('ohio', 'OH'),
        ('maryland', 'MD'),
        ('mississippi', 'MS'),
    ]

    all_dispensaries = []

    for state_slug, state_abbrev in states:
        print(f"\n{'='*60}")
        print(f"Scraping {state_abbrev} ({state_slug})...")
        print('='*60)

        dispensaries = scrape_leafly_state(state_slug, state_abbrev)
        all_dispensaries.extend(dispensaries)
        print(f"Total for {state_abbrev}: {len(dispensaries)}")

        time.sleep(2)

    # Save results
    output_file = '/Users/gleaf/shelfintel/leafly_dispensaries.json'
    with open(output_file, 'w') as f:
        json.dump(all_dispensaries, f, indent=2)

    print(f"\n{'='*60}")
    print(f"TOTAL: {len(all_dispensaries)} dispensaries saved to {output_file}")
    print('='*60)


if __name__ == '__main__':
    main()
