import { DRAWER_SHELL, DRAWER_BACKDROP } from '../../../../ui/classes.js?v=13';
import { opsIconButtonHtml } from '../../../../ui/hud-table.js?v=3';
import {
    dieFeeCalcTemplate,
    CALC_HISTORY_COLSPAN,
} from './template.js?v=19';
import {
    DEFAULT_PAGE_SIZE,
    bindPagination,
    paintPagination,
} from '../../../../ui/page-size.js?v=11';
import {
    formatDurationSeconds,
    formatTimingLine,
} from '../../../../domain/duration.js?v=3';

const API_BASE = '/api/stamping/die-fees';
const DIE_FILTERS_API = '/api/stamping/die/filters';
const CALC_API = `${API_BASE}/calc`;
const CALC_READY_API = `${API_BASE}/calc/ready`;
const CALC_TASK_API = `${API_BASE}/calc/progress`;
const CALC_LOGS_API = `${API_BASE}/calc/logs`;
const POLL_INTERVAL_MS = 1500;
const SCOPE_REQUIRED_MESSAGE = '须选定年度、基地、项目。';
const READY_FALLBACK =
    '提示：先选年度、基地、项目（版本可不选）。一次算出本项目各供应商的模具费。只算这一年布点还有效的零件，不按项目档案的起止时间。模具单价必须已生效。';

const STATUS_META = {
    processing: { label: '计算中', className: 'text-ink-muted' },
    success: { label: '成功', className: 'text-ok' },
    failed: { label: '失败', className: 'text-danger' },
};

const calcState = {
    isCalculating: false,
    activeTaskId: null,
    pollTimer: null,
    pollInFlight: false,
    canRun: true,
    canDelete: true,
    ready: { part_count: 0, calculable_count: 0, has_unit_price: false, message: null },
    history: { page: 1, size: DEFAULT_PAGE_SIZE, total: 0, totalPages: 1, items: [] },
};

