/**
 * 总成核价计算报告（独立浅色页签 · Brabus light）
 */

import { resolveBomNodeShortCode } from '../../../../part-identity.js?v=3';
import { formatDurationSeconds } from '../../../../duration.js?v=1';

const STATUS_LABEL = {
    ok: '成功',
    partial: '部分成功',
    failed: '失败',
    skipped: '跳过',
    processing: '计算中',
    success: '成功',
};

const CARD_STATUS_CLASS = {
    ok: 'status-ok',
    partial: 'status-partial',
    failed: 'status-failed',
    skipped: 'status-skipped',
};

const state = {
    logId: 0,
    log: null,
    keyword: '',
    status: 'all',
    level: 'all',
    treeRoot: 'all',
    exporting: false,
};

function hasActiveFilters() {
    return Boolean(
        state.keyword.trim()
        || state.status !== 'all'
        || state.level !== 'all'
        || state.treeRoot !== 'all',
    );
}

function showToast(message, type) {
    const node = document.getElementById('reportToast');
    if (!node) return;
    node.textContent = message;
    node.classList.toggle('is-error', type === 'error');
    node.classList.add('is-on');
    window.clearTimeout(showToast._timer);
    showToast._timer = window.setTimeout(() => node.classList.remove('is-on'), 2600);
}

function display(value) {
    if (value == null || value === '') return '—';
    return window.esc(value);
}

function partShortCode(card) {
    const partNumber = card?.part_number || '';
    const shortNo = resolveBomNodeShortCode(partNumber, {
        level: card?.level,
        nodeRole: card?.is_tree_root ? 'supply' : undefined,
    });
    return shortNo || partNumber;
}

function restoreView(card) {
    return card?.object_kind ? 'procurement' : 'finance';
}

function restoreHref(card) {
    const log = state.log || {};
    const query = new URLSearchParams({
        year: String(log.year || ''),
        month: String(log.month || ''),
        part_number: card.part_number || '',
        view: restoreView(card),
    });
    if (log.location) query.set('location', log.location);
    if (log.vehicle_model) query.set('vehicle_model', log.vehicle_model);
    if (log.bom_version) query.set('bom_version', log.bom_version);
    return `/assembly-cost-restore?${query.toString()}`;
}

const CALCULATOR_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><rect x="4" y="2" width="16" height="20" rx="2"/><path d="M8 6h8"/><path d="M8 10h8"/><path d="M8 14h2"/><path d="M14 14h2"/><path d="M8 18h2"/><path d="M14 18h2"/></svg>';

function restoreBadgeHtml(card) {
    if (!card?.part_number) return '';
    return `<a class="restore-badge" href="${restoreHref(card)}" target="_blank" rel="noopener noreferrer" title="计算过程" aria-label="计算过程">${CALCULATOR_ICON}</a>`;
}

function logIdFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return parseInt(params.get('log_id') || '', 10);
}

async function loadLog(logId) {
    const res = await HttpClient.get(`/api/costing/assembly-costs/calc/logs/${logId}`);
    return res.data || {};
}

function formatWhen(value) {
    if (!value) return '—';
    return String(value).replace('T', ' ').slice(0, 19);
}

function printDateText() {
    const now = new Date();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hour = String(now.getHours()).padStart(2, '0');
    const minute = String(now.getMinutes()).padStart(2, '0');
    return `${now.getFullYear()}年${month}月${day}日 ${hour}:${minute}`;
}

function printHeadInnerHtml() {
    const log = state.log || {};
    const period = fmtPeriod(log.year, log.month);
    const scope = [log.location, log.vehicle_model, log.bom_version].filter(Boolean).join(' / ');
    return `
        <div class="print-running-brand">
            <span class="print-kicker">Assembly Costing Process Report</span>
            <strong>总成核价计算报告</strong>
        </div>
        <div class="print-running-meta">
            <span>${display(scope || '—')}</span>
            <span>${display(period)}</span>
            <span>打印 ${display(printDateText())}</span>
        </div>
    `;
}

function paintPrintHead() {
    const node = document.getElementById('reportPrintHead');
    if (!node || !state.log) return;
    node.innerHTML = printHeadInnerHtml();
}

function printBannerRowHtml() {
    return `
        <tr class="print-page-banner">
            <th colspan="11">
                <div class="print-running-head" id="reportPrintHead">${printHeadInnerHtml()}</div>
            </th>
        </tr>
    `;
}

