import json
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "https://www.gleaf.com/stores/maryland/rockville/shop"
OUTDIR = Path("sweed_capture")
OUTDIR.mkdir(exist_ok=True)

def safe_name(url: str) -> str:
    return url.split("/")[-1].replace("?", "_").replace("&", "_")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        def handle_request(req):
            if "/_api/proxy/" not in req.url:
                return
            if req.method != "POST":
                return
            try:
                post = req.post_data
            except Exception:
                post = None

            rec = {
                "method": req.method,
                "url": req.url,
                "headers": req.headers,
                "post_data": post,
            }
            fname = OUTDIR / f"REQ_{safe_name(req.url)}.json"
            fname.write_text(json.dumps(rec, indent=2), encoding="utf-8")

        def handle_response(resp):
            if "/_api/proxy/" not in resp.url:
                return
            # only save JSON responses
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
            rec = {
                "status": resp.status,
                "url": resp.url,
                "data": data,
            }
            fname = OUTDIR / f"RES_{safe_name(resp.url)}.json"
            fname.write_text(json.dumps(rec, indent=2), encoding="utf-8")

        page.on("request", handle_request)
        page.on("response", handle_response)

        page.goto(URL, wait_until="domcontentloaded", timeout=60000)

        # Age gate clicks (if present)
        for label in ["I am 21", "I’m 21", "I'm 21", "Yes", "Enter", "Continue", "Agree"]:
            try:
                btn = page.get_by_role("button", name=label)
                if btn.count() > 0:
                    btn.first.click(timeout=2000)
                    break
            except Exception:
                pass

        # Wait for initial API calls
        page.wait_for_timeout(8000)

        # Try to trigger more product calls:
        # click Flower if exists, then scroll a few times.
        try:
            flower = page.get_by_role("button", name="Flower")
            if flower.count() > 0:
                flower.first.click(timeout=3000)
                page.wait_for_timeout(2000)
        except Exception:
            pass

        for _ in range(8):
            page.mouse.wheel(0, 2500)
            page.wait_for_timeout(1200)

        # Try clicking "Next" if there is pagination
        for label in ["Next", "›", "→", "Next page"]:
            try:
                nxt = page.get_by_role("button", name=label)
                if nxt.count() > 0 and not nxt.first.is_disabled():
                    nxt.first.click(timeout=2500)
                    page.wait_for_timeout(2500)
                    break
            except Exception:
                pass

        page.wait_for_timeout(5000)

        browser.close()

    print("✅ Saved request/response JSON in ./sweed_capture/")

if __name__ == "__main__":
    main()
