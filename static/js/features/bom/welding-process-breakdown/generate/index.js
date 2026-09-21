/**
 * BOM 焊接工艺拆解 — 生成页
 * 级联筛选 + 异步后台拆解 + 进度轮询 + 历史过程日志
 */

import { DRAWER_CLOSE, DRAWER_SHELL, DRAWER_BACKDROP } from '../../../../ui/classes.js?v=12';
import {
    weldingProcessBreakdownGenerateTemplate,
} from './template.js?v=13';
import {
    DEFAULT_PAGE_SIZE,
    bindPagination,
    paintPagination,
} from '../../../../ui/page-size.js?v=6';
import {
    formatDurationSeconds,
    formatTimingLine,
} from '../../../../domain/duration.js?v=3';

const API_BASE = '/api/bom/welding-process-breakdown';
const CASCADE_API = '/api/bom/filters/cascade';
const GENERATE_API = `${API_BASE}/generate`;
const TASK_API = `${API_BASE}/generate/tasks`;
const LOGS_API = `${API_BASE}/generate/logs`;
const PREP_STATS_API = `${API_BASE}/generate/prep-stats`;
const POLL_INTERVAL_MS = 1500;
const DUPLICATE_SCOPE_MESSAGE = '当前范围正在拆解中，请勿重复提交。';

const STATUS_META = {
    processing: { label: '拆解中', className: 'text-ink-muted' },
    success: { label: '成功', className: 'text-ok' },
    failed: { label: '失败', className: 'text-danger' },
};

const genState = {
    isCalculating: false,
    activeTaskId: null,
    pollTimer: null,
    pollInFlight: false,
    canGenerate: true,
    canDeleteLog: true,
    location: '',
    vehicleModel: '',
    bomVersion: '',
    stats: {
        weld_node_count: 0,
        breakdown_node_count: 0,
        approved_count: 0,
        ready: false,
        message: '',
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
        selectId: 'wpbGenHistoryPageSize',
        buttonsId: 'calcHistoryPagination',
        getSize: () => genState.history.size,
        setSize: (size) => {
            genState.history.size = size;
        },
        onPage: (page) => loadCalcHistory(page),
    });
    applyPermissionUi();
    loadCascadeFilters().then(() => loadPrepStats());
    loadCalcHistory();
    hideProgress();
}

function destroy() {
    stopPolling();
    closeProcessDrawer();
}

function applyPermissionUi() {
    const canFn = typeof window.can === 'function' ? window.can : () => true;
    genState.canGenerate = canFn('op:bom-welding-process-breakdown:generate');
    genState.canDeleteLog = canFn('op:bom-welding-process-breakdown:delete-log');
    if (!genState.canGenerate) {
        document.getElementById('wpbGenSubmitBtn')?.classList.add('hidden');
    }
    document.getElementById('calcHistoryDeleteAllBtn')?.classList.toggle('hidden', !genState.canDeleteLog);
}

function bindEvents() {
    document.getElementById('wpbGenResetBtn')?.addEventListener('click', resetFilters);
    document.getElementById('wpbGenLocation')?.addEventListener('change', () => {
        genState.location = val('wpbGenLocation');
        genState.vehicleModel = '';
        genState.bomVersion = '';
        loadCascadeFilters().then(() => loadPrepStats());
    });
    document.getElementById('wpbGenModel')?.addEventListener('change', () => {
        genState.vehicleModel = val('wpbGenModel');
        genState.bomVersion = '';
        loadCascadeFilters().then(() => loadPrepStats());
    });
    document.getElementById('wpbGenVersion')?.addEventListener('change', () => {
        genState.bomVersion = val('wpbGenVersion');
        loadPrepStats();
    });
    document.getElementById('wpbGenSubmitBtn')?.addEventListener('click', startGenerate);
    document.getElementById('calcHistoryRefreshBtn')?.addEventListener('click', () => loadCalcHistory(1));
    document.getElementById('calcHistoryDeleteAllBtn')?.addEventListener('click', () => deleteAllGenerateLogs());
}

function val(id) {
    return (document.getElementById(id)?.value || '').trim();
}

