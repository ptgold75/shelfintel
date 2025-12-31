import sys, json
from pathlib import Path
from playwright.sync_api import sync_playwright

DEFAULT_URL = "https://www.gleaf.com/stores/maryland/rockville/shop/recreational/menu?filters=%7B%22category%22%3A%5B495364%5D%7D"
URL = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL

OUTDIR = Path("sweed_capture_menu")
OUTDIR.mkdir(exist_ok=True)

def safe_name(url: str) -> str:
    return url.split("/")[-1].split("?")[0]

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        def save_req(req):
            if "/_api/proxy/Products/" not in req.url:
                return
            if req.method != "POST":
                return
            rec = {"url": req.url, "headers": req.headers, "post_data": req.post_data}
            (OUTDIR / f"REQ_{safe_name(req.url)}.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
            print("REQ:", req.method, req.url)

        def save_res(resp):
            if "/_api/proxy/Products/" not in resp.url:
                return
            try:
                ct = resp.headers.get("content-type", "")
            except Exception:
                ct = ""
            if "application/json" not in ct:
                return
            try:
                data = resp.json()
            except Exception:
                return
            rec = {"url": resp.url, "status": resp.status, "data": data}
            (OUTDIR / f"RES_{safe_name(resp.url)}.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
            print("RES:", resp.status, resp.url)

        page.on("request", save_req)
        page.on("response", save_res)

        print("Opening:", URL)
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)

        # Age gate
        for label in ["I am 21", "I’m 21", "I'm 21", "Yes", "Enter", "Continue", "Agree"]:
            try:
                btn = page.get_by_role("button", name=label)
                if btn.count() > 0:
                    btn.first.click(timeout=4000)
                    print("Clicked age gate:", label)
                    break
            except Exception:
                pass

        # Wait for listing page to load & fire API requests
        page.wait_for_timeout(12000)

        # Scroll to force additional page loads if infinite scroll
        for _ in range(8):
            page.mouse.wheel(0, 4500)
            page.wait_for_timeout(1500)

        page.screenshot(path=str(OUTDIR / "menu_page.png"), full_page=True)
        browser.close()

    print("✅ Saved files to ./sweed_capture_menu/")

if __name__ == "__main__":
    main()
