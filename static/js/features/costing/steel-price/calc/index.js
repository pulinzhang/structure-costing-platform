/**
 * Steel Price Calc Page
 * 钢价计算 —过滤条件 + 异步后台计算 + 进度轮询 + 历史过程日志
 */

import { steelPriceCalcTemplate } from './template.js?v=18';
import { DRAWER_CLOSE, DRAWER_SHELL, DRAWER_BACKDROP } from '../../../../ui/classes.js?v=13';

import {
    DEFAULT_PAGE_SIZE,
    bindPagination,
    paintPagination,
} from '../../../../ui/page-size.js?v=6';
import {
    formatDurationSeconds,
    formatTimingLine,
} from '../../../../domain/duration.js?v=3';

const STEEL_PRICE_CALC_STATS_API = '/api/dashboard/stats/steel-price-calc';
const STEEL_PRICE_CALC_API = '/api/costing/steel-price/calc';
const STEEL_PRICE_CALC_TASK_API = '/api/costing/steel-price/calc/tasks';
const STEEL_PRICE_CALC_LOGS_API = '/api/costing/steel-price/calc/logs';
const POLL_INTERVAL_MS = 1500;
const DUPLICATE_PERIOD_CALC_MESSAGE = '当前期别正在计算中，请勿重复提交。'

const STATUS_META = {
    processing: { label: '计算中', className: 'text-ink-muted' },
    success: { label: '成功', className: 'text-ok' },
    partial: { label: '部分成功', className: 'text-warn' },
    failed: { label: '失败', className: 'text-danger' },
};

const calcState = {
    isCalculating: false,
    activeTaskId: null,
    pollTimer: null,
    pollInFlight: false,
    stats: {
        base_price_count: 0,
        adjustment_rule_count: 0,
        thickness_row_count: 0,
    },
    lastResult: null,
    history: {
        page: 1,
        size: DEFAULT_PAGE_SIZE,
        total: 0,
        totalPages: 1,
        items: [],
    },
};

export function init() {
    stopPolling();
    bindEvents();
    bindPagination({
        selectId: 'steelCalcHistoryPageSize',
        buttonsId: 'calcHistoryPagination',
        getSize: () => calcState.history.size,
        setSize: (size) => {
            calcState.history.size = size;
        },
        onPage: (page) => loadCalcHistory(page),
    });
    applyPermissionUi();
    loadCalcStats();
    loadCalcHistory();

    if (calcState.isCalculating && calcState.activeTaskId) {
        setCalculating(true);
        showProgress(0, '正在恢复任务进度...');
        startPolling(calcState.activeTaskId);
    } else {
        hideProgress();
    }
}

export function destroy() {
    stopPolling();
}

function applyPermissionUi() {
    const canRun = typeof can === 'function' ? can('op:steel-price-calc:run') : true;
    calcState.canRun = canRun;
    calcState.canDelete = typeof can === 'function' ? can('op:steel-price-calc:delete') : true;
    if (!canRun) {
        document.getElementById('startCalcBtn')?.classList.add('hidden');
    }
    document.getElementById('calcHistoryDeleteAllBtn')?.classList.toggle('hidden', !calcState.canDelete);
}

function bindEvents() {
    document.getElementById('calcResetBtn')?.addEventListener('click', () => resetFilters());
    document.getElementById('calcYear')?.addEventListener('change', () => loadCalcStats());
    document.getElementById('calcMonth')?.addEventListener('change', () => loadCalcStats());
    document.getElementById('calcLocation')?.addEventListener('change', () => loadCalcStats());
    document.getElementById('calcVehicle')?.addEventListener('change', () => loadCalcStats());

    document.getElementById('startCalcBtn')?.addEventListener('click', () => startCalculation());
    document.getElementById('calcHistoryRefreshBtn')?.addEventListener('click', () => loadCalcHistory(1));
    document.getElementById('calcHistoryDeleteAllBtn')?.addEventListener('click', () => deleteAllCalcLogs());
}

