/**
 * 冲压零件价格计算页
 */

import { DRAWER_CLOSE, DRAWER_SHELL, DRAWER_BACKDROP } from '../../../../ui/classes.js?v=13';
import { opsIconButtonHtml } from '../../../../ui/hud-table.js?v=2';
import {
    partCostCalcTemplate,
} from './template.js?v=20';
import {
    DEFAULT_PAGE_SIZE,
    bindPagination,
    paintPagination,
} from '../../../../ui/page-size.js?v=6';
import {
    formatDurationSeconds,
    formatTimingLine,
} from '../../../../domain/duration.js?v=3';

const CASCADE_API = '/api/stamping/filters/cascade';
const API_BASE = '/api/costing/stamping-part-cost';
const CALC_API = `${API_BASE}/calc`;
const CALC_READY_API = `${API_BASE}/calc/ready`;
const CALC_TASK_API = `${API_BASE}/calc/tasks`;
const CALC_LOGS_API = `${API_BASE}/calc/logs`;
const POLL_INTERVAL_MS = 1500;
const DUPLICATE_SCOPE_CALC_MESSAGE = '当前年度/月份/基地/项目正在计算中，请勿重复提交。';
const SCOPE_REQUIRED_MESSAGE = '须选定年度、月份、基地、项目。';
const READY_FALLBACK =
    '提示：须选定年度、月份、基地、项目。计算覆盖该车各冲压工厂。并确保钢材联动价、废料月度价、加工费与匹配零件均已就绪。模具费、检具费缺档按 0 计入。';

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
    canRun: true,
    canDelete: true,
    lastResult: null,
    ready: {
        part_count: 0,
        steel_price_count: 0,
        scrap_price_count: 0,
        process_fee_count: 0,
        die_fee_count: 0,
        gauge_fee_count: 0,
        can_calculate: false,
        message: null,
    },
    history: {
        page: 1,
        size: DEFAULT_PAGE_SIZE,
        total: 0,
        totalPages: 1,
        items: [],
    },
};

function init() {
    stopPolling();
    bindEvents();
    bindPagination({
        selectId: 'partCostCalcHistoryPageSize',
        buttonsId: 'calcHistoryPagination',
        getSize: () => calcState.history.size,
        setSize: (size) => {
            calcState.history.size = size;
        },
        onPage: (page) => loadCalcHistory(page),
    });
    applyPermissionUi();
    fillMonthOptions();
    validateDataPreparation();
    loadYearOptions().then(() => {
        const now = new Date();
        const monthEl = document.getElementById('calcMonth');
        if (monthEl && !monthEl.value) monthEl.value = String(now.getMonth() + 1);
        loadCascadeFilters();
        loadCalcReady();
        loadCalcHistory(1);
    });
    hideProgress();
}

function destroy() {
    stopPolling();
    closeProcessDrawer();
}

function applyPermissionUi() {
    const canRun = typeof can === 'function' ? can('op:stamping-part-cost-calc:run') : true;
    calcState.canRun = canRun;
    calcState.canDelete = typeof can === 'function' ? can('op:stamping-part-cost-calc:delete') : true;
    if (!canRun) {
        document.getElementById('startCalcBtn')?.classList.add('hidden');
    }
    document.getElementById('calcHistoryDeleteAllBtn')?.classList.toggle('hidden', !calcState.canDelete);
}

function fillMonthOptions() {
    const select = document.getElementById('calcMonth');
    if (!select) return;
    const current = select.value;
    select.innerHTML =
        '<option value="">请选择</option>' +
        Array.from({ length: 12 }, (_, i) => {
            const m = i + 1;
            return `<option value="${m}"${String(current) === String(m) ? ' selected' : ''}>${esc(fmtMonth(m))}</option>`;
        }).join('');
}

