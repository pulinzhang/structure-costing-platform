/**
 * BOM 焊接费计算页
 * 异步后台计算 + 进度轮询 + 历史过程日志
 */

import { DRAWER_CLOSE, DRAWER_SHELL, DRAWER_BACKDROP } from '../../../../ui/classes.js?v=13';
import { opsIconButtonHtml } from '../../../../ui/hud-table.js?v=3';
import {
    l0WeldingFeeCalcTemplate,
} from './template.js?v=21';
import {
    DEFAULT_PAGE_SIZE,
    bindPagination,
    paintPagination,
} from '../../../../ui/page-size.js?v=11';
import {
    formatDurationSeconds,
    formatTimingLine,
} from '../../../../domain/duration.js?v=3';

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
    '提示：先选年度、基地、项目。这一年还有效的焊接工艺拆解，以及当年焊接单价，都必须有。';

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
        const color = n > 0 ? 'text-warn' : 'text-ink';
        zeroEl.className = `text-xs font-mono font-bold ${color}`;
        zeroEl.innerHTML = `${n.toLocaleString('zh-CN')} <span class="text-[9px] font-normal text-ink-faint">条</span>`;
    }
}

function setCountHtml(id, count, unit) {
    const el = document.getElementById(id);
    if (!el) return;
    const display = Number.isFinite(count) ? Number(count).toLocaleString('zh-CN') : '-';
    el.innerHTML = `${display} <span class="text-[9px] font-normal text-ink-faint">${unit}</span>`;
}

