"""芜湖 T13J 模具布点：从前端上传页导入样表，再在模具列表核对件数。

先开开发服务（http://127.0.0.1:8000），在仓库根目录执行：

    python -X utf8 tests/frontend/2026-10-12/import_wuhu_t13j_die_layout.py

样表：excel_sample/T13J/副本②T13J项目冲压模具布点工艺清单-2024-01-22.xlsx
管理员走登录页 admin / admin123。同一基地+项目再导会整包覆盖。
"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, sync_playwright

BASE = "http://127.0.0.1:8000"
LOCATION = "芜湖"
VEHICLE = "T13J"
EXPECTED_PARTS = 88
EXPECTED_PROCESSES = 355
SAMPLE = (
    Path(__file__).resolve().parents[3]
    / "excel_sample"
    / "T13J"
    / "副本②T13J项目冲压模具布点工艺清单-2024-01-22.xlsx"
)


def login(page: Page) -> None:
    page.goto(f"{BASE}/login", wait_until="domcontentloaded")
    page.fill("#loginUsername", "admin")
    page.fill("#loginPassword", "admin123")
    page.click("#btnLogin")
    page.wait_for_url("**/app**", timeout=20000)


def set_select(page: Page, select_id: str, value: str) -> None:
    page.evaluate(
        """([selectId, value]) => {
            const select = document.getElementById(selectId);
            const opt = [...select.options].find(
                (item) => item.value === value || (item.textContent || '').trim() === value
            );
            if (!opt) throw new Error(selectId + ' missing ' + value);
            select.value = opt.value;
            select.dispatchEvent(new Event('change', { bubbles: true }));
        }""",
        [select_id, value],
    )


def upload(page: Page) -> str:
    page.goto(f"{BASE}/app#/stamping-die-upload", wait_until="domcontentloaded")
    page.wait_for_function(
        "() => document.querySelectorAll('#dieLocation option').length > 1",
        timeout=20000,
    )
    set_select(page, "dieLocation", LOCATION)
    page.wait_for_function(
        "() => [...document.querySelectorAll('#dieVehicleModel option')].some(o => o.value === 'T13J')",
        timeout=20000,
    )
    set_select(page, "dieVehicleModel", VEHICLE)
    page.set_input_files("#dieFileInput", str(SAMPLE.resolve()))
    page.wait_for_function(
        "() => { const btn = document.getElementById('dieSubmitBtn'); return btn && !btn.disabled; }",
        timeout=10000,
    )
    with page.expect_response(
        lambda response: response.request.method == "POST"
        and response.url.endswith("/api/stamping/die/upload"),
        timeout=60000,
    ) as posted:
        page.click("#dieSubmitBtn")
    response = posted.value
    if response.status != 200:
        raise RuntimeError(f"上传提交失败: {response.status} {response.text()[:400]}")
    page.wait_for_function(
        """() => {
            const title = document.getElementById('dieProgressTitle');
            const text = title ? title.textContent || '' : '';
            return text.includes('解析成功') || text.includes('解析失败');
        }""",
        timeout=180000,
    )
    title = page.locator("#dieProgressTitle").inner_text().strip()
    message = page.locator("#dieProgressMsg").inner_text().strip()
    if "失败" in title:
        raise RuntimeError(f"解析失败\n{message}")
    return message


def assert_list(page: Page) -> int:
    page.goto(f"{BASE}/app#/stamping-die-list", wait_until="domcontentloaded")
    page.wait_for_function(
        "() => document.querySelectorAll('#dieListLocation option').length > 1",
        timeout=20000,
    )
    set_select(page, "dieListLocation", LOCATION)
    page.wait_for_function(
        "() => [...document.querySelectorAll('#dieListVehicle option')].some(o => o.value === 'T13J')",
        timeout=20000,
    )
    with page.expect_response(
        lambda response: response.request.method == "GET"
        and "/api/stamping/die/parts" in response.url
        and "vehicle_model=T13J" in response.url
        and "location=" in response.url,
        timeout=20000,
    ) as listed:
        set_select(page, "dieListVehicle", VEHICLE)
    response = listed.value
    if response.status != 200:
        raise RuntimeError(f"模具列表打开失败: {response.status} {response.text()[:400]}")
    payload = response.json()
    total = int(payload["data"]["total"])
    page.wait_for_function(
        """(expected) => document.getElementById('dieHudTotal')?.textContent === expected""",
        arg=str(EXPECTED_PARTS),
        timeout=10000,
    )
    scope = page.locator("#dieHudScope").inner_text().strip()
    if LOCATION not in scope or VEHICLE not in scope:
        raise RuntimeError(f"列表范围不是芜湖 / T13J: {scope}")
    rows = page.locator("#dieListTableBody tr").count()
    if rows < 1:
        raise RuntimeError("模具列表没有零件行")
    return total


def main() -> None:
    if not SAMPLE.is_file():
        raise SystemExit(f"找不到样表: {SAMPLE}")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        login(page)
        message = upload(page)
        print(f"upload: {message}")
        if (
            f"{EXPECTED_PARTS} 个零件" not in message
            or f"{EXPECTED_PROCESSES} 道工序" not in message
        ):
            raise SystemExit(
                f"件数不符，期望 {EXPECTED_PARTS} 零件 / {EXPECTED_PROCESSES} 工序\n{message}"
            )
        total = assert_list(page)
        print(f"list: 芜湖 / T13J 零件 {total}")
        if total != EXPECTED_PARTS:
            raise SystemExit(f"列表件数 {total}，期望 {EXPECTED_PARTS}")
        browser.close()
    print(f"ok: 芜湖 T13J 布点已引入，{EXPECTED_PARTS} 个零件，{EXPECTED_PROCESSES} 道工序")


if __name__ == "__main__":
    main()
