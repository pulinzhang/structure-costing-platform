/**
 * Steel Price Calc Page
 * 钢价计算 — 过滤条件 + 批量计算 + 历史过程日志
 */

import { steelPriceCalcTemplate, renderCalcHistoryPagination } from './template.js';

const STAMPING_CASCADE_FILTERS_API = '/api/stamping/filters/cascade';
const STEEL_PRICE_CALC_STATS_API = '/api/dashboard/stats/steel-price-calc';
const STEEL_PRICE_CALC_API = '/api/steel-prices/calc';
const STEEL_PRICE_CALC_LOGS_API = '/api/steel-prices/calc/logs';
const CALC_TIMEOUT_MS = 180000;
const HISTORY_PAGE_SIZE = 10;

const STATUS_META = {
    success: { label: '成功', className: 'text-[#66bb6a]' },
    partial: { label: '部分成功', className: 'text-[#ffb74d]' },
    failed: { label: '失败', className: 'text-[#ef5350]' },
};

const calcState = {
    isCalculating: false,
    stats: {
        base_price_count: 0,
        adjustment_rule_count: 0,
        thickness_row_count: 0,
    },
    lastResult: null,
    history: {
        page: 1,
        size: HISTORY_PAGE_SIZE,
        total: 0,
        totalPages: 1,
        items: [],
    },
};

export function init() {
    bindEvents();
    loadStampingFilters();
    loadCalcStats();
    loadCalcHistory();
}

function bindEvents() {
    document.getElementById('calcResetBtn')?.addEventListener('click', () => resetFilters());
    document.getElementById('calcYear')?.addEventListener('change', () => loadCalcStats());
    document.getElementById('calcMonth')?.addEventListener('change', () => loadCalcStats());

    document.getElementById('calcLocation')?.addEventListener('change', () => {
        resetDependentFilters(['calcSupplier', 'calcVehicleModel', 'calcVersion']);
        loadStampingFilters();
        loadCalcStats();
    });
    document.getElementById('calcSupplier')?.addEventListener('change', () => {
        resetDependentFilters(['calcVehicleModel', 'calcVersion']);
        loadStampingFilters();
        loadCalcStats();
    });
    document.getElementById('calcVehicleModel')?.addEventListener('change', () => {
        resetDependentFilters(['calcVersion']);
        loadStampingFilters();
        loadCalcStats();
    });

    document.getElementById('startCalcBtn')?.addEventListener('click', () => startCalculation());
    document.getElementById('calcHistoryRefreshBtn')?.addEventListener('click', () => loadCalcHistory(1));
    document.getElementById('calcHistoryPagination')?.addEventListener('click', event => {
        const btn = event.target.closest('.calc-history-page-btn');
        if (btn && !btn.disabled) {
            const page = parseInt(btn.dataset.page, 10);
            if (page) loadCalcHistory(page);
        }
    });
}

function getSelectedPeriod() {
    const now = new Date();
    let year = parseInt(document.getElementById('calcYear')?.value, 10);
    let month = parseInt(document.getElementById('calcMonth')?.value, 10);
    if (Number.isNaN(year)) year = now.getFullYear();
    if (Number.isNaN(month)) month = now.getMonth() + 1;
    return { year, month };
}

function resetDependentFilters(ids) {
    ids.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
}

function resetFilters() {
    ['calcLocation', 'calcSupplier', 'calcVehicleModel', 'calcVersion'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });

    const now = new Date();
    const yearEl = document.getElementById('calcYear');
    const monthEl = document.getElementById('calcMonth');
    if (yearEl) yearEl.value = String(now.getFullYear());
    if (monthEl) monthEl.value = String(now.getMonth() + 1);

    calcState.lastResult = null;
    loadStampingFilters();
    loadCalcStats();
    loadCalcHistory(1);
}