function uniqueLevels(cards) {
    return [...new Set(cards.map((card) => Number(card.level)).filter((n) => Number.isFinite(n)))].sort((a, b) => a - b);
}

function matches(card) {
    if (state.status !== 'all' && card.status !== state.status) return false;
    if (state.level !== 'all' && String(card.level) !== state.level) return false;
    if (state.treeRoot === 'yes' && !card.is_tree_root) return false;
    if (state.treeRoot === 'no' && card.is_tree_root) return false;
    const keyword = state.keyword.trim().toLowerCase();
    if (!keyword) return true;
    const hay = [
        card.seq_label,
        partShortCode(card),
        card.part_number,
        card.part_name,
        card.message,
        card.object_kind,
        ...(card.missing_parts || []),
    ].join(' ').toLowerCase();
    return hay.includes(keyword);
}

function filterSelectHtml(id, options) {
    const items = options.map(([value, label]) => (
        `<li role="option" data-value="${display(value)}">${display(label)}</li>`
    )).join('');
    return `
        <div class="filter-select" id="${id}">
            <button type="button" class="filter-select-btn" aria-haspopup="listbox" aria-expanded="false"></button>
            <ul class="filter-select-menu" hidden role="listbox">${items}</ul>
        </div>
    `;
}

function closeFilterSelects(root) {
    root.querySelectorAll('.filter-select').forEach((host) => {
        host.classList.remove('is-open');
        const btn = host.querySelector('.filter-select-btn');
        const menu = host.querySelector('.filter-select-menu');
        if (btn) btn.setAttribute('aria-expanded', 'false');
        if (menu) menu.hidden = true;
    });
}

function syncFilterSelect(host, currentValue) {
    const btn = host.querySelector('.filter-select-btn');
    host.querySelectorAll('[data-value]').forEach((item) => {
        const on = item.dataset.value === String(currentValue);
        item.classList.toggle('is-on', on);
        if (on && btn) btn.textContent = item.textContent.trim();
    });
}

function bindFilterSelect(root, hostId, stateKey) {
    const host = root.querySelector(`#${hostId}`);
    if (!host) return;
    const btn = host.querySelector('.filter-select-btn');
    const menu = host.querySelector('.filter-select-menu');
    syncFilterSelect(host, state[stateKey]);
    btn.addEventListener('click', (event) => {
        event.stopPropagation();
        const willOpen = menu.hidden;
        closeFilterSelects(root);
        if (willOpen) {
            host.classList.add('is-open');
            menu.hidden = false;
            btn.setAttribute('aria-expanded', 'true');
        }
    });
    menu.addEventListener('click', (event) => {
        const item = event.target.closest('[data-value]');
        if (!item) return;
        state[stateKey] = item.dataset.value;
        closeFilterSelects(root);
        syncFilterSelect(host, state[stateKey]);
        refreshRows(root);
    });
}

function bindFilters(root) {
    const keyword = root.querySelector('#reportKeyword');
    keyword.value = state.keyword;
    keyword.addEventListener('input', () => {
        state.keyword = keyword.value;
        refreshRows(root);
    });
    root.querySelectorAll('[data-status]').forEach((btn) => {
        btn.addEventListener('click', () => {
            state.status = btn.dataset.status;
            refreshRows(root);
        });
    });
    bindFilterSelect(root, 'reportLevel', 'level');
    bindFilterSelect(root, 'reportTreeRoot', 'treeRoot');
    document.addEventListener('click', () => closeFilterSelects(root));
    root.querySelector('#reportPrintBtn')?.addEventListener('click', () => {
        paintPrintHead();
        window.print();
    });
    root.querySelector('#reportExportBtn')?.addEventListener('click', () => exportExcel(true));
    root.querySelector('#reportExportAllBtn')?.addEventListener('click', () => exportExcel(false));
}

