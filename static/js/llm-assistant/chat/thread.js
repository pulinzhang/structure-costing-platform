/**
 * 消息线程 — Snapshot 证据 + Markdown 解释 + Actions
 */

import { humanizeUserFacingError } from '../errors.js';
import { EXPORT_ICON_BTN_CLASS, llmIconPrint, llmIconWord } from '../icons.js';
import { renderMarkdown } from '../markdown/render.js';
import { renderActionsHtml } from '../report/actions.js';
import { renderSnapshotPanel } from '../report/snapshot-panel.js';

/**
 * @param {HTMLElement} root
 * @param {object[]} messages
 */
export function renderThread(root, messages) {
    if (!root) return;
    if (!Array.isArray(messages) || messages.length === 0) {
        root.innerHTML = `
<div class="flex flex-col items-center justify-center h-full min-h-[160px] text-center px-4">
  <p class="text-xs text-[#757575]">点下方常见问题，或直接输入一句人话提问</p>
  <p class="text-[10px] text-[#484848] mt-1">数字以系统证据为准；解释由 AI 生成。对话仅保存在本机</p>
</div>`;
        return;
    }

    root.innerHTML = messages.map((msg) => renderMessage(msg)).join('');
    root.scrollTop = root.scrollHeight;
}

/**
 * @param {object} msg
 * @returns {string}
 */
function renderMessage(msg) {
    const isUser = msg.role === 'user';
    const bubbleClass = isUser
        ? 'ml-8 bg-[#1e1e1e] border border-[#2c2c2c] text-[#F5F5F5]'
        : 'mr-2 bg-[#141414] border border-[#222222] text-[#E8E8E8]';

    let body;
    if (msg.status === 'pending') {
        body = `<div class="text-[11px] text-[#9e9e9e] flex items-center gap-2">
          <span class="inline-block w-3 h-3 border border-[#616161] border-t-[#ff5252] rounded-full animate-spin"></span>
          <span>${esc(msg.content || 'AI思考中…')}</span>
        </div>`;
    } else if (msg.status === 'error') {
        body = `<div class="text-[11px] text-[#ef5350]">${esc(humanizeUserFacingError(msg.content))}</div>`;
    } else if (!isUser) {
        let snapshotBlock = '';
        try {
            snapshotBlock = renderSnapshotPanel(
                msg.snapshot,
                msg.scope,
                msg.resolved_report_type,
            );
        } catch (renderError) {
            console.warn('[llm-assistant] snapshot render failed', renderError);
            snapshotBlock = '<div class="mb-2 text-[10px] text-[#757575]">证据面板暂时无法展示，请查看下方 AI 说明。</div>';
        }
        const exportToolbar = renderExportToolbar(msg);
        const markdownBlock = `<div class="llm-md text-[11px] leading-relaxed [&_h1]:text-sm [&_h2]:text-xs [&_h3]:text-[11px] [&_p]:my-1.5 [&_ul]:my-1.5 [&_ul]:list-disc [&_ul]:pl-4 [&_code]:font-mono [&_code]:text-[10px] [&_code]:text-[#ff8a80]">${renderMarkdown(msg.content || '')}</div>`;
        const actionsBlock = renderActionsHtml(msg.actions);
        body = `${snapshotBlock}<div class="mt-2 border-t border-[#1f1f1f] pt-2">${exportToolbar}${markdownBlock}</div>${actionsBlock}`;
    } else {
        body = `<div class="text-[11px] whitespace-pre-wrap break-words">${esc(msg.content || '')}</div>`;
    }

    const metaParts = [];
    if (msg.report_id) {
        metaParts.push(`#${msg.report_id}`);
    }
    if (msg.from_cache) {
        metaParts.push('缓存');
    }
    if (msg.prompt_version) {
        metaParts.push(msg.prompt_version);
    }
    const meta = metaParts.length
        ? `<div class="mt-1.5 text-[9px] font-mono text-[#3a3a3a]">${esc(metaParts.join(' · '))}</div>`
        : '';

    return `
<div class="flex ${isUser ? 'justify-end' : 'justify-start'}" data-msg-id="${escAttr(msg.id)}">
  <div class="max-w-[96%] px-2.5 py-2 rounded-sm ${bubbleClass}">
    ${body}
    ${meta}
  </div>
</div>`;
}

/**
 * @param {object} msg
 * @returns {boolean}
 */
function canShowExportToolbar(msg) {
    if (msg.role !== 'assistant') return false;
    if (msg.status === 'pending' || msg.status === 'error') return false;
    const content = String(msg.content || '').trim();
    if (!content || content === 'AI正在思考中...' || content.startsWith('AI思考中')) return false;
    return true;
}

/**
 * @param {object} msg
 * @returns {string}
 */
function renderExportToolbar(msg) {
    if (!canShowExportToolbar(msg)) return '';

    return `
<div class="flex items-center justify-end gap-0.5 mb-1.5" data-llm-export-toolbar>
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
