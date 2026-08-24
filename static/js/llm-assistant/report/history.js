/**
 * 服务端分析历史（GET /api/llm/reports）
 * 每人仅自己的记录；每页 10 条，触底加载更多。
 */

import { deleteReport, listReports } from '../api.js';
import { analysesKeyLabelZh } from './labels.js';

const PAGE_SIZE = 10;
const SCROLL_LOAD_THRESHOLD_PX = 48;

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
 *   onDeleted?: (reportId: number) => void,
 *   onClose: () => void,
 * }} options
 */
export async function openHistoryPanel(overlay, options) {
    if (!overlay) return;

    /** @type {{ items: object[], skip: number, total: number, loading: boolean, hasMore: boolean }} */
    const state = {
        items: [],
        skip: 0,
        total: 0,
        loading: false,
        hasMore: true,
    };

    overlay.classList.remove('hidden');
    overlay.innerHTML = `
<div class="flex items-center justify-between px-3 py-2 border-b border-[#222] bg-[#1e1e1e] shrink-0">
  <div class="text-xs font-semibold text-[#F0F0F2]">分析历史</div>
  <button type="button" id="llmHistoryClose" class="w-7 h-7 inline-flex items-center justify-center text-[#9e9e9e] hover:text-white" aria-label="关闭">×</button>
</div>
<div id="llmHistoryBody" class="flex-1 overflow-y-auto px-3 py-2 bg-[#0a0a0a] min-h-0">
  <div id="llmHistoryList"></div>
  <div id="llmHistoryFooter" class="py-3 text-center text-[10px] text-[#555555]"></div>
</div>`;

    overlay.querySelector('#llmHistoryClose')?.addEventListener('click', () => {
        overlay.classList.add('hidden');
        options.onClose?.();
    });

    const body = overlay.querySelector('#llmHistoryBody');
    const listEl = overlay.querySelector('#llmHistoryList');
    const footerEl = overlay.querySelector('#llmHistoryFooter');
    if (!body || !listEl || !footerEl) return;

    const renderFooter = () => {
        if (!state.items.length && !state.loading) {
            footerEl.innerHTML = '';
            return;
        }
        // 已无更多：绝不显示「加载更多」，避免触底后仍误以为还有
        if (!state.hasMore) {
            footerEl.textContent = state.items.length ? '没有更多了' : '';
            return;
        }
        if (state.loading && state.items.length) {
            footerEl.innerHTML = `
  <span class="inline-block w-3 h-3 border border-[#616161] border-t-[#ff5252] rounded-full animate-spin mr-1 align-middle"></span>
  加载更多…`;
            return;
        }
        footerEl.textContent = '';
    };

    const renderList = () => {
        if (!state.items.length && !state.loading) {
            listEl.innerHTML = `<div class="py-10 text-center text-[11px] text-[#757575]">暂无分析记录</div>`;
            renderFooter();
            return;
        }
        listEl.innerHTML = state.items.map((item) => renderHistoryItem(item)).join('');
        renderFooter();
    };

    const loadMore = async () => {
        if (state.loading || !state.hasMore) return;
        state.loading = true;
        if (!state.items.length) {
            listEl.innerHTML = `
  <div class="flex items-center justify-center py-8 text-[11px] text-[#757575]">
    <span class="inline-block w-3 h-3 border border-[#616161] border-t-[#ff5252] rounded-full animate-spin mr-2"></span>
    加载中…
  </div>`;
            footerEl.innerHTML = '';
        } else {
            renderFooter();
        }

        try {
            const data = await listReports({ skip: state.skip, limit: PAGE_SIZE });
            const batch = data?.items || [];
            state.total = Number(data?.total ?? state.total);
            state.items = state.items.concat(batch);
            state.skip = state.items.length;
            state.hasMore = state.skip < state.total && batch.length > 0;
            state.loading = false;
            renderList();
        } catch (error) {
            state.loading = false;
            if (!state.items.length) {
                listEl.innerHTML = `<div class="py-8 text-center text-[11px] text-[#ef5350]">${esc(error?.message || '加载失败')}</div>`;
                footerEl.innerHTML = '';
            } else {
                window.showToast?.(error?.message || '加载失败', 'error');
                renderFooter();
            }
        }
    };

    const reloadFromStart = async () => {
        state.items = [];
        state.skip = 0;
        state.total = 0;
        state.hasMore = true;
        state.loading = false;
        await loadMore();
    };

    body.addEventListener('scroll', () => {
        if (state.loading || !state.hasMore) return;
        const nearBottom = body.scrollTop + body.clientHeight >= body.scrollHeight - SCROLL_LOAD_THRESHOLD_PX;
        if (nearBottom) {
            void loadMore();
        }
    });

    body.addEventListener('click', (event) => {
        const openBtn = event.target.closest('[data-action="open-report"]');
        if (openBtn) {
            const reportId = Number(openBtn.getAttribute('data-report-id'));
            if (reportId) {
                options.onSelect?.(reportId);
            }
            return;
        }

        const deleteBtn = event.target.closest('[data-action="delete-report"]');
        if (!deleteBtn) return;

        const reportId = Number(deleteBtn.getAttribute('data-report-id'));
        if (!reportId) return;

        const question = deleteBtn.getAttribute('data-question') || '';
        const promptText = question
            ? `确定删除这条分析记录？\n${question}`
            : '确定删除这条分析记录？';
        if (!window.confirm(promptText)) return;

        void (async () => {
            deleteBtn.disabled = true;
            try {
                await deleteReport(reportId);
                window.showToast?.('已删除', 'success');
                options.onDeleted?.(reportId);
                const index = state.items.findIndex(
                    (item) => Number(item.report_id) === reportId,
                );
                if (index >= 0) {
                    state.items.splice(index, 1);
                    state.total = Math.max(0, state.total - 1);
                    state.skip = state.items.length;
                    state.hasMore = state.skip < state.total;
                    renderList();
                    if (state.hasMore && state.items.length < PAGE_SIZE) {
                        await loadMore();
                    }
                } else {
                    await reloadFromStart();
                }
            } catch (error) {
                window.showToast?.(error?.message || '删除失败', 'error');
                deleteBtn.disabled = false;
            }
        })();
    });

    await loadMore();
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
<div class="mb-2 px-2.5 py-2 border border-[#222222] bg-[#141414] rounded-sm">
  <div class="text-[11px] text-[#F0F0F2] line-clamp-2">${esc(question)}</div>
  <div class="mt-1 flex flex-wrap gap-x-2 gap-y-0.5 text-[9px] text-[#555555]">
    <span class="${statusClass}">${esc(statusLabel)}</span>
    ${scopeText ? `<span>${esc(scopeText)}</span>` : ''}
    ${types ? `<span class="font-mono">${esc(types)}</span>` : ''}
    ${generated ? `<span>${esc(generated)}</span>` : ''}
  </div>
  <div class="mt-2 flex items-center justify-end gap-1">
    <button type="button" data-action="open-report" data-report-id="${escAttr(item.report_id)}"
      class="px-2 py-1 text-[10px] text-[#9e9e9e] border border-[#2c2c2c] hover:border-[#9e9e9e] hover:text-white rounded-sm transition-colors">
      打开
    </button>
    <button type="button" data-action="delete-report"
      data-report-id="${escAttr(item.report_id)}"
      data-question="${escAttr(question)}"
      class="px-2 py-1 text-[10px] text-[#ef5350] border border-[#2c2c2c] hover:border-[#ef5350] hover:bg-[#1a0808] rounded-sm transition-colors">
      删除
    </button>
  </div>
</div>`;
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