function bindEvents() {
    document.getElementById('calcResetBtn')?.addEventListener('click', () => resetFilters());
    document.getElementById('calcYear')?.addEventListener('change', () => {
        loadCascadeFilters();
        loadCalcReady();
    });
    document.getElementById('calcMonth')?.addEventListener('change', () => {
        loadCascadeFilters();
        loadCalcReady();
    });

    document.getElementById('calcLocation')?.addEventListener('change', () => {
        resetDependentFilters(['calcVehicleModel']);
        loadCascadeFilters();
        loadCalcReady();
    });
    document.getElementById('calcVehicleModel')?.addEventListener('change', () => {
        loadCascadeFilters();
        loadCalcReady();
    });

    document.getElementById('startCalcBtn')?.addEventListener('click', () => startCalculation());
    document.getElementById('calcHistoryRefreshBtn')?.addEventListener('click', () => loadCalcHistory(1));
    document.getElementById('calcHistoryDeleteAllBtn')?.addEventListener('click', () => deleteAllCalcLogs());
}

function resetDependentFilters(ids) {
    ids.forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
}

function fillSelect(id, values = [], preferredValue = null, formatLabel = null) {
    const select = document.getElementById(id);
    if (!select) return;
    const current = preferredValue != null ? preferredValue : select.value;
    const emptyLabel = select.querySelector('option[value=""]')?.textContent || '全部';
    select.innerHTML =
        `<option value="">${emptyLabel}</option>` +
        values.map((value) => {
            const text = String(value);
            const label = formatLabel ? formatLabel(value) : text;
            return `<option value="${esc(text)}"${text === String(current) ? ' selected' : ''}>${esc(String(label))}</option>`;
        }).join('');
}

async function loadYearOptions() {
    try {
        const res = await HttpClient.get(`${API_BASE}/filters/years`);
        const years = Array.isArray(res.data) ? res.data.slice() : [];
        const currentYear = new Date().getFullYear();
        if (!years.includes(currentYear)) years.unshift(currentYear);
        fillSelect('calcYear', years, String(currentYear), fmtYear);
    } catch (error) {
        showToast(error.message || '加载年度失败', 'error');
    }
}

async function loadCascadeFilters() {
    try {
        const params = {
            location: document.getElementById('calcLocation')?.value || '',
            vehicle_model: document.getElementById('calcVehicleModel')?.value || '',
        };
        const year = parseInt(document.getElementById('calcYear')?.value, 10);
        if (Number.isFinite(year)) params.year = year;
        const month = parseInt(document.getElementById('calcMonth')?.value, 10);
        if (Number.isFinite(month)) params.month = month;
        const res = await HttpClient.get(CASCADE_API, { params });
        const filters = res.data || {};
        fillSelect('calcLocation', filters.locations || []);
        fillSelect('calcVehicleModel', filters.vehicle_models || []);
    } catch (error) {
        console.error('加载冲压筛选选项失败:', error);
    }
}

