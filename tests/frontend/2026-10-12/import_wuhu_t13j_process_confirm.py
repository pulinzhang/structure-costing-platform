"""芜湖 T13J 冲压工艺确认表：四家供应商已建档后，从前端再导入四份样表。

先开开发服务（http://127.0.0.1:8000），在仓库根目录执行：

    python -X utf8 tests/frontend/2026-10-12/import_wuhu_t13j_process_confirm.py

样表：excel_sample/T13J 下文件名含「工艺确认表」的 xlsx。
管理员走登录页 admin / admin123。只选文件，项目和冲压工厂从表头解析。
同一基地 + 冲压厂 + 项目 + 版本再导会整包覆盖。
"""

from __future__ import annotations

import re
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

BASE = "http://127.0.0.1:8000"
SAMPLE_DIR = Path(__file__).resolve().parents[3] / "excel_sample" / "T13J"
PARTS_COUNT = re.compile(r"上传成功：(\d+) 个零件")


def login(page: Page) -> None:
    page.goto(f"{BASE}/login", wait_until="domcontentloaded")
    page.fill("#loginUsername", "admin")
    page.fill("#loginPassword", "admin123")
    page.click("#btnLogin")
    page.wait_for_url("**/app**", timeout=20000)


def sample_files() -> list[Path]:
    files = sorted(SAMPLE_DIR.glob("*工艺确认表*.xlsx"))
    if not files:
        raise SystemExit(f"找不到工艺确认表: {SAMPLE_DIR}")
    return files


def upload_one(page: Page, path: Path) -> str:
    page.goto(f"{BASE}/app#/stamping-upload", wait_until="domcontentloaded")
    page.wait_for_selector("#fileInput", state="attached", timeout=20000)
    page.set_input_files("#fileInput", str(path.resolve()))
    page.wait_for_function(
        "() => { const btn = document.getElementById('submitBtn'); return btn && !btn.disabled; }",
        timeout=10000,
    )
    with page.expect_response(
        lambda response: response.request.method == "POST"
        and "/api/stamping/upload" in response.url,
        timeout=60000,
    ) as posted:
        page.click("#submitBtn")
    response = posted.value
    if response.status >= 500:
        raise RuntimeError(f"{path.name} 提交失败: {response.status} {response.text()[:400]}")
    page.wait_for_function(
        """() => {
            const title = document.getElementById('stampingProgressTitle');
            const text = title ? title.textContent || '' : '';
            return text.includes('解析成功') || text.includes('解析失败') || text.includes('未导入');
        }""",
        timeout=180000,
    )
    title = page.locator("#stampingProgressTitle").inner_text().strip()
    message = page.locator("#stampingProgressMsg").inner_text().strip()
    return f"{title}：{message}"


def part_count(outcome: str) -> int:
    matched = PARTS_COUNT.search(outcome)
    if "解析成功" not in outcome or matched is None:
        raise RuntimeError(f"导入没有成功\n{outcome[:500]}")
    return int(matched.group(1))


def assert_parts_landed(page: Page, expected_total: int) -> None:
    with page.expect_response(
        lambda response: response.request.method == "GET"
        and "/api/stamping/parts" in response.url
        and "page=" in response.url,
        timeout=20000,
    ) as listed:
        page.goto(f"{BASE}/app#/stamping-parts", wait_until="domcontentloaded")
    response = listed.value
    if response.status != 200:
        raise RuntimeError(f"工艺列表打开失败: {response.status} {response.text()[:400]}")
    payload = response.json()["data"]
    total = int(payload["total"])
    summary = (payload.get("filters") or {}).get("summary") or {}
    supplier_count = int(summary.get("stamping_supplier_count") or 0)
    page.wait_for_function(
        """() => document.getElementById('partsHudSupplier')?.textContent === '4'""",
        timeout=10000,
    )
    if supplier_count != 4:
        raise RuntimeError(f"冲压工厂数不是 4: {supplier_count}")
    if total != expected_total:
        raise RuntimeError(f"工艺列表 {total} 个零件，四份合计 {expected_total}")


def main() -> None:
    files = sample_files()
    landed = 0
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        login(page)
        for path in files:
            outcome = upload_one(page, path)
            count = part_count(outcome)
            landed += count
            print(f"{path.name}: {outcome.splitlines()[0][:160]}")
        assert_parts_landed(page, landed)
        browser.close()
    print(f"ok: {len(files)} 份工艺确认表已引入，列表 {landed} 个零件，4 家冲压工厂")


if __name__ == "__main__":
    main()