function fillSelect(id, values, selected, emptyLabel = '请选择') {
    const el = document.getElementById(id);
    if (!el) return;
    let html = `<option value="">${emptyLabel}</option>`;
    (values || []).forEach((item) => {
        const mark = item === selected ? ' selected' : '';
        html += `<option value="${esc(item)}"${mark}>${esc(item)}</option>`;
    });
    el.innerHTML = html;
    if (selected && (values || []).includes(selected)) {
        el.value = selected;
    } else {
        el.value = '';
    }
}

function resetFilters() {
    if (genState.isCalculating) {
        showToast('拆解进行中，请稍候再重置', 'warning');
        return;
    }
    genState.location = '';
    genState.vehicleModel = '';
    genState.bomVersion = '';
    hideProgress();
    loadCascadeFilters().then(() => {
        renderPrepStats({
            weld_node_count: 0,
            breakdown_node_count: 0,
            approved_count: 0,
            ready: false,
            message: '',
        });
        validateReady();
    });
    loadCalcHistory(1);
}

async function loadCascadeFilters() {
    try {
        const params = {};
        if (genState.location) params.location = genState.location;
        if (genState.vehicleModel) params.vehicle_model = genState.vehicleModel;
        const res = await HttpClient.get(CASCADE_API, { params });
        const data = res.data || {};
        const locations = data.locations || [];
        const vehicleModels = data.vehicle_models || [];
        const bomVersions = data.bom_versions || [];

        if (genState.location && !locations.includes(genState.location)) {
            genState.location = '';
            genState.vehicleModel = '';
            genState.bomVersion = '';
        }
        if (genState.vehicleModel && !vehicleModels.includes(genState.vehicleModel)) {
            genState.vehicleModel = '';
            genState.bomVersion = '';
        }
        if (genState.bomVersion && !bomVersions.includes(genState.bomVersion)) {
            genState.bomVersion = '';
        }

        if (!genState.location && locations.length === 1) {
            genState.location = locations[0];
            return loadCascadeFilters();
        }
        if (genState.location && !genState.vehicleModel && vehicleModels.length === 1) {
            genState.vehicleModel = vehicleModels[0];
            return loadCascadeFilters();
        }
        if (
            genState.location
            && genState.vehicleModel
            && !genState.bomVersion
            && bomVersions.length === 1
        ) {
            genState.bomVersion = bomVersions[0];
        }

        fillSelect('wpbGenLocation', locations, genState.location);
        fillSelect('wpbGenModel', vehicleModels, genState.vehicleModel);
        fillSelect('wpbGenVersion', bomVersions, genState.bomVersion);
    } catch (error) {
        console.error('加载 BOM 级联筛选失败', error);
    }
}

async function loadPrepStats() {
    const location = genState.location || val('wpbGenLocation');
    const vehicleModel = genState.vehicleModel || val('wpbGenModel');
    const bomVersion = genState.bomVersion || val('wpbGenVersion');
    if (!location || !vehicleModel || !bomVersion) {
        renderPrepStats({
            weld_node_count: 0,
            breakdown_node_count: 0,
            approved_count: 0,
            ready: false,
            message: '请选定基地 / 项目 / 版本',
        });
        validateReady();
        return;
    }
    try {
        const res = await HttpClient.get(PREP_STATS_API, {
            params: {
                location,
                vehicle_model: vehicleModel,
                bom_version: bomVersion,
            },
        });
        renderPrepStats(res.data || {});
        validateReady();
    } catch (error) {
        console.error('加载拆解就绪统计失败', error);
        renderPrepStats({
            weld_node_count: 0,
            breakdown_node_count: 0,
            approved_count: 0,
            ready: false,
            message: '统计加载失败',
        });
        validateReady();
    }
}

function renderPrepStats(stats) {
    genState.stats = {
        weld_node_count: Number(stats.weld_node_count) || 0,
        breakdown_node_count: Number(stats.breakdown_node_count) || 0,
        approved_count: Number(stats.approved_count) || 0,
        ready: Boolean(stats.ready),
        message: stats.message || '',
    };
    setCountHtml('cntWeldNodes', genState.stats.weld_node_count, '条');
    setCountHtml('cntBreakdownNodes', genState.stats.breakdown_node_count, '条');
    setCountHtml('cntApproved', genState.stats.approved_count, '条');
    const banner = document.getElementById('dataReadyErrorBanner');
    if (banner && genState.stats.message && !genState.stats.ready) {
        banner.textContent = `提示：${genState.stats.message}`;
    }
}

