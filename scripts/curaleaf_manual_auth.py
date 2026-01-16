#!/usr/bin/env python3
"""
Manual Curaleaf Authentication Script

Run this script to:
1. Open a browser window
2. Manually complete the age verification
3. Save cookies for automated scraping

Usage:
    python scripts/curaleaf_manual_auth.py
"""

import asyncio
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.async_api import async_playwright

COOKIE_FILE = "data/curaleaf_cookies.json"
STORAGE_FILE = "data/curaleaf_storage.json"


async def manual_auth():
    """Launch browser for manual age verification."""

    os.makedirs("data", exist_ok=True)

    async with async_playwright() as p:
        # Launch VISIBLE browser
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("=" * 60)
        print("CURALEAF MANUAL AUTHENTICATION")
        print("=" * 60)
        print()
        print("Instructions:")
        print("  1. Complete the age verification in the browser:")
        print("     - Select 'Maryland' from dropdown")
        print("     - Click 'Select date' and pick a birthday (1990 or earlier)")
        print("     - Click 'I'm over 21'")
        print("  2. Wait for the MENU page to load")
        print("  3. Come back here and press ENTER")
        print()
        print("=" * 60)

        # Navigate to Curaleaf
        await page.goto("https://curaleaf.com/stores/curaleaf-md-gaithersburg-montgomery-village-au")

        # Wait for user
        input("\n>>> Press ENTER after you see the menu page...")

        current_url = page.url
        print(f"\nCurrent URL: {current_url}")

        if 'age-gate' not in current_url:
            print("\n✓ SUCCESS - Past age gate!")

            # Capture cookies
            cookies = await context.cookies()

            print(f"\nCaptured {len(cookies)} cookies:")
            print("-" * 40)

            for c in cookies:
                expiry = c.get('expires', -1)
                if expiry == -1:
                    exp_str = "Session (browser close)"
                elif expiry > 0:
                    exp_date = datetime.fromtimestamp(expiry)
                    days_left = (exp_date - datetime.now()).days
                    exp_str = f"{exp_date.strftime('%Y-%m-%d')} ({days_left} days)"
                else:
                    exp_str = "Unknown"

                if 'curaleaf' in c.get('domain', ''):
                    print(f"  ✓ {c['name']}: expires {exp_str}")

            # Save cookies
            with open(COOKIE_FILE, 'w') as f:
                json.dump(cookies, f, indent=2)
            print(f"\n✓ Cookies saved to: {COOKIE_FILE}")

            # Save localStorage
            local_storage = await page.evaluate("() => Object.entries(localStorage)")
            storage_dict = {k: v for k, v in local_storage}
            with open(STORAGE_FILE, 'w') as f:
                json.dump(storage_dict, f, indent=2)
            print(f"✓ localStorage saved to: {STORAGE_FILE}")

            # Test the cookies immediately
            print("\n" + "=" * 60)
            print("TESTING COOKIES...")
            print("=" * 60)

            # Create new context with saved cookies
            test_context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            await test_context.add_cookies(cookies)
            test_page = await test_context.new_page()

            # Try loading a different Curaleaf store
            await test_page.goto("https://curaleaf.com/stores/curaleaf-md-reisterstown-au")
            await asyncio.sleep(3)

            if 'age-gate' not in test_page.url:
                print("✓ Cookies work for other MD stores!")
            else:
                print("✗ Cookies may be store-specific")

            await test_context.close()

        else:
            print("\n✗ Still on age gate - try again")

        await browser.close()

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Run: python scripts/scrape_curaleaf.py")
    print("  2. Cookies should last ~7-30 days")
    print("  3. Re-run this script if scraping starts failing")


if __name__ == "__main__":
    asyncio.run(manual_auth())
