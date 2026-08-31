import {
    dieFeeCalcTemplate,
    renderCalcHistoryPagination,
    CALC_HISTORY_COLSPAN,
} from './template.js?v=2';
import {
    DEFAULT_PAGE_SIZE,
    bindPageSizeSelect,
} from '../../../../page-size.js?v=2';

const API_BASE = '/api/stamping/die-fees';
const DIE_FILTERS_API = '/api/stamping/die/filters';
const CALC_API = `${API_BASE}/calc`;
const CALC_READY_API = `${API_BASE}/calc/ready`;
const CALC_TASK_API = `${API_BASE}/calc/progress`;
const CALC_LOGS_API = `${API_BASE}/calc/logs`;
const POLL_INTERVAL_MS = 1500;
const SCOPE_REQUIRED_MESSAGE = '须选定年度、基地、项目。';

const STATUS_META = {
    processing: { label: '计算中', className: 'text-[#64b5f6]' },
    success: { label: '成功', className: 'text-[#66bb6a]' },
    failed: { label: '失败', className: 'text-[#ef5350]' },
};

const calcState = {
    isCalculating: false,
    activeTaskId: null,
    pollTimer: null,
    pollInFlight: false,
    canRun: true,
    canDelete: true,
    ready: { part_count: 0, calculable_count: 0, has_unit_price: false },
    history: { page: 1, size: DEFAULT_PAGE_SIZE, total: 0, totalPages: 1, items: [] },
};

