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

    /** @type {{ items: object[], page: number, total: number, loading: boolean, hasMore: boolean }} */
    const state = {
        items: [],
        page: 1,
        total: 0,
        loading: false,
        hasMore: true,
    };

    overlay.classList.remove('hidden');
    overlay.innerHTML = `
<div class="flex items-center justify-between px-3 py-2 border-b border-line-subtle bg-app-surface shrink-0">
  <div class="text-xs font-semibold text-ink">分析历史</div>
  <button type="button" id="llmHistoryClose" class="w-7 h-7 inline-flex items-center justify-center text-ink-muted hover:text-ink" aria-label="关闭">×</button>
</div>
<div id="llmHistoryBody" class="flex-1 overflow-y-auto px-3 py-2 bg-app-deep min-h-0">
  <div id="llmHistoryList"></div>
  <div id="llmHistoryFooter" class="py-3 text-center text-[10px] text-ink-faint"></div>
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
  <span class="inline-block w-3 h-3 border border-ink-muted border-brand-active rounded-full animate-spin mr-1 align-middle"></span>
  加载更多…`;
            return;
        }
        footerEl.textContent = '';
    };

    const renderList = () => {
        if (!state.items.length && !state.loading) {
            listEl.innerHTML = `<div class="py-10 text-center text-[11px] text-ink-muted">暂无分析记录</div>`;
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
  <div class="flex items-center justify-center py-8 text-[11px] text-ink-muted">
    <span class="inline-block w-3 h-3 border border-ink-muted border-brand-active rounded-full animate-spin mr-2"></span>
    加载中…
  </div>`;
            footerEl.innerHTML = '';
        } else {
            renderFooter();
        }

        try {
            const data = await listReports({ page: state.page, size: PAGE_SIZE });
            const batch = data?.items || [];
            state.total = Number(data?.total ?? state.total);
            state.items = state.items.concat(batch);
            state.page += 1;
            state.hasMore = state.items.length < state.total && batch.length > 0;
            state.loading = false;
            renderList();
        } catch (error) {
            state.loading = false;
            if (!state.items.length) {
                listEl.innerHTML = `<div class="py-8 text-center text-[11px] text-danger">${esc(error?.message || '加载失败')}</div>`;
                footerEl.innerHTML = '';
            } else {
                window.showToast?.(error?.message || '加载失败', 'error');
                renderFooter();
            }
        }
    };

    const reloadFromStart = async () => {
        state.items = [];
        state.page = 1;
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

    body.addEventListener('click', async (event) => {
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
        if (!await window.confirmAction(promptText)) return;

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
                    state.hasMore = state.items.length < state.total;
                    renderList();
                    if (state.hasMore && state.items.length < PAGE_SIZE) {
                        await loadMore();
                    }
                } else {
                    await reloadFromStart();
                }
            } catch (_error) {
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
        ? 'text-ok'
        : status === 'failed'
            ? 'text-danger'
            : 'text-warn';
    const question = item.user_question || '（无问句）';
    const scope = item.scope || {};
    const scopeText = [scope.location, fmtPeriod(scope.year, scope.month)].filter(Boolean).join(' · ');
    const types = item.resolved_report_type
        ? analysesKeyLabelZh(item.resolved_report_type)
        : '';
    const generated = item.metadata?.generated_at
        ? formatTime(item.metadata.generated_at)
        : '';

    return `
<div class="mb-2 px-2.5 py-2 border border-line-subtle bg-app-main rounded-sm">
  <div class="text-[11px] text-ink line-clamp-2">${esc(question)}</div>
  <div class="mt-1 flex flex-wrap gap-x-2 gap-y-0.5 text-[9px] text-ink-faint">
    <span class="${statusClass}">${esc(statusLabel)}</span>
    ${scopeText ? `<span>${esc(scopeText)}</span>` : ''}
    ${types ? `<span class="font-mono">${esc(types)}</span>` : ''}
    ${generated ? `<span>${esc(generated)}</span>` : ''}
  </div>
  <div class="mt-2 flex items-center justify-end gap-1">
    <button type="button" data-action="open-report" data-report-id="${escAttr(item.report_id)}"
      class="px-2 py-1 text-[10px] text-ink-muted border border-line hover:border-ink-muted hover:text-ink rounded-sm transition-colors">
      打开
    </button>
    <button type="button" data-action="delete-report"
      data-report-id="${escAttr(item.report_id)}"
      data-question="${escAttr(question)}"
      class="px-2 py-1 text-[10px] text-danger border border-line hover:border-danger hover:bg-app-deep rounded-sm transition-colors">
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