function getSelectedPeriod() {
    const now = new Date();
    let year = parseInt(document.getElementById('calcYear')?.value, 10);
    let month = parseInt(document.getElementById('calcMonth')?.value, 10);
    if (Number.isNaN(year)) year = now.getFullYear();
    if (Number.isNaN(month)) month = now.getMonth() + 1;
    return { year, month };
}

function resetFilters() {
    if (calcState.isCalculating) {
        showToast('计算进行中，请稍候再重置', 'warning');
        return;
    }

    const locationEl = document.getElementById('calcLocation');
    const vehicleEl = document.getElementById('calcVehicle');
    if (locationEl) locationEl.value = '';
    if (vehicleEl) vehicleEl.value = '';

    const now = new Date();
    const yearEl = document.getElementById('calcYear');
    const monthEl = document.getElementById('calcMonth');
    if (yearEl) yearEl.value = String(now.getFullYear());
    if (monthEl) monthEl.value = String(now.getMonth() + 1);

    calcState.lastResult = null;
    hideProgress();
    loadCalcStats();
    loadCalcHistory(1);
}

async function loadCalcStats() {
    const { year, month } = getSelectedPeriod();
    const location = document.getElementById('calcLocation')?.value || '';
    const vehicleModel = document.getElementById('calcVehicle')?.value || '';

    try {
        const params = { year, month };
        if (location) params.location = location;
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

    body.innerHTML = `<tr><td colspan="14" class="py-8 text-center text-ink-faint">加载中..</td></tr>`;

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
        if (totalEl) totalEl.textContent = `全${calcState.history.total} 条`;

        paintPagination('calcHistoryPagination', 
                calcState.history.page,
                calcState.history.totalPages
            );
    } catch (error) {
        console.error('加载计算历史失败:', error);
        body.innerHTML = `<tr><td colspan="14" class="py-8 text-center text-danger">加载失败</td></tr>`;
    }
}