async function exportExcel(useFilter) {
    if (state.exporting || !state.logId) return;
    state.exporting = true;
    refreshExportButtons();
    const params = {};
    if (useFilter) {
        const keyword = state.keyword.trim();
        if (keyword) params.keyword = keyword;
        if (state.status !== 'all') params.status = state.status;
        if (state.level !== 'all') params.level = state.level;
        if (state.treeRoot !== 'all') params.tree_root = state.treeRoot;
    }
    try {
        const { blob, filename } = await HttpClient.download(
            `/api/costing/assembly-costs/calc/logs/${state.logId}/export-download`,
            {
                params,
                defaultFilename: '总成核价计算报告.xlsx',
            },
        );
        const objectUrl = URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = objectUrl;
        anchor.download = filename;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        URL.revokeObjectURL(objectUrl);
        showToast(useFilter && hasActiveFilters() ? '已导出当前筛选。' : '已导出全部核价卡。');
    } catch (error) {
        if (!error.status) {
            showToast(error.message || '导出失败', 'error');
        }
    } finally {
        state.exporting = false;
        refreshExportButtons();
    }
}

function refreshExportButtons() {
    const exportBtn = document.getElementById('reportExportBtn');
    const exportAllBtn = document.getElementById('reportExportAllBtn');
    const hint = document.getElementById('reportExportHint');
    const filtered = hasActiveFilters();
    if (exportBtn) {
        exportBtn.disabled = state.exporting;
        exportBtn.textContent = state.exporting ? '导出中…' : (filtered ? '导出当前筛选' : '导出 Excel');
    }
    if (exportAllBtn) {
        exportAllBtn.hidden = !filtered;
        exportAllBtn.disabled = state.exporting;
    }
    if (hint) {
        hint.textContent = filtered
            ? 'Excel 与当前表格一致；需要全量时点「全部」。'
            : '含封面摘要、核价卡与过程说明。快捷键 Ctrl+E';
    }
}

function refreshRows(root) {
    const log = state.log;
    const cards = Array.isArray(log.cards) ? log.cards : [];
    const filtered = cards.filter(matches);
    root.querySelectorAll('[data-status]').forEach((btn) => {
        btn.classList.toggle('is-on', btn.dataset.status === state.status);
    });
    const count = root.querySelector('.count');
    if (count) count.textContent = `显示 ${filtered.length} / ${cards.length} 张卡`;
    refreshExportButtons();
    const tableHost = root.querySelector('#reportTableHost');
    if (tableHost) tableHost.innerHTML = renderTable(filtered);
    paintPrintHead();
}

function render(root) {
    const log = state.log;
    const cards = Array.isArray(log.cards) ? log.cards : [];
    const filtered = cards.filter(matches);
    const period = fmtPeriod(log.year, log.month);
    const levels = uniqueLevels(cards);
    document.title = `总成核价计算报告 · ${period} · ${log.vehicle_model || ''}`;

    root.innerHTML = `
        <header class="report-head">
            <div>
                <p>Assembly Costing Process Report</p>
                <h1>总成核价计算报告</h1>
            </div>
            <div class="report-actions">
                <span class="export-hint" id="reportExportHint"></span>
                <button type="button" id="reportPrintBtn">打印</button>
                <button type="button" id="reportExportAllBtn" class="btn-ghost" hidden>全部</button>
                <button type="button" id="reportExportBtn" class="btn-export">导出 Excel</button>
            </div>
        </header>
        <div class="meta">
            <div>范围 <strong>${display(`${log.location} / ${log.vehicle_model} / ${log.bom_version}`)}</strong></div>
            <div>核价期 <strong>${display(period)}</strong></div>
            <div>状态 <strong>${display(STATUS_LABEL[log.status] || log.status)}</strong></div>
            <div>操作人 <strong>${display(log.operator_name)}</strong></div>
            <div>开始 <strong>${display(formatWhen(log.started_at))}</strong></div>
            <div>结束 <strong>${display(formatWhen(log.finished_at))}</strong></div>
            <div>耗时 <strong>${display(formatDurationSeconds(log))}</strong></div>
            <div>核价卡 <strong>${display(log.subject_total)}</strong></div>
            <div>成功 / 部分成功 / 失败 / 跳过
                <strong>${display(log.ok_count)} / ${display(log.partial_count)} / ${display(log.failed_count)} / ${display(log.skipped_approved_count)}</strong>
            </div>
        </div>
        <div class="filters">
            <input id="reportKeyword" type="search" placeholder="短码、零件号、名称、说明">
            <button type="button" data-status="all">全部</button>
            <button type="button" data-status="ok">成功</button>
            <button type="button" data-status="partial">部分成功</button>
            <button type="button" data-status="failed">失败</button>
            <button type="button" data-status="skipped">跳过</button>
            ${filterSelectHtml('reportLevel', [
                ['all', '全部层级'],
                ...levels.map((level) => [String(level), `L${level}`]),
            ])}
            ${filterSelectHtml('reportTreeRoot', [
                ['all', '树根/非树根'],
                ['yes', '仅树根'],
                ['no', '非树根'],
            ])}
            <span class="count">显示 ${filtered.length} / ${cards.length} 张卡</span>
        </div>
        <div class="body">
            ${log.message ? `<p class="summary">${display(log.message)}</p>` : ''}
            ${log.detail_text ? `<pre class="narrative">${display(log.detail_text)}</pre>` : ''}
            <div id="reportTableHost">${renderTable(filtered)}</div>
        </div>
    `;
    bindFilters(root);
    refreshRows(root);
}

