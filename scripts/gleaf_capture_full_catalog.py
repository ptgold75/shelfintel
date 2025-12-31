import json
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "https://www.gleaf.com/stores/maryland/rockville/shop"
OUTDIR = Path("sweed_capture_full")
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
            rec = {
                "url": req.url,
                "headers": req.headers,
                "post_data": req.post_data,
            }
            fname = OUTDIR / f"REQ_{safe_name(req.url)}.json"
            fname.write_text(json.dumps(rec, indent=2), encoding="utf-8")
            print("✅ captured request:", req.url)

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
            fname = OUTDIR / f"RES_{safe_name(resp.url)}.json"
            fname.write_text(json.dumps(rec, indent=2), encoding="utf-8")

        page.on("request", save_req)
        page.on("response", save_res)

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

        # Try clicking "Flower" in a few ways to enter the full listing view
        clicked = False
        for selector_try in [
            lambda: page.get_by_role("button", name="Flower"),
            lambda: page.get_by_role("link", name="Flower"),
            lambda: page.locator("text=Flower"),
        ]:
            try:
                loc = selector_try()
                if loc.count() > 0:
                    loc.first.click(timeout=4000)
                    clicked = True
                    break
            except Exception:
                pass

        # Also try "See all" / "View all" if present (common in carousels)
        for label in ["See all", "See All", "View all", "View All"]:
            try:
                loc = page.get_by_role("link", name=label)
                if loc.count() > 0:
                    loc.first.click(timeout=4000)
                    clicked = True
                    break
            except Exception:
                pass

        page.wait_for_timeout(6000)

        # Trigger search (often forces SearchProducts endpoint)
        try:
            sb = page.get_by_placeholder("Search")
            if sb.count() > 0:
                sb.first.click()
                sb.first.fill("flower")
                page.wait_for_timeout(4000)
        except Exception:
            pass

        # Scroll and try pagination "Next" several times
        for _ in range(4):
            page.mouse.wheel(0, 4000)
            page.wait_for_timeout(1500)

            for next_label in ["Next", "›", "→", "Next page"]:
                try:
                    btn = page.get_by_role("button", name=next_label)
                    if btn.count() > 0 and not btn.first.is_disabled():
                        btn.first.click(timeout=3500)
                        page.wait_for_timeout(4500)
                        break
                except Exception:
                    pass

        page.wait_for_timeout(6000)
        browser.close()

    print("✅ Done. Check ./sweed_capture_full/")