async function loadStampingFilters() {
    try {
        const params = {
            location: document.getElementById('calcLocation')?.value || '',
            stamping_supplier: document.getElementById('calcSupplier')?.value || '',
            vehicle_model: document.getElementById('calcVehicleModel')?.value || '',
        };
        const response = await HttpClient.get(STAMPING_CASCADE_FILTERS_API, { params });
        const filters = response.data || {};

        fillSelect('calcLocation', filters.locations || []);
        fillSelect('calcSupplier', filters.stamping_suppliers || []);
        fillSelect('calcVehicleModel', filters.vehicle_models || []);
        fillSelect('calcVersion', filters.versions || []);
    } catch (error) {
        console.error('加载冲压筛选选项失败:', error);
    }
}

async function loadCalcStats() {
    const { year, month } = getSelectedPeriod();
    const location = document.getElementById('calcLocation')?.value || '';
    const stampingSupplier = document.getElementById('calcSupplier')?.value || '';
    const vehicleModel = document.getElementById('calcVehicleModel')?.value || '';

    try {
        const params = { year, month };
        if (location) params.location = location;
        if (stampingSupplier) params.stamping_supplier = stampingSupplier;
        if (vehicleModel) params.vehicle_model = vehicleModel;

        const response = await HttpClient.get(STEEL_PRICE_CALC_STATS_API, { params });
        const stats = response.data || {};
        const filters = stats.filters || {};

        renderPeriodFilters(filters, year, month);

        const baseCount = Number(stats.base_price_count) || 0;
        const adjustmentCount = Number(stats.adjustment_rule_count) || 0;
        const thicknessCount = Number(stats.thickness_row_count) || 0;

        renderCalcStats({
            base_price_count: baseCount,
            adjustment_rule_count: adjustmentCount,
            thickness_row_count: thicknessCount,
        });
        validateDataPreparation(location, year, month, baseCount, adjustmentCount, thicknessCount);
    } catch (error) {
        console.error('加载钢价计算统计失败:', error);
        renderCalcStats({
            base_price_count: 0,
            adjustment_rule_count: 0,
            thickness_row_count: 0,
        });
        validateDataPreparation(location, year, month, 0, 0, 0);
        showToast('加载数据依据失败', 'error');
    }
}

async function loadCalcHistory(page = calcState.history.page) {
    const body = document.getElementById('calcHistoryBody');
    if (!body) return;

    const params = {
        page,
        size: calcState.history.size,
    };

    body.innerHTML = `<tr><td colspan="12" class="py-8 text-center text-[#555]">加载中...</td></tr>`;

    try {
        const response = await HttpClient.get(STEEL_PRICE_CALC_LOGS_API, { params });
        const pageData = response.data || {};
        const items = Array.isArray(pageData.items) ? pageData.items : [];
        calcState.history.page = pageData.page || page;
        calcState.history.total = pageData.total || 0;
        calcState.history.totalPages = pageData.total_pages || 1;
        calcState.history.items = items;

        renderHistoryRows(items);

        const totalEl = document.getElementById('calcHistoryTotal');
        if (totalEl) totalEl.textContent = `共 ${calcState.history.total} 条`;

        const pagination = document.getElementById('calcHistoryPagination');
        if (pagination) {
            pagination.innerHTML = renderCalcHistoryPagination(
                calcState.history.page,
                calcState.history.totalPages
            );
        }
    } catch (error) {
        console.error('加载计算历史失败:', error);
        body.innerHTML = `<tr><td colspan="12" class="py-8 text-center text-[#ef5350]">加载失败</td></tr>`;
    }
}

