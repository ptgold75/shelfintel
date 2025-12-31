from playwright.sync_api import sync_playwright

URL = "https://www.gleaf.com/stores/maryland/rockville/shop"

KEYWORDS = [
    "graphql", "products", "product", "menu", "inventory", "catalog",
    "search", "collections", "categories", "shop", "commerce", "store"
]

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        def log_request(req):
            u = req.url.lower()
            if any(k in u for k in KEYWORDS):
                print("REQ:", req.method, req.url)

        def log_response(resp):
            u = resp.url.lower()
            if any(k in u for k in KEYWORDS):
                try:
                    ct = resp.headers.get("content-type", "")
                except Exception:
                    ct = ""
                if "application/json" in ct or "graphql" in u:
                    print("RES:", resp.status, resp.url)

        page.on("request", log_request)
        page.on("response", log_response)

        page.goto(URL, wait_until="domcontentloaded", timeout=60000)

        # Try common age gate clicks
        for label in ["I am 21", "I’m 21", "I'm 21", "Yes", "Enter", "Continue", "Agree"]:
            try:
                btn = page.get_by_role("button", name=label)
                if btn.count() > 0:
                    btn.first.click(timeout=2000)
                    break
            except Exception:
                pass

        # Wait for menu to load + network calls to fire
        page.wait_for_timeout(12000)

        browser.close()

if __name__ == "__main__":
    main()