function resetFilters() {
    if (calcState.isCalculating) {
        showToast('计算进行中，请稍候再重置', 'warning');
        return;
    }
    ['calcLocation', 'calcVehicleModel'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    const now = new Date();
    const yearEl = document.getElementById('calcYear');
    if (yearEl) yearEl.value = String(now.getFullYear());
    const monthEl = document.getElementById('calcMonth');
    if (monthEl) monthEl.value = String(now.getMonth() + 1);
    calcState.lastResult = null;
    hideProgress();
    loadYearOptions().then(() => {
        loadCascadeFilters();
        loadCalcReady();
        loadCalcHistory(1);
    });
}

async function loadCalcReady() {
    const year = parseInt(document.getElementById('calcYear')?.value, 10);
    const month = parseInt(document.getElementById('calcMonth')?.value, 10);
    const location = document.getElementById('calcLocation')?.value || '';
    const vehicleModel = document.getElementById('calcVehicleModel')?.value || '';

    if (!year || Number.isNaN(year)) {
        calcState.ready = {
            part_count: 0,
            steel_price_count: 0,
            scrap_price_count: 0,
            process_fee_count: 0,
            die_fee_count: 0,
            gauge_fee_count: 0,
            can_calculate: false,
            message: null,
        };
        setReadyCounts(calcState.ready);
        validateDataPreparation();
        return;
    }

    try {
        const params = { year };
        if (month) params.month = month;
        if (location) params.location = location;
        if (vehicleModel) params.vehicle_model = vehicleModel;

        const res = await HttpClient.get(CALC_READY_API, { params });
        const data = res.data || {};
        calcState.ready = {
            part_count: Number(data.part_count) || 0,
            steel_price_count: Number(data.steel_price_count) || 0,
            scrap_price_count: Number(data.scrap_price_count) || 0,
            process_fee_count: Number(data.process_fee_count) || 0,
            die_fee_count: Number(data.die_fee_count) || 0,
            gauge_fee_count: Number(data.gauge_fee_count) || 0,
            can_calculate: Boolean(data.can_calculate),
            message: data.message || null,
        };
        setReadyCounts(calcState.ready);
        validateDataPreparation();
    } catch (error) {
        console.error('加载计算就绪统计失败:', error);
        calcState.ready = {
            part_count: 0,
            steel_price_count: 0,
            scrap_price_count: 0,
            process_fee_count: 0,
            die_fee_count: 0,
            gauge_fee_count: 0,
            can_calculate: false,
            message: null,
        };
        setReadyCounts(calcState.ready);
        validateDataPreparation();
        showToast('加载数据依据失败', 'error');
    }
}

function validateDataPreparation() {
    const startBtn = document.getElementById('startCalcBtn');
    const errorBanner = document.getElementById('dataReadyErrorBanner');
    if (!startBtn || calcState.isCalculating) return;

    const year = parseInt(document.getElementById('calcYear')?.value, 10);
    const month = parseInt(document.getElementById('calcMonth')?.value, 10);
    const location = document.getElementById('calcLocation')?.value || '';
    const vehicleModel = document.getElementById('calcVehicleModel')?.value || '';
    const isScopeSelected = Boolean(year && month && location && vehicleModel);
    const isReady = isScopeSelected && calcState.ready.can_calculate;

    startBtn.disabled = !isReady;
    if (isReady) {
        errorBanner?.classList.add('hidden');
    } else if (errorBanner) {
        errorBanner.textContent = calcState.ready.message
            ? `提示：${calcState.ready.message}`
            : READY_FALLBACK;
        errorBanner.classList.remove('hidden');
    }
}

function setReadyCounts(ready) {
    setCountHtml('cntParts', ready.part_count, '件');
    setCountHtml('cntSteel', ready.steel_price_count, '条');
    setCountHtml('cntScrap', ready.scrap_price_count, '条');
    setCountHtml('cntFee', ready.process_fee_count, '条');
    setCountHtml('cntDieFee', ready.die_fee_count, '条');
    setCountHtml('cntGaugeFee', ready.gauge_fee_count, '条');
}

function setCountHtml(id, count, unit) {
    const el = document.getElementById(id);
    if (!el) return;
    const display = Number.isFinite(count) ? Number(count).toLocaleString('zh-CN') : '-';
    el.innerHTML = `${display} <span class="text-[9px] font-normal text-ink-faint">${unit}</span>`;
}

async function loadCalcHistory(page = calcState.history.page) {
    const body = document.getElementById('calcHistoryBody');
    if (!body) return;
    body.innerHTML = `<tr><td colspan="14" class="py-8 text-center text-ink-faint">加载中..</td></tr>`;
    try {
        const res = await HttpClient.get(CALC_LOGS_API, {
            params: { page, size: calcState.history.size },
        });
        const pageData = res.data || {};
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
                calcState.history.totalPages,
            );
    } catch (error) {
        console.error('加载计算历史失败:', error);
        body.innerHTML = `<tr><td colspan="14" class="py-8 text-center text-danger">加载失败</td></tr>`;
    }
}

function formatDateTime(value) {
    if (!value) return '-';
    const text = String(value).replace('T', ' ');
    return text.length >= 16 ? text.slice(0, 16) : text;
}

