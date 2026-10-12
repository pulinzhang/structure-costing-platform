"""确认用户抽屉里的管理员开关，并把 zhangpulin 设为管理员。

先开开发服务（http://127.0.0.1:8000），在仓库根目录执行：

    python -X utf8 tests/frontend/2026-10-12/set_user_admin_switch.py
"""

from __future__ import annotations

from playwright.sync_api import Page, sync_playwright

BASE = "http://127.0.0.1:8000"


def login(page: Page) -> None:
    page.goto(f"{BASE}/login", wait_until="domcontentloaded")
    page.fill("#loginUsername", "admin")
    page.fill("#loginPassword", "admin123")
    page.click("#btnLogin")
    page.wait_for_url("**/app**", timeout=20000)


def open_users(page: Page) -> None:
    with page.expect_response(
        lambda response: response.request.method == "GET"
        and "/api/settings/users" in response.url
        and "page=" in response.url,
        timeout=20000,
    ) as listed:
        page.goto(f"{BASE}/app#/settings-users", wait_until="domcontentloaded")
    if listed.value.status != 200:
        raise RuntimeError(f"用户列表打开失败: {listed.value.status}")
    page.wait_for_selector("#btnAddUser", timeout=20000)


def search(page: Page, username: str) -> None:
    panel = page.locator("#usersAdvancedFilterPanel")
    if not panel.is_visible():
        page.click("#usersToggleAdvancedFilter")
        panel.wait_for(state="visible", timeout=5000)
    page.fill("#filterKeyword", username)
    with page.expect_response(
        lambda response: response.request.method == "GET"
        and "/api/settings/users" in response.url
        and "keyword=" in response.url,
        timeout=20000,
    ):
        page.click("#btnFilter")
    page.locator("#usersTableBody tr", has_text=username).wait_for(timeout=10000)


def open_edit(page: Page, username: str) -> None:
    search(page, username)
    page.locator("#usersTableBody tr", has_text=username).locator(".edit-btn").click()
    page.wait_for_selector("#editIsAdmin", state="visible", timeout=10000)


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        login(page)
        open_users(page)

        open_edit(page, "zhangpulin")
        switch_class = page.get_attribute("#editIsAdmin", "class") or ""
        if "brabus-switch" not in switch_class:
            raise RuntimeError(f"管理员开关样式不对: {switch_class}")
        if page.is_disabled("#editIsAdmin"):
            raise RuntimeError("管理员登录后，开关不应禁用")
        page.set_checked("#editIsAdmin", True)
        with page.expect_response(
            lambda response: response.request.method == "PUT"
            and "/api/settings/users/" in response.url,
            timeout=20000,
        ) as saved:
            page.click("#submitEditBtn")
        if saved.value.status != 200:
            raise RuntimeError(f"设置管理员失败: {saved.value.status} {saved.value.text()[:300]}")

        search(page, "zhangpulin")
        row_text = page.locator("#usersTableBody tr", has_text="zhangpulin").inner_text()
        if "管理员" not in row_text:
            raise RuntimeError("zhangpulin 保存后列表没有管理员标记")

        open_edit(page, "wanger")
        if page.is_checked("#editIsAdmin"):
            raise RuntimeError("wanger 不应是管理员")

        browser.close()
        print("管理员开关可用；zhangpulin 已是管理员；wanger 不是管理员")


if __name__ == "__main__":
    main()
