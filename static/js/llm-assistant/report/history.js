/**
 * 服务端分析历史（GET /api/llm/reports）
 */

import { listReports } from '../api.js';
import { analysesKeyLabelZh } from './labels.js';

const STATUS_LABEL = {
    succeeded: '完成',
    failed: '失败',
    running: '进行中',
    pending: '排队',
    processing: '进行中',
};

/**
 * @param {HTMLElement} overlay
 * @param {{
 *   onSelect: (reportId: number) => void,
 *   onClose: () => void,
 * }} options
 */
export async function openHistoryPanel(overlay, options) {
    if (!overlay) return;

    overlay.classList.remove('hidden');
    overlay.innerHTML = `
<div class="flex items-center justify-between px-3 py-2 border-b border-[#222] bg-[#1e1e1e] shrink-0">
  <div class="text-xs font-semibold text-[#F0F0F2]">分析历史</div>
  <button type="button" id="llmHistoryClose" class="w-7 h-7 inline-flex items-center justify-center text-[#9e9e9e] hover:text-white" aria-label="关闭">×</button>
</div>
<div id="llmHistoryBody" class="flex-1 overflow-y-auto px-3 py-2 bg-[#0a0a0a] min-h-0">
  <div class="flex items-center justify-center py-8 text-[11px] text-[#757575]">
    <span class="inline-block w-3 h-3 border border-[#616161] border-t-[#ff5252] rounded-full animate-spin mr-2"></span>
    加载中…
  </div>
</div>`;

    overlay.querySelector('#llmHistoryClose')?.addEventListener('click', () => {
        overlay.classList.add('hidden');
        options.onClose?.();
    });

    const body = overlay.querySelector('#llmHistoryBody');
    try {
        const data = await listReports({ skip: 0, limit: 30 });
        const items = data?.items || [];
        if (!items.length) {
            body.innerHTML = `<div class="py-10 text-center text-[11px] text-[#757575]">暂无分析记录</div>`;
            return;
        }

        body.innerHTML = items.map((item) => renderHistoryItem(item)).join('');
        body.querySelectorAll('[data-report-id]').forEach((btn) => {
            btn.addEventListener('click', () => {
                const reportId = Number(btn.getAttribute('data-report-id'));
                if (reportId) {
                    options.onSelect?.(reportId);
                }
            });
        });
    } catch (error) {
        body.innerHTML = `<div class="py-8 text-center text-[11px] text-[#ef5350]">${esc(error?.message || '加载失败')}</div>`;
    }
}

/**
 * @param {object} item
 * @returns {string}
 */
function renderHistoryItem(item) {
    const status = String(item.status || '').toLowerCase();
    const statusLabel = STATUS_LABEL[status] || status || '-';
    const statusClass = status === 'succeeded'
        ? 'text-[#4caf50]'
        : status === 'failed'
            ? 'text-[#ef5350]'
            : 'text-[#ffb74d]';
    const question = item.user_question || '（无问句）';
    const scope = item.scope || {};
    const scopeText = [scope.location, scope.year, scope.month].filter(Boolean).join(' · ');
    const types = item.resolved_report_type
        ? analysesKeyLabelZh(item.resolved_report_type)
        : '';
    const generated = item.metadata?.generated_at
        ? formatTime(item.metadata.generated_at)
        : '';

    return `
<button type="button" data-report-id="${escAttr(item.report_id)}"
  class="w-full text-left mb-2 px-2.5 py-2 border border-[#222222] bg-[#141414] hover:bg-[#1a1a1a] hover:border-[#2c2c2c] transition-colors rounded-sm">
  <div class="text-[11px] text-[#F0F0F2] line-clamp-2">${esc(question)}</div>
  <div class="mt-1 flex flex-wrap gap-x-2 gap-y-0.5 text-[9px] text-[#555555]">
    <span class="${statusClass}">${esc(statusLabel)}</span>
    ${scopeText ? `<span>${esc(scopeText)}</span>` : ''}
    ${types ? `<span class="font-mono">${esc(types)}</span>` : ''}
    ${generated ? `<span>${esc(generated)}</span>` : ''}
  </div>
</button>`;
}

/**
 * @param {string} iso
 * @returns {string}
 */
function formatTime(iso) {
    try {
        const date = new Date(iso);
        if (Number.isNaN(date.getTime())) return iso;
        const pad = (n) => String(n).padStart(2, '0');
        return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
    } catch {
        return iso;
    }
}

function esc(value) {
    if (typeof window.esc === 'function') return window.esc(value);
    return String(value ?? '-');
}

function escAttr(value) {
    return esc(value).replace(/'/g, '&#39;');
}