function fmtInt(value) {
    const n = Number(value);
    return Number.isFinite(n) ? n.toLocaleString('zh-CN') : '0';
}

function renderHistoryRows(items) {
    const body = document.getElementById('calcHistoryBody');
    if (!body) return;
    if (!items.length) {
        body.innerHTML = `<tr><td colspan="14" class="py-8 text-center text-ink-faint">暂无计算记录</td></tr>`;
        return;
    }

    body.innerHTML = items.map((item) => {
        const status = STATUS_META[item.status] || STATUS_META.failed;
        const filterParts = [];
        if (item.vehicle_model) filterParts.push(item.vehicle_model);
        if (item.version) filterParts.push(item.version);
        const filterText = filterParts.length ? filterParts.join(' / ') : '全部';
        const ym = fmtPeriod(item.year, item.month) || '-';
        const isProcessing = item.status === 'processing';
        const processBtn = isProcessing ? '' : opsIconButtonHtml({
            extraClass: 'calc-view-process-btn',
            title: '过程',
            icon: window.svgIcon('file-earmark-text', 'w-3.5 h-3.5'),
            attrs: `data-log-id="${esc(item.id)}"`,
        });
        const resultBtn = isProcessing || item.status === 'failed' ? '' : opsIconButtonHtml({
            extraClass: 'calc-view-result-btn',
            title: '结果',
            icon: window.svgIcon('external-link', 'w-3.5 h-3.5'),
            attrs: `data-year="${esc(item.year)}" data-month="${esc(item.month || '')}" data-location="${esc(item.location || '')}" data-vehicle="${esc(item.vehicle_model || '')}"`,
        });
        const deleteBtn = calcState.canDelete !== false ? opsIconButtonHtml({
            extraClass: 'calc-delete-log-btn',
            danger: true,
            title: '有正在计算的：删掉后就可以重新算',
            icon: window.svgIcon('trash', 'w-3.5 h-3.5'),
            attrs: `data-log-id="${esc(item.id)}"`,
        }) : '';
        const processingMark = isProcessing
            ? '<span class="text-[9px] text-ink-faint mr-1">进行中</span>'
            : '';
        return `
            <tr class="group hover:bg-ink/[0.02] transition-colors text-ink-muted" data-log-id="${esc(item.id)}">
                <td class="py-2 px-2 font-mono text-ink-dim whitespace-nowrap">${esc(formatDateTime(item.started_at))}</td>
                <td class="py-2 px-2 font-mono text-ink-dim whitespace-nowrap">${esc(formatDateTime(item.finished_at))}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-ink-dim whitespace-nowrap">${esc(formatDurationSeconds(item))}</td>
                <td class="py-2 px-2 text-ink-muted whitespace-nowrap">${esc(item.created_by || item.operator_name || '-')}</td>
                <td class="py-2 px-2 font-mono text-ink-muted whitespace-nowrap">${esc(ym)}</td>
                <td class="py-2 px-2 text-ink-muted whitespace-nowrap">${esc(item.location || '-')}</td>
                <td class="py-2 px-2 text-ink-muted whitespace-nowrap">${esc(item.stamping_supplier || '-')}</td>
                <td class="py-2 px-2 text-ink-dim max-w-[140px] truncate" title="${esc(filterText)}">${esc(filterText)}</td>
                <td class="py-2 px-2 text-center text-[9px] ${status.className}">${status.label}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-ink-dim">${fmtInt(item.total_parts)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-ink-dim">${fmtInt(item.success_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums ${Number(item.failed_count) > 0 ? 'text-danger' : 'text-ink-dim'}">${fmtInt(item.failed_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-ink-dim">${fmtInt(item.skipped_approved_count)}</td>
                <td class="py-2 px-1 text-right whitespace-nowrap">
                    <div class="inline-flex items-center justify-end">${processingMark}${processBtn}${resultBtn}${deleteBtn}</div>
                </td>
            </tr>
        `;
    }).join('');

    body.querySelectorAll('.calc-view-process-btn').forEach((btn) => {
        btn.addEventListener('click', () => openProcessDrawer(Number(btn.dataset.logId)));
    });
    body.querySelectorAll('.calc-view-result-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
            const qs = new URLSearchParams();
            if (btn.dataset.year) qs.set('year', btn.dataset.year);
            if (btn.dataset.month) qs.set('month', btn.dataset.month);
            if (btn.dataset.location) qs.set('location', btn.dataset.location);
            if (btn.dataset.vehicle) qs.set('vehicle_model', btn.dataset.vehicle);
            const suffix = qs.toString() ? `?${qs.toString()}` : '';
            window.location.hash = `/stamping-part-cost${suffix}`;
        });
    });
    body.querySelectorAll('.calc-delete-log-btn').forEach((btn) => {
        btn.addEventListener('click', () => deleteCalcLog(Number(btn.dataset.logId)));
    });
}

