from playwright.sync_api import sync_playwright

URL = "https://www.gleaf.com/stores/maryland/rockville/shop"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    page.goto(URL, wait_until="domcontentloaded", timeout=60000)

    # Try common age-gate patterns (buttons)
    for label in ["I am 21", "I’m 21", "I'm 21", "Yes", "Enter", "Continue", "Agree"]:
        try:
            btn = page.get_by_role("button", name=label)
            if btn.count() > 0:
                btn.first.click(timeout=2000)
                break
        except Exception:
            pass

    # Wait for content to render
    page.wait_for_timeout(6000)

    page.screenshot(path="gleaf_page.png", full_page=True)
    html = page.content()
    with open("gleaf_page.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("✅ Saved gleaf_page.png and gleaf_page.html")
    browser.close()
