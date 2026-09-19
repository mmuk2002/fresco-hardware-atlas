"""Browser smoke checks against an isolated local review store.

Requires the optional Playwright package and Chromium (or installed Edge).
Start the API with FRESCO_DATA_DIR pointing at tmp/ui-store, register/extract a
real specification, then run: python scripts/ui_smoke.py --url http://127.0.0.1:8001
The test saves corrections: do not point it at your working review store.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8001")
    parser.add_argument("--screenshots", type=Path, default=Path("tmp/screenshots"))
    args = parser.parse_args()
    url = args.url.rstrip("/")
    args.screenshots.mkdir(parents=True, exist_ok=True)
    with urlopen(f"{url}/api/documents") as response:
        documents = json.load(response)
    assert documents, "The smoke store needs one registered and extracted real PDF."
    with urlopen(f"{url}/api/documents/{documents[0]['id']}") as response:
        result = json.load(response)
    selected = result["sets"][0]
    assert selected["components"], "The first set must have at least one component."
    original_qty = selected["components"][0]["qty"]
    original_notes = selected["components"][0]["notes"]
    errors: list[str] = []
    checks: list[str] = []

    with sync_playwright() as playwright:
        edge = Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
        options = {"executable_path": str(edge)} if edge.exists() else {}
        browser = playwright.chromium.launch(headless=True, **options)
        context = browser.new_context(viewport={"width": 1512, "height": 1100}, device_scale_factor=1)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url, wait_until="networkidle")
        expect(page.locator("#workspace")).to_be_visible()
        expect(page.locator("#stat-sets")).to_have_text(str(len(result["sets"])))
        page.wait_for_function("document.querySelector('#source-image').naturalWidth > 0")
        assert page.locator(".bbox-overlay").count() > 0
        page.screenshot(path=str(args.screenshots / "review-desktop.png"), full_page=True)
        checks.append("real PDF loading, extracted set counts, source image and set overlays")

        quantity = page.locator('[data-field="qty"]').first
        quantity.fill("")
        page.locator('[data-field="notes"]').first.fill("Browser smoke correction")
        expect(page.locator("#save-button")).to_be_enabled()
        if len(result["sets"]) > 1:
            page.locator(f'[data-set-id="{result["sets"][1]["id"]}"]').click()
            page.locator(f'[data-set-id="{selected["id"]}"]').click()
            expect(page.locator('[data-field="qty"]').first).to_have_value("")
            expect(page.locator('[data-field="notes"]').first).to_have_value("Browser smoke correction")
        with page.expect_response(lambda response: response.request.method == "PUT") as response_info:
            page.locator("#save-button").click()
        saved = response_info.value.json()
        assert saved["components"][0]["qty"] is None
        assert saved["components"][0]["notes"] == "Browser smoke correction"
        assert saved["corrected"] is True
        expect(page.locator("#save-button")).to_be_disabled()
        checks.append("draft retention between sets, null quantity, full-set save and correction flag")

        count = page.locator("#component-rows tr").count()
        page.locator("#add-component").click()
        expect(page.locator("#component-rows tr")).to_have_count(count + 1)
        page.locator('[data-field="description"]').last.fill("Temporary review row")
        page.get_by_role("button", name=f"Remove component {count + 1}", exact=True).click()
        expect(page.locator("#component-rows tr")).to_have_count(count)
        expect(page.locator("#save-button")).to_be_disabled()
        checks.append("add/remove component rows and accurate unsaved state")

        page.locator("#export-button").click()
        with page.expect_download() as download_info:
            page.locator("#export-json").click()
        exported = json.loads(Path(download_info.value.path()).read_text(encoding="utf-8"))
        assert exported["sets"][0]["components"][0]["notes"] == "Browser smoke correction"
        page.locator("#export-button").click()
        with page.expect_download() as download_info:
            page.locator("#export-csv").click()
        assert "Browser smoke correction" in Path(download_info.value.path()).read_text(encoding="utf-8")
        checks.append("JSON and CSV downloads include persisted corrections")

        page.locator('[data-field="qty"]').first.fill("" if original_qty is None else str(original_qty))
        page.locator('[data-field="notes"]').first.fill(original_notes or "")
        if page.locator("#save-button").is_enabled():
            with page.expect_response(lambda response: response.request.method == "PUT"):
                page.locator("#save-button").click()
        expect(page.locator("#save-button")).to_be_disabled()
        page.locator('[data-field="notes"]').first.fill("Discard me")
        page.locator("#reset-button").click()
        expect(page.locator('[data-field="notes"]').first).to_have_value(original_notes or "")

        page.locator("#set-search").fill("zzzz-no-matching-hardware-set")
        expect(page.locator("#no-sets")).to_be_visible()
        page.locator("#set-search").fill("")
        page.locator("#set-filter").select_option("not_used")
        expected_not_used = sum(item["status"] == "not_used" for item in result["sets"])
        expect(page.locator(".set-item")).to_have_count(expected_not_used)
        page.locator("#set-filter").select_option("all")
        page.locator("#document-search").fill("zzzz-no-matching-document")
        expect(page.locator(".document-item")).to_have_count(0)
        page.locator("#document-search").fill("")
        expect(page.locator(".document-item")).to_have_count(len(documents))
        checks.append("discard, library search, set search and not-used filter")

        page.locator("#zoom-in").click()
        expect(page.locator("#zoom-value")).to_have_text("125%")
        page.locator("#zoom-reset").click()
        expect(page.locator("#zoom-value")).to_have_text("Fit")
        start_page = int(page.locator("#page-select").input_value())
        if start_page < result["page_count"]:
            page.locator("#next-page").click()
            expect(page.locator("#page-select")).to_have_value(str(start_page + 1))
            page.locator("#previous-page").click()
        multipage = next((item for item in result["sets"] if len({location["page"] for location in item["locations"]}) > 1), None)
        if multipage:
            page.locator(f'[data-set-id="{multipage["id"]}"]').click()
            second_page = sorted({location["page"] for location in multipage["locations"]})[1]
            page.locator("#page-select").select_option(str(second_page))
            expect(page.locator(".bbox-overlay")).not_to_have_count(0)
        checks.append("source zoom, page navigation, and multi-page set overlays where present")

        page.set_viewport_size({"width": 390, "height": 844})
        page.screenshot(path=str(args.screenshots / "review-mobile.png"), full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "Mobile page overflows horizontally"
        checks.append("390px mobile layout without page overflow")

        page.set_viewport_size({"width": 1512, "height": 1100})
        page.route("**/api/documents", lambda route: route.fulfill(status=503, content_type="application/json", body='{"detail":"Smoke test: library temporarily unavailable"}'))
        page.reload(wait_until="networkidle")
        expect(page.locator("#notice")).to_contain_text("library temporarily unavailable")
        page.unroute("**/api/documents")
        page.reload(wait_until="networkidle")
        expect(page.locator("#workspace")).to_be_visible()
        checks.append("visible API failure and successful recovery")

        assert not errors, "Browser errors: " + "\n".join(errors)
        browser.close()
    print(json.dumps({"status": "passed", "checks": checks, "browser_errors": errors, "screenshots": str(args.screenshots)}, indent=2))


if __name__ == "__main__":
    main()
