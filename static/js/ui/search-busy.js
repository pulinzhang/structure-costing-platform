/**
 * 列表「查询」按钮加载态：转圈 +「查询中」+ disabled。
 * 调用方必须在 finally 里 setSearchBusy(id, false)，请求失败也要恢复。
 */

const SEARCH_BUSY_HTML =
    '<div class="w-3 h-3 border border-brand border-t-transparent rounded-full animate-spin"></div>查询中';

export function setSearchBusy(buttonId, isBusy) {
    const btn = document.getElementById(buttonId);
    if (!btn) return;
    if (isBusy) {
        if (!btn.dataset.searchIdleHtml) btn.dataset.searchIdleHtml = btn.innerHTML;
        btn.disabled = true;
        btn.setAttribute('aria-busy', 'true');
        btn.innerHTML = SEARCH_BUSY_HTML;
        return;
    }
    btn.disabled = false;
    btn.setAttribute('aria-busy', 'false');
    if (btn.dataset.searchIdleHtml) btn.innerHTML = btn.dataset.searchIdleHtml;
}
