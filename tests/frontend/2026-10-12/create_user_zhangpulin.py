"""前端新增用户 zhangpulin / 123456，并用该账号再登录一次确认。

先开开发服务（http://127.0.0.1:8000），在仓库根目录执行：

    python -X utf8 tests/frontend/2026-10-12/create_user_zhangpulin.py

管理员走登录页 admin / admin123。账号已存在时，在用户管理里把密码改成 123456。
"""

from __future__ import annotations

from playwright.sync_api import Page, sync_playwright

BASE = "http://127.0.0.1:8000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
NEW_USERNAME = "zhangpulin"
NEW_PASSWORD = "123456"


def login(page: Page, username: str, password: str) -> None:
    page.goto(f"{BASE}/login", wait_until="domcontentloaded")
    page.fill("#loginUsername", username)
    page.fill("#loginPassword", password)
    page.click("#btnLogin")
    page.wait_for_url("**/app**", timeout=20000)


def logout(page: Page) -> None:
    page.click("#userMenuBtn")
    page.click("#userLogoutBtn")
    page.wait_for_url("**/login**", timeout=20000)


def toast_text(page: Page) -> str:
    return page.evaluate(
        """() => [...document.querySelectorAll('.toast-shell')]
            .map((node) => (node.textContent || '').trim())
            .join(' | ')"""
    )


def wait_toast_after(page: Page, needle: str, previous: str) -> str:
    page.wait_for_function(
        """([expected, before]) => {
            const text = [...document.querySelectorAll('.toast-shell')]
                .map((node) => (node.textContent || '').trim())
                .join(' | ');
            return text.includes(expected) && text !== before;
        }""",
        arg=[needle, previous],
        timeout=15000,
    )
    return toast_text(page)


def open_users(page: Page) -> None:
    with page.expect_response(
        lambda response: response.request.method == "GET"
        and "/api/settings/users" in response.url
        and "page=" in response.url,
        timeout=20000,
    ) as listed:
        page.goto(f"{BASE}/app#/settings-users", wait_until="domcontentloaded")
    response = listed.value
    if response.status != 200:
        raise RuntimeError(f"用户列表打开失败: {response.status} {response.text()[:300]}")
    page.wait_for_selector("#btnAddUser", timeout=20000)


def user_row(page: Page):
    return page.locator("#usersTableBody tr", has_text=NEW_USERNAME)


def search_user(page: Page) -> None:
    panel = page.locator("#usersAdvancedFilterPanel")
    if not panel.is_visible():
        page.click("#usersToggleAdvancedFilter")
        panel.wait_for(state="visible", timeout=5000)
    page.fill("#filterKeyword", NEW_USERNAME)
    with page.expect_response(
        lambda response: response.request.method == "GET"
        and "/api/settings/users" in response.url
        and "keyword=" in response.url,
        timeout=20000,
    ) as listed:
        page.click("#btnFilter")
    response = listed.value
    if response.status != 200:
        raise RuntimeError(f"搜索用户失败: {response.status} {response.text()[:300]}")


def create_user(page: Page) -> tuple[int, str]:
    page.click("#btnAddUser")
    page.wait_for_selector("#editUsername", state="visible", timeout=10000)
    page.fill("#editUsername", NEW_USERNAME)
    page.fill("#editPassword", NEW_PASSWORD)
    with page.expect_response(
        lambda response: response.request.method == "POST"
        and response.url.rstrip("/").endswith("/api/settings/users"),
        timeout=20000,
    ) as created:
        page.click("#submitEditBtn")
    response = created.value
    body = ""
    try:
        payload = response.json()
        body = str(payload.get("message") or "")
    except Exception:
        body = response.text()[:200]
    return response.status, body


def reset_password(page: Page) -> None:
    search_user(page)
    row = user_row(page)
    row.wait_for(timeout=10000)
    row.locator(".password-btn").click()
    page.wait_for_selector("#newPassword", state="visible", timeout=10000)
    page.fill("#newPassword", NEW_PASSWORD)
    page.fill("#confirmPassword", NEW_PASSWORD)
    before = toast_text(page)
    page.click("#submitPasswordBtn")
    wait_toast_after(page, "密码已更新", before)


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        login(page, ADMIN_USERNAME, ADMIN_PASSWORD)
        open_users(page)
        status, message = create_user(page)
        if status == 201:
            outcome = "created"
        elif status == 400 and "账号已存在" in message:
            page.click("#closeEditDrawer")
            reset_password(page)
            outcome = "password-reset"
        else:
            raise RuntimeError(f"新增用户未成功: {status} {message}")

        search_user(page)
        row = user_row(page)
        row.wait_for(timeout=10000)
        if "启用" not in (row.inner_text() or ""):
            raise RuntimeError("用户已出现，但状态不是启用")

        logout(page)
        login(page, NEW_USERNAME, NEW_PASSWORD)
        session_name = page.evaluate(
            """() => {
                const raw = localStorage.getItem('brabus_user');
                if (!raw) return '';
                const session = JSON.parse(raw);
                return session.username || '';
            }"""
        )
        if session_name != NEW_USERNAME:
            raise RuntimeError(f"登录会话不是 {NEW_USERNAME}: {session_name}")
        browser.close()
        print(f"{outcome}: {NEW_USERNAME} 可登录")


if __name__ == "__main__":
    main()
