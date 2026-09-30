/**
 * 消息线程 — Markdown 回答
 */

import { humanizeUserFacingError } from '../errors.js';
import { EXPORT_ICON_BTN_CLASS, llmIconCopy, llmIconPrint, llmIconWord } from '../icons.js?v=2';
import { renderMarkdown } from '../markdown/render.js?v=7';
import { canExportAssistantMessage } from '../export/document.js?v=12';

/**
 * @param {HTMLElement} root
 * @param {object[]} messages
 * @param {{ stick?: boolean }} [options]
 */
export function renderThread(root, messages, options = {}) {
    if (!root) return;
    const distanceFromBottom = root.scrollHeight - root.scrollTop - root.clientHeight;
    const stickToBottom = options.stick === true || distanceFromBottom < 80;
    const previousTop = root.scrollTop;

    if (!Array.isArray(messages) || messages.length === 0) {
        root.innerHTML = '';
        return;
    }

    root.innerHTML = messages.map((msg) => renderMessage(msg)).join('');
    root.scrollTop = stickToBottom ? root.scrollHeight : previousTop;
}

/**
 * @param {object} msg
 * @returns {string}
 */
function renderMessage(msg) {
    const isUser = msg.role === 'user';

    let body;
    if (msg.status === 'pending') {
        body = `<div class="text-[13px] text-ink-muted flex items-center gap-2">
          <span class="inline-block w-3 h-3 border border-ink-faint border-t-ink-muted rounded-full animate-spin"></span>
          <span>${esc(msg.content || 'AI思考中…')}</span>
        </div>`;
    } else if (msg.status === 'error') {
        body = `<div class="text-[13px] leading-relaxed text-danger">${esc(humanizeUserFacingError(msg.content))}</div>`;
    } else if (!isUser) {
        const exportToolbar = renderExportToolbar(msg);
        const periodChip = renderPeriodChip(msg);
        const markdownBlock = `<div class="llm-md text-[13px] leading-6 text-ink [&_h1]:text-base [&_h1]:font-semibold [&_h1]:mt-4 [&_h1]:mb-2 [&_h2]:text-sm [&_h2]:font-semibold [&_h2]:mt-3 [&_h2]:mb-1.5 [&_h3]:text-[13px] [&_h3]:font-medium [&_h3]:mt-2 [&_p]:my-2 [&_ul]:my-2 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:my-2 [&_ol]:list-decimal [&_ol]:pl-5 [&_li]:my-0.5 [&_strong]:font-semibold [&_code]:font-mono [&_code]:text-[12px] [&_code]:bg-app-elevated [&_code]:px-1 [&_code]:rounded [&_.table-scroll]:overflow-x-auto [&_.table-scroll]:max-w-full [&_.table-scroll]:my-3 [&_table]:w-full [&_table]:border-collapse [&_table]:text-[13px] [&_table]:leading-relaxed [&_th]:border-0 [&_th]:border-b [&_th]:border-line [&_th]:px-0 [&_th]:pr-4 [&_th]:py-1.5 [&_th]:text-left [&_th]:align-bottom [&_th]:font-medium [&_th]:text-ink-muted [&_th]:whitespace-nowrap [&_td]:border-0 [&_td]:border-b [&_td]:border-line-subtle [&_td]:px-0 [&_td]:pr-4 [&_td]:py-1.5 [&_td]:align-top [&_tbody_tr:last-child_td]:border-b-0 [&_.cell-keep]:whitespace-nowrap [&_.cell-wrap]:max-w-[12em] [&_.cell-wrap]:break-words">${renderMarkdown(msg.content || '')}</div>`;
        body = `${periodChip}${markdownBlock}${exportToolbar}`;
    } else {
        body = `<div class="whitespace-pre-wrap break-words">${esc(msg.content || '')}</div>`;
    }

    if (isUser) {
        return `
<div class="group flex flex-col items-end" data-msg-id="${escAttr(msg.id)}">
  <div class="max-w-[85%] px-3.5 py-2 rounded-2xl bg-app-elevated text-[13px] leading-relaxed text-ink">
    ${body}
  </div>
  ${renderQuestionCopy(msg)}
</div>`;
    }

    return `
<div class="group flex justify-start" data-msg-id="${escAttr(msg.id)}">
  <div class="w-full min-w-0">
    ${body}
  </div>
</div>`;
}

/**
 * @param {object} msg
 * @returns {string}
 */
function renderPeriodChip(msg) {
    const scope = msg.scope || {};
    const period = typeof window.fmtPeriod === 'function'
        ? window.fmtPeriod(scope.year, scope.month)
        : '';
    if (!period) return '';
    const extra = [scope.location, scope.vehicle_model, scope.part_number]
        .filter(Boolean)
        .map((item) => esc(String(item)))
        .join(' · ');
    return `<p class="text-[11px] text-ink-faint mb-2">${esc(period)}${extra ? ` · ${extra}` : ''}</p>`;
}

function renderQuestionCopy(msg) {
    const text = String(msg.content || '').trim();
    if (!text) return '';
    return `
<div class="mt-1 h-6 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
  <button type="button" data-llm-copy-question data-msg-id="${escAttr(msg.id)}"
    class="${EXPORT_ICON_BTN_CLASS}"
    title="复制问题" aria-label="复制问题">${llmIconCopy()}</button>
</div>`;
}

function renderExportToolbar(msg) {
    if (!canExportAssistantMessage(msg)) return '';

    return `
<div class="flex items-center justify-end gap-0.5 mt-1 h-6 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100" data-llm-export-toolbar>
  <button type="button" data-llm-export="print" data-msg-id="${escAttr(msg.id)}"
    class="${EXPORT_ICON_BTN_CLASS}"
    title="打印" aria-label="打印">${llmIconPrint()}</button>
  <button type="button" data-llm-export="word" data-msg-id="${escAttr(msg.id)}"
    class="${EXPORT_ICON_BTN_CLASS}"
    title="导出 Word" aria-label="导出 Word">${llmIconWord()}</button>
</div>`;
}

function esc(value) {
    if (typeof window.esc === 'function') return window.esc(value);
    return String(value ?? '-')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function escAttr(value) {
    return esc(value).replace(/'/g, '&#39;');
}
