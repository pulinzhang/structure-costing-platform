/**
 * 冲压零件价格计算页
 */

import {
    partCostCalcTemplate,
    renderCalcHistoryPagination,
} from './template.js?v=10';
import {
    DEFAULT_PAGE_SIZE,
    bindPageSizeSelect,
} from '../../../../page-size.js?v=2';

const CASCADE_API = '/api/stamping/filters/cascade';
const API_BASE = '/api/costing/stamping-part-cost';
const CALC_API = `${API_BASE}/calc`;
const CALC_READY_API = `${API_BASE}/calc/ready`;
const CALC_TASK_API = `${API_BASE}/calc/tasks`;
const CALC_LOGS_API = `${API_BASE}/calc/logs`;
const POLL_INTERVAL_MS = 1500;
const DUPLICATE_SCOPE_CALC_MESSAGE = '当前年度/月份/基地/车型正在计算中，请勿重复提交。';
const SCOPE_REQUIRED_MESSAGE = '须选定年度、月份、基地、配套车型。';

const STATUS_META = {
    processing: { label: '计算中', className: 'text-[#64b5f6]' },
    success: { label: '成功', className: 'text-[#66bb6a]' },
    partial: { label: '部分成功', className: 'text-[#ffb74d]' },
    failed: { label: '失败', className: 'text-[#ef5350]' },
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
    bindPageSizeSelect('partCostCalcHistoryPageSize', {
        getSize: () => calcState.history.size,
        setSize: (size) => {
            calcState.history.size = size;
        },
        onChange: () => loadCalcHistory(1),
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
    document.getElementById('calcYear')?.addEventListener('change', () => loadCalcReady());
    document.getElementById('calcMonth')?.addEventListener('change', () => loadCalcReady());

    document.getElementById('calcLocation')?.addEventListener('change', () => {
        resetDependentFilters(['calcVehicleModel', 'calcVersion']);
        loadCascadeFilters();
        loadCalcReady();
    });
    document.getElementById('calcVehicleModel')?.addEventListener('change', () => {
        resetDependentFilters(['calcVersion']);
        loadCascadeFilters();
        loadCalcReady();
    });
    document.getElementById('calcVersion')?.addEventListener('change', () => {
        loadCascadeFilters();
        loadCalcReady();
    });

    document.getElementById('startCalcBtn')?.addEventListener('click', () => startCalculation());
    document.getElementById('calcHistoryRefreshBtn')?.addEventListener('click', () => loadCalcHistory(1));
    document.getElementById('calcHistoryDeleteAllBtn')?.addEventListener('click', () => deleteAllCalcLogs());
    document.getElementById('calcHistoryPagination')?.addEventListener('click', (event) => {
        const btn = event.target.closest('.calc-history-page-btn');
        if (btn && !btn.disabled) {
            const page = parseInt(btn.dataset.page, 10);
            if (page) loadCalcHistory(page);
        }
    });
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
            version: document.getElementById('calcVersion')?.value || '',
        };
        const res = await HttpClient.get(CASCADE_API, { params });
        const filters = res.data || {};
        fillSelect('calcLocation', filters.locations || []);
        fillSelect('calcVehicleModel', filters.vehicle_models || []);
        fillSelect('calcVersion', filters.versions || []);
    } catch (error) {
        console.error('加载冲压筛选选项失败:', error);
    }
}

