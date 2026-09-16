/**
 * BOM 焊接费计算页
 * 异步后台计算 + 进度轮询 + 历史过程日志
 */

import {
    l0WeldingFeeCalcTemplate,
} from './template.js?v=13';
import {
    DEFAULT_PAGE_SIZE,
    bindPagination,
    paintPagination,
} from '../../../../page-size.js?v=3';

const API_BASE = '/api/bom/welding-fees';
const UNIT_PRICE_YEARS_API = '/api/bom/welding-unit-price/filters/years';
const CASCADE_API = '/api/bom/filters/cascade';
const CALC_API = `${API_BASE}/calc`;
const CALC_READY_API = `${API_BASE}/calc/ready`;
const CALC_TASK_API = `${API_BASE}/calc/tasks`;
const CALC_LOGS_API = `${API_BASE}/calc/logs`;
const POLL_INTERVAL_MS = 1500;
const DUPLICATE_SCOPE_CALC_MESSAGE = '当前范围正在计算中，请勿重复提交。';
const SCOPE_REQUIRED_MESSAGE = '须选定年度、基地、项目。';
const READY_FALLBACK =
    '提示：须选定年度、基地、项目；并确保存在有效期内的焊接工艺拆解与该年焊接单价。';

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
        unit_price_count: 0,
        levels: [],
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
        selectId: 'l0wfCalcHistoryPageSize',
        buttonsId: 'l0wfCalcHistoryPagination',
        getSize: () => calcState.history.size,
        setSize: (size) => {
            calcState.history.size = size;
        },
        onPage: (page) => loadCalcHistory(page),
    });
    applyPermissionUi();
    validateDataPreparation();
    loadYearOptions().then(() => {
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
    const canFn = typeof can === 'function' ? can : () => true;
    calcState.canRun = canFn('op:bom-welding-fee-calc:run');
    calcState.canDelete = canFn('op:bom-welding-fee-calc:delete');
    if (!calcState.canRun) {
        document.getElementById('l0wfStartCalcBtn')?.classList.add('hidden');
    }
    document.getElementById('l0wfCalcHistoryDeleteAllBtn')?.classList.toggle('hidden', !calcState.canDelete);
}

function bindEvents() {
    document.getElementById('l0wfCalcResetBtn')?.addEventListener('click', resetFilters);
    document.getElementById('l0wfCalcYear')?.addEventListener('change', () => {
        loadCascadeFilters().then(() => loadCalcReady());
    });
    document.getElementById('l0wfCalcLocation')?.addEventListener('change', () => {
        resetDependentFilters(['l0wfCalcVehicleModel']);
        loadCascadeFilters().then(() => loadCalcReady());
    });
    document.getElementById('l0wfCalcVehicleModel')?.addEventListener('change', () => {
        loadCascadeFilters().then(() => loadCalcReady());
    });
    document.getElementById('l0wfStartCalcBtn')?.addEventListener('click', startCalculation);
    document.getElementById('l0wfCalcHistoryRefreshBtn')?.addEventListener('click', () => loadCalcHistory(1));
    document.getElementById('l0wfCalcHistoryDeleteAllBtn')?.addEventListener('click', () => deleteAllCalcLogs());
}

function val(id) {
    return (document.getElementById(id)?.value || '').trim();
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
    const emptyLabel = select.querySelector('option[value=""]')?.textContent || '请选择';
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
        const res = await HttpClient.get(UNIT_PRICE_YEARS_API);
        const years = Array.isArray(res.data) ? res.data.slice() : [];
        const currentYear = new Date().getFullYear();
        if (!years.includes(currentYear)) years.unshift(currentYear);
        fillSelect('l0wfCalcYear', years, String(currentYear), fmtYear);
    } catch (error) {
        showToast(error.message || '加载年度失败', 'error');
    }
}