function setCountHtml(id, count, unit) {
    const el = document.getElementById(id);
    if (!el) return;
    const display = Number.isFinite(count) ? Number(count).toLocaleString('zh-CN') : '-';
    el.innerHTML = `${display} <span class="text-[9px] font-normal text-ink-faint">${unit}</span>`;
}

function validateReady() {
    const startBtn = document.getElementById('wpbGenSubmitBtn');
    const errorBanner = document.getElementById('dataReadyErrorBanner');
    if (!startBtn || genState.isCalculating) return;

    const location = genState.location || val('wpbGenLocation');
    const vehicleModel = genState.vehicleModel || val('wpbGenModel');
    const bomVersion = genState.bomVersion || val('wpbGenVersion');
    const scopeReady = Boolean(location && vehicleModel && bomVersion);
    const isReady = scopeReady && genState.stats.ready;

    startBtn.disabled = !isReady;
    if (isReady) {
        errorBanner?.classList.add('hidden');
    } else {
        errorBanner?.classList.remove('hidden');
    }
}

async function loadCalcHistory(page = genState.history.page) {
    const body = document.getElementById('calcHistoryBody');
    if (!body) return;
    body.innerHTML = `<tr><td colspan="11" class="py-8 text-center text-ink-faint">加载中..</td></tr>`;
    try {
        const response = await HttpClient.get(LOGS_API, {
            params: { page, size: genState.history.size },
        });
        const pageData = response.data || {};
        const items = Array.isArray(pageData.items) ? pageData.items : [];
        genState.history.page = pageData.page || page;
        genState.history.total = pageData.total || 0;
        genState.history.totalPages = pageData.total_pages || 1;
        genState.history.items = items;
        renderHistoryRows(items);

        const totalEl = document.getElementById('calcHistoryTotal');
        if (totalEl) totalEl.textContent = `全${genState.history.total} 条`;
        paintPagination('calcHistoryPagination', 
                genState.history.page,
                genState.history.totalPages,
            );
    } catch (error) {
        console.error('加载拆解历史失败:', error);
        body.innerHTML = `<tr><td colspan="11" class="py-8 text-center text-danger">加载失败</td></tr>`;
    }
}