function renderHistoryRows(items) {
    const body = document.getElementById('calcHistoryBody');
    if (!body) return;

    if (!items.length) {
        body.innerHTML = `<tr><td colspan="14" class="py-8 text-center text-ink-faint">暂无计算记录</td></tr>`;
        return;
    }

    body.innerHTML = items.map(item => {
        const status = STATUS_META[item.status] || STATUS_META.failed;
        const period = fmtPeriod(item.year, item.month);
        const createdBy = item.created_by || item.operator_name || '-';
        const isProcessing = item.status === 'processing';

        return `
            <tr class="hover:bg-ink/[0.02] transition-colors text-ink-muted" data-log-id="${esc(item.id)}">
                <td class="py-2 px-2 font-mono text-ink-dim whitespace-nowrap">${esc(formatDateTime(item.started_at))}</td>
                <td class="py-2 px-2 font-mono text-ink-dim whitespace-nowrap">${esc(formatDateTime(item.finished_at))}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-ink-dim whitespace-nowrap">${esc(formatDurationSeconds(item))}</td>
                <td class="py-2 px-2 text-ink-muted whitespace-nowrap">${esc(createdBy)}</td>
                <td class="py-2 px-2 font-mono text-ink-muted whitespace-nowrap">${esc(period)}</td>
                <td class="py-2 px-2 text-ink-muted whitespace-nowrap">${esc(item.location || '-')}</td>
                <td class="py-2 px-2 text-center text-[9px] ${status.className}">${status.label}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-ink-dim">${fmtInt(item.material_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-ink-dim">${fmtInt(item.enriched_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums ${Number(item.no_base_count) > 0 ? 'text-warn' : 'text-ink-dim'}">${fmtInt(item.no_base_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-ink-dim">${fmtInt(item.created_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-ink-dim">${fmtInt(item.updated_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums ${Number(item.failed_count) > 0 ? 'text-danger' : 'text-ink-dim'}">${fmtInt(item.failed_count)}</td>
                <td class="py-2 px-2 text-right whitespace-nowrap">
                    ${isProcessing ? `
                    <span class="text-[9px] text-ink-faint mr-2">进行中</span>
                    ` : `
                    <button type="button"
                            class="calc-view-process-btn text-[9px] text-ink-dim hover:text-ink mr-2"
                            data-log-id="${esc(item.id)}">过程</button>
                    ${item.status === 'failed' ? '' : `
                    <button type="button"
                            class="calc-view-result-btn text-[9px] text-ink-dim hover:text-ink mr-2"
                            data-year="${esc(item.year)}"
                            data-month="${esc(item.month)}"
                            data-location="${esc(item.location || '')}">结果</button>
                    `}
                    `}
                    ${calcState.canDelete !== false ? `
                    <button type="button"
                            class="calc-delete-log-btn text-[9px] text-ink-dim hover:text-danger"
                            data-log-id="${esc(item.id)}"
                            title="含计算中：删除可释放锁">删除</button>` : ''}
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

async function deleteAllCalcLogs() {
    if (calcState.canDelete === false) {
        showToast('无删除权限', 'warning');
        return;
    }
    if (!window.confirm('确定删除全部计算历史？仅删除日志，不影响已落库的钢材价格。计算中的记录删除后将释放锁。')) {
        return;
    }
    try {
        const res = await HttpClient.delete(STEEL_PRICE_CALC_LOGS_API);
        const count = res.data?.deleted_count ?? 0;
        showToast(`已删除 ${count} 条`, 'success');
        loadCalcHistory(1);
    } catch (error) {
        console.error('清空计算历史失败:', error);
    }
}

async function deleteCalcLog(logId) {
    if (!logId) return;
    if (calcState.canDelete === false) {
        showToast('无删除权限', 'warning');
        return;
    }
    if (!window.confirm('确定删除这条计算历史？计算中的记录删除后将释放锁；仅删除日志，不影响已落库的钢材价格。')) {
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
        const period = fmtPeriod(log.year, log.month);
    const backdrop = document.createElement('div');
    backdrop.id = 'calcProcessBackdrop';
    backdrop.className = DRAWER_BACKDROP;

    const drawer = document.createElement('div');
    drawer.id = 'calcProcessDrawer';
    drawer.className =
        `${DRAWER_SHELL} w-[640px]`;
    drawer.innerHTML = `
        <div class="px-5 py-3.5 flex items-center justify-between shrink-0 bg-app-surface border-b border-line">
            <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted uppercase">
                计算过程 · ${esc(period)} · ${esc(log.location || '-')}
                <span class="ml-2 normal-case ${status.className}">${status.label}</span>
            </h5>
            <div class="flex items-center gap-0.5 shrink-0">
                ${window.copyProcessReportButtonHtml()}
                <button type="button" id="closeCalcProcessDrawer"
                    class="${DRAWER_CLOSE}">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
        </div>
        <div class="px-5 py-3 border-b border-line-subtle text-[10px] text-ink-dim space-y-1 shrink-0">
            <div>批次<span class="font-mono text-ink-muted">${esc(log.calc_batch_id || '-')}</span></div>
            <div>${esc(formatTimingLine(log, formatDateTime) || '-')}</div>
            <div>汇总：材料 ${fmtInt(log.material_count)} · 命中 ${fmtInt(log.enriched_count)} · 无基价${fmtInt(log.no_base_count)} · 新增 ${fmtInt(log.created_count)} · 更新 ${fmtInt(log.updated_count)} · 失败 ${fmtInt(log.failed_count)}</div>
        </div>
        <div class="flex-1 overflow-y-auto overscroll-contain p-5">
            <pre class="text-[11px] leading-5 font-mono text-ink-muted whitespace-pre-wrap break-words bg-app-main border border-app-elevated p-4">${esc(log.detail_text || '（无过程文本）')}</pre>
        </div>
    `;

    document.body.appendChild(backdrop);
    document.body.appendChild(drawer);
    window.bindProcessReportCopy(drawer);
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

    fillSelect('calcYear', years, fmtYear, String(year));
    fillSelect('calcMonth', months, fmtMonth, String(month));
    fillSelect('calcLocation', Array.isArray(filters.locations) ? filters.locations : []);
    fillSelect('calcVehicle', Array.isArray(filters.vehicle_models) ? filters.vehicle_models : []);
}

function renderCalcStats(stats) {
    calcState.stats = stats;
    setCountHtml('cntBasePrice', stats.base_price_count, '条');
    setCountHtml('cntAdjustment', stats.adjustment_rule_count, '条');
    setCountHtml('cntThicknessRows', stats.thickness_row_count, '表');
}

function setCountHtml(id, count, unit) {
    const el = document.getElementById(id);
    if (!el) return;
    const display = Number.isFinite(count) ? Number(count).toLocaleString('zh-CN') : '-';
    el.innerHTML = `${display} <span class="text-[9px] font-normal text-ink-faint">${unit}</span>`;
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

async function isPeriodProcessing(year, month, location) {
    try {
        const response = await HttpClient.get(STEEL_PRICE_CALC_LOGS_API, {
            params: { year, month, location, page: 1, size: 20 },
        });
        const items = response.data?.items || [];
        return items.some(item => item.status === 'processing');
    } catch (error) {
        console.error('检查期别计算锁失败:', error);
        return false;
    }
}

async function startCalculation() {
    if (calcState.canRun === false) {
        showToast('无计算权限', 'warning');
        return;
    }
    if (calcState.isCalculating) return;

    const year = parseInt(document.getElementById('calcYear')?.value, 10);
    const month = parseInt(document.getElementById('calcMonth')?.value, 10);
    const location = document.getElementById('calcLocation')?.value || '';

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

    if (await isPeriodProcessing(year, month, location)) {
        showToast(DUPLICATE_PERIOD_CALC_MESSAGE, 'warning');
        loadCalcHistory(1);
        return;
    }

    const payload = { year, month, location };

    setCalculating(true);
    showProgress(0, '已提交计算队列');

    try {
        const response = await HttpClient.post(STEEL_PRICE_CALC_API, payload);
        const taskId = response.data?.task_id;
        if (!taskId) {
            throw new Error('未返回任加ID');
        }
        loadCalcHistory(1);
        startPolling(taskId);
    } catch (error) {
        console.error('提交钢价计算失败:', error);
        stopPolling();
        hideProgress();
        calcState.activeTaskId = null;
        setCalculating(false);
        loadCalcHistory(1);
    }
}

function showProgress(progress = 0, msg = '已提交计算队列') {
    const panel = document.getElementById('calcProgressPanel');
    if (panel) panel.classList.remove('hidden');
    updateProgress(progress, msg);
}

function hideProgress() {
    const panel = document.getElementById('calcProgressPanel');
    if (panel) panel.classList.add('hidden');
    updateProgress(0, '已提交计算队列');
}

function updateProgress(progress, msg, status) {
    const pct = Math.max(0, Math.min(100, Number(progress) || 0));
    const bar = document.getElementById('calcProgressBar');
    const percentEl = document.getElementById('calcProgressPercent');
    const msgEl = document.getElementById('calcProgressMsg');
    const titleEl = document.getElementById('calcProgressTitle');
    const spinner = document.getElementById('calcProgressSpinner');

    if (bar) bar.style.width = `${pct}%`;
    if (percentEl) percentEl.textContent = `${pct}%`;
    if (msgEl) msgEl.textContent = msg || '';

    if (spinner) {
        if (status === 'completed' || status === 'failed') {
            spinner.classList.add('hidden');
        } else {
            spinner.classList.remove('hidden');
        }
    }

    if (titleEl) {
        if (status === 'completed') {
            titleEl.textContent = '计算完成';
            titleEl.className = 'text-xs font-medium text-ok truncate mb-0';
        } else if (status === 'failed') {
            titleEl.textContent = '计算失败';
            titleEl.className = 'text-xs font-medium text-danger truncate mb-0';
        } else {
            titleEl.textContent = '正在计算钢价...';
            titleEl.className = 'text-xs font-medium text-ink truncate mb-0';
        }
    }

    if (status === 'completed' && bar) {
        bar.className = 'h-full bg-ok transition-all duration-300';
        if (percentEl) percentEl.className = 'text-xs font-mono tabular-nums text-ok shrink-0';
    } else if (status === 'failed' && bar) {
        bar.className = 'h-full bg-danger transition-all duration-300';
        if (percentEl) percentEl.className = 'text-xs font-mono tabular-nums text-danger shrink-0';
    } else if (bar) {
        bar.className = 'h-full bg-brand hud-brand-glow transition-all duration-300';
        if (percentEl) percentEl.className = 'text-xs font-mono tabular-nums text-brand shrink-0';
    }
}

function stopPolling() {
    if (calcState.pollTimer) {
        clearInterval(calcState.pollTimer);
        calcState.pollTimer = null;
    }
    calcState.pollInFlight = false;
}

async function fetchTaskProgress(taskId) {
    const response = await HttpClient.get(
        `${STEEL_PRICE_CALC_TASK_API}/${encodeURIComponent(taskId)}`,
    );
    return response.data;
}

function startPolling(taskId) {
    stopPolling();
    calcState.activeTaskId = taskId;

    const tick = async () => {
        if (calcState.pollInFlight) return;
        calcState.pollInFlight = true;
        try {
            const data = await fetchTaskProgress(taskId);
            const status = data?.status || 'running';
            const progress = data?.progress ?? 0;
            const msg = data?.msg || '';

            updateProgress(progress, msg, status);

            if (status === 'completed') {
                stopPolling();
                const result = data?.result || {};
                calcState.lastResult = result;
                const bizStatus = result.status || 'success';
                showToast(
                    `计算${STATUS_META[bizStatus]?.label || '完成'}：新增${fmtInt(result.created_count)}，更新${fmtInt(result.updated_count)}，失败${fmtInt(result.failed_count)}`,
                    bizStatus === 'failed' ? 'error' : bizStatus === 'partial' ? 'warning' : 'success'
                );
                calcState.activeTaskId = null;
                setCalculating(false);
                loadCalcStats();
                loadCalcHistory(1);
                if (result.log_id) {
                    openProcessDrawer(result.log_id);
                }
                setTimeout(() => {
                    if (!calcState.isCalculating) hideProgress();
                }, 1800);
                return;
            }

            if (status === 'failed') {
                stopPolling();
                const result = data?.result || null;
                calcState.lastResult = result;
                showToast(msg || '计算失败', 'error');
                calcState.activeTaskId = null;
                setCalculating(false);
                loadCalcStats();
                loadCalcHistory(1);
                if (result?.log_id) {
                    openProcessDrawer(result.log_id);
                }
                return;
            }
        } catch (error) {
            stopPolling();
            showToast(error.message || '查询进度失败', 'error');
            calcState.activeTaskId = null;
            setCalculating(false);
            loadCalcHistory(1);
        } finally {
            calcState.pollInFlight = false;
        }
    };

    tick();
    calcState.pollTimer = setInterval(tick, POLL_INTERVAL_MS);
}

function setCalculating(isCalculating) {
    calcState.isCalculating = isCalculating;
    const startBtn = document.getElementById('startCalcBtn');
    const filterIds = ['calcYear', 'calcMonth', 'calcLocation', 'calcVehicle', 'calcResetBtn'];

    filterIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.disabled = isCalculating;
    });

    if (!startBtn) return;
    if (isCalculating) {
        startBtn.setAttribute('disabled', 'true');
        startBtn.classList.add('opacity-50', 'pointer-events-none');
        startBtn.textContent = '计算中..';
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
    destroy: () => destroy(),
};