function onKeydown(event) {
    if (event.key === 'Escape') {
        const root = document.getElementById('reportRoot');
        if (root) closeFilterSelects(root);
        return;
    }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'e') {
        event.preventDefault();
        exportExcel(true);
    }
}

function tableColgroupHtml() {
    return `
        <colgroup>
            <col class="col-seq">
            <col class="col-short">
            <col class="col-part">
            <col class="col-status">
            <col class="col-money">
            <col class="col-money">
            <col class="col-money">
            <col class="col-money">
            <col class="col-money">
            <col class="col-missing">
            <col class="col-note">
        </colgroup>
    `;
}

function renderTable(cards) {
    if (!cards.length) {
        return `
            <table>
                ${tableColgroupHtml()}
                <thead>${printBannerRowHtml()}</thead>
                <tbody>
                    <tr>
                        <td colspan="11" class="empty" style="padding:24px 0;">没有符合筛选的核价卡。</td>
                    </tr>
                </tbody>
            </table>
        `;
    }
    const rows = cards.map((card) => {
        const statusClass = CARD_STATUS_CLASS[card.status] || '';
        const missing = (card.missing_parts || []).join('；');
        return `
            <tr>
                <td class="seq">${display(card.seq_label)}</td>
                <td class="short-code"><span class="short-code-text">${display(partShortCode(card))}</span>${restoreBadgeHtml(card)}</td>
                <td>
                    <div class="part-number">${display(card.part_number)}</div>
                    <div class="part-name">${display(card.part_name)}</div>
                </td>
                <td class="${statusClass}">${display(STATUS_LABEL[card.status] || card.status)}</td>
                <td class="num">${display(card.material_amount)}</td>
                <td class="num">${display(card.welding_amount)}</td>
                <td class="num">${display(card.should_cost)}</td>
                <td class="num">${display(card.indirect_amount)}</td>
                <td class="num">${display(card.grand_total)}</td>
                <td class="num">${Number(card.missing_leaf_count) > 0 ? display(card.missing_leaf_count) : ''}</td>
                <td>${card.message ? display(card.message) : ''}${missing ? `<div class="missing">${display(missing)}</div>` : ''}</td>
            </tr>
        `;
    }).join('');
    return `
        <table>
            ${tableColgroupHtml()}
            <thead>
                ${printBannerRowHtml()}
                <tr>
                    <th>序号</th>
                    <th>短码</th>
                    <th>零件</th>
                    <th>状态</th>
                    <th style="text-align:right;">材料</th>
                    <th style="text-align:right;">焊接</th>
                    <th style="text-align:right;">应成本</th>
                    <th style="text-align:right;">间接费用</th>
                    <th style="text-align:right;">总费用</th>
                    <th style="text-align:right;">缺价</th>
                    <th>说明</th>
                </tr>
            </thead>
            <tbody>${rows}</tbody>
        </table>
    `;
}

async function boot() {
    const root = document.getElementById('reportRoot');
    const logId = logIdFromUrl();
    if (!Number.isFinite(logId) || logId <= 0) {
        root.innerHTML = '<p class="error">缺少 log_id。</p>';
        return;
    }
    state.logId = logId;
    document.addEventListener('keydown', onKeydown);
    window.addEventListener('beforeprint', paintPrintHead);
    try {
        state.log = await loadLog(logId);
        render(root);
    } catch (error) {
        root.innerHTML = `<p class="error">${display(error.message || '加载失败')}</p>`;
    }
}

boot();
