/**
 * 错误提示框：停到用户关闭，正文可选中，可复制全文。
 * 各页只传 id 前缀、标题、说明；禁止再复制遮罩、正文和复制按钮。
 */

import { BTN_GHOST, BTN_SOLID, DRAWER_CLOSE } from './classes.js?v=13';

const DEFAULT_HINT = '原因留在这里，看完再关。正文可选中，也可复制全文。';
const DEFAULT_MESSAGE = '操作失败';

function escapeHtml(value) {
    if (typeof window.esc === 'function') return window.esc(value);
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function dialogIds(prefix) {
    const base = String(prefix || '').trim();
    return {
        dialog: `${base}Dialog`,
        backdrop: `${base}Backdrop`,
        panel: `${base}Panel`,
        title: `${base}Title`,
        body: `${base}Body`,
        close: `${base}CloseBtn`,
        copy: `${base}CopyBtn`,
        ok: `${base}OkBtn`,
    };
}

/**
 * @param {{ prefix: string, title: string, hint?: string }} opts
 * @returns {string}
 */
export function errorDialogHtml({ prefix, title, hint = DEFAULT_HINT }) {
    const id = dialogIds(prefix);
    const heading = String(title || '').trim() || DEFAULT_MESSAGE;
    const note = String(hint || '').trim() || DEFAULT_HINT;
    const closeIcon = typeof window.svgIcon === 'function'
        ? window.svgIcon('x-lg', 'w-4 h-4')
        : '';
    return `
        <div id="${escapeHtml(id.dialog)}"
             class="hidden fixed inset-0 z-[100] flex items-center justify-center p-4"
             role="alertdialog"
             aria-modal="true"
             aria-labelledby="${escapeHtml(id.title)}"
             aria-describedby="${escapeHtml(id.body)}">
            <div id="${escapeHtml(id.backdrop)}" class="absolute inset-0 bg-overlay/70 backdrop-blur-sm"></div>
            <div id="${escapeHtml(id.panel)}"
                 tabindex="-1"
                 class="relative w-[640px] max-w-[95vw] bg-app-main border border-danger/50 flex flex-col shadow-[var(--shadow-drawer)] outline-none">
                <div class="flex items-start justify-between gap-3 px-4 py-3 border-b border-danger/30">
                    <div class="min-w-0">
                        <h6 id="${escapeHtml(id.title)}" class="text-[13px] font-semibold text-danger mb-0.5">${escapeHtml(heading)}</h6>
                        <p class="text-[10px] text-ink-muted mb-0">${escapeHtml(note)}</p>
                    </div>
                    <button type="button" id="${escapeHtml(id.close)}"
                            class="${DRAWER_CLOSE}"
                            aria-label="关闭">
                        ${closeIcon}
                    </button>
                </div>
                <pre id="${escapeHtml(id.body)}"
                     class="m-0 px-4 py-3 text-[12px] font-mono leading-relaxed text-ink whitespace-pre-wrap break-words max-h-[360px] overflow-y-auto select-text"></pre>
                <div class="flex items-center justify-end gap-2 px-4 py-3 border-t border-line">
                    <button type="button" id="${escapeHtml(id.copy)}" class="${BTN_GHOST}">复制</button>
                    <button type="button" id="${escapeHtml(id.ok)}" class="${BTN_SOLID}">关闭</button>
                </div>
            </div>
        </div>
    `;
}

/**
 * 渲染进页面后调用。框会挂到 document.body，避免被内容区 overflow 裁切。
 * @param {string} prefix
 * @returns {{ show: (message: string) => void, close: () => void, unbind: () => void }}
 */
export function bindErrorDialog(prefix) {
    const id = dialogIds(prefix);
    const dialog = document.getElementById(id.dialog);
    const body = document.getElementById(id.body);
    const panel = document.getElementById(id.panel);
    const copyBtn = document.getElementById(id.copy);
    const closeBtn = document.getElementById(id.close);
    const okBtn = document.getElementById(id.ok);
    const backdrop = document.getElementById(id.backdrop);
    if (dialog && dialog.parentElement !== document.body) {
        document.body.appendChild(dialog);
    }

    let text = '';

    function close() {
        dialog?.classList.add('hidden');
        if (body) body.textContent = '';
        text = '';
    }

    function show(message) {
        const next = String(message || '').trim() || DEFAULT_MESSAGE;
        text = next;
        if (!dialog || !body) return;
        body.textContent = next;
        if (copyBtn) copyBtn.textContent = '复制';
        dialog.classList.remove('hidden');
        panel?.focus();
    }

    function onEscape(event) {
        if (event.key !== 'Escape') return;
        if (!dialog || dialog.classList.contains('hidden')) return;
        event.preventDefault();
        event.stopPropagation();
        close();
    }

    async function copyText() {
        if (!text) return;
        try {
            await navigator.clipboard.writeText(text);
            if (copyBtn) copyBtn.textContent = '已复制';
            window.setTimeout(() => {
                if (copyBtn && copyBtn.isConnected && copyBtn.textContent === '已复制') {
                    copyBtn.textContent = '复制';
                }
            }, 1600);
        } catch (_error) {
            if (!body) return;
            const range = document.createRange();
            range.selectNodeContents(body);
            const selection = window.getSelection();
            selection?.removeAllRanges();
            selection?.addRange(range);
            if (copyBtn) copyBtn.textContent = '已选中';
        }
    }

    closeBtn?.addEventListener('click', close);
    okBtn?.addEventListener('click', close);
    backdrop?.addEventListener('click', close);
    copyBtn?.addEventListener('click', copyText);
    document.addEventListener('keydown', onEscape, true);

    return {
        show,
        close,
        unbind() {
            document.removeEventListener('keydown', onEscape, true);
            closeBtn?.removeEventListener('click', close);
            okBtn?.removeEventListener('click', close);
            backdrop?.removeEventListener('click', close);
            copyBtn?.removeEventListener('click', copyText);
            dialog?.remove();
            text = '';
        },
    };
}