function init() {
    stopPolling();
    bindEvents();
    bindPagination({
        selectId: 'dieFeeCalcHistoryPageSize',
        buttonsId: 'calcHistoryPagination',
        getSize: () => calcState.history.size,
        setSize: (size) => {
            calcState.history.size = size;
        },
        onPage: (page) => loadCalcHistory(page),
    });
    applyPermissionUi();
    loadYearOptions().then(() => {
        loadFilters().then(() => {
            loadCalcReady();
            loadCalcHistory(1);
        });
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
    document.getElementById('calcHistoryDeleteAllBtn')?.classList.toggle('hidden', !calcState.canDelete);
}

function bindEvents() {
    document.getElementById('calcResetBtn')?.addEventListener('click', () => resetFilters());
    document.getElementById('calcYear')?.addEventListener('change', () => {
        loadFilters(true).then(() => loadCalcReady());
    });
    document.getElementById('calcLocation')?.addEventListener('change', () => {
        loadFilters(true);
        loadCalcReady();
    });
    document.getElementById('calcVehicleModel')?.addEventListener('change', () => {
        loadIdentityFilters(true);
        loadCalcReady();
    });
    document.getElementById('calcVersion')?.addEventListener('change', () => loadCalcReady());
    document.getElementById('startCalcBtn')?.addEventListener('click', () => startCalculation());
    document.getElementById('calcHistoryRefreshBtn')?.addEventListener('click', () => loadCalcHistory(1));
    document.getElementById('calcHistoryDeleteAllBtn')?.addEventListener('click', () => deleteAllCalcLogs());
}

function fillSelect(id, values, preferredValue, placeholder = '请选择', formatLabel = null) {
    const select = document.getElementById(id);
    if (!select) return;
    const current = preferredValue != null ? preferredValue : select.value;
    select.innerHTML =
        `<option value="">${esc(placeholder)}</option>` +
        values.map((value) => {
            const text = String(value);
            const label = formatLabel ? formatLabel(value) : text;
            return `<option value="${esc(text)}"${text === String(current) ? ' selected' : ''}>${esc(String(label))}</option>`;
        }).join('');
}

async function loadYearOptions() {
    try {
        const res = await HttpClient.get(`${API_BASE}/filters`);
        const years = Array.isArray(res.data?.years) ? res.data.years.slice() : [];
        const currentYear = new Date().getFullYear();
        if (!years.includes(currentYear)) years.unshift(currentYear);
        fillSelect('calcYear', years, String(currentYear), '请选择', fmtYear);
    } catch (error) {
        showToast(error.message || '加载年度失败', 'error');
    }
}

async function loadFilters(keepVehicle) {
    const location = document.getElementById('calcLocation')?.value || '';
    try {
        const res = await HttpClient.get(`${API_BASE}/filters`, {
            params: {
                ...(location ? { location } : {}),
                ...(Number.isFinite(Number(document.getElementById('calcYear')?.value))
                    ? { year: Number(document.getElementById('calcYear')?.value) }
                    : {}),
                for_calc: 1,
            },
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
        const versionEl = document.getElementById('calcVersion');
        if (versionEl) versionEl.value = '';
    }
    if (!location || !vehicle) {
        fillSelect('calcVersion', [], '', '请先选择项目');
        return;
    }
    try {
        const res = await HttpClient.get(DIE_FILTERS_API, {
            params: {
                location,
                vehicle_model: vehicle,
            },
        });
        const data = res.data || {};
        fillSelect('calcVersion', data.versions || [], undefined, '全部');
    } catch (error) {
        showToast(error.message || '加载供应商/版本失败', 'error');
    }
}

function resetFilters() {
    if (calcState.isCalculating) {
        showToast('计算进行中，请稍候再重置', 'warning');
        return;
    }
    const loc = document.getElementById('calcLocation');
    if (loc) loc.value = '';
    loadYearOptions().then(() => {
        loadFilters().then(() => {
            loadCalcReady();
            loadCalcHistory(1);
        });
    });
}

async function loadCalcReady() {
    const year = Number(document.getElementById('calcYear')?.value);
    const location = document.getElementById('calcLocation')?.value || '';
    const vehicleModel = document.getElementById('calcVehicleModel')?.value || '';
    if (!year || year < 2000) {
        setReady(0, 0, false, null);
        return;
    }
    try {
        const params = { year };
        if (location) params.location = location;
        if (vehicleModel) params.vehicle_model = vehicleModel;
        const version = document.getElementById('calcVersion')?.value || '';
        if (version) params.version = version;
        const res = await HttpClient.get(CALC_READY_API, { params });
        const data = res.data || {};
        setReady(
            Number(data.part_count) || 0,
            Number(data.calculable_count) || 0,
            Boolean(data.has_unit_price),
            data.message || null,
        );
    } catch (error) {
        setReady(0, 0, false, null);
        showToast(error.message || '加载就绪失败', 'error');
    }
}

function setReady(parts, calculable, hasUnitPrice, message) {
    calcState.ready = {
        part_count: parts,
        calculable_count: calculable,
        has_unit_price: hasUnitPrice,
        message: message || null,
    };
    setCountHtml('cntParts', parts, '件');
    setCountHtml('cntCalculable', calculable, '件');
    const priceEl = document.getElementById('cntUnitPrice');
    if (priceEl) {
        priceEl.textContent = hasUnitPrice ? '有' : '无';
        priceEl.className = `text-xs font-mono font-bold ${hasUnitPrice ? 'text-ink' : 'text-danger'}`;
    }
    validateReady();
}

function setCountHtml(id, count, unit) {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = `${Number(count).toLocaleString('zh-CN')} <span class="text-[9px] font-normal text-ink-faint">${unit}</span>`;
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
    if (ready) {
        banner?.classList.add('hidden');
    } else if (banner) {
        banner.textContent = calcState.ready.message
            ? `提示：${calcState.ready.message}`
            : READY_FALLBACK;
        banner.classList.remove('hidden');
    }
}

async function loadCalcHistory(page = calcState.history.page) {
    const body = document.getElementById('calcHistoryBody');
    if (!body) return;
            body.innerHTML = `<tr><td colspan="${CALC_HISTORY_COLSPAN}" class="py-8 text-center text-ink-faint">加载中..</td></tr>`;
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
        paintPagination('calcHistoryPagination', 
                calcState.history.page,
                calcState.history.totalPages,
            );
    } catch (error) {
            body.innerHTML = `<tr><td colspan="${CALC_HISTORY_COLSPAN}" class="py-8 text-center text-danger">加载失败</td></tr>`;
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
        body.innerHTML = `<tr><td colspan="${CALC_HISTORY_COLSPAN}" class="py-8 text-center text-ink-faint">暂无计算记录</td></tr>`;
        return;
    }
    body.innerHTML = items.map((item) => {
        const status = STATUS_META[item.status] || STATUS_META.failed;
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
            attrs: `data-year="${esc(item.year)}" data-location="${esc(item.location || '')}" data-vehicle="${esc(item.vehicle_model || '')}" data-version="${esc(item.version || '')}"`,
        });
        const deleteBtn = calcState.canDelete !== false && !isProcessing ? opsIconButtonHtml({
            extraClass: 'calc-delete-log-btn',
            danger: true,
            title: '删除',
            icon: window.svgIcon('trash', 'w-3.5 h-3.5'),
            attrs: `data-log-id="${esc(item.id)}"`,
        }) : '';
        const processingMark = isProcessing
            ? '<span class="text-[9px] text-ink-faint">进行中</span>'
            : '';
        return `
            <tr class="group hover:bg-ink/[0.02] text-ink-muted">
                <td class="py-2 px-2 font-mono text-ink-dim whitespace-nowrap">${esc(formatDateTime(item.started_at))}</td>
                <td class="py-2 px-2 font-mono text-ink-dim whitespace-nowrap">${esc(formatDateTime(item.finished_at))}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-ink-dim whitespace-nowrap">${esc(formatDurationSeconds(item))}</td>
                <td class="py-2 px-2 text-ink-muted whitespace-nowrap">${esc(item.created_by || item.operator_name || '-')}</td>
                <td class="py-2 px-2 font-mono text-ink-muted">${esc(fmtYear(item.year))}</td>
                <td class="py-2 px-2 text-ink-muted">${esc(item.location || '-')}</td>
                <td class="py-2 px-2 text-ink-muted">${esc(item.vehicle_model || '-')}</td>
                <td class="py-2 px-2 text-ink-muted whitespace-nowrap">${esc(item.stamping_supplier || '全部工厂')}</td>
                <td class="py-2 px-2 text-ink-muted whitespace-nowrap">${esc(item.version || '全部')}</td>
                <td class="py-2 px-2 text-center text-[9px] ${status.className}">${status.label}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-ink-dim">${fmtInt(item.total_parts)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-ink-dim">${fmtInt(item.success_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-ink-dim">${fmtInt(item.skipped_no_die_count)}</td>
                <td class="py-2 px-1 text-right whitespace-nowrap">
                    <div class="inline-flex items-center justify-end">${processingMark}${processBtn}${resultBtn}${deleteBtn}</div>
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
            if (btn.dataset.version) qs.set('version', btn.dataset.version);
            window.location.hash = `/stamping-die-fee?${qs.toString()}`;
        });
    });
    body.querySelectorAll('.calc-delete-log-btn').forEach((btn) => {
        btn.addEventListener('click', () => deleteCalcLog(Number(btn.dataset.logId)));
    });
}

async function deleteAllCalcLogs() {
    if (calcState.canDelete === false) return;
    if (!await window.confirmAction('确定删除全部计算历史？只删记录，不影响已经算好的模具费。正在计算的不会删。')) {
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
    if (!logId || calcState.canDelete === false) return;
    if (!await window.confirmAction('确定删除这条计算历史？只删记录，不影响已经算好的模具费。')) return;
    try {
        await HttpClient.delete(`${CALC_LOGS_API}/${logId}`);
        showToast('删除成功', 'success');
        loadCalcHistory(calcState.history.page);
    } catch (error) {
        console.error('删除失败:', error);
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
        backdrop.className = DRAWER_BACKDROP;
        const drawer = document.createElement('div');
        drawer.id = 'calcProcessDrawer';
        drawer.className = `${DRAWER_SHELL} w-[640px]`;
        drawer.innerHTML = `
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0 bg-app-surface border-b border-line">
                <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted uppercase">计算过程
                    <span class="ml-2 normal-case ${status.className}">${status.label}</span>
                </h5>
                <div class="flex items-center gap-0.5 shrink-0">
                    ${window.copyProcessReportButtonHtml()}
                    <button type="button" id="closeCalcProcessDrawer" class="w-8 h-8 text-ink-dim hover:text-ink">×</button>
                </div>
            </div>
            <div class="px-5 py-3 border-b border-line-subtle text-[10px] text-ink-dim shrink-0">
                <div>${esc(formatTimingLine(log, formatDateTime) || '-')}</div>
                <div class="mt-1">
                入库 ${fmtInt(log.success_count)} · 跳过 ${fmtInt(log.skipped_no_die_count)}
                ${String(log.detail_text || '').includes('有尺寸但无模具编号')
                    ? ' · <span class="text-warn">有长宽高无模具号（仅提示）</span>'
                    : ''}
                </div>
            </div>
            <div class="flex-1 overflow-y-auto p-5">
                <pre class="text-[11px] font-mono text-ink-muted whitespace-pre-wrap bg-app-main border border-app-elevated p-4">${esc(log.detail_text || '（无过程文本）')}</pre>
            </div>`;
        document.body.appendChild(backdrop);
        document.body.appendChild(drawer);
        window.bindProcessReportCopy(drawer);
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
    ['calcYear', 'calcLocation', 'calcVehicleModel', 'calcVersion', 'calcResetBtn'].forEach((id) => {
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
