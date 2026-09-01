"""Capture feature screenshots for static/helper/img (dev helper, not shipped)."""

from __future__ import annotations

import contextlib
import pathlib
import time

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
OUT = pathlib.Path(__file__).resolve().parent / "img"
OUT.mkdir(parents=True, exist_ok=True)

# (filename, hash route or absolute path, wait selector optional)
PAGES: list[tuple[str, str, str | None]] = [
    ("00-login.png", "/login", "text=系统登录"),
    ("01-dashboard.png", "/app#/dashboard", "text=本期核价产出"),
    ("02-stamping-parts.png", "/app#/stamping-parts", "text=冲压零件"),
    ("03-stamping-tonnage.png", "/app#/stamping-tonnage", None),
    ("04-stamping-process-fee.png", "/app#/stamping-process-fee", None),
    ("05-bom-material.png", "/app#/bom-material", None),
    ("06-bom-structure.png", "/app#/bom-structure", None),
    ("07-welding-unit-price.png", "/app#/bom-welding-unit-price", None),
    ("08-annual-part-price.png", "/app#/bom-annual-part-price", None),
    ("09-packaging-transport.png", "/app#/bom-packaging-transport-fee", None),
    ("10-welding-breakdown.png", "/app#/bom-welding-process-breakdown-list", None),
    ("11-l0-welding-fee.png", "/app#/bom-welding-fee-list", None),
    ("12-base-price.png", "/app#/base-price-download", None),
    ("13-policy.png", "/app#/steel-price-policy-download", None),
    ("14-scrap-price.png", "/app#/scrap-price", None),
    ("15-steel-price.png", "/app#/steel-price-list", None),
    ("16-stamping-part-cost.png", "/app#/stamping-part-cost", None),
    ("17-l0-assembly-cost.png", "/app#/assembly-cost", None),
    ("18-costing-engine.png", "/app#/costing", None),
    ("19-file-trace.png", "/app#/file-trace", None),
    ("20-settings.png", "/app#/settings", None),
]


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1,
        )
        page = context.new_page()

        # Login page screenshot first (logged out)
        page.goto(f"{BASE}/login", wait_until="networkidle")
        page.wait_for_selector("text=系统登录", timeout=15000)
        page.screenshot(path=str(OUT / "00-login.png"), full_page=False)
        print("saved 00-login.png")

        page.fill("#loginUsername", "admin")
        page.fill("#loginPassword", "admin123")
        page.click("#btnLogin")
        page.wait_for_url("**/app**", timeout=20000)
        time.sleep(1.5)

        for filename, route, wait_text in PAGES:
            if filename == "00-login.png":
                continue
            url = f"{BASE}{route}"
            page.goto(url, wait_until="networkidle")
            time.sleep(1.0)
            if wait_text:
                with contextlib.suppress(Exception):
                    page.wait_for_selector(wait_text, timeout=8000)
            else:
                # wait for page content mount
                try:
                    page.wait_for_selector("#pageContent", timeout=8000)
                    time.sleep(0.8)
                except Exception:
                    time.sleep(1.0)
            page.screenshot(path=str(OUT / filename), full_page=False)
            print(f"saved {filename}")

        # Sidebar open on dashboard
        page.goto(f"{BASE}/app#/dashboard", wait_until="networkidle")
        time.sleep(0.8)
        toggle = page.locator("#sidebarToggle, button[aria-label='打开导航']")
        if toggle.count():
            toggle.first.click()
            time.sleep(0.6)
            page.screenshot(path=str(OUT / "01b-sidebar.png"), full_page=False)
            print("saved 01b-sidebar.png")

        browser.close()
        print(f"done -> {OUT}")


if __name__ == "__main__":
    main()