async function deleteAllCalcLogs() {
    if (calcState.canDelete === false) {
        showToast('无删除权限', 'warning');
        return;
    }
    if (!await window.confirmAction('确定删除全部计算历史？只删记录，不影响已经算好的结果。正在计算的删掉之后就可以重新算。')) {
        return;
    }
    try {
        const res = await HttpClient.delete(CALC_LOGS_API);
        const count = res.data?.deleted_count ?? 0;
        showToast(`已删除 ${count} 条`, 'success');
        loadCalcHistory(1);
    } catch (error) {
        console.error('删除失败:', error);
    }
}

async function deleteCalcLog(logId) {
    if (!logId) return;
    if (calcState.canDelete === false) {
        showToast('无删除权限', 'warning');
        return;
    }
    if (!await window.confirmAction('确定删除这条计算历史？只删记录，不影响已经算好的结果。正在计算的删掉之后就可以重新算。')) return;
    try {
        await HttpClient.delete(`${CALC_LOGS_API}/${logId}`);
        showToast('删除成功', 'success');
        const nextPage =
            calcState.history.items.length === 1 && calcState.history.page > 1
                ? calcState.history.page - 1
                : calcState.history.page;
        loadCalcHistory(nextPage);
    } catch (error) {
        console.error('删除失败:', error);
    }
}

async function openProcessDrawer(logId) {
    if (!logId) return;
    try {
        const response = await HttpClient.get(`${CALC_LOGS_API}/${logId}`);
        showProcessDrawer(response.data || {});
    } catch (error) {
        showToast(error.message || '加载过程失败', 'error');
    }
}

