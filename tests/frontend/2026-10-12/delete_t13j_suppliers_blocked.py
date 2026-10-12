"""前端删除四家 T13J 冲压工厂。工艺零件还在，期望都不能删。

先开开发服务（http://127.0.0.1:8000），在仓库根目录执行：

    python -X utf8 tests/frontend/2026-10-12/delete_t13j_suppliers_blocked.py

管理员走登录页 admin / admin123。在供应商列表点每行删除并确认。
"""

from __future__ import annotations

from playwright.sync_api import Page, sync_playwright

BASE = "http://127.0.0.1:8000"
SUPPLIERS = (
    ("安庆常庆汽车部件有限公司", 4),
    ("芜湖全鑫模具机械股份有限公司", 50),
    ("安徽振华汽车部件有限责任公司", 34),
    ("昆山贝奇精密机械有限公司安庆分公司", 1),
)


def login(page: Page) -> None:
    page.goto(f"{BASE}/login", wait_until="domcontentloaded")
    page.fill("#loginUsername", "admin")
    page.fill("#loginPassword", "admin123")
    page.click("#btnLogin")
    page.wait_for_url("**/app**", timeout=20000)


def open_supplier_list(page: Page) -> None:
    with page.expect_response(
        lambda response: response.request.method == "GET"
        and "/api/masterdata/suppliers" in response.url
        and "page=" in response.url,
        timeout=20000,
    ) as listed:
        page.goto(f"{BASE}/app#/supplier-list", wait_until="domcontentloaded")
    response = listed.value
    if response.status != 200:
        raise RuntimeError(f"供应商列表打开失败: {response.status} {response.text()[:300]}")
    page.wait_for_selector("#supplierTableBody tr", timeout=20000)


def try_delete(page: Page, full_name: str) -> str:
    row = page.locator("#supplierTableBody tr", has_text=full_name)
    if row.count() != 1:
        raise RuntimeError(f"列表里找不到唯一的 {full_name}")
    row.locator('button[data-action="delete"]').click()
    page.wait_for_function(
        """(name) => {
            const drawer = document.getElementById('supplierDeleteDrawer');
            const title = document.getElementById('supplierDeleteName');
            return drawer && drawer.style.display !== 'none'
                && title && title.textContent === name;
        }""",
        arg=full_name,
        timeout=10000,
    )
    with page.expect_response(
        lambda response: response.request.method == "DELETE"
        and "/api/masterdata/suppliers/" in response.url,
        timeout=20000,
    ) as deleted:
        page.click("#confirmSupplierDeleteBtn")
    response = deleted.value
    message = ""
    try:
        message = str(response.json().get("message") or "")
    except Exception:
        message = response.text()[:300]
    page.wait_for_selector("#appDeleteErrorDialog:not(.hidden)", timeout=10000)
    dialog_text = page.locator("#appDeleteErrorDialog").inner_text().strip()
    page.click("#appDeleteErrorOkBtn")
    page.wait_for_function(
        "() => document.getElementById('appDeleteErrorDialog')?.classList.contains('hidden')",
        timeout=10000,
    )
    page.click("#cancelSupplierDeleteBtn")
    page.wait_for_function(
        "() => document.getElementById('supplierDeleteDrawer')?.style.display === 'none'",
        timeout=10000,
    )
    if row.count() != 1:
        raise RuntimeError(f"{full_name} 已从列表消失")
    return f"{response.status} {message} | {dialog_text.splitlines()[0]}"


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        login(page)
        open_supplier_list(page)
        for full_name, part_count in SUPPLIERS:
            outcome = try_delete(page, full_name)
            print(f"{full_name}: {outcome.splitlines()[0][:120]}")
            expected = f"有 {part_count} 条冲压零件"
            if (
                not outcome.startswith("400")
                or f"无法删除供应商「{full_name}」" not in outcome
                or expected not in outcome
            ):
                raise SystemExit(f"{full_name} 没有被引用保护拦住\n{outcome}")
        info = page.locator("#supplierPageInfo").inner_text().strip()
        if info != "共 4 条":
            raise SystemExit(f"删除尝试之后列表条数变了: {info}")
        browser.close()
    print("ok: 4 家供应商都删不掉，列表仍是 4 条")


if __name__ == "__main__":
    main()
