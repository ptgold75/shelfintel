from playwright.sync_api import sync_playwright

URL_HINTS = ["product", "menu", "strain", "flower", "vape", "edible", "concentrate"]

def _try_age_gate(page):
    # Try buttons
    for label in ["I am 21", "I’m 21", "I'm 21", "Yes", "Enter", "Continue", "Agree"]:
        try:
            btn = page.get_by_role("button", name=label)
            if btn.count() > 0:
                btn.first.click(timeout=2000)
                return True
        except Exception:
            pass
    return False

def fetch_menu_items(menu_url: str):
    items = []
    seen = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.goto(menu_url, wait_until="domcontentloaded", timeout=60000)
        _try_age_gate(page)

        # Give the app time to render, then scroll a few times to load items
        page.wait_for_timeout(4000)
        for _ in range(6):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(1200)

        # Heuristic selectors for product titles
        selectors = [
            "[data-testid*='product']",
            "[class*='product']",
            "article",
            "h3",
            "h2",
        ]

        for sel in selectors:
            loc = page.locator(sel)
            for i in range(min(loc.count(), 400)):
                try:
                    txt = loc.nth(i).inner_text(timeout=1000).strip()
                except Exception:
                    continue
                if not txt or len(txt) < 4:
                    continue
                # Split into lines; keep lines that look like product names
                for line in [x.strip() for x in txt.splitlines()]:
                    if len(line) < 4:
                        continue
                    # basic noise filter
                    if any(w.lower() in line.lower() for w in ["filter", "sort", "cart", "search", "hours", "directions"]):
                        continue
                    if line in seen:
                        continue
                    seen.add(line)
                    items.append({
                        "provider_product_id": None,
                        "name": line,
                        "category": None,
                        "brand": None,
                        "price": None,
                        "discount_price": None,
                        "discount_text": None,
                        "raw": {"source": "gleaf_playwright"}
                    })

        browser.close()

    return items