async function loadCascadeFilters() {
    try {
        const params = {
            location: val('l0wfCalcLocation'),
            vehicle_model: val('l0wfCalcVehicleModel'),
        };
        const year = parseInt(val('l0wfCalcYear'), 10);
        if (Number.isFinite(year)) params.year = year;
        const res = await HttpClient.get(CASCADE_API, { params });
        const filters = res.data || {};
        fillSelect('l0wfCalcLocation', filters.locations || []);
        fillSelect('l0wfCalcVehicleModel', filters.vehicle_models || []);
    } catch (error) {
        console.error('加载 BOM 级联筛选失败:', error);
    }
}

function resetFilters() {
    if (calcState.isCalculating) {
        showToast('计算进行中，请稍候再重置', 'warning');
        return;
    }
    ['l0wfCalcLocation', 'l0wfCalcVehicleModel'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    calcState.lastResult = null;
    hideProgress();
    loadYearOptions().then(() => {
        loadCascadeFilters();
        loadCalcReady();
        loadCalcHistory(1);
    });
}

function getScope() {
    const year = parseInt(val('l0wfCalcYear'), 10);
    return {
        year: Number.isFinite(year) ? year : null,
        location: val('l0wfCalcLocation'),
        vehicle_model: val('l0wfCalcVehicleModel'),
    };
}

async function loadCalcReady() {
    const scope = getScope();
    if (!scope.year || !scope.location || !scope.vehicle_model) {
        calcState.ready = { unit_price_count: 0, levels: [], message: null };
        setReadyCounts(0, 0, 0, 0);
        validateDataPreparation();
        return;
    }
    try {
        const res = await HttpClient.get(CALC_READY_API, { params: scope });
        const data = res.data || {};
        calcState.ready = {
            unit_price_count: Number(data.unit_price_count) || 0,
            levels: Array.isArray(data.levels) ? data.levels : [],
            message: data.message || null,
        };
        applyReadyCounts();
        validateDataPreparation();
    } catch (error) {
        console.error('加载计算就绪统计失败:', error);
        calcState.ready = { unit_price_count: 0, levels: [], message: null };
        setReadyCounts(0, 0, 0, 0);
        validateDataPreparation();
    }
}

function readyStats() {
    const levels = calcState.ready.levels || [];
    return {
        node_count: levels.reduce((sum, row) => sum + (Number(row.node_count) || 0), 0),
        process_line_total: levels.reduce((sum, row) => sum + (Number(row.process_line_total) || 0), 0),
        zero_process_count: levels.reduce((sum, row) => sum + (Number(row.zero_process_count) || 0), 0),
    };
}

function applyReadyCounts() {
    const stats = readyStats();
    setReadyCounts(
        stats.node_count,
        calcState.ready.unit_price_count,
        stats.process_line_total,
        stats.zero_process_count,
    );
}

function validateDataPreparation() {
    const startBtn = document.getElementById('l0wfStartCalcBtn');
    const errorBanner = document.getElementById('l0wfDataReadyErrorBanner');
    if (!startBtn || calcState.isCalculating) return;

    const scope = getScope();
    const isScopeSelected = Boolean(
        scope.year && scope.location && scope.vehicle_model,
    );
    const stats = readyStats();
    const isDataValid =
        stats.node_count > 0 && calcState.ready.unit_price_count > 0;
    const isReady = isScopeSelected && isDataValid;

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

function setReadyCounts(l0, prices, processLines, zeroProcess) {
    setCountHtml('l0wfCntL0', l0, '条');
    setCountHtml('l0wfCntUnitPrice', prices, '条');
    setCountHtml('l0wfCntProcessLines', processLines, '行');
    const zeroEl = document.getElementById('l0wfCntZeroProcess');
    if (zeroEl) {
        const n = Number(zeroProcess) || 0;
        const color = n > 0 ? 'text-[#ffb74d]' : 'text-[#dddddd]';
        zeroEl.className = `text-xs font-mono font-bold ${color}`;
        zeroEl.innerHTML = `${n.toLocaleString('zh-CN')} <span class="text-[9px] font-normal text-[#555]">条</span>`;
    }
}

function setCountHtml(id, count, unit) {
    const el = document.getElementById(id);
    if (!el) return;
    const display = Number.isFinite(count) ? Number(count).toLocaleString('zh-CN') : '-';
    el.innerHTML = `${display} <span class="text-[9px] font-normal text-[#555]">${unit}</span>`;
}

async function loadCalcHistory(page = calcState.history.page) {
    const body = document.getElementById('l0wfCalcHistoryBody');
    if (!body) return;
    body.innerHTML = `<tr><td colspan="14" class="py-8 text-center text-[#555]">加载中..</td></tr>`;

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

        const totalEl = document.getElementById('l0wfCalcHistoryTotal');
        if (totalEl) totalEl.textContent = `共 ${calcState.history.total} 条`;

        paintPagination('l0wfCalcHistoryPagination', 
                calcState.history.page,
                calcState.history.totalPages,
            );
    } catch (error) {
        console.error('加载计算历史失败:', error);
        body.innerHTML = `<tr><td colspan="14" class="py-8 text-center text-[#ef5350]">加载失败</td></tr>`;
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
    const body = document.getElementById('l0wfCalcHistoryBody');
    if (!body) return;
    if (!items.length) {
        body.innerHTML = `<tr><td colspan="14" class="py-8 text-center text-[#555]">暂无计算记录</td></tr>`;
        return;
    }

    body.innerHTML = items.map((item) => {
        const status = STATUS_META[item.status] || STATUS_META.failed;
        const isProcessing = item.status === 'processing';
        return `
            <tr class="hover:bg-[#ffffff]/[0.02] transition-colors text-[#999]">
                <td class="py-2 px-2 font-mono text-[#666] whitespace-nowrap">${esc(formatDateTime(item.started_at))}</td>
                <td class="py-2 px-2 text-[#ccc] whitespace-nowrap">${esc(item.created_by || item.operator_name || '-')}</td>
                <td class="py-2 px-2 font-mono text-[#ccc] whitespace-nowrap">${esc(fmtYear(item.year))}</td>
                <td class="py-2 px-2 text-[#ccc] whitespace-nowrap">${esc(item.location || '-')}</td>
                <td class="py-2 px-2 text-[#ccc] whitespace-nowrap">${esc(item.vehicle_model || '-')}</td>
                <td class="py-2 px-2 text-[#ccc] whitespace-nowrap">${esc(item.bom_version || '-')}</td>
                <td class="py-2 px-2 text-center text-[9px] ${status.className}">${status.label}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-[#777]">${fmtInt(item.l0_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-[#777]">${fmtInt(item.created_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-[#777]">${fmtInt(item.updated_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums ${Number(item.failed_count) > 0 ? 'text-[#ef5350]' : 'text-[#777]'}">${fmtInt(item.failed_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums ${Number(item.missing_price_count) > 0 ? 'text-[#ffb74d]' : 'text-[#777]'}">${fmtInt(item.missing_price_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-[#777]">${fmtInt(item.skipped_approved_count)}</td>
                <td class="py-2 px-2 text-right whitespace-nowrap">
                    ${isProcessing ? `<span class="text-[9px] text-[#555] mr-2">进行中</span>` : `
                    <button type="button" class="wf-calc-view-process-btn text-[9px] text-[#777] hover:text-white mr-2" data-log-id="${esc(item.id)}">过程</button>
                    ${item.status === 'failed' ? '' : `
                    <button type="button" class="wf-calc-view-result-btn text-[9px] text-[#777] hover:text-white mr-2"
                            data-year="${esc(item.year)}"
                            data-location="${esc(item.location || '')}"
                            data-vehicle-model="${esc(item.vehicle_model || '')}"
                            data-bom-version="${esc(item.bom_version || '')}">结果</button>`}
                    `}
                    ${calcState.canDelete !== false ? `
                    <button type="button" class="wf-calc-delete-log-btn text-[9px] text-[#777] hover:text-[#ef5350]" data-log-id="${esc(item.id)}" title="含计算中：删除可释放锁">删除</button>` : ''}
                </td>
            </tr>
        `;
    }).join('');

    body.querySelectorAll('.wf-calc-view-process-btn').forEach((btn) => {
        btn.addEventListener('click', () => openProcessDrawer(Number(btn.dataset.logId)));
    });
    body.querySelectorAll('.wf-calc-view-result-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
            const qs = new URLSearchParams();
            if (btn.dataset.year) qs.set('year', btn.dataset.year);
            if (btn.dataset.location) qs.set('location', btn.dataset.location);
            if (btn.dataset.vehicleModel) qs.set('vehicle_model', btn.dataset.vehicleModel);
            if (btn.dataset.bomVersion) qs.set('bom_version', btn.dataset.bomVersion);
            const suffix = qs.toString() ? `?${qs.toString()}` : '';
            window.location.hash = `/bom-welding-fee-list${suffix}`;
        });
    });
    body.querySelectorAll('.wf-calc-delete-log-btn').forEach((btn) => {
        btn.addEventListener('click', () => deleteCalcLog(Number(btn.dataset.logId)));
    });
}