function renderHistoryRows(items) {
    const body = document.getElementById('calcHistoryBody');
    if (!body) return;

    if (!items.length) {
        body.innerHTML = `<tr><td colspan="12" class="py-8 text-center text-[#555]">暂无计算记录</td></tr>`;
        return;
    }

    body.innerHTML = items.map(item => {
        const status = STATUS_META[item.status] || STATUS_META.failed;
        const period = `${item.year}-${String(item.month).padStart(2, '0')}`;
        const filterParts = [];
        if (item.stamping_supplier) filterParts.push(item.stamping_supplier);
        if (item.vehicle_model) filterParts.push(item.vehicle_model);
        const filterText = filterParts.length ? filterParts.join(' / ') : '全部';
        const started = formatDateTime(item.started_at);

        return `
            <tr class="hover:bg-[#ffffff]/[0.02] transition-colors text-[#999]" data-log-id="${esc(item.id)}">
                <td class="py-2 px-2 font-mono text-[#666] whitespace-nowrap">${esc(started)}</td>
                <td class="py-2 px-2 font-mono text-[#ccc] whitespace-nowrap">${esc(period)}</td>
                <td class="py-2 px-2 text-[#ccc] whitespace-nowrap">${esc(item.location || '-')}</td>
                <td class="py-2 px-2 text-[#777] max-w-[140px] truncate" title="${esc(filterText)}">${esc(filterText)}</td>
                <td class="py-2 px-2 text-center text-[9px] ${status.className}">${status.label}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-[#777]">${fmtInt(item.material_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-[#777]">${fmtInt(item.enriched_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums ${Number(item.no_base_count) > 0 ? 'text-[#ffb74d]' : 'text-[#777]'}">${fmtInt(item.no_base_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-[#777]">${fmtInt(item.created_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-[#777]">${fmtInt(item.updated_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums ${Number(item.failed_count) > 0 ? 'text-[#ef5350]' : 'text-[#777]'}">${fmtInt(item.failed_count)}</td>
                <td class="py-2 px-2 text-right whitespace-nowrap">
                    <button type="button"
                            class="calc-view-process-btn text-[9px] text-[#777] hover:text-white mr-2"
                            data-log-id="${esc(item.id)}">过程</button>
                    ${item.status === 'failed' ? '' : `
                    <button type="button"
                            class="calc-view-result-btn text-[9px] text-[#777] hover:text-white mr-2"
                            data-year="${esc(item.year)}"
                            data-month="${esc(item.month)}"
                            data-location="${esc(item.location || '')}">结果</button>
                    `}
                    <button type="button"
                            class="calc-delete-log-btn text-[9px] text-[#777] hover:text-[#ef5350]"
                            data-log-id="${esc(item.id)}">删除</button>
                </td>
            </tr>
        `;
    }).join('');

    body.querySelectorAll('.calc-view-process-btn').forEach(btn => {
        btn.addEventListener('click', () => openProcessDrawer(Number(btn.dataset.logId)));
    });
    body.querySelectorAll('.calc-view-result-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const qs = new URLSearchParams();
            if (btn.dataset.year) qs.set('year', btn.dataset.year);
            if (btn.dataset.month) qs.set('month', btn.dataset.month);
            if (btn.dataset.location) qs.set('location', btn.dataset.location);
            const suffix = qs.toString() ? `?${qs.toString()}` : '';
            window.location.hash = `/steel-price-list${suffix}`;
        });
    });
    body.querySelectorAll('.calc-delete-log-btn').forEach(btn => {
        btn.addEventListener('click', () => deleteCalcLog(Number(btn.dataset.logId)));
    });
}

async function deleteCalcLog(logId) {
    if (!logId) return;
    if (!window.confirm('确定删除这条计算历史？仅删除日志，不影响已落库的钢材价格。')) {
        return;
    }
    try {
        await HttpClient.delete(`${STEEL_PRICE_CALC_LOGS_API}/${logId}`);
        showToast('删除成功', 'success');
        const nextPage =
            calcState.history.items.length === 1 && calcState.history.page > 1
                ? calcState.history.page - 1
                : calcState.history.page;
        loadCalcHistory(nextPage);
    } catch (error) {
        console.error('删除计算历史失败:', error);
    }
}

async function openProcessDrawer(logId) {
    if (!logId) return;
    try {
        const response = await HttpClient.get(`${STEEL_PRICE_CALC_LOGS_API}/${logId}`);
        const log = response.data || {};
        showProcessDrawer(log);
    } catch (error) {
        console.error('加载计算过程失败:', error);
    }
}

