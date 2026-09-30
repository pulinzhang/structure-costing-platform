/**
 * 内容区等待：转圈居中，数据落地后由调用方换掉整块。
 * 手机和电脑、深色和浅色共用语义色，禁止再各写居中转圈。
 */

function escapeHtml(value) {
    if (typeof window.esc === 'function') return window.esc(value);
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function pageStatusShell(innerHtml, busy) {
    const busyAttr = busy ? ' aria-busy="true"' : '';
    return `
        <div class="flex min-h-[calc(100dvh-8rem)] flex-col items-center justify-center gap-3 px-4 sm:min-h-[calc(100dvh-9rem)]" role="status" aria-live="polite"${busyAttr}>
            ${innerHtml}
        </div>`;
}

export function pageLoadingHtml(label = '正在加载') {
    return pageStatusShell(`
            <div class="h-5 w-5 animate-spin rounded-full border-2 border-brand-hud border-t-transparent sm:h-6 sm:w-6" aria-hidden="true"></div>
            <span class="text-[11px] text-ink-faint">${escapeHtml(label)}</span>`, true);
}

export function pageNoticeHtml(message) {
    return pageStatusShell(
        `<p class="text-center text-sm text-danger">${escapeHtml(message)}</p>`,
        false,
    );
}