async function deleteAllCalcLogs() {
    if (calcState.canDelete === false) {
        showToast('无删除权限', 'warning');
        return;
    }
    if (!window.confirm('确定删除全部计算历史？仅删除日志，不影响已落库的焊接费。计算中的记录删除后将释放锁。')) {
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
    if (!logId || calcState.canDelete === false) {
        if (calcState.canDelete === false) showToast('无删除权限', 'warning');
        return;
    }
    if (!window.confirm('确定删除这条计算历史？计算中的记录删除后将释放锁；仅删除日志，不影响已落库的焊接费。')) return;
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
    const scope = `${log.year || '-'} · ${log.location || '-'} · ${log.vehicle_model || '-'} · ${log.bom_version || '-'}`;
    const backdrop = document.createElement('div');
    backdrop.id = 'l0wfCalcProcessBackdrop';
    backdrop.className = 'fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm';

    const drawer = document.createElement('div');
    drawer.id = 'l0wfCalcProcessDrawer';
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
                <button type="button" id="l0wfCloseCalcProcessDrawer"
                    class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
        </div>
        <div class="px-5 py-3 border-b border-[#222] text-[10px] text-[#777] space-y-1 shrink-0">
            <div>批次 <span class="font-mono text-[#999]">${esc(log.calc_batch_id || '-')}</span></div>
            <div>时间：${esc(formatDateTime(log.started_at))} → ${esc(formatDateTime(log.finished_at))}</div>
            <div>汇总：节点 ${fmtInt(log.l0_count)} · 新增 ${fmtInt(log.created_count)} · 更新 ${fmtInt(log.updated_count)} · 失败 ${fmtInt(log.failed_count)} · 缺单价 ${fmtInt(log.missing_price_count)} · 跳过 ${fmtInt(log.skipped_approved_count)}</div>
        </div>
        <div class="flex-1 overflow-y-auto overscroll-contain p-5">
            <pre class="text-[11px] leading-5 font-mono text-[#9e9e9e] whitespace-pre-wrap break-words bg-[#111111] border border-[#262626] p-4">${esc(log.detail_text || '（无过程文本）')}</pre>
        </div>
    `;

    document.body.appendChild(backdrop);
    document.body.appendChild(drawer);
    window.bindProcessReportCopy(drawer);
    backdrop.addEventListener('click', closeProcessDrawer);
    document.getElementById('l0wfCloseCalcProcessDrawer')?.addEventListener('click', closeProcessDrawer);
}

function closeProcessDrawer() {
    document.getElementById('l0wfCalcProcessBackdrop')?.remove();
    document.getElementById('l0wfCalcProcessDrawer')?.remove();
}

async function startCalculation() {
    if (calcState.canRun === false) {
        showToast('无计算权限', 'warning');
        return;
    }
    if (calcState.isCalculating) return;

    const scope = getScope();
    if (!scope.year || !scope.location || !scope.vehicle_model) {
        showToast(SCOPE_REQUIRED_MESSAGE, 'warning');
        return;
    }
    if (readyStats().node_count <= 0 || calcState.ready.unit_price_count <= 0) {
        showToast('当前所选条件数据未就绪，无法计算', 'warning');
        document.getElementById('l0wfDataReadyErrorBanner')?.classList.remove('hidden');
        return;
    }

    setCalculating(true);
    showProgress(0, '已提交计算队列');

    try {
        const payload = { ...scope };
        const response = await HttpClient.post(CALC_API, payload);
        const taskId = response.data?.task_id;
        if (!taskId) throw new Error('未返回任务 ID');
        loadCalcHistory(1);
        startPolling(taskId);
    } catch (error) {
        const msg = error.message || '提交计算失败';
        showToast(msg.includes('正在计算') ? DUPLICATE_SCOPE_CALC_MESSAGE : msg, msg.includes('正在计算') ? 'warning' : 'error');
        stopPolling();
        hideProgress();
        calcState.activeTaskId = null;
        setCalculating(false);
        loadCalcHistory(1);
    }
}

function showProgress(progress = 0, msg = '已提交计算队列') {
    document.getElementById('l0wfCalcProgressPanel')?.classList.remove('hidden');
    updateProgress(progress, msg);
}

function hideProgress() {
    document.getElementById('l0wfCalcProgressPanel')?.classList.add('hidden');
    updateProgress(0, '已提交计算队列');
}

function updateProgress(progress, msg, status) {
    const pct = Math.max(0, Math.min(100, Number(progress) || 0));
    const bar = document.getElementById('l0wfCalcProgressBar');
    const percentEl = document.getElementById('l0wfCalcProgressPercent');
    const msgEl = document.getElementById('l0wfCalcProgressMsg');
    const titleEl = document.getElementById('l0wfCalcProgressTitle');
    const spinner = document.getElementById('l0wfCalcProgressSpinner');

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
            titleEl.textContent = '正在计算焊接费…';
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

function startPolling(taskId) {
    stopPolling();
    calcState.activeTaskId = taskId;

    const tick = async () => {
        if (calcState.pollInFlight) return;
        calcState.pollInFlight = true;
        try {
            const response = await HttpClient.get(`${CALC_TASK_API}/${encodeURIComponent(taskId)}`);
            const data = response.data;
            const status = data?.status || 'running';
            updateProgress(data?.progress ?? 0, data?.msg || '', status);

            if (status === 'completed') {
                stopPolling();
                const result = data?.result || {};
                calcState.lastResult = result;
                const bizStatus = result.status || 'success';
                showToast(
                    data?.msg
                    || `计算${STATUS_META[bizStatus]?.label || '完成'}：新增 ${fmtInt(result.created_count)}，更新 ${fmtInt(result.updated_count)}，失败 ${fmtInt(result.failed_count)}，缺单价 ${fmtInt(result.missing_price_count)}`,
                    bizStatus === 'failed' ? 'error' : bizStatus === 'partial' ? 'warning' : 'success',
                );
                calcState.activeTaskId = null;
                setCalculating(false);
                loadCalcReady();
                loadCalcHistory(1);
                if (result.log_id) openProcessDrawer(result.log_id);
                setTimeout(() => {
                    if (!calcState.isCalculating) hideProgress();
                }, 1800);
                return;
            }

            if (status === 'failed') {
                stopPolling();
                const result = data?.result || null;
                calcState.lastResult = result;
                showToast(data?.msg || '计算失败', 'error');
                calcState.activeTaskId = null;
                setCalculating(false);
                loadCalcReady();
                loadCalcHistory(1);
                if (result?.log_id) openProcessDrawer(result.log_id);
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
    const startBtn = document.getElementById('l0wfStartCalcBtn');
    [
        'l0wfCalcYear',
        'l0wfCalcLocation',
        'l0wfCalcVehicleModel',
        'l0wfCalcResetBtn',
    ].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.disabled = isCalculating;
    });

    if (!startBtn) return;
    if (isCalculating) {
        startBtn.setAttribute('disabled', 'true');
        startBtn.classList.add('opacity-50', 'pointer-events-none');
        startBtn.textContent = '计算中…';
    } else {
        startBtn.removeAttribute('disabled');
        startBtn.classList.remove('opacity-50', 'pointer-events-none');
        startBtn.textContent = '开始计算';
        validateDataPreparation();
    }
}

export const pageConfig = {
    render: l0WeldingFeeCalcTemplate,
    init: () => init(),
    destroy: () => destroy(),
};
