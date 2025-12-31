import json
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "https://www.gleaf.com/stores/maryland/rockville/shop"
OUTDIR = Path("sweed_capture_full_debug")
OUTDIR.mkdir(exist_ok=True)

def safe_name(url: str) -> str:
    return url.split("/")[-1].split("?")[0].replace(":", "_")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        def save_req(req):
            if "/_api/proxy/Products/" not in req.url:
                return
            print("REQ:", req.method, req.url)
            rec = {
                "url": req.url,
                "method": req.method,
                "headers": req.headers,
                "post_data": req.post_data,
            }
            fname = OUTDIR / f"REQ_{safe_name(req.url)}.json"
            fname.write_text(json.dumps(rec, indent=2), encoding="utf-8")

        def save_res(resp):
            if "/_api/proxy/Products/" not in resp.url:
                return
            print("RES:", resp.status, resp.url)
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
            fname = OUTDIR / f"RES_{safe_name(resp.url)}.json"
            fname.write_text(json.dumps(rec, indent=2), encoding="utf-8")

        page.on("request", save_req)
        page.on("response", save_res)

        print("Opening:", URL)
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)

        # age gate
        for label in ["I am 21", "I’m 21", "I'm 21", "Yes", "Enter", "Continue", "Agree"]:
            try:
                btn = page.get_by_role("button", name=label)
                if btn.count() > 0:
                    btn.first.click(timeout=2000)
                    print("Clicked age gate:", label)
                    break
            except Exception:
                pass

        page.wait_for_timeout(8000)

        # screenshot of where we are
        page.screenshot(path=str(OUTDIR / "after_load.png"), full_page=True)

        # Try clicking into a category card / carousel tile by text
        for label in ["Flower", "Vapes", "Edibles", "Concentrates"]:
            try:
                loc = page.locator(f"text={label}")
                if loc.count() > 0:
                    loc.first.click(timeout=4000)
                    print("Clicked text:", label)
                    page.wait_for_timeout(5000)
                    break
            except Exception:
                pass

        # Try search (often forces SearchProducts)
        try:
            sb = page.get_by_placeholder("Search")
            if sb.count() > 0:
                sb.first.click()
                sb.first.fill("vape")
                print("Typed search: vape")
                page.wait_for_timeout(6000)
        except Exception:
            pass

        # Scroll a bunch
        for _ in range(8):
            page.mouse.wheel(0, 3500)
            page.wait_for_timeout(1500)

        page.screenshot(path=str(OUTDIR / "after_actions.png"), full_page=True)
        page.wait_for_timeout(8000)

        browser.close()

    print("✅ Done. Files saved in:", OUTDIR)

if __name__ == "__main__":
    main()