function showProcessDrawer(log) {
    closeProcessDrawer();

    const status = STATUS_META[log.status] || STATUS_META.failed;
    const period = `${log.year}-${String(log.month).padStart(2, '0')}`;
    const backdrop = document.createElement('div');
    backdrop.id = 'calcProcessBackdrop';
    backdrop.className = 'fixed inset-0 z-40 bg-black/70 backdrop-blur-sm';

    const drawer = document.createElement('div');
    drawer.id = 'calcProcessDrawer';
    drawer.className =
        'fixed inset-y-0 right-0 z-50 w-[640px] max-w-[95vw] bg-[#1a1a1a] border-l border-[#2a2a2a] flex flex-col';
    drawer.innerHTML = `
        <div class="px-5 py-3.5 flex items-center justify-between shrink-0 bg-[#1f1f1f] border-b border-[#333333]">
            <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] uppercase">
                计算过程 · ${esc(period)} · ${esc(log.location || '-')}
                <span class="ml-2 normal-case ${status.className}">${status.label}</span>
            </h5>
            <button type="button" id="closeCalcProcessDrawer"
                    class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
            </button>
        </div>
        <div class="px-5 py-3 border-b border-[#222] text-[10px] text-[#777] space-y-1 shrink-0">
            <div>批次：<span class="font-mono text-[#999]">${esc(log.calc_batch_id || '-')}</span></div>
            <div>时间：${esc(formatDateTime(log.started_at))} → ${esc(formatDateTime(log.finished_at))}</div>
            <div>汇总：材料 ${fmtInt(log.material_count)} · 命中 ${fmtInt(log.enriched_count)} · 无基价 ${fmtInt(log.no_base_count)} · 新增 ${fmtInt(log.created_count)} · 更新 ${fmtInt(log.updated_count)} · 失败 ${fmtInt(log.failed_count)}</div>
        </div>
        <div class="flex-1 overflow-y-auto overscroll-contain p-5">
            <pre class="text-[11px] leading-5 font-mono text-[#9e9e9e] whitespace-pre-wrap break-words bg-[#111111] border border-[#262626] p-4">${esc(log.detail_text || '（无过程文本）')}</pre>
        </div>
    `;

    document.body.appendChild(backdrop);
    document.body.appendChild(drawer);
    backdrop.addEventListener('click', closeProcessDrawer);
    document.getElementById('closeCalcProcessDrawer')?.addEventListener('click', closeProcessDrawer);
}

function closeProcessDrawer() {
    document.getElementById('calcProcessBackdrop')?.remove();
    document.getElementById('calcProcessDrawer')?.remove();
}

function renderPeriodFilters(filters, year, month) {
    const years = Array.isArray(filters.years) ? filters.years.slice() : [];
    const months = Array.isArray(filters.months) ? filters.months.slice() : [];

    if (!years.includes(year)) years.unshift(year);
    if (!months.includes(month)) months.push(month);
    months.sort((a, b) => a - b);

    fillSelect('calcYear', years, value => `${value} 年`, String(year));
    fillSelect('calcMonth', months, value => `${value} 月`, String(month));
}

function renderCalcStats(stats) {
    calcState.stats = stats;
    setCountHtml('cntBasePrice', stats.base_price_count, '条');
    setCountHtml('cntAdjustment', stats.adjustment_rule_count, '条');
    setCountHtml('cntThicknessRows', stats.thickness_row_count, '行');
}

function setCountHtml(id, count, unit) {
    const el = document.getElementById(id);
    if (!el) return;
    const display = Number.isFinite(count) ? Number(count).toLocaleString('zh-CN') : '-';
    el.innerHTML = `${display} <span class="text-[9px] font-normal text-[#555]">${unit}</span>`;
}

function fillSelect(id, values = [], label = value => value, preferredValue = null) {
    const select = document.getElementById(id);
    if (!select) return;
    const current = preferredValue != null ? preferredValue : select.value;
    select.innerHTML =
        '<option value="">全部</option>' +
        values.map(v => {
            const value = String(v);
            return `<option value="${esc(value)}"${value === String(current) ? ' selected' : ''}>${esc(label(v))}</option>`;
        }).join('');
}