function renderHistoryRows(items) {
    const body = document.getElementById('calcHistoryBody');
    if (!body) return;
    if (!items.length) {
        body.innerHTML = `<tr><td colspan="11" class="py-8 text-center text-ink-faint">暂无拆解记录</td></tr>`;
        return;
    }

    body.innerHTML = items.map((item) => {
        const status = STATUS_META[item.status] || STATUS_META.failed;
        const createdBy = item.created_by || item.operator_name || '-';
        const isProcessing = item.status === 'processing';
        return `
            <tr class="hover:bg-ink/[0.02] transition-colors text-ink-muted">
                <td class="py-2 px-2 font-mono text-ink-dim whitespace-nowrap">${esc(formatDateTime(item.started_at))}</td>
                <td class="py-2 px-2 font-mono text-ink-dim whitespace-nowrap">${esc(formatDateTime(item.finished_at))}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-ink-dim whitespace-nowrap">${esc(formatDurationSeconds(item))}</td>
                <td class="py-2 px-2 text-ink-muted whitespace-nowrap">${esc(createdBy)}</td>
                <td class="py-2 px-2 text-ink-muted whitespace-nowrap">${esc(item.location || '-')}</td>
                <td class="py-2 px-2 text-ink-muted whitespace-nowrap">${esc(item.vehicle_model || '-')}</td>
                <td class="py-2 px-2 font-mono text-ink-muted whitespace-nowrap">${esc(item.bom_version || '-')}</td>
                <td class="py-2 px-2 text-center text-[9px] ${status.className}">${status.label}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-ink-dim">${fmtInt(item.node_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-ink-dim">${fmtInt(item.line_count)}</td>
                <td class="py-2 px-2 text-right whitespace-nowrap">
                    ${isProcessing ? `
                    <span class="text-[9px] text-ink-faint mr-2">进行中</span>
                    ` : `
                    <button type="button" class="calc-view-process-btn text-[9px] text-ink-dim hover:text-ink mr-2"
                            data-log-id="${esc(item.id)}">过程</button>
                    ${item.status === 'failed' ? '' : `
                    <button type="button" class="calc-view-result-btn text-[9px] text-ink-dim hover:text-ink mr-2"
                            data-location="${esc(item.location || '')}"
                            data-model="${esc(item.vehicle_model || '')}">结果</button>
                    `}
                    `}
                    ${genState.canDeleteLog ? `
                    <button type="button" class="calc-delete-log-btn text-[9px] text-ink-dim hover:text-danger"
                            data-log-id="${esc(item.id)}"
                            title="含拆解中：删除可释放锁">删除</button>` : ''}
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
            if (btn.dataset.location) qs.set('location', btn.dataset.location);
            if (btn.dataset.model) qs.set('vehicle_model', btn.dataset.model);
            const suffix = qs.toString() ? `?${qs.toString()}` : '';
            window.location.hash = `/bom-welding-process-breakdown-list${suffix}`;
        });
    });
    body.querySelectorAll('.calc-delete-log-btn').forEach((btn) => {
        btn.addEventListener('click', () => deleteCalcLog(Number(btn.dataset.logId)));
    });
}

async function deleteAllGenerateLogs() {
    if (!genState.canDeleteLog) return;
    if (!window.confirm('确定删除全部拆解历史？仅删除日志，不影响已落库的拆解数据。拆解中的记录删除后将释放锁。')) {
        return;
    }
    try {
        const res = await HttpClient.delete(LOGS_API);
        const count = res.data?.deleted_count ?? 0;
        showToast(`已删除 ${count} 条`, 'success');
        loadCalcHistory(1);
    } catch (error) {
        console.error('清空拆解历史失败:', error);
    }
}

async function deleteCalcLog(logId) {
    if (!logId || !genState.canDeleteLog) return;
    if (!window.confirm('确定删除这条拆解历史？拆解中的记录删除后将释放锁；仅删除日志，不影响已落库的拆解数据。')) {
        return;
    }
    try {
        await HttpClient.delete(`${LOGS_API}/${logId}`);
        showToast('删除成功', 'success');
        const nextPage =
            genState.history.items.length === 1 && genState.history.page > 1
                ? genState.history.page - 1
                : genState.history.page;
        loadCalcHistory(nextPage);
    } catch (error) {
        console.error('删除拆解历史失败:', error);
    }
}

async function openProcessDrawer(logId) {
    if (!logId) return;
    try {
        const response = await HttpClient.get(`${LOGS_API}/${logId}`);
        showProcessDrawer(response.data || {});
    } catch (error) {
        console.error('加载拆解过程失败:', error);
    }
}

function showProcessDrawer(log) {
    closeProcessDrawer();
    const status = STATUS_META[log.status] || STATUS_META.failed;
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
                拆解过程 · ${esc(log.location || '-')} · ${esc(log.vehicle_model || '-')} · ${esc(log.bom_version || '-')}
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
            <div>批次 <span class="font-mono text-ink-muted">${esc(log.calc_batch_id || '-')}</span></div>
            <div>${esc(formatTimingLine(log, formatDateTime) || '-')}</div>
            <div>汇总：主表 ${fmtInt(log.node_count)} · 明细 ${fmtInt(log.line_count)}</div>
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

async function isScopeProcessing(location, vehicleModel, bomVersion) {
    try {
        const response = await HttpClient.get(LOGS_API, {
            params: {
                location,
                vehicle_model: vehicleModel,
                bom_version: bomVersion,
                page: 1,
                size: 20,
            },
        });
        const items = response.data?.items || [];
        return items.some((item) => item.status === 'processing');
    } catch (error) {
        console.error('检查拆解锁失败:', error);
        return false;
    }
}

async function startGenerate() {
    if (!genState.canGenerate || genState.isCalculating) return;

    const location = genState.location || val('wpbGenLocation');
    const vehicleModel = genState.vehicleModel || val('wpbGenModel');
    const bomVersion = genState.bomVersion || val('wpbGenVersion');
    if (!location || !vehicleModel || !bomVersion) {
        showToast('请从级联下拉选定基地、项目、版本', 'warning');
        return;
    }
    if (!genState.stats.ready) {
        showToast(genState.stats.message || '当前条件不可拆解', 'warning');
        return;
    }
    if (await isScopeProcessing(location, vehicleModel, bomVersion)) {
        showToast(DUPLICATE_SCOPE_MESSAGE, 'warning');
        loadCalcHistory(1);
        return;
    }

    setCalculating(true);
    showProgress(0, '已提交拆解队列');

    try {
        const response = await HttpClient.post(GENERATE_API, {
            location,
            vehicle_model: vehicleModel,
            bom_version: bomVersion,
        });
        const taskId = response.data?.task_id;
        if (!taskId) throw new Error('未返回任务 ID');
        loadCalcHistory(1);
        startPolling(taskId);
    } catch (error) {
        console.error('提交拆解失败:', error);
        stopPolling();
        hideProgress();
        genState.activeTaskId = null;
        setCalculating(false);
        loadCalcHistory(1);
    }
}

function showProgress(progress = 0, msg = '已提交拆解队列') {
    document.getElementById('calcProgressPanel')?.classList.remove('hidden');
    updateProgress(progress, msg);
}

function hideProgress() {
    document.getElementById('calcProgressPanel')?.classList.add('hidden');
    updateProgress(0, '已提交拆解队列');
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
            titleEl.textContent = '拆解完成';
            titleEl.className = 'text-xs font-medium text-ok truncate mb-0';
        } else if (status === 'failed') {
            titleEl.textContent = '拆解失败';
            titleEl.className = 'text-xs font-medium text-danger truncate mb-0';
        } else {
            titleEl.textContent = '正在拆解焊接工艺...';
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
    if (genState.pollTimer) {
        clearInterval(genState.pollTimer);
        genState.pollTimer = null;
    }
    genState.pollInFlight = false;
}

async function fetchTaskProgress(taskId) {
    const response = await HttpClient.get(`${TASK_API}/${encodeURIComponent(taskId)}`);
    return response.data;
}

function startPolling(taskId) {
    stopPolling();
    genState.activeTaskId = taskId;

    const tick = async () => {
        if (genState.pollInFlight) return;
        genState.pollInFlight = true;
        try {
            const data = await fetchTaskProgress(taskId);
            const status = data?.status || 'running';
            const progress = data?.progress ?? 0;
            const msg = data?.msg || '';
            updateProgress(progress, msg, status);

            if (status === 'completed') {
                stopPolling();
                const result = data?.result || {};
                showToast(
                    result.message
                        || `拆解完成：主表 ${fmtInt(result.node_count)} · 明细 ${fmtInt(result.line_count)}`,
                    'success',
                );
                genState.activeTaskId = null;
                setCalculating(false);
                loadPrepStats();
                loadCalcHistory(1);
                if (result.log_id) openProcessDrawer(result.log_id);
                setTimeout(() => {
                    if (!genState.isCalculating) hideProgress();
                }, 1800);
                return;
            }

            if (status === 'failed') {
                stopPolling();
                const result = data?.result || null;
                showToast(msg || '拆解失败', 'error');
                genState.activeTaskId = null;
                setCalculating(false);
                loadPrepStats();
                loadCalcHistory(1);
                if (result?.log_id) openProcessDrawer(result.log_id);
            }
        } catch (error) {
            stopPolling();
            showToast(error.message || '查询进度失败', 'error');
            genState.activeTaskId = null;
            setCalculating(false);
            loadCalcHistory(1);
        } finally {
            genState.pollInFlight = false;
        }
    };

    tick();
    genState.pollTimer = setInterval(tick, POLL_INTERVAL_MS);
}

function setCalculating(isCalculating) {
    genState.isCalculating = isCalculating;
    const startBtn = document.getElementById('wpbGenSubmitBtn');
    ['wpbGenLocation', 'wpbGenModel', 'wpbGenVersion', 'wpbGenResetBtn'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.disabled = isCalculating;
    });
    if (!startBtn) return;
    if (isCalculating) {
        startBtn.setAttribute('disabled', 'true');
        startBtn.classList.add('opacity-50', 'pointer-events-none');
        startBtn.textContent = '拆解中..';
    } else {
        startBtn.removeAttribute('disabled');
        startBtn.classList.remove('opacity-50', 'pointer-events-none');
        startBtn.textContent = '开始拆解';
        validateReady();
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
    render: weldingProcessBreakdownGenerateTemplate,
    init: () => init(),
    destroy: () => destroy(),
};
