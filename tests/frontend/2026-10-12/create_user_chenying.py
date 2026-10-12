"""前端新增 chenying / 123456，并给 chenying、zhangpulin 勾上全部权限。

先开开发服务（http://127.0.0.1:8000），在仓库根目录执行：

    python -X utf8 tests/frontend/2026-10-12/create_user_chenying.py

管理员走登录页 admin / admin123。账号已存在时，把密码改成 123456 再授权。
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BASE = "http://127.0.0.1:8000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
NEW_USERNAME = "chenying"
NEW_PASSWORD = "123456"
GRANT_USERNAMES = ("chenying", "zhangpulin")


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


def user_row(page: Page, username: str):
    return page.locator("#usersTableBody tr", has_text=username)


def search_user(page: Page, username: str) -> None:
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
    search_user(page, NEW_USERNAME)
    row = user_row(page, NEW_USERNAME)
    row.wait_for(timeout=10000)
    row.locator(".password-btn").click()
    page.wait_for_selector("#newPassword", state="visible", timeout=10000)
    page.fill("#newPassword", NEW_PASSWORD)
    page.fill("#confirmPassword", NEW_PASSWORD)
    before = toast_text(page)
    page.click("#submitPasswordBtn")
    wait_toast_after(page, "密码已更新", before)


def grant_all(page: Page, username: str) -> list[str]:
    search_user(page, username)
    row = user_row(page, username)
    row.wait_for(timeout=10000)
    row.locator(".grant-btn").click()
    page.wait_for_selector("#grantTreeContainer .grant-check", timeout=20000)
    page.wait_for_function(
        "() => document.querySelectorAll('#grantTreeContainer .grant-check').length > 5",
        timeout=20000,
    )
    page.evaluate(
        """() => {
            document.querySelectorAll('#grantTreeContainer .grant-check').forEach((box) => {
                if (!box.disabled) box.checked = true;
            });
        }"""
    )
    with page.expect_response(
        lambda response: response.request.method == "PUT" and response.url.endswith("/permissions"),
        timeout=20000,
    ) as saved:
        page.click("#submitGrantBtn")
    response = saved.value
    payload = response.json()
    if response.status != 200:
        raise RuntimeError(f"{username} 授权失败: {response.status} {payload}")
    codes = payload.get("data") or []
    if not isinstance(codes, list):
        raise RuntimeError(f"{username} 授权返回不是权限码列表")
    return [str(code) for code in codes]


def main() -> None:
    from app.common.permissions.catalog import get_all_codes

    expected = set(get_all_codes())
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

        for username in GRANT_USERNAMES:
            granted = set(grant_all(page, username))
            missing = expected - granted
            if missing:
                raise RuntimeError(f"{username} 仍缺权限: {sorted(missing)}")

        logout(page)
        login(page, NEW_USERNAME, NEW_PASSWORD)
        session = page.evaluate(
            """() => {
                const raw = localStorage.getItem('brabus_user');
                if (!raw) return null;
                const user = JSON.parse(raw);
                return {
                    username: user.username || '',
                    count: Array.isArray(user.permissions) ? user.permissions.length : 0,
                };
            }"""
        )
        if not session or session["username"] != NEW_USERNAME:
            raise RuntimeError(f"登录会话不是 {NEW_USERNAME}: {session}")
        if session["count"] < len(expected):
            raise RuntimeError(
                f"{NEW_USERNAME} 登录后权限不足: {session['count']} / {len(expected)}"
            )
        browser.close()
        print(
            f"{outcome}: {NEW_USERNAME} 可登录；{', '.join(GRANT_USERNAMES)} 已有全部 {len(expected)} 项权限"
        )


if __name__ == "__main__":
    main()
