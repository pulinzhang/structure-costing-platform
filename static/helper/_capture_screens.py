"""Capture feature screenshots for static/helper/img (dev helper, not shipped)."""

from __future__ import annotations

import contextlib
import pathlib
import sqlite3
import sys
import time
from urllib.parse import urlencode

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
OUT = pathlib.Path(__file__).resolve().parent / "img"
OUT.mkdir(parents=True, exist_ok=True)

# (filename, hash route or absolute path, wait selector optional)
PAGES: list[tuple[str, str, str | None]] = [
    ("00-login.png", "/login", "text=系统登录"),
    ("01-dashboard.png", "/app#/dashboard", "text=本期核价产出"),
    ("15-steel-price.png", "/app#/steel-price-list", None),
    ("16-stamping-part-cost.png", "/app#/stamping-part-cost", None),
    ("17-l0-assembly-cost.png", "/app#/assembly-cost", None),
    ("18-costing-engine.png", "/app#/costing", "text=月度核价控制台"),
    ("19-procurement-contract.png", "/app#/procurement-contract-report", "text=导出协议"),
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
        page.goto(f"{BASE}/login", wait_until="domcontentloaded")
        page.wait_for_selector("text=系统登录", timeout=15000)
        llm_only = "--llm-only" in sys.argv
        restore_only = "--restore-only" in sys.argv
        if not llm_only and not restore_only:
            page.screenshot(path=str(OUT / "00-login.png"), full_page=False)
            print("saved 00-login.png")

        page.fill("#loginUsername", "admin")
        page.fill("#loginPassword", "admin123")
        page.click("#btnLogin")
        page.wait_for_url("**/app**", timeout=20000)
        time.sleep(1.5)

        if llm_only:
            _capture_llm(page)
            browser.close()
            print(f"done -> {OUT}")
            return

        if restore_only:
            _capture_assembly_restore(page)
            browser.close()
            print(f"done -> {OUT}")
            return

        for filename, route, wait_text in PAGES:
            if filename == "00-login.png":
                continue
            url = f"{BASE}{route}"
            page.goto(url, wait_until="domcontentloaded")
            _wait_page_ready(page, wait_text)
            page.screenshot(path=str(OUT / filename), full_page=False)
            print(f"saved {filename}")

        # Sidebar open on dashboard
        page.goto(f"{BASE}/app#/dashboard", wait_until="domcontentloaded")
        time.sleep(0.8)
        toggle = page.locator("#sidebarToggle, button[aria-label='打开导航']")
        if toggle.count():
            toggle.first.click()
            time.sleep(0.6)
            page.screenshot(path=str(OUT / "01b-sidebar.png"), full_page=False)
            print("saved 01b-sidebar.png")
            page.keyboard.press("Escape")
            time.sleep(0.4)

        _capture_llm(page)
        _capture_assembly_restore(page)

        browser.close()
        print(f"done -> {OUT}")


def _wait_page_ready(page, wait_text: str | None) -> None:
    """等页面挂上，并等列表「查询中」结束再截。"""
    time.sleep(0.4)
    if wait_text:
        with contextlib.suppress(Exception):
            page.wait_for_selector(wait_text, timeout=8000)
    else:
        with contextlib.suppress(Exception):
            page.wait_for_selector("#pageContent", timeout=8000)
    with contextlib.suppress(Exception):
        page.wait_for_function(
            """() => ![...document.querySelectorAll('button')].some(
                (btn) => (btn.textContent || '').includes('查询中')
            )""",
            timeout=20000,
        )
    time.sleep(0.6)


def _capture_llm(page) -> None:
    """右侧圆钮浮窗 + 打印新开页（/llm-analysis-report）。"""
    page.goto(f"{BASE}/app#/dashboard", wait_until="domcontentloaded")
    dock = page.locator("#llmAssistantDock")
    dock.wait_for(state="visible", timeout=15000)
    dock.click()
    page.wait_for_selector("#llmAssistantPanel:not(.hidden)", timeout=10000)

    report_id = _first_succeeded_report_id(page)
    if report_id is not None:
        page.locator("#llmAssistantPanel header").hover()
        page.locator("#llmBtnHistory").click()
        with contextlib.suppress(Exception):
            page.wait_for_selector(
                f'[data-action="open-report"][data-report-id="{report_id}"]',
                timeout=10000,
            )
        opener = page.locator(f'[data-action="open-report"][data-report-id="{report_id}"]')
        if opener.count():
            opener.first.click()
            with contextlib.suppress(Exception):
                page.wait_for_selector("#llmThread .llm-md", timeout=15000)
            time.sleep(0.6)
        else:
            time.sleep(0.6)
    else:
        time.sleep(0.8)

    # 最大化后整屏都是对话；滚到问句，并悬停标题让清空 / 历史 / 最大化 / 收起露出来。
    header = page.locator("#llmAssistantPanel header")
    header.hover()
    maximize = page.locator("#llmBtnMaximize")
    if maximize.count():
        maximize.click()
        time.sleep(0.4)
    page.locator("#llmThread").evaluate("element => { element.scrollTop = 0; }")
    header.hover()
    time.sleep(0.5)
    page.screenshot(path=str(OUT / "28-llm-assistant.png"), full_page=False)
    print("saved 28-llm-assistant.png")

    if report_id is None:
        print("skip 29-llm-analysis-report.png (no succeeded report)")
        return
    page.goto(
        f"{BASE}/llm-analysis-report?report_id={report_id}",
        wait_until="domcontentloaded",
    )
    with contextlib.suppress(Exception):
        page.wait_for_selector("text=AI 分析报告", timeout=12000)
    time.sleep(1.2)
    page.screenshot(path=str(OUT / "29-llm-analysis-report.png"), full_page=False)
    print("saved 29-llm-analysis-report.png")


def _first_succeeded_report_id(page) -> int | None:
    token = page.evaluate(
        """() => {
            try {
                const session = JSON.parse(localStorage.getItem('brabus_user') || 'null');
                return session && session.token ? session.token : '';
            } catch {
                return '';
            }
        }"""
    )
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = page.request.get(
        f"{BASE}/api/llm/reports",
        params={"status": "succeeded", "page": 1, "size": 20},
        headers=headers,
    )
    if not response.ok:
        print(f"list reports HTTP {response.status}")
        return None
    payload = response.json()
    items = (payload.get("data") or {}).get("items") or []
    costing = []
    fallback = []
    for item in items:
        raw_id = item.get("report_id")
        if raw_id is None:
            continue
        report_type = str(item.get("resolved_report_type") or "")
        if report_type == "usage_help":
            fallback.append(int(raw_id))
        else:
            costing.append(int(raw_id))
    for report_id in costing + fallback:
        if not _report_uses_old_list_name(page, headers, report_id):
            return report_id
    if costing:
        return costing[0]
    if fallback:
        return fallback[0]
    return None


def _report_uses_old_list_name(page, headers: dict, report_id: int) -> bool:
    """历史分析正文里的旧称呼（一览）不要再拍进帮助图。"""
    response = page.request.get(f"{BASE}/api/llm/reports/{report_id}", headers=headers)
    if not response.ok:
        return True
    markdown = str((response.json().get("data") or {}).get("markdown_content") or "")
    return "一览" in markdown


def _capture_assembly_restore(page) -> None:
    """总成核价「计算过程」浅色报告（封面 + 资料来源）。"""
    row = _assembly_restore_scope()
    if row is None:
        print("skip 30/31 assembly restore (no costing_assembly_costs row)")
        return
    year, month, part_number, location, vehicle_model, bom_version = row
    query = urlencode(
        {
            "year": year,
            "month": month,
            "part_number": part_number,
            "view": "finance",
            "location": location,
            "vehicle_model": vehicle_model,
            "bom_version": bom_version,
        }
    )
    page.goto(f"{BASE}/assembly-cost-restore?{query}", wait_until="domcontentloaded")
    with contextlib.suppress(Exception):
        page.wait_for_selector("text=计算过程", timeout=15000)
    time.sleep(1.2)
    page.screenshot(path=str(OUT / "30-assembly-cost-restore.png"), full_page=False)
    print("saved 30-assembly-cost-restore.png")

    sources = page.locator("text=资料来源")
    if sources.count():
        sources.first.scroll_into_view_if_needed()
        time.sleep(0.4)
        page.screenshot(path=str(OUT / "31-assembly-cost-restore-sources.png"), full_page=False)
        print("saved 31-assembly-cost-restore-sources.png")
    else:
        print("skip 31-assembly-cost-restore-sources.png (no 资料来源)")


def _assembly_restore_scope() -> tuple[int, int, str, str, str, str] | None:
    db_path = pathlib.Path(__file__).resolve().parents[2] / "data" / "stamping_costing.db"
    if not db_path.exists():
        return None

    conn = sqlite3.connect(str(db_path))
    try:
        preferred = conn.execute(
            """
            SELECT year, month, part_number, location, vehicle_model, bom_version
            FROM costing_assembly_costs
            WHERE part_number = '501006873AA'
            ORDER BY year DESC, month DESC
            LIMIT 1
            """
        ).fetchone()
        if preferred:
            return preferred
        any_row = conn.execute(
            """
            SELECT year, month, part_number, location, vehicle_model, bom_version
            FROM costing_assembly_costs
            WHERE is_tree_root = 1
            ORDER BY year DESC, month DESC, id DESC
            LIMIT 1
            """
        ).fetchone()
        return any_row
    finally:
        conn.close()


if __name__ == "__main__":
    main()
