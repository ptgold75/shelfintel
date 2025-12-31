from playwright.sync_api import sync_playwright

URL = "https://www.gleaf.com/stores/maryland/rockville/shop"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)

        # Age gate
        for label in ["I am 21", "I’m 21", "I'm 21", "Yes", "Enter", "Continue", "Agree"]:
            try:
                btn = page.get_by_role("button", name=label)
                if btn.count() > 0:
                    btn.first.click(timeout=2000)
                    break
            except Exception:
                pass

        page.wait_for_timeout(6000)

        # Find anything that contains text "Flower"
        loc = page.locator(":is(a,button,div,span) >> text=Flower")
        count = loc.count()
        print("Found elements containing 'Flower':", count)

        # Print details about up to 25 matches
        for i in range(min(count, 25)):
            el = loc.nth(i)
            try:
                tag = el.evaluate("e => e.tagName")
            except Exception:
                tag = "?"
            try:
                href = el.evaluate("e => e.getAttribute('href')")
            except Exception:
                href = None
            try:
                aria = el.evaluate("e => e.getAttribute('aria-label')")
            except Exception:
                aria = None
            try:
                text = el.inner_text(timeout=1000).strip().replace("\n", " ")
            except Exception:
                text = "(no text)"
            print(f"{i}: tag={tag} href={href} aria={aria} text='{text[:80]}'")

        browser.close()

if __name__ == "__main__":
    main()
