"""微信里打开帮助要有「关闭」；普通浏览器不出现。

加载现网 `static/helper/` 页面，不启动应用、不登录。
手机微信、企业微信、电脑版微信窗口的用户代理都带 MicroMessenger。
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")

from playwright.sync_api import Browser, Page, Route, sync_playwright  # noqa: E402

_HELPER = Path(__file__).resolve().parents[2] / "static" / "helper"
_ORIGIN = "http://127.0.0.1:9"

_WECHAT_USER_AGENTS = (
    (
        "iphone",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
        "MicroMessenger/8.0.49(0x1800312a) NetType/WIFI Language/zh_CN",
    ),
    (
        "windows",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 "
        "MicroMessenger/7.0.20.1781(0x6700143B) WindowsWechat",
    ),
    (
        "wecom",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
        "wxwork/4.1.30 MicroMessenger/7.0.1 Language/zh",
    ),
)

_DESKTOP_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

_PAGES = ("index.html", "help.html", "knowledge.html", "example.html", "print-all.html")


@pytest.fixture(scope="module")
def chromium() -> Iterator[Browser]:
    playwright = sync_playwright().start()
    try:
        browser = playwright.chromium.launch(headless=True)
    except Exception as error:
        playwright.stop()
        pytest.skip(f"Chromium 未安装: {error}")
    yield browser
    browser.close()
    playwright.stop()


def _content_type(name: str) -> str:
    if name.endswith(".css"):
        return "text/css; charset=utf-8"
    if name.endswith(".js"):
        return "text/javascript; charset=utf-8"
    return "text/html; charset=utf-8"


def _serve_helper(page: Page) -> None:
    def fulfill(route: Route) -> None:
        url = route.request.url.split("?", 1)[0]
        if url.rstrip("/") == _ORIGIN:
            route.fulfill(
                status=200,
                content_type="text/html; charset=utf-8",
                body="<html><body>home</body></html>",
            )
            return
        marker = "/helper/"
        if marker not in url:
            route.fulfill(status=404, body="missing")
            return
        name = url.split(marker, 1)[-1] or "index.html"
        path = (_HELPER / name).resolve()
        if not path.is_relative_to(_HELPER.resolve()) or not path.is_file():
            route.fulfill(status=404, body="missing")
            return
        route.fulfill(status=200, content_type=_content_type(name), body=path.read_bytes())

    page.route("**/*", fulfill)


def _open(browser: Browser, *, user_agent: str, mobile: bool, page_name: str) -> Page:
    page = browser.new_page(
        user_agent=user_agent,
        viewport={"width": 390, "height": 700} if mobile else {"width": 1280, "height": 800},
        is_mobile=mobile,
        has_touch=mobile,
    )
    _serve_helper(page)
    page.goto(f"{_ORIGIN}/helper/{page_name}", wait_until="domcontentloaded")
    return page


@pytest.mark.parametrize("page_name", _PAGES)
@pytest.mark.parametrize(
    "user_agent",
    [item[1] for item in _WECHAT_USER_AGENTS],
    ids=[item[0] for item in _WECHAT_USER_AGENTS],
)
def test_wechat_help_shows_close(
    chromium: Browser,
    user_agent: str,
    page_name: str,
) -> None:
    page = _open(chromium, user_agent=user_agent, mobile=True, page_name=page_name)
    try:
        button = page.locator("#wechatHelpClose")
        assert button.count() == 1
        assert button.inner_text() == "关闭"
        assert button.is_visible()
    finally:
        page.close()


@pytest.mark.parametrize("page_name", _PAGES)
def test_desktop_help_has_no_close(chromium: Browser, page_name: str) -> None:
    page = _open(chromium, user_agent=_DESKTOP_USER_AGENT, mobile=False, page_name=page_name)
    try:
        assert page.locator("#wechatHelpClose").count() == 0
    finally:
        page.close()


def test_wechat_close_returns_home(chromium: Browser) -> None:
    page = _open(
        chromium,
        user_agent=_WECHAT_USER_AGENTS[0][1],
        mobile=True,
        page_name="index.html",
    )
    try:
        page.click("#wechatHelpClose")
        page.wait_for_url(f"{_ORIGIN}/", timeout=3000)
        assert page.locator("body").inner_text() == "home"
    finally:
        if not page.is_closed():
            page.close()