function showProcessDrawer(log) {
    closeProcessDrawer();
    const status = STATUS_META[log.status] || STATUS_META.failed;
    const scope = `${fmtPeriod(log.year, log.month) || '-'} · ${log.location || '-'} · ${log.vehicle_model || '-'}`;
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
                计算过程 · ${esc(scope)}
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
            <div>汇总：零件 ${fmtInt(log.total_parts)} · 成功 ${fmtInt(log.success_count)} · 失败 ${fmtInt(log.failed_count)} · 跳过 ${fmtInt(log.skipped_approved_count)}</div>
        </div>
        <div class="flex-1 overflow-y-auto overscroll-contain p-5">
            <pre class="text-[11px] leading-5 font-mono text-ink-muted whitespace-pre-wrap break-words bg-app-main border border-app-elevated p-4">${esc(log.detail_text || '（无过程文本）')}
</pre>
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

async function startCalculation() {
    if (calcState.canRun === false) {
        showToast('无计算权限', 'warning');
        return;
    }
    if (calcState.isCalculating) return;

    const year = parseInt(document.getElementById('calcYear')?.value, 10);
    const month = parseInt(document.getElementById('calcMonth')?.value, 10);
    const location = document.getElementById('calcLocation')?.value || '';
    const vehicleModel = document.getElementById('calcVehicleModel')?.value || '';

    if (Number.isNaN(year) || Number.isNaN(month) || !location || !vehicleModel) {
        showToast(SCOPE_REQUIRED_MESSAGE, 'warning');
        return;
    }
    if (!calcState.ready.can_calculate) {
        showToast('当前所选条件数据未就绪，无法计算', 'warning');
        document.getElementById('dataReadyErrorBanner')?.classList.remove('hidden');
        return;
    }

    const payload = {
        year,
        month,
        location,
        vehicle_model: vehicleModel,
    };

    setCalculating(true);
    showProgress(0, '已提交计算队列');

    try {
        const response = await HttpClient.post(CALC_API, payload);
        const taskId = response.data?.task_id;
        if (!taskId) throw new Error('未返回任加ID');
        loadCalcHistory(1);
        startPolling(taskId);
    } catch (error) {
        const msg = error.message || '提交计算失败';
        showToast(msg.includes('正在计算') ? DUPLICATE_SCOPE_CALC_MESSAGE : msg, 'warning');
        stopPolling();
        hideProgress();
        calcState.activeTaskId = null;
        setCalculating(false);
        loadCalcHistory(1);
    }
}

function showProgress(progress = 0, msg = '已提交计算队列') {
    document.getElementById('calcProgressPanel')?.classList.remove('hidden');
    updateProgress(progress, msg);
}

function hideProgress() {
    document.getElementById('calcProgressPanel')?.classList.add('hidden');
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
        if (status === 'completed' || status === 'failed') spinner.classList.add('hidden');
        else spinner.classList.remove('hidden');
    }
    if (titleEl) {
        if (status === 'completed') {
            titleEl.textContent = '计算完成';
            titleEl.className = 'text-xs font-medium text-ok truncate mb-0';
        } else if (status === 'failed') {
            titleEl.textContent = '计算失败';
            titleEl.className = 'text-xs font-medium text-danger truncate mb-0';
        } else {
            titleEl.textContent = '正在核算零件价格...';
            titleEl.className = 'text-xs font-medium text-ink truncate mb-0';
        }
    }
}

function stopPolling() {
    if (calcState.pollTimer) {
        clearInterval(calcState.pollTimer);
        calcState.pollTimer = null;
    }
    calcState.pollInFlight = false;
}

function startPolling(taskId) {
    stopPolling();
    calcState.activeTaskId = taskId;
    const tick = async () => {
        if (calcState.pollInFlight) return;
        calcState.pollInFlight = true;
        try {
            const response = await HttpClient.get(
                `${CALC_TASK_API}/${encodeURIComponent(taskId)}`,
            );
            const data = response.data;
            const status = data?.status || 'running';
            updateProgress(data?.progress ?? 0, data?.msg || '', status);
            if (status === 'completed' || status === 'failed') {
                stopPolling();
                const result = data?.result || {};
                calcState.lastResult = result;
                const bizStatus = result.status || status;
                showToast(
                    status === 'failed'
                        ? data?.msg || '计算失败'
                        : `计算${STATUS_META[bizStatus]?.label || '完成'}：成功${fmtInt(result.success_count)}，失败${fmtInt(result.failed_count)}`,
                    status === 'failed' || bizStatus === 'failed'
                        ? 'error'
                        : bizStatus === 'partial'
                          ? 'warning'
                          : 'success',
                );
                calcState.activeTaskId = null;
                setCalculating(false);
                loadCalcReady();
                loadCalcHistory(1);
                if (result.log_id) openProcessDrawer(result.log_id);
                if (status === 'completed') {
                    setTimeout(() => {
                        if (!calcState.isCalculating) hideProgress();
                    }, 1800);
                }
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
    [
        'calcYear',
        'calcMonth',
        'calcLocation',
        'calcVehicleModel',
        'calcResetBtn',
    ].forEach((id) => {
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
        validateDataPreparation();
    }
}

export const pageConfig = {
    render: partCostCalcTemplate,
    init: () => init(),
    destroy: () => destroy(),
};