async function startCalculation() {
    if (calcState.isCalculating) return;

    const year = parseInt(document.getElementById('calcYear')?.value, 10);
    const month = parseInt(document.getElementById('calcMonth')?.value, 10);
    const location = document.getElementById('calcLocation')?.value || '';
    const stampingSupplier = document.getElementById('calcSupplier')?.value || '';
    const vehicleModel = document.getElementById('calcVehicleModel')?.value || '';

    if (Number.isNaN(year) || Number.isNaN(month)) {
        showToast('请填写完整的计算年度与月份', 'warning');
        return;
    }
    if (!location) {
        showToast('请选择生产基地', 'warning');
        return;
    }

    const { base_price_count, adjustment_rule_count, thickness_row_count } = calcState.stats;
    if (base_price_count <= 0 || adjustment_rule_count <= 0 || thickness_row_count <= 0) {
        showToast('当前所选条件数据未就绪，无法计算', 'warning');
        return;
    }

    const payload = { year, month, location };
    if (stampingSupplier) payload.stamping_supplier = stampingSupplier;
    if (vehicleModel) payload.vehicle_model = vehicleModel;

    setCalculating(true);
    try {
        const response = await HttpClient.post(STEEL_PRICE_CALC_API, payload, {
            timeout: CALC_TIMEOUT_MS,
        });
        const result = response.data || {};
        calcState.lastResult = result;
        const status = result.status || 'success';
        showToast(
            `计算${STATUS_META[status]?.label || '完成'}：新增 ${fmtInt(result.created_count)}，更新 ${fmtInt(result.updated_count)}，失败 ${fmtInt(result.failed_count)}`,
            status === 'failed' ? 'error' : status === 'partial' ? 'warning' : 'success'
        );
        if (result.log_id) {
            openProcessDrawer(result.log_id);
        }
    } catch (error) {
        console.error('钢价计算失败:', error);
        // 失败时日志仍可能已落库，刷新历史以便查看过程
    } finally {
        setCalculating(false);
        loadCalcStats();
        loadCalcHistory(1);
    }
}

function setCalculating(isCalculating) {
    calcState.isCalculating = isCalculating;
    const startBtn = document.getElementById('startCalcBtn');
    if (!startBtn) return;
    if (isCalculating) {
        startBtn.setAttribute('disabled', 'true');
        startBtn.classList.add('opacity-50', 'pointer-events-none');
        startBtn.textContent = '计算中...';
    } else {
        startBtn.removeAttribute('disabled');
        startBtn.classList.remove('opacity-50', 'pointer-events-none');
        startBtn.textContent = '开始计算';
        validateDataPreparation(
            document.getElementById('calcLocation')?.value || '',
            parseInt(document.getElementById('calcYear')?.value, 10),
            parseInt(document.getElementById('calcMonth')?.value, 10),
            calcState.stats.base_price_count,
            calcState.stats.adjustment_rule_count,
            calcState.stats.thickness_row_count
        );
    }
}

function validateDataPreparation(location, year, month, cntBasePrice, cntAdjustment, cntThickness) {
    const startBtn = document.getElementById('startCalcBtn');
    const errorBanner = document.getElementById('dataReadyErrorBanner');
    if (!startBtn || calcState.isCalculating) return;

    const isLocationSelected = Boolean(location);
    const isPeriodSelected = Boolean(year && month);
    const isDataValid = cntBasePrice > 0 && cntAdjustment > 0 && cntThickness > 0;
    const isReady = isLocationSelected && isPeriodSelected && isDataValid;

    startBtn.disabled = !isReady;
    if (isReady) {
        errorBanner?.classList.add('hidden');
    } else {
        errorBanner?.classList.remove('hidden');
    }
}

function fmtInt(value) {
    const n = Number(value);
    return Number.isFinite(n) ? n.toLocaleString('zh-CN') : '0';
}

function formatDateTime(value) {
    if (!value) return '-';
    const text = String(value).replace('T', ' ');
    return text.length >= 16 ? text.slice(0, 16) : text;
}

export const pageConfig = {
    render: steelPriceCalcTemplate,
    init: () => init(),
};