function resetFilters() {
    if (calcState.isCalculating) {
        showToast('计算进行中，请稍候再重置', 'warning');
        return;
    }
    ['calcLocation', 'calcVehicleModel', 'calcVersion'].forEach((id) => {
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
    const version = document.getElementById('calcVersion')?.value || '';

    if (!year || Number.isNaN(year)) {
        calcState.ready = {
            part_count: 0,
            steel_price_count: 0,
            scrap_price_count: 0,
            process_fee_count: 0,
            die_fee_count: 0,
            gauge_fee_count: 0,
            can_calculate: false,
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
        if (version) params.version = version;

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
    } else {
        errorBanner?.classList.remove('hidden');
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
    el.innerHTML = `${display} <span class="text-[9px] font-normal text-[#555]">${unit}</span>`;
}

async function loadCalcHistory(page = calcState.history.page) {
    const body = document.getElementById('calcHistoryBody');
    if (!body) return;
    body.innerHTML = `<tr><td colspan="12" class="py-8 text-center text-[#555]">加载中..</td></tr>`;
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
        const pagination = document.getElementById('calcHistoryPagination');
        if (pagination) {
            pagination.innerHTML = renderCalcHistoryPagination(
                calcState.history.page,
                calcState.history.totalPages,
            );
        }
    } catch (error) {
        console.error('加载计算历史失败:', error);
        body.innerHTML = `<tr><td colspan="12" class="py-8 text-center text-[#ef5350]">加载失败</td></tr>`;
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
        body.innerHTML = `<tr><td colspan="12" class="py-8 text-center text-[#555]">暂无计算记录</td></tr>`;
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
        return `
            <tr class="hover:bg-[#ffffff]/[0.02] transition-colors text-[#999]" data-log-id="${esc(item.id)}">
                <td class="py-2 px-2 font-mono text-[#666] whitespace-nowrap">${esc(formatDateTime(item.started_at))}</td>
                <td class="py-2 px-2 text-[#ccc] whitespace-nowrap">${esc(item.created_by || item.operator_name || '-')}</td>
                <td class="py-2 px-2 font-mono text-[#ccc] whitespace-nowrap">${esc(ym)}</td>
                <td class="py-2 px-2 text-[#ccc] whitespace-nowrap">${esc(item.location || '-')}</td>
                <td class="py-2 px-2 text-[#ccc] whitespace-nowrap">${esc(item.stamping_supplier || '-')}</td>
                <td class="py-2 px-2 text-[#777] max-w-[140px] truncate" title="${esc(filterText)}">${esc(filterText)}</td>
                <td class="py-2 px-2 text-center text-[9px] ${status.className}">${status.label}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-[#777]">${fmtInt(item.total_parts)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-[#777]">${fmtInt(item.success_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums ${Number(item.failed_count) > 0 ? 'text-[#ef5350]' : 'text-[#777]'}">${fmtInt(item.failed_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-[#777]">${fmtInt(item.skipped_approved_count)}</td>
                <td class="py-2 px-2 text-right whitespace-nowrap">
                    ${isProcessing ? `<span class="text-[9px] text-[#555] mr-2">进行中</span>` : `
                    <button type="button" class="calc-view-process-btn text-[9px] text-[#777] hover:text-white mr-2" data-log-id="${esc(item.id)}">过程</button>
                    ${item.status === 'failed' ? '' : `
                    <button type="button" class="calc-view-result-btn text-[9px] text-[#777] hover:text-white mr-2"
                            data-year="${esc(item.year)}" data-month="${esc(item.month || '')}"
                            data-location="${esc(item.location || '')}"
                            data-vehicle="${esc(item.vehicle_model || '')}">结果</button>`}
                    `}
                    ${calcState.canDelete !== false ? `
                    <button type="button" class="calc-delete-log-btn text-[9px] text-[#777] hover:text-[#ef5350]" data-log-id="${esc(item.id)}" title="含计算中：删除可释放锁">删除</button>` : ''}
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
    if (!window.confirm('确定删除全部计算历史？仅删除日志，不影响已落库结果。计算中的记录删除后将释放锁。')) {
        return;
    }
    try {
        const res = await HttpClient.delete(CALC_LOGS_API);
        const count = res.data?.deleted_count ?? 0;
        showToast(`已删除 ${count} 条`, 'success');
        loadCalcHistory(1);
    } catch (error) {
        showToast(error.message || '删除失败', 'error');
    }
}

async function deleteCalcLog(logId) {
    if (!logId) return;
    if (calcState.canDelete === false) {
        showToast('无删除权限', 'warning');
        return;
    }
    if (!window.confirm('确定删除这条计算历史？计算中的记录删除后将释放锁；仅删除日志，不影响已落库结果。')) return;
    try {
        await HttpClient.delete(`${CALC_LOGS_API}/${logId}`);
        showToast('删除成功', 'success');
        const nextPage =
            calcState.history.items.length === 1 && calcState.history.page > 1
                ? calcState.history.page - 1
                : calcState.history.page;
        loadCalcHistory(nextPage);
    } catch (error) {
        showToast(error.message || '删除失败', 'error');
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
    backdrop.className = 'fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm';
    const drawer = document.createElement('div');
    drawer.id = 'calcProcessDrawer';
    drawer.className =
        'fixed inset-y-0 right-0 z-[85] w-[640px] max-w-[95vw] bg-[#1a1a1a] border-l border-[#2a2a2a] flex flex-col';
    drawer.innerHTML = `
        <div class="px-5 py-3.5 flex items-center justify-between shrink-0 bg-[#1f1f1f] border-b border-[#333333]">
            <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] uppercase">
                计算过程 · ${esc(scope)}
                <span class="ml-2 normal-case ${status.className}">${status.label}</span>
            </h5>
            <div class="flex items-center gap-0.5 shrink-0">
                ${window.copyProcessReportButtonHtml()}
                <button type="button" id="closeCalcProcessDrawer"
                    class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
        </div>
        <div class="px-5 py-3 border-b border-[#222] text-[10px] text-[#777] space-y-1 shrink-0">
            <div>批次<span class="font-mono text-[#999]">${esc(log.calc_batch_id || '-')}</span></div>
            <div>时间：${esc(formatDateTime(log.started_at))} → ${esc(formatDateTime(log.finished_at))}</div>
            <div>汇总：零件 ${fmtInt(log.total_parts)} · 成功 ${fmtInt(log.success_count)} · 失败 ${fmtInt(log.failed_count)} · 跳过 ${fmtInt(log.skipped_approved_count)}</div>
        </div>
        <div class="flex-1 overflow-y-auto overscroll-contain p-5">
            <pre class="text-[11px] leading-5 font-mono text-[#9e9e9e] whitespace-pre-wrap break-words bg-[#111111] border border-[#262626] p-4">${esc(log.detail_text || '（无过程文本）')}
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
    const version = document.getElementById('calcVersion')?.value || '';

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
    if (version) payload.version = version;

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
            titleEl.className = 'text-xs font-medium text-[#4caf50] truncate mb-0';
        } else if (status === 'failed') {
            titleEl.textContent = '计算失败';
            titleEl.className = 'text-xs font-medium text-[#ef5350] truncate mb-0';
        } else {
            titleEl.textContent = '正在核算零件价格...';
            titleEl.className = 'text-xs font-medium text-[#ffffff] truncate mb-0';
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
        'calcVersion',
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
