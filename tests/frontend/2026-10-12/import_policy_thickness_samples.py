"""厚度加减价样例：从前端加减价导入页按生效月上传，再到列表核对。

先开开发服务（http://127.0.0.1:8000），在仓库根目录执行：

    python -X utf8 tests/frontend/2026-10-12/import_policy_thickness_samples.py

样例挑选与 scripts/import_policy_thickness_samples.py 相同。
管理员走登录页 admin / admin123。同一年、同一个月再传会盖掉原来的。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from scripts.import_policy_thickness_samples import (  # noqa: E402
    DEFAULT_ROOT,
    _iter_sample_jobs,
)

BASE = "http://127.0.0.1:8000"
UPLOAD_HASH = "#/steel-price-policy-upload"
LIST_HASH = "#/steel-price-policy-download"


def login(page: Page) -> None:
    page.goto(f"{BASE}/login", wait_until="domcontentloaded")
    page.fill("#loginUsername", "admin")
    page.fill("#loginPassword", "admin123")
    page.click("#btnLogin")
    page.wait_for_url("**/app**", timeout=20000)


def sample_jobs() -> list[tuple[int, int, Path]]:
    jobs = _iter_sample_jobs(DEFAULT_ROOT)
    if not jobs:
        raise SystemExit(f"找不到厚度加减价样例: {DEFAULT_ROOT}")
    return [(period.year, period.month, path) for period, path in jobs]


def upload_one(page: Page, year: int, month: int, path: Path) -> tuple[str, int, bool, str]:
    page.goto(f"{BASE}/app{UPLOAD_HASH}", wait_until="domcontentloaded")
    page.wait_for_selector("#policyYear", state="attached", timeout=20000)
    page.fill("#policyYear", str(year))
    page.fill("#policyMonth", str(month))
    page.set_input_files("#policyFileInput", str(path.resolve()))
    page.wait_for_function(
        "() => { const btn = document.getElementById('policySubmitButton'); return btn && !btn.disabled; }",
        timeout=10000,
    )
    page.click("#policySubmitButton")
    page.wait_for_function(
        """() => {
            const title = document.getElementById('policyProgressTitle');
            const text = title ? title.textContent || '' : '';
            return text.includes('解析成功') || text.includes('未写入');
        }""",
        timeout=180000,
    )
    title = page.locator("#policyProgressTitle").inner_text().strip()
    message = page.locator("#policyProgressMsg").inner_text().strip()
    outcome = f"{title}：{message}"
    matched = re.search(r"共\s*(\d+)\s*条", message)
    written = int(matched.group(1)) if matched else 0
    return outcome, written, "解析成功" in title, message


def assert_listed(page: Page, year: int, month: int) -> int:
    page.goto(f"{BASE}/app{LIST_HASH}", wait_until="domcontentloaded")
    page.wait_for_selector("#policyDownloadToggleAdvancedFilter", state="visible", timeout=20000)
    page.click("#policyDownloadToggleAdvancedFilter")
    page.wait_for_selector("#policyDownloadYear", state="visible", timeout=10000)
    page.wait_for_function(
        """(year) => {
            const select = document.getElementById('policyDownloadYear');
            return select && [...select.options].some((option) => option.value === String(year));
        }""",
        arg=year,
        timeout=20000,
    )
    with page.expect_response(
        lambda response: response.request.method == "GET"
        and "/api/yishiyiyi/policy/export-preview" in response.url,
        timeout=20000,
    ):
        page.select_option("#policyDownloadYear", str(year))
    page.wait_for_function(
        """() => {
            const button = document.getElementById('btnPreview');
            return button && !button.disabled;
        }""",
        timeout=20000,
    )
    with page.expect_response(
        lambda response: response.request.method == "GET"
        and "/api/yishiyiyi/policy/export-preview" in response.url
        and f"year={year}" in response.url
        and f"month={month}" in response.url,
        timeout=20000,
    ) as listed:
        page.select_option("#policyDownloadMonth", str(month))
    response = listed.value
    if response.status != 200:
        raise RuntimeError(
            f"{year}年{month:02d}月列表打开失败: {response.status} {response.text()[:400]}"
        )
    total = int(response.json()["data"]["total"])
    page.wait_for_function(
        """(total) => document.getElementById('recordCount')?.textContent === String(total)""",
        arg=total,
        timeout=10000,
    )
    if total <= 0:
        raise RuntimeError(f"{year}年{month:02d}月加减价列表是空的")
    return total


def main() -> None:
    jobs = sample_jobs()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        login(page)
        written_months = 0
        failed: list[str] = []
        for index, (year, month, path) in enumerate(jobs, start=1):
            outcome, written, imported, message = upload_one(page, year, month, path)
            head = outcome.splitlines()[0][:160]
            label = f"[{index}/{len(jobs)}] {year}年{month:02d}月 {path.name}"
            if not imported:
                failed.append(f"{year}年{month:02d}月 {path.name}：{message[:240]}")
                print(f"{label}: 未导入：{message[:240]}")
                continue
            if written <= 0:
                print(f"{label}: {head}")
                continue
            total = assert_listed(page, year, month)
            written_months += 1
            print(f"{label}: {head}；列表 {total} 条")
        browser.close()
    if failed:
        raise SystemExit("这些月份没有从导入页写入：\n" + "\n".join(failed))
    if written_months <= 0:
        raise SystemExit("加减价导入页没有写入任何生效月")
    print(f"ok: {written_months}/{len(jobs)} 个生效月的厚度加减价已从导入页写入")


if __name__ == "__main__":
    main()
