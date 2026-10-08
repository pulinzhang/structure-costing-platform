"""微信里三份报告的「关闭」与帮助页同一套；网页仍是页边灰字。

加载现网报告页，不启动应用、不登录。
手机微信、企业微信、电脑版微信窗口的用户代理都带 MicroMessenger。
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")

from playwright.sync_api import Browser, Page, Route, sync_playwright  # noqa: E402

_STATIC = Path(__file__).resolve().parents[2] / "static"
_ORIGIN = "http://127.0.0.1:9"

_PAGES = (
    "/llm-analysis-report",
    "/assembly-cost-calc-report",
    "/assembly-cost-restore",
)

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

_FILE_BY_PATH = {
    "/llm-analysis-report": _STATIC / "llm-analysis-report.html",
    "/assembly-cost-calc-report": _STATIC / "assembly-cost-calc-report.html",
    "/assembly-cost-restore": _STATIC / "assembly-cost-restore.html",
    "/static/css/report-close.css": _STATIC / "css" / "report-close.css",
    "/static/js/ui/report-close.js": _STATIC / "js" / "ui" / "report-close.js",
}


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


def _content_type(path: Path) -> str:
    if path.suffix == ".css":
        return "text/css; charset=utf-8"
    if path.suffix == ".js":
        return "text/javascript; charset=utf-8"
    return "text/html; charset=utf-8"


def _serve(page: Page) -> None:
    def fulfill(route: Route) -> None:
        url = route.request.url.split("?", 1)[0]
        path = _FILE_BY_PATH.get(url.removeprefix(_ORIGIN))
        if path is None or not path.is_file():
            route.fulfill(status=404, body="missing")
            return
        route.fulfill(status=200, content_type=_content_type(path), body=path.read_bytes())

    page.route("**/*", fulfill)


def _open(browser: Browser, *, user_agent: str, mobile: bool, page_path: str) -> Page:
    page = browser.new_page(
        user_agent=user_agent,
        viewport={"width": 390, "height": 700} if mobile else {"width": 1280, "height": 800},
        is_mobile=mobile,
        has_touch=mobile,
    )
    _serve(page)
    page.goto(f"{_ORIGIN}{page_path}", wait_until="domcontentloaded")
    return page


def _paint(page: Page) -> dict[str, str]:
    raw: object = page.evaluate(
        """() => {
            const button = document.getElementById('reportCloseBtn');
            const bar = button && button.closest('.report-close-bar');
            const mark = button && button.querySelector('span');
            const buttonStyle = button ? getComputedStyle(button) : null;
            const barStyle = bar ? getComputedStyle(bar) : null;
            return {
                barClass: bar ? bar.className : '',
                barPosition: barStyle ? barStyle.position : '',
                background: buttonStyle ? buttonStyle.backgroundColor : '',
                color: buttonStyle ? buttonStyle.color : '',
                letterSpacing: buttonStyle ? buttonStyle.letterSpacing : '',
                markDisplay: mark ? getComputedStyle(mark).display : '',
            };
        }"""
    )
    assert isinstance(raw, dict)
    return {str(key): str(value) for key, value in raw.items()}


@pytest.mark.parametrize("page_path", _PAGES)
@pytest.mark.parametrize(
    "user_agent",
    [item[1] for item in _WECHAT_USER_AGENTS],
    ids=[item[0] for item in _WECHAT_USER_AGENTS],
)
def test_wechat_report_close_matches_help(
    chromium: Browser,
    user_agent: str,
    page_path: str,
) -> None:
    page = _open(chromium, user_agent=user_agent, mobile=True, page_path=page_path)
    try:
        paint = _paint(page)
        assert "is-wechat" in paint["barClass"]
        assert paint["barPosition"] == "fixed"
        assert paint["background"] == "rgb(1, 1, 1)"
        assert paint["color"] == "rgb(255, 255, 255)"
        assert paint["letterSpacing"] == "normal"
        assert paint["markDisplay"] == "none"
        assert page.locator("#reportCloseBtn").inner_text() == "关闭"

        page.hover("#reportCloseBtn")
        hovered = _paint(page)
        assert hovered["background"] == "rgb(183, 8, 38)"
        assert hovered["color"] == "rgb(255, 255, 255)"
    finally:
        page.close()


@pytest.mark.parametrize("page_path", _PAGES)
def test_desktop_report_close_stays_margin_style(chromium: Browser, page_path: str) -> None:
    page = _open(chromium, user_agent=_DESKTOP_USER_AGENT, mobile=False, page_path=page_path)
    try:
        paint = _paint(page)
        assert "is-wechat" not in paint["barClass"]
        assert paint["barPosition"] == "sticky"
        assert paint["background"] == "rgb(244, 244, 245)"
        assert paint["markDisplay"] != "none"
        assert "×" in page.locator("#reportCloseBtn").inner_text()
    finally:
        page.close()