function init() {
    stopPolling();
    bindEvents();
    bindPageSizeSelect('dieFeeCalcHistoryPageSize', {
        getSize: () => calcState.history.size,
        setSize: (size) => {
            calcState.history.size = size;
        },
        onChange: () => loadCalcHistory(1),
    });
    applyPermissionUi();
    const yearEl = document.getElementById('calcYear');
    if (yearEl && !yearEl.value) yearEl.value = String(new Date().getFullYear());
    loadFilters().then(() => {
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
    calcState.canRun = typeof can === 'function' ? can('op:stamping-die-fee-calc:run') : true;
    calcState.canDelete = typeof can === 'function' ? can('op:stamping-die-fee-calc:delete') : true;
    if (!calcState.canRun) document.getElementById('startCalcBtn')?.classList.add('hidden');
}

function bindEvents() {
    document.getElementById('calcResetBtn')?.addEventListener('click', () => resetFilters());
    document.getElementById('calcYear')?.addEventListener('change', () => loadCalcReady());
    document.getElementById('calcLocation')?.addEventListener('change', () => {
        loadFilters(true);
        loadCalcReady();
    });
    document.getElementById('calcVehicleModel')?.addEventListener('change', () => {
        loadIdentityFilters(true);
        loadCalcReady();
    });
    document.getElementById('calcSupplier')?.addEventListener('change', () => {
        loadVersionOptions();
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

function fillSelect(id, values, preferredValue, placeholder = '请选择') {
    const select = document.getElementById(id);
    if (!select) return;
    const current = preferredValue != null ? preferredValue : select.value;
    select.innerHTML =
        `<option value="">${esc(placeholder)}</option>` +
        values.map((value) => {
            const text = String(value);
            return `<option value="${esc(text)}"${text === String(current) ? ' selected' : ''}>${esc(text)}</option>`;
        }).join('');
}

async function loadFilters(keepVehicle) {
    const location = document.getElementById('calcLocation')?.value || '';
    try {
        const res = await HttpClient.get(`${API_BASE}/filters`, {
            params: location ? { location } : {},
        });
        const filters = res.data || {};
        fillSelect('calcLocation', filters.locations || []);
        fillSelect('calcVehicleModel', filters.vehicle_models || [], keepVehicle ? undefined : '');
        await loadIdentityFilters(!keepVehicle);
    } catch (error) {
        showToast(error.message || '加载筛选项失败', 'error');
    }
}

async function loadIdentityFilters(resetDownstream) {
    const location = document.getElementById('calcLocation')?.value || '';
    const vehicle = document.getElementById('calcVehicleModel')?.value || '';
    if (resetDownstream) {
        ['calcSupplier', 'calcVersion'].forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
    }
    if (!location || !vehicle) {
        fillSelect('calcSupplier', [], '', '请先选择项目');
        fillSelect('calcVersion', [], '', '请先选择项目');
        return;
    }
    try {
        const supplier = document.getElementById('calcSupplier')?.value || '';
        const res = await HttpClient.get(DIE_FILTERS_API, {
            params: {
                location,
                vehicle_model: vehicle,
                stamping_supplier: supplier || undefined,
            },
        });
        const data = res.data || {};
        fillSelect('calcSupplier', data.stamping_suppliers || [], undefined, '全部');
        fillSelect('calcVersion', data.versions || [], undefined, '全部');
    } catch (error) {
        showToast(error.message || '加载供应商/版本失败', 'error');
    }
}

async function loadVersionOptions() {
    const versionEl = document.getElementById('calcVersion');
    if (versionEl) versionEl.value = '';
    await loadIdentityFilters(false);
}

function resetFilters() {
    if (calcState.isCalculating) {
        showToast('计算进行中，请稍候再重置', 'warning');
        return;
    }
    const yearEl = document.getElementById('calcYear');
    if (yearEl) yearEl.value = String(new Date().getFullYear());
    const loc = document.getElementById('calcLocation');
    if (loc) loc.value = '';
    loadFilters().then(() => {
        loadCalcReady();
        loadCalcHistory(1);
    });
}

async function loadCalcReady() {
    const year = Number(document.getElementById('calcYear')?.value);
    const location = document.getElementById('calcLocation')?.value || '';
    const vehicleModel = document.getElementById('calcVehicleModel')?.value || '';
    if (!year || year < 2000) {
        setReady(0, 0, false);
        return;
    }
    try {
        const params = { year };
        if (location) params.location = location;
        if (vehicleModel) params.vehicle_model = vehicleModel;
        const supplier = document.getElementById('calcSupplier')?.value || '';
        const version = document.getElementById('calcVersion')?.value || '';
        if (supplier) params.stamping_supplier = supplier;
        if (version) params.version = version;
        const res = await HttpClient.get(CALC_READY_API, { params });
        const data = res.data || {};
        setReady(
            Number(data.part_count) || 0,
            Number(data.calculable_count) || 0,
            Boolean(data.has_unit_price),
        );
    } catch (error) {
        setReady(0, 0, false);
        showToast(error.message || '加载就绪失败', 'error');
    }
}

function setReady(parts, calculable, hasUnitPrice) {
    calcState.ready = {
        part_count: parts,
        calculable_count: calculable,
        has_unit_price: hasUnitPrice,
    };
    setCountHtml('cntParts', parts, '件');
    setCountHtml('cntCalculable', calculable, '件');
    const priceEl = document.getElementById('cntUnitPrice');
    if (priceEl) {
        priceEl.textContent = hasUnitPrice ? '有' : '无';
        priceEl.className = `text-xs font-mono font-bold ${hasUnitPrice ? 'text-[#dddddd]' : 'text-[#ef5350]'}`;
    }
    validateReady();
}

function setCountHtml(id, count, unit) {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = `${Number(count).toLocaleString('zh-CN')} <span class="text-[9px] font-normal text-[#555]">${unit}</span>`;
}

function validateReady() {
    const startBtn = document.getElementById('startCalcBtn');
    const banner = document.getElementById('dataReadyErrorBanner');
    if (!startBtn || calcState.isCalculating) return;
    const year = Number(document.getElementById('calcYear')?.value);
    const location = document.getElementById('calcLocation')?.value || '';
    const vehicleModel = document.getElementById('calcVehicleModel')?.value || '';
    const ready =
        year >= 2000 &&
        location &&
        vehicleModel &&
        calcState.ready.part_count > 0 &&
        calcState.ready.has_unit_price;
    startBtn.disabled = !ready;
    banner?.classList.toggle('hidden', ready);
}

async function loadCalcHistory(page = calcState.history.page) {
    const body = document.getElementById('calcHistoryBody');
    if (!body) return;
            body.innerHTML = `<tr><td colspan="${CALC_HISTORY_COLSPAN}" class="py-8 text-center text-[#555]">加载中..</td></tr>`;
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
        if (totalEl) totalEl.textContent = `共 ${calcState.history.total} 条`;
        const pagination = document.getElementById('calcHistoryPagination');
        if (pagination) {
            pagination.innerHTML = renderCalcHistoryPagination(
                calcState.history.page,
                calcState.history.totalPages,
            );
        }
    } catch (error) {
            body.innerHTML = `<tr><td colspan="${CALC_HISTORY_COLSPAN}" class="py-8 text-center text-[#ef5350]">加载失败</td></tr>`;
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
        body.innerHTML = `<tr><td colspan="${CALC_HISTORY_COLSPAN}" class="py-8 text-center text-[#555]">暂无计算记录</td></tr>`;
        return;
    }
    body.innerHTML = items.map((item) => {
        const status = STATUS_META[item.status] || STATUS_META.failed;
        const isProcessing = item.status === 'processing';
        return `
            <tr class="hover:bg-[#ffffff]/[0.02] text-[#999]">
                <td class="py-2 px-2 font-mono text-[#666] whitespace-nowrap">${esc(formatDateTime(item.started_at))}</td>
                <td class="py-2 px-2 text-[#ccc] whitespace-nowrap">${esc(item.created_by || item.operator_name || '-')}</td>
                <td class="py-2 px-2 font-mono text-[#ccc]">${esc(item.year)}</td>
                <td class="py-2 px-2 text-[#ccc]">${esc(item.location || '-')}</td>
                <td class="py-2 px-2 text-[#ccc]">${esc(item.vehicle_model || '-')}</td>
                <td class="py-2 px-2 text-[#ccc] whitespace-nowrap">${esc(item.stamping_supplier || '全部')}</td>
                <td class="py-2 px-2 text-[#ccc] whitespace-nowrap">${esc(item.version || '全部')}</td>
                <td class="py-2 px-2 text-center text-[9px] ${status.className}">${status.label}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-[#777]">${fmtInt(item.total_parts)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-[#777]">${fmtInt(item.success_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-[#777]">${fmtInt(item.skipped_no_die_count)}</td>
                <td class="py-2 px-2 text-right whitespace-nowrap">
                    ${isProcessing ? '<span class="text-[9px] text-[#555]">进行中</span>' : `
                    <button type="button" class="calc-view-process-btn text-[9px] text-[#777] hover:text-white mr-2" data-log-id="${esc(item.id)}">过程</button>
                    ${item.status === 'failed' ? '' : `
                    <button type="button" class="calc-view-result-btn text-[9px] text-[#777] hover:text-white mr-2"
                        data-year="${esc(item.year)}" data-location="${esc(item.location || '')}"
                        data-vehicle="${esc(item.vehicle_model || '')}"
                        data-supplier="${esc(item.stamping_supplier || '')}"
                        data-version="${esc(item.version || '')}">结果</button>`}
                    `}
                    ${calcState.canDelete !== false && !isProcessing ? `
                    <button type="button" class="calc-delete-log-btn text-[9px] text-[#777] hover:text-[#ef5350]" data-log-id="${esc(item.id)}">删除</button>` : ''}
                </td>
            </tr>`;
    }).join('');
    body.querySelectorAll('.calc-view-process-btn').forEach((btn) => {
        btn.addEventListener('click', () => openProcessDrawer(Number(btn.dataset.logId)));
    });
    body.querySelectorAll('.calc-view-result-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
            const qs = new URLSearchParams();
            if (btn.dataset.year) qs.set('year', btn.dataset.year);
            if (btn.dataset.location) qs.set('location', btn.dataset.location);
            if (btn.dataset.vehicle) qs.set('vehicle_model', btn.dataset.vehicle);
            if (btn.dataset.supplier) qs.set('stamping_supplier', btn.dataset.supplier);
            if (btn.dataset.version) qs.set('version', btn.dataset.version);
            window.location.hash = `/stamping-die-fee?${qs.toString()}`;
        });
    });
    body.querySelectorAll('.calc-delete-log-btn').forEach((btn) => {
        btn.addEventListener('click', () => deleteCalcLog(Number(btn.dataset.logId)));
    });
}

async function deleteCalcLog(logId) {
    if (!logId || calcState.canDelete === false) return;
    if (!window.confirm('确定删除这条计算历史？仅删日志，不影响已落库模具费。')) return;
    try {
        await HttpClient.delete(`${CALC_LOGS_API}/${logId}`);
        showToast('删除成功', 'success');
        loadCalcHistory(calcState.history.page);
    } catch (error) {
        showToast(error.message || '删除失败', 'error');
    }
}

async function openProcessDrawer(logId) {
    try {
        const response = await HttpClient.get(`${CALC_LOGS_API}/${logId}`);
        const log = response.data || {};
        closeProcessDrawer();
        const status = STATUS_META[log.status] || STATUS_META.failed;
        const backdrop = document.createElement('div');
        backdrop.id = 'calcProcessBackdrop';
        backdrop.className = 'fixed inset-0 z-[80] bg-black/70';
        const drawer = document.createElement('div');
        drawer.id = 'calcProcessDrawer';
        drawer.className = 'fixed inset-y-0 right-0 z-[85] w-[640px] max-w-[95vw] bg-[#1a1a1a] border-l border-[#2a2a2a] flex flex-col';
        drawer.innerHTML = `
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0 bg-[#1f1f1f] border-b border-[#333333]">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] uppercase">计算过程
                    <span class="ml-2 normal-case ${status.className}">${status.label}</span>
                </h5>
                <button type="button" id="closeCalcProcessDrawer" class="w-8 h-8 text-[#707070] hover:text-white">×</button>
            </div>
            <div class="px-5 py-3 border-b border-[#222] text-[10px] text-[#777] shrink-0">
                入库 ${fmtInt(log.success_count)} · 跳过 ${fmtInt(log.skipped_no_die_count)}
                ${String(log.detail_text || '').includes('有尺寸但无模具编号')
                    ? ' · <span class="text-[#ffb74d]">有长宽高无模具号（仅提示）</span>'
                    : ''}
            </div>
            <div class="flex-1 overflow-y-auto p-5">
                <pre class="text-[11px] font-mono text-[#9e9e9e] whitespace-pre-wrap bg-[#111111] border border-[#262626] p-4">${esc(log.detail_text || '（无过程文本）')}</pre>
            </div>`;
        document.body.appendChild(backdrop);
        document.body.appendChild(drawer);
        backdrop.addEventListener('click', closeProcessDrawer);
        document.getElementById('closeCalcProcessDrawer')?.addEventListener('click', closeProcessDrawer);
    } catch (error) {
        showToast(error.message || '加载过程失败', 'error');
    }
}

function closeProcessDrawer() {
    document.getElementById('calcProcessBackdrop')?.remove();
    document.getElementById('calcProcessDrawer')?.remove();
}

async function startCalculation() {
    if (calcState.canRun === false || calcState.isCalculating) return;
    const year = parseInt(document.getElementById('calcYear')?.value, 10);
    const location = document.getElementById('calcLocation')?.value || '';
    const vehicleModel = document.getElementById('calcVehicleModel')?.value || '';
    const supplier = document.getElementById('calcSupplier')?.value || '';
    const version = document.getElementById('calcVersion')?.value || '';
    if (Number.isNaN(year) || !location || !vehicleModel) {
        showToast(SCOPE_REQUIRED_MESSAGE, 'warning');
        return;
    }
    if (calcState.ready.part_count <= 0 || !calcState.ready.has_unit_price) {
        showToast('当前所选条件数据未就绪，无法计算', 'warning');
        return;
    }
    setCalculating(true);
    showProgress(0, '已提交计算队列');
    try {
        const payload = {
            year,
            location,
            vehicle_model: vehicleModel,
        };
        if (supplier) payload.stamping_supplier = supplier;
        if (version) payload.version = version;
        const response = await HttpClient.post(CALC_API, payload);
        const taskId = response.data?.task_id;
        if (!taskId) throw new Error('未返回任务 ID');
        loadCalcHistory(1);
        startPolling(taskId);
    } catch (error) {
        showToast(error.message || '提交计算失败', 'error');
        stopPolling();
        hideProgress();
        setCalculating(false);
        loadCalcHistory(1);
    }
}

function showProgress(progress, msg) {
    document.getElementById('calcProgressPanel')?.classList.remove('hidden');
    updateProgress(progress, msg);
}

function hideProgress() {
    document.getElementById('calcProgressPanel')?.classList.add('hidden');
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
    if (spinner) spinner.classList.toggle('hidden', status === 'completed' || status === 'failed');
    if (titleEl) {
        if (status === 'completed') titleEl.textContent = '计算完成';
        else if (status === 'failed') titleEl.textContent = '计算失败';
        else titleEl.textContent = '正在计算模具费..';
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
            const response = await HttpClient.get(`${CALC_TASK_API}/${encodeURIComponent(taskId)}`);
            const data = response.data || {};
            const status = data.status || 'running';
            updateProgress(data.progress ?? 0, data.msg || '', status);
            if (status === 'completed' || status === 'failed') {
                stopPolling();
                const result = data.result || {};
                const missingCount = Number(result.missing_die_number_count) || 0;
                if (status === 'failed') {
                    showToast(data.msg || '计算失败', 'error');
                } else if (missingCount > 0) {
                    showToast(
                        `计算完成。有 ${missingCount} 处工序已有长宽高但无模具号（未拦截，详见计算过程）`,
                        'warning',
                    );
                } else {
                    showToast(data.msg || '计算完成', 'success');
                }
                calcState.activeTaskId = null;
                setCalculating(false);
                loadCalcReady();
                loadCalcHistory(1);
                if (result.log_id) openProcessDrawer(result.log_id);
                return;
            }
        } catch (error) {
            stopPolling();
            showToast(error.message || '查询进度失败', 'error');
            setCalculating(false);
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
    ['calcYear', 'calcLocation', 'calcVehicleModel', 'calcSupplier', 'calcVersion', 'calcResetBtn'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.disabled = isCalculating;
    });
    if (startBtn && isCalculating) startBtn.disabled = true;
    if (!isCalculating) validateReady();
}

export const pageConfig = {
    render: dieFeeCalcTemplate,
    init,
    destroy,
};
