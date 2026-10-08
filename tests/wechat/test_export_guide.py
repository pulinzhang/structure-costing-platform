"""微信内置浏览器点导出时只出说明，不发下载请求。

加载现网 `static/js/main.js`，不启动应用、不登录。
手机微信、企业微信、电脑版微信窗口的用户代理都带 MicroMessenger。
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")

from playwright.sync_api import Browser, Page, Route, sync_playwright  # noqa: E402

_MAIN_JS = Path(__file__).resolve().parents[2] / "static" / "js" / "main.js"
_EXPORT_URL = "http://127.0.0.1:9/api/example/export"
_GUIDE = "微信里不能保存文件。请点右上角 ··· ，选择在浏览器中打开，然后再导出。"

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


def _open(browser: Browser, *, user_agent: str, mobile: bool) -> Page:
    page = browser.new_page(
        user_agent=user_agent,
        viewport={"width": 390, "height": 700} if mobile else {"width": 1280, "height": 800},
        is_mobile=mobile,
        has_touch=mobile,
    )
    page.set_content("<!DOCTYPE html><html><body></body></html>", wait_until="domcontentloaded")
    page.add_script_tag(path=str(_MAIN_JS))
    return page


def _track_export(page: Page) -> list[str]:
    hits: list[str] = []

    def fulfill(route: Route) -> None:
        hits.append(route.request.url)
        route.fulfill(
            status=200,
            content_type="application/octet-stream",
            headers={"Content-Disposition": "attachment; filename*=UTF-8''demo.xlsx"},
            body=b"PK\x03\x04",
        )

    page.route("**/api/example/export**", fulfill)
    return hits


def _download(page: Page) -> dict[str, object]:
    raw: object = page.evaluate(
        """async (url) => {
            try {
                await window.HttpClient.download(url, { skipToast: true });
                return { ok: true, status: '', wechatGuide: false, message: '' };
            } catch (error) {
                return {
                    ok: false,
                    status: String((error && error.status) || ''),
                    wechatGuide: Boolean(error && error.wechatGuide),
                    message: String((error && error.message) || ''),
                };
            }
        }""",
        _EXPORT_URL,
    )
    assert isinstance(raw, dict)
    return raw


@pytest.mark.parametrize(
    "user_agent",
    [item[1] for item in _WECHAT_USER_AGENTS],
    ids=[item[0] for item in _WECHAT_USER_AGENTS],
)
def test_wechat_download_shows_guide_without_request(
    chromium: Browser,
    user_agent: str,
) -> None:
    page = _open(chromium, user_agent=user_agent, mobile=True)
    try:
        hits = _track_export(page)
        outcome = _download(page)

        assert hits == []
        assert outcome["ok"] is False
        assert outcome["status"] == "wechat"
        assert outcome["wechatGuide"] is True
        assert outcome["message"] == _GUIDE

        dialog = page.locator("#wechatExportGuide")
        assert dialog.get_attribute("role") == "alertdialog"
        assert "hidden" not in (dialog.get_attribute("class") or "")
        assert dialog.evaluate("node => node.style.zIndex") == "140"
        assert dialog.locator("#wechatExportGuideTitle").inner_text() == "微信里不能保存文件"
        assert "在浏览器中打开" in dialog.inner_text()

        page.click("#wechatExportGuideOk")
        assert "hidden" in (dialog.get_attribute("class") or "")

        _download(page)
        assert hits == []
        assert "hidden" not in (dialog.get_attribute("class") or "")
        page.keyboard.press("Escape")
        assert "hidden" in (dialog.get_attribute("class") or "")
    finally:
        page.close()


def test_wechat_guide_sits_above_assistant_panel(chromium: Browser) -> None:
    page = _open(chromium, user_agent=_WECHAT_USER_AGENTS[0][1], mobile=True)
    try:
        page.evaluate(
            """() => {
                const style = document.createElement('style');
                style.textContent = '.fixed{position:fixed}.inset-0{inset:0}';
                document.head.appendChild(style);
                const panel = document.createElement('section');
                panel.id = 'llmAssistantPanel';
                panel.style.cssText = 'position:fixed;inset:0;z-index:110;background:#fff';
                document.body.appendChild(panel);
            }"""
        )
        page.evaluate("() => window.refuseWeChatDownload()")
        top_id = page.evaluate(
            """() => {
                const hit = document.elementFromPoint(195, 350);
                const dialog = hit && hit.closest('#wechatExportGuide');
                return dialog ? dialog.id : '';
            }"""
        )
        assert top_id == "wechatExportGuide"
    finally:
        page.close()


def test_desktop_download_requests_file(chromium: Browser) -> None:
    page = _open(chromium, user_agent=_DESKTOP_USER_AGENT, mobile=False)
    try:
        hits = _track_export(page)
        outcome = _download(page)

        assert outcome["ok"] is True
        assert hits
        assert page.locator("#wechatExportGuide").count() == 0
    finally:
        page.close()