async function loadCalcHistory(page = calcState.history.page) {
    const body = document.getElementById('l0wfCalcHistoryBody');
    if (!body) return;
    body.innerHTML = `<tr><td colspan="16" class="py-8 text-center text-ink-faint">加载中..</td></tr>`;

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
        body.innerHTML = `<tr><td colspan="16" class="py-8 text-center text-danger">加载失败</td></tr>`;
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
        body.innerHTML = `<tr><td colspan="16" class="py-8 text-center text-ink-faint">暂无计算记录</td></tr>`;
        return;
    }

    body.innerHTML = items.map((item) => {
        const status = STATUS_META[item.status] || STATUS_META.failed;
        const isProcessing = item.status === 'processing';
        const processBtn = isProcessing ? '' : opsIconButtonHtml({
            extraClass: 'wf-calc-view-process-btn',
            title: '过程',
            icon: window.svgIcon('file-earmark-text', 'w-3.5 h-3.5'),
            attrs: `data-log-id="${esc(item.id)}"`,
        });
        const resultBtn = isProcessing || item.status === 'failed' ? '' : opsIconButtonHtml({
            extraClass: 'wf-calc-view-result-btn',
            title: '结果',
            icon: window.svgIcon('external-link', 'w-3.5 h-3.5'),
            attrs: `data-year="${esc(item.year)}" data-location="${esc(item.location || '')}" data-vehicle-model="${esc(item.vehicle_model || '')}" data-bom-version="${esc(item.bom_version || '')}"`,
        });
        const deleteBtn = calcState.canDelete !== false ? opsIconButtonHtml({
            extraClass: 'wf-calc-delete-log-btn',
            danger: true,
            title: '有正在计算的：删掉后就可以重新算',
            icon: window.svgIcon('trash', 'w-3.5 h-3.5'),
            attrs: `data-log-id="${esc(item.id)}"`,
        }) : '';
        const processingMark = isProcessing
            ? '<span class="text-[9px] text-ink-faint mr-1">进行中</span>'
            : '';
        return `
            <tr class="group hover:bg-ink/[0.02] transition-colors text-ink-muted">
                <td class="py-2 px-2 font-mono text-ink-dim whitespace-nowrap">${esc(formatDateTime(item.started_at))}</td>
                <td class="py-2 px-2 font-mono text-ink-dim whitespace-nowrap">${esc(formatDateTime(item.finished_at))}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-ink-dim whitespace-nowrap">${esc(formatDurationSeconds(item))}</td>
                <td class="py-2 px-2 text-ink-muted whitespace-nowrap">${esc(item.created_by || item.operator_name || '-')}</td>
                <td class="py-2 px-2 font-mono text-ink-muted whitespace-nowrap">${esc(fmtYear(item.year))}</td>
                <td class="py-2 px-2 text-ink-muted whitespace-nowrap">${esc(item.location || '-')}</td>
                <td class="py-2 px-2 text-ink-muted whitespace-nowrap">${esc(item.vehicle_model || '-')}</td>
                <td class="py-2 px-2 text-ink-muted whitespace-nowrap">${esc(item.bom_version || '-')}</td>
                <td class="py-2 px-2 text-center text-[9px] ${status.className}">${status.label}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-ink-dim">${fmtInt(item.l0_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-ink-dim">${fmtInt(item.created_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-ink-dim">${fmtInt(item.updated_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums ${Number(item.failed_count) > 0 ? 'text-danger' : 'text-ink-dim'}">${fmtInt(item.failed_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums ${Number(item.missing_price_count) > 0 ? 'text-warn' : 'text-ink-dim'}">${fmtInt(item.missing_price_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-ink-dim">${fmtInt(item.skipped_approved_count)}</td>
                <td class="py-2 px-1 text-right whitespace-nowrap">
                    <div class="inline-flex items-center justify-end">${processingMark}${processBtn}${resultBtn}${deleteBtn}</div>
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
    if (!await window.confirmAction('确定删除全部计算历史？只删记录，不影响已经算好的焊接费。正在计算的删掉之后就可以重新算。')) {
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
    if (!logId || calcState.canDelete === false) {
        if (calcState.canDelete === false) showToast('无删除权限', 'warning');
        return;
    }
    if (!await window.confirmAction('确定删除这条计算历史？只删记录，不影响已经算好的焊接费。正在计算的删掉之后就可以重新算。')) return;
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
    const scope = `${log.year || '-'} · ${log.location || '-'} · ${log.vehicle_model || '-'} · ${log.bom_version || '-'}`;
    const backdrop = document.createElement('div');
    backdrop.id = 'l0wfCalcProcessBackdrop';
    backdrop.className = DRAWER_BACKDROP;

    const drawer = document.createElement('div');
    drawer.id = 'l0wfCalcProcessDrawer';
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
                <button type="button" id="l0wfCloseCalcProcessDrawer"
                    class="${DRAWER_CLOSE}">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
        </div>
        <div class="px-5 py-3 border-b border-line-subtle text-[10px] text-ink-dim space-y-1 shrink-0">
            <div>批次 <span class="font-mono text-ink-muted">${esc(log.calc_batch_id || '-')}</span></div>
            <div>${esc(formatTimingLine(log, formatDateTime) || '-')}</div>
            <div>汇总：节点 ${fmtInt(log.l0_count)} · 新增 ${fmtInt(log.created_count)} · 更新 ${fmtInt(log.updated_count)} · 失败 ${fmtInt(log.failed_count)} · 缺单价 ${fmtInt(log.missing_price_count)} · 跳过 ${fmtInt(log.skipped_approved_count)}</div>
        </div>
        <div class="flex-1 overflow-y-auto overscroll-contain p-5">
            <pre class="text-[11px] leading-5 font-mono text-ink-muted whitespace-pre-wrap break-words bg-app-main border border-app-elevated p-4">${esc(log.detail_text || '（无过程文本）')}</pre>
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
            titleEl.className = 'text-xs font-medium text-ok truncate mb-0';
        } else if (status === 'failed') {
            titleEl.textContent = '计算失败';
            titleEl.className = 'text-xs font-medium text-danger truncate mb-0';
        } else {
            titleEl.textContent = '正在计算焊接费…';
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
