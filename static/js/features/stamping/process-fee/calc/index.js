/**
 * 冲压加工费计算页
 * 对齐钢价计算：异步后台计算+ 进度轮询 + 历史过程日志
 */

import {
    processFeeCalcTemplate,
    renderCalcHistoryPagination,
} from './template.js?v=15';
import {
    DEFAULT_PAGE_SIZE,
    bindPageSizeSelect,
} from '../../../../page-size.js?v=2';

const CASCADE_API = '/api/stamping/filters/cascade';
const API_BASE = '/api/stamping/process-fees';
const CALC_API = `${API_BASE}/calc`;
const CALC_READY_API = `${API_BASE}/calc/ready`;
const CALC_TASK_API = `${API_BASE}/calc/tasks`;
const CALC_LOGS_API = `${API_BASE}/calc/logs`;
const POLL_INTERVAL_MS = 1500;
const DUPLICATE_SCOPE_CALC_MESSAGE = '当前年度/基地/工厂正在计算中，请勿重复提交。;
const SCOPE_REQUIRED_MESSAGE = '须选定年度、基地、冲压工厂;

const STATUS_META = {
    processing: { label: '计算中, className: 'text-[#64b5f6]' },
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
    ready: { part_count: 0, tonnage_rate_count: 0 },
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
    bindPageSizeSelect('feeCalcHistoryPageSize', {
        getSize: () => calcState.history.size,
        setSize: (size) => {
            calcState.history.size = size;
        },
        onChange: () => loadCalcHistory(1),
    });
    applyPermissionUi();
    validateDataPreparation('', null, '', 0, 0);
    loadYearOptions().then(() => {
        loadCascadeFilters();
        loadCalcReady();
        loadCalcHistory(1);
    });

    if (calcState.isCalculating && calcState.activeTaskId) {
        setCalculating(true);
        showProgress(0, '正在恢复任务进度...');
        startPolling(calcState.activeTaskId);
    } else {
        hideProgress();
    }
}

function destroy() {
    stopPolling();
    closeProcessDrawer();
}

function applyPermissionUi() {
    const canRun = typeof can === 'function' ? can('op:stamping-process-fee-calc:run') : true;
    calcState.canRun = canRun;
    calcState.canDelete = typeof can === 'function' ? can('op:stamping-process-fee-calc:delete') : true;
    if (!canRun) {
        document.getElementById('startCalcBtn')?.classList.add('hidden');
    }
}

function bindEvents() {
    document.getElementById('calcResetBtn')?.addEventListener('click', () => resetFilters());
    document.getElementById('calcYear')?.addEventListener('change', () => loadCalcReady());

    document.getElementById('calcLocation')?.addEventListener('change', () => {
        resetDependentFilters(['calcSupplier', 'calcVehicleModel', 'calcVersion']);
        loadCascadeFilters();
        loadCalcReady();
    });
    document.getElementById('calcSupplier')?.addEventListener('change', () => {
        resetDependentFilters(['calcVehicleModel', 'calcVersion']);
        loadCascadeFilters();
        loadCalcReady();
    });
    document.getElementById('calcVehicleModel')?.addEventListener('change', () => {
        resetDependentFilters(['calcVersion']);
        loadCascadeFilters();
        loadCalcReady();
    });
    document.getElementById('calcVersion')?.addEventListener('change', () => loadCalcReady());

    document.getElementById('startCalcBtn')?.addEventListener('click', () => startCalculation());
    document.getElementById('calcHistoryRefreshBtn')?.addEventListener('click', () => loadCalcHistory(1));
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

function fillSelect(id, values = [], preferredValue = null) {
    const select = document.getElementById(id);
    if (!select) return;
    const current = preferredValue != null ? preferredValue : select.value;
    const emptyLabel = select.querySelector('option[value=""]')?.textContent || '全部';
    select.innerHTML =
        `<option value="">${emptyLabel}</option>` +
        values.map((value) => {
            const text = String(value);
            return `<option value="${esc(text)}"${text === String(current) ? ' selected' : ''}>${esc(text)}</option>`;
        }).join('');
}

async function loadYearOptions() {
    try {
        const res = await HttpClient.get(`${API_BASE}/filters/years`);
        const years = Array.isArray(res.data) ? res.data.slice() : [];
        const currentYear = new Date().getFullYear();
        if (!years.includes(currentYear)) years.unshift(currentYear);
        fillSelect('calcYear', years, String(currentYear));
    } catch (error) {
        showToast(error.message || '加载年度失败', 'error');
    }
}

async function loadCascadeFilters() {
    try {
        const params = {
            location: document.getElementById('calcLocation')?.value || '',
            stamping_supplier: document.getElementById('calcSupplier')?.value || '',
            vehicle_model: document.getElementById('calcVehicleModel')?.value || '',
        };
        const res = await HttpClient.get(CASCADE_API, { params });
        const filters = res.data || {};
        fillSelect('calcLocation', filters.locations || []);
        fillSelect('calcSupplier', filters.stamping_suppliers || []);
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

    ['calcLocation', 'calcSupplier', 'calcVehicleModel', 'calcVersion'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });

    const now = new Date();
    const yearEl = document.getElementById('calcYear');
    if (yearEl) yearEl.value = String(now.getFullYear());

    calcState.lastResult = null;
    hideProgress();
    loadYearOptions().then(() => {
        loadCascadeFilters();
        loadCalcReady();
        loadCalcHistory(1);
    });
}

async function loadCalcReady() {
    const yearRaw = document.getElementById('calcYear')?.value;
    const year = yearRaw ? Number(yearRaw) : null;
    const location = document.getElementById('calcLocation')?.value || '';
    const supplier = document.getElementById('calcSupplier')?.value || '';
    const vehicleModel = document.getElementById('calcVehicleModel')?.value || '';
    const version = document.getElementById('calcVersion')?.value || '';

    if (!year) {
        calcState.ready = { part_count: 0, tonnage_rate_count: 0 };
        setReadyCounts(0, 0);
        validateDataPreparation(location, year, supplier, 0, 0);
        return;
    }

    try {
        const params = { year };
        if (location) params.location = location;
        if (supplier) params.stamping_supplier = supplier;
        if (vehicleModel) params.vehicle_model = vehicleModel;
        if (version) params.version = version;

        const res = await HttpClient.get(CALC_READY_API, { params });
        const data = res.data || {};
        const partCount = Number(data.part_count) || 0;
        const rateCount = Number(data.tonnage_rate_count) || 0;
        calcState.ready = { part_count: partCount, tonnage_rate_count: rateCount };
        setReadyCounts(partCount, rateCount);
        validateDataPreparation(location, year, supplier, partCount, rateCount);
    } catch (error) {
        console.error('加载计算就绪统计失败:', error);
        calcState.ready = { part_count: 0, tonnage_rate_count: 0 };
        setReadyCounts(0, 0);
        validateDataPreparation(location, year, supplier, 0, 0);
        showToast('加载数据依据失败', 'error');
    }
}

function validateDataPreparation(location, year, supplier, partCount, rateCount) {
    const startBtn = document.getElementById('startCalcBtn');
    const errorBanner = document.getElementById('dataReadyErrorBanner');
    if (!startBtn || calcState.isCalculating) return;

    const isScopeSelected = Boolean(year && location && supplier);
    const isDataValid = Number(partCount) > 0 && Number(rateCount) > 0;
    const isReady = isScopeSelected && isDataValid;

    startBtn.disabled = !isReady;
    if (isReady) {
        errorBanner?.classList.add('hidden');
    } else {
        errorBanner?.classList.remove('hidden');
    }
}

function setReadyCounts(parts, rates) {
    setCountHtml('cntParts', parts, '价);
    setCountHtml('cntTonnageRates', rates, '条);
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

    body.innerHTML = `<tr><td colspan="13" class="py-8 text-center text-[#555]">加载中..</td></tr>`;

    try {
        const res = await HttpClient.get(CALC_LOGS_API, {
            params: {
                page,
                size: calcState.history.size,
            },
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
        body.innerHTML = `<tr><td colspan="13" class="py-8 text-center text-[#ef5350]">加载失败</td></tr>`;
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
        body.innerHTML = `<tr><td colspan="13" class="py-8 text-center text-[#555]">暂无计算记录</td></tr>`;
        return;
    }

    body.innerHTML = items.map((item) => {
        const status = STATUS_META[item.status] || STATUS_META.failed;
        const filterParts = [];
        if (item.vehicle_model) filterParts.push(item.vehicle_model);
        if (item.version) filterParts.push(item.version);
        const filterText = filterParts.length ? filterParts.join(' / ') : '全部';
        const started = formatDateTime(item.started_at);
        const createdBy = item.created_by || item.operator_name || '-';
        const isProcessing = item.status === 'processing';

        return `
            <tr class="hover:bg-[#ffffff]/[0.02] transition-colors text-[#999]" data-log-id="${esc(item.id)}">
                <td class="py-2 px-2 font-mono text-[#666] whitespace-nowrap">${esc(started)}</td>
                <td class="py-2 px-2 text-[#ccc] whitespace-nowrap">${esc(createdBy)}</td>
                <td class="py-2 px-2 font-mono text-[#ccc] whitespace-nowrap">${esc(item.year)}</td>
                <td class="py-2 px-2 text-[#ccc] whitespace-nowrap">${esc(item.location || '-')}</td>
                <td class="py-2 px-2 text-[#ccc] whitespace-nowrap">${esc(item.stamping_supplier || '-')}</td>
                <td class="py-2 px-2 text-[#777] max-w-[140px] truncate" title="${esc(filterText)}">${esc(filterText)}</td>
                <td class="py-2 px-2 text-center text-[9px] ${status.className}">${status.label}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-[#777]">${fmtInt(item.total_parts)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-[#777]">${fmtInt(item.success_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums ${Number(item.failed_count) > 0 ? 'text-[#ef5350]' : 'text-[#777]'}">${fmtInt(item.failed_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums ${Number(item.zero_fee_count) > 0 ? 'text-[#ffb74d]' : 'text-[#777]'}">${fmtInt(item.zero_fee_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-[#777]">${fmtInt(item.skipped_approved_count)}</td>
                <td class="py-2 px-2 text-right whitespace-nowrap">
                    ${isProcessing ? `
                    <span class="text-[9px] text-[#555]">进行中</span>
                    ` : `
                    <button type="button"
                            class="calc-view-process-btn text-[9px] text-[#777] hover:text-white mr-2"
                            data-log-id="${esc(item.id)}">过程</button>
                    ${item.status === 'failed' ? '' : `
                    <button type="button"
                            class="calc-view-result-btn text-[9px] text-[#777] hover:text-white mr-2"
                            data-year="${esc(item.year)}"
                            data-location="${esc(item.location || '')}"
                            data-supplier="${esc(item.stamping_supplier || '')}">结果</button>
                    `}
                    ${calcState.canDelete !== false ? `
                    <button type="button"
                            class="calc-delete-log-btn text-[9px] text-[#777] hover:text-[#ef5350]"
                            data-log-id="${esc(item.id)}">删除</button>` : ''}
                    `}
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
            if (btn.dataset.location) qs.set('location', btn.dataset.location);
            if (btn.dataset.supplier) qs.set('stamping_supplier', btn.dataset.supplier);
            const suffix = qs.toString() ? `?${qs.toString()}` : '';
            window.location.hash = `/stamping-process-fee${suffix}`;
        });
    });
    body.querySelectorAll('.calc-delete-log-btn').forEach((btn) => {
        btn.addEventListener('click', () => deleteCalcLog(Number(btn.dataset.logId)));
    });
}

async function deleteCalcLog(logId) {
    if (!logId) return;
    if (calcState.canDelete === false) {
        showToast('无删除权除, 'warning');
        return;
    }
    if (!window.confirm('确定删除这条计算历史？仅删除日志，不影响已落库的加工费。)) {
        return;
    }
    try {
        await HttpClient.delete(`${CALC_LOGS_API}/${logId}`);
        showToast('删除成功', 'success');
        const nextPage =
            calcState.history.items.length === 1 && calcState.history.page > 1
                ? calcState.history.page - 1
                : calcState.history.page;
        loadCalcHistory(nextPage);
    } catch (error) {
        console.error('删除计算历史失败:', error);
        showToast(error.message || '删除失败', 'error');
    }
}

async function openProcessDrawer(logId) {
    if (!logId) return;
    try {
        const response = await HttpClient.get(`${CALC_LOGS_API}/${logId}`);
        const log = response.data || {};
        showProcessDrawer(log);
    } catch (error) {
        console.error('加载计算过程失败:', error);
        showToast(error.message || '加载过程失败', 'error');
    }
}

function showProcessDrawer(log) {
    closeProcessDrawer();

    const status = STATUS_META[log.status] || STATUS_META.failed;
    const scope = `${log.year || '-'} · ${log.location || '-'} · ${log.stamping_supplier || '-'}`;
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
            <button type="button" id="closeCalcProcessDrawer"
                    class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
            </button>
        </div>
        <div class="px-5 py-3 border-b border-[#222] text-[10px] text-[#777] space-y-1 shrink-0">
            <div>批次（span class="font-mono text-[#999]">${esc(log.calc_batch_id || '-')}</span></div>
            <div>时间（${esc(formatDateTime(log.started_at))} →${esc(formatDateTime(log.finished_at))}</div>
            <div>汇总：零件 ${fmtInt(log.total_parts)} · 成功 ${fmtInt(log.success_count)} · 失败 ${fmtInt(log.failed_count)} · 零价 ${fmtInt(log.zero_fee_count)} · 跳过 ${fmtInt(log.skipped_approved_count)}</div>
        </div>
        <div class="flex-1 overflow-y-auto overscroll-contain p-5">
            <pre class="text-[11px] leading-5 font-mono text-[#9e9e9e] whitespace-pre-wrap break-words bg-[#111111] border border-[#262626] p-4">${esc(log.detail_text || '（无过程文本）)}</pre>
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

async function isScopeProcessing(year, location, supplier) {
    try {
        const response = await HttpClient.get(CALC_LOGS_API, {
            params: {
                year,
                location,
                stamping_supplier: supplier,
                page: 1,
                size: 20,
            },
        });
        const items = response.data?.items || [];
        return items.some((item) => item.status === 'processing');
    } catch (error) {
        console.error('检查计算锁失败:', error);
        return false;
    }
}

async function startCalculation() {
    if (calcState.canRun === false) {
        showToast('无计算权除, 'warning');
        return;
    }
    if (calcState.isCalculating) return;

    const year = parseInt(document.getElementById('calcYear')?.value, 10);
    const location = document.getElementById('calcLocation')?.value || '';
    const supplier = document.getElementById('calcSupplier')?.value || '';
    const vehicleModel = document.getElementById('calcVehicleModel')?.value || '';
    const version = document.getElementById('calcVersion')?.value || '';

    if (Number.isNaN(year) || !location || !supplier) {
        showToast(SCOPE_REQUIRED_MESSAGE, 'warning');
        return;
    }

    const { part_count, tonnage_rate_count } = calcState.ready;
    if (part_count <= 0 || tonnage_rate_count <= 0) {
        showToast('当前所选条件数据未就绪，无法计算, 'warning');
        document.getElementById('dataReadyErrorBanner')?.classList.remove('hidden');
        return;
    }

    if (await isScopeProcessing(year, location, supplier)) {
        showToast(DUPLICATE_SCOPE_CALC_MESSAGE, 'warning');
        loadCalcHistory(1);
        return;
    }

    const payload = {
        year,
        location,
        stamping_supplier: supplier,
    };
    if (vehicleModel) payload.vehicle_model = vehicleModel;
    if (version) payload.version = version;

    setCalculating(true);
    showProgress(0, '已提交计算队列);

    try {
        const response = await HttpClient.post(CALC_API, payload);
        const taskId = response.data?.task_id;
        if (!taskId) throw new Error('未返回任加ID');
        loadCalcHistory(1);
        startPolling(taskId);
    } catch (error) {
        console.error('提交加工费计算失败', error);
        const msg = error.message || '提交计算失败';
        if (msg.includes('正在计算')) {
            showToast(DUPLICATE_SCOPE_CALC_MESSAGE, 'warning');
        } else {
            showToast(msg, 'error');
        }
        stopPolling();
        hideProgress();
        calcState.activeTaskId = null;
        setCalculating(false);
        loadCalcHistory(1);
    }
}

function showProgress(progress = 0, msg = '已提交计算队列) {
    document.getElementById('calcProgressPanel')?.classList.remove('hidden');
    updateProgress(progress, msg);
}

function hideProgress() {
    document.getElementById('calcProgressPanel')?.classList.add('hidden');
    updateProgress(0, '已提交计算队列);
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
            titleEl.className = 'text-xs font-medium text-[#4caf50] truncate mb-0';
        } else if (status === 'failed') {
            titleEl.textContent = '计算失败';
            titleEl.className = 'text-xs font-medium text-[#ef5350] truncate mb-0';
        } else {
            titleEl.textContent = '正在计算加工费..';
            titleEl.className = 'text-xs font-medium text-[#ffffff] truncate mb-0';
        }
    }

    if (status === 'completed' && bar) {
        bar.className = 'h-full bg-[#2e7d32] transition-all duration-300';
        if (percentEl) percentEl.className = 'text-xs font-mono tabular-nums text-[#4caf50] shrink-0';
    } else if (status === 'failed' && bar) {
        bar.className = 'h-full bg-[#c62828] transition-all duration-300';
        if (percentEl) percentEl.className = 'text-xs font-mono tabular-nums text-[#ef5350] shrink-0';
    } else if (bar) {
        bar.className = 'h-full bg-[#d32f2f] shadow-[0_0_8px_rgba(211,47,47,0.5)] transition-all duration-300';
        if (percentEl) percentEl.className = 'text-xs font-mono tabular-nums text-[#d32f2f] shrink-0';
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
        `${CALC_TASK_API}/${encodeURIComponent(taskId)}`,
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
                const zero = result.zero_fee_count || 0;
                if (zero > 0) {
                    showToast(
                        `计算${STATUS_META[bizStatus]?.label || '完成'}：成加${fmtInt(result.success_count)}，零价${fmtInt(zero)}，请到列表手工调整`,
                        'warning',
                    );
                } else {
                    showToast(
                        `计算${STATUS_META[bizStatus]?.label || '完成'}：成加${fmtInt(result.success_count)}，失败${fmtInt(result.failed_count)}`,
                        bizStatus === 'failed' ? 'error' : bizStatus === 'partial' ? 'warning' : 'success',
                    );
                }
                calcState.activeTaskId = null;
                setCalculating(false);
                loadCalcReady();
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
                loadCalcReady();
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
    const filterIds = [
        'calcYear',
        'calcLocation',
        'calcSupplier',
        'calcVehicleModel',
        'calcVersion',
        'calcResetBtn',
    ];

    filterIds.forEach((id) => {
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
        startBtn.textContent = '开始计算;
        validateDataPreparation(
            document.getElementById('calcLocation')?.value || '',
            parseInt(document.getElementById('calcYear')?.value, 10) || null,
            document.getElementById('calcSupplier')?.value || '',
            calcState.ready.part_count || 0,
            calcState.ready.tonnage_rate_count || 0,
        );
    }
}

export const pageConfig = {
    render: processFeeCalcTemplate,
    init: () => init(),
    destroy: () => destroy(),
};
