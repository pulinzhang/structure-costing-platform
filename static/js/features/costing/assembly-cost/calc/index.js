/**
 * 总成核价计算页
 */

import {
    assemblyCostCalcTemplate,
} from './template.js?v=17';
import {
    DEFAULT_PAGE_SIZE,
    bindPagination,
    paintPagination,
} from '../../../../ui/page-size.js?v=6';
import {
    formatDurationSeconds,
} from '../../../../domain/duration.js?v=3';
import { opsIconButtonHtml } from '../../../../ui/hud-table.js?v=2';

const API_BASE = '/api/costing/assembly-costs';
const CASCADE_API = '/api/bom/filters/cascade';
const CALC_API = `${API_BASE}/calc`;
const CALC_READY_API = `${API_BASE}/calc/ready`;
const CALC_TASK_API = `${API_BASE}/calc/tasks`;
const CALC_LOGS_API = `${API_BASE}/calc/logs`;
const YEARS_API = `${API_BASE}/filters/years`;
const POLL_INTERVAL_MS = 1500;

function emptyReady(message = null) {
    return {
        tree_root_count: 0,
        subject_count: 0,
        procurement_object_count: 0,
        stamping_price_count: 0,
        annual_price_count: 0,
        welding_fee_count: 0,
        packaging_fee_count: 0,
        stamping_complete: null,
        welding_calc_complete: null,
        ready: false,
        message,
    };
}

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
    ready: emptyReady(),
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
        selectId: 'lacCalcHistoryPageSize',
        buttonsId: 'lacCalcHistoryPagination',
        getSize: () => calcState.history.size,
        setSize: (size) => {
            calcState.history.size = size;
        },
        onPage: (page) => loadCalcHistory(page),
    });
    applyPermissionUi();
    fillMonthOptions();
    loadYearOptions().then(() => {
        loadCascadeFilters();
        loadCalcReady();
        loadCalcHistory(1);
    });
    hideProgress();
}

function destroy() {
    stopPolling();
}

function applyPermissionUi() {
    const canFn = typeof can === 'function' ? can : () => true;
    calcState.canRun = canFn('op:assembly-cost-calc:run');
    calcState.canDelete = canFn('op:assembly-cost-calc:delete');
    if (!calcState.canRun) {
        document.getElementById('lacStartCalcBtn')?.classList.add('hidden');
    }
    document.getElementById('lacCalcHistoryDeleteAllBtn')?.classList.toggle('hidden', !calcState.canDelete);
}

function bindEvents() {
    document.getElementById('lacCalcResetBtn')?.addEventListener('click', resetFilters);
    document.getElementById('lacCalcYear')?.addEventListener('change', () => {
        loadCascadeFilters().then(() => loadCalcReady());
    });
    document.getElementById('lacCalcMonth')?.addEventListener('change', () => {
        loadCascadeFilters().then(() => loadCalcReady());
    });
    document.getElementById('lacCalcLocation')?.addEventListener('change', () => {
        resetDependentFilters(['lacCalcVehicleModel']);
        loadCascadeFilters().then(() => loadCalcReady());
    });
    document.getElementById('lacCalcVehicleModel')?.addEventListener('change', () => {
        loadCascadeFilters().then(() => loadCalcReady());
    });
    document.getElementById('lacStartCalcBtn')?.addEventListener('click', startCalculation);
    document.getElementById('lacCalcHistoryRefreshBtn')?.addEventListener('click', () => loadCalcHistory(1));
    document.getElementById('lacCalcHistoryDeleteAllBtn')?.addEventListener('click', () => deleteAllCalcLogs());
    document.getElementById('lacCalcHistoryBody')?.addEventListener('click', (event) => {
        const delBtn = event.target.closest('[data-action="delete-log"]');
        if (delBtn) {
            const logId = parseInt(delBtn.dataset.id, 10);
            if (logId) deleteCalcLog(logId);
            return;
        }
        const jumpBtn = event.target.closest('[data-action="jump-list"]');
        if (jumpBtn) {
            const q = jumpBtn.dataset.query || '';
            window.location.hash = `/assembly-cost${q}`;
            return;
        }
        const reportBtn = event.target.closest('[data-action="open-report"]');
        if (reportBtn) {
            const logId = parseInt(reportBtn.dataset.id, 10);
            if (logId) openCalcReport(logId);
        }
    });
}

function openCalcReport(logId) {
    const url = `/assembly-cost-calc-report?log_id=${encodeURIComponent(logId)}`;
    const tab = window.open(url, '_blank', 'noopener');
    if (!tab) showToast('无法打开新页签，请允许弹窗', 'warning');
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

function fillMonthOptions() {
    const months = Array.from({ length: 12 }, (_, i) => String(i + 1));
    const currentMonth = String(new Date().getMonth() + 1);
    fillSelect('lacCalcMonth', months, currentMonth, fmtMonth);
}

async function loadYearOptions() {
    try {
        const res = await HttpClient.get(YEARS_API);
        const years = Array.isArray(res.data) ? res.data.slice() : [];
        const currentYear = new Date().getFullYear();
        // 仅当上游尚无任何年度时，才回退当前自然年（就绪检查会提示缺数据）
        if (!years.length) years.push(currentYear);
        const preferred = years.includes(currentYear) ? currentYear : years[0];
        fillSelect('lacCalcYear', years, String(preferred), fmtYear);
    } catch (error) {
        const currentYear = new Date().getFullYear();
        fillSelect('lacCalcYear', [currentYear], String(currentYear), fmtYear);
    }
}

async function loadCascadeFilters() {
    try {
        const params = {
            location: val('lacCalcLocation'),
            vehicle_model: val('lacCalcVehicleModel'),
        };
        const year = parseInt(val('lacCalcYear'), 10);
        const month = parseInt(val('lacCalcMonth'), 10);
        if (Number.isFinite(year)) params.year = year;
        if (Number.isFinite(month)) params.month = month;
        const res = await HttpClient.get(CASCADE_API, { params });
        const filters = res.data || {};
        fillSelect('lacCalcLocation', filters.locations || []);
        fillSelect('lacCalcVehicleModel', filters.vehicle_models || []);
    } catch (error) {
        console.error('加载 BOM 级联筛选失败:', error);
    }
}

function resetFilters() {
    if (calcState.isCalculating) {
        showToast('计算进行中，请稍候再重置', 'warning');
        return;
    }
    ['lacCalcLocation', 'lacCalcVehicleModel'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    hideProgress();
    loadYearOptions().then(() => {
        fillMonthOptions();
        loadCascadeFilters();
        loadCalcReady();
        loadCalcHistory(1);
    });
}

function getScope() {
    const year = parseInt(val('lacCalcYear'), 10);
    const month = parseInt(val('lacCalcMonth'), 10);
    return {
        year: Number.isFinite(year) ? year : null,
        month: Number.isFinite(month) ? month : null,
        location: val('lacCalcLocation'),
        vehicle_model: val('lacCalcVehicleModel'),
    };
}

async function loadCalcReady() {
    const scope = getScope();
    if (!scope.year || !scope.month || !scope.location || !scope.vehicle_model) {
        calcState.ready = emptyReady();
        setReadyCounts(calcState.ready);
        validateDataPreparation();
        return;
    }
    try {
        const res = await HttpClient.get(CALC_READY_API, { params: scope });
        const data = res.data || {};
        calcState.ready = {
            tree_root_count: Number(data.tree_root_count) || 0,
            subject_count: Number(data.subject_count) || 0,
            procurement_object_count: Number(data.procurement_object_count) || 0,
            stamping_price_count: Number(data.stamping_price_count) || 0,
            annual_price_count: Number(data.annual_price_count) || 0,
            welding_fee_count: Number(data.welding_fee_count) || 0,
            packaging_fee_count: Number(data.packaging_fee_count) || 0,
            stamping_complete: Boolean(data.stamping_complete),
            welding_calc_complete: Boolean(data.welding_calc_complete),
            ready: Boolean(data.ready),
            message: data.message || null,
        };
        setReadyCounts(calcState.ready);
        validateDataPreparation();
    } catch (error) {
        console.error('加载计算就绪统计失败:', error);
        calcState.ready = emptyReady(error.message || '就绪统计加载失败');
        setReadyCounts(calcState.ready);
        validateDataPreparation();
    }
}

function validateDataPreparation() {
    const startBtn = document.getElementById('lacStartCalcBtn');
    const errorBanner = document.getElementById('lacDataReadyErrorBanner');
    if (!startBtn || calcState.isCalculating) return;
    const scope = getScope();
    const isScopeSelected = Boolean(
        scope.year && scope.month && scope.location && scope.vehicle_model,
    );
    const isReady = isScopeSelected && calcState.ready.ready;
    startBtn.disabled = !isReady;
    let hint = null;
    if (!isScopeSelected) {
        hint = '须选定年度、月份、基地、项目。';
    } else if (calcState.ready.message) {
        hint = calcState.ready.message;
    }
    if (hint && errorBanner) {
        errorBanner.textContent = `提示：${hint}`;
        errorBanner.classList.remove('hidden');
    } else {
        errorBanner?.classList.add('hidden');
    }
}

function setReadyCounts(ready) {
    setCountHtml('lacCntTreeRoot', ready.tree_root_count, '条');
    setCountHtml('lacCntSubject', ready.subject_count, '条');
    setCountHtml('lacCntProcObj', ready.procurement_object_count, '条');
    setCountHtml('lacCntStamping', ready.stamping_price_count, '条', ready.stamping_complete);
    setCountHtml('lacCntAnnual', ready.annual_price_count, '条');
    setCountHtml('lacCntWelding', ready.welding_fee_count, '条', ready.welding_calc_complete);
    setCountHtml('lacCntPackaging', ready.packaging_fee_count, '条');
}

function setCountHtml(id, count, unit, isComplete) {
    const el = document.getElementById(id);
    if (!el) return;
    const display = Number.isFinite(count) ? Number(count).toLocaleString('zh-CN') : '-';
    const tone = isComplete === false ? 'text-warn' : 'text-ink';
    el.className = `text-xs font-mono font-bold ${tone}`;
    el.innerHTML = `${display} <span class="text-[9px] font-normal text-ink-faint">${unit}</span>`;
}

async function loadCalcHistory(page = calcState.history.page) {
    const body = document.getElementById('lacCalcHistoryBody');
    if (!body) return;
    body.innerHTML = `<tr><td colspan="15" class="py-8 text-center text-ink-faint">加载中..</td></tr>`;
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
        const totalEl = document.getElementById('lacCalcHistoryTotal');
        if (totalEl) totalEl.textContent = `共 ${calcState.history.total} 条`;
        paintPagination('lacCalcHistoryPagination', 
                calcState.history.page,
                calcState.history.totalPages,
            );
    } catch (error) {
        body.innerHTML = `<tr><td colspan="15" class="py-8 text-center text-danger">${esc(error.message || '加载失败')}</td></tr>`;
    }
}

function renderHistoryRows(items) {
    const body = document.getElementById('lacCalcHistoryBody');
    if (!body) return;
    if (!items.length) {
        body.innerHTML = `<tr><td colspan="15" class="py-8 text-center text-ink-faint">暂无计算历史</td></tr>`;
        return;
    }
    body.innerHTML = items.map((row) => {
        const meta = STATUS_META[row.status] || { label: row.status, className: 'text-ink-muted' };
        const query = `?year=${encodeURIComponent(row.year)}&month=${encodeURIComponent(row.month)}&location=${encodeURIComponent(row.location)}&vehicle_model=${encodeURIComponent(row.vehicle_model)}`;
        const versionLabel = row.bom_version ? String(row.bom_version) : '—';
        const reportBtn = opsIconButtonHtml({
            action: 'open-report',
            title: '报告',
            icon: window.svgIcon('file-earmark-text', 'w-3.5 h-3.5'),
            attrs: `data-id="${row.id}"`,
        });
        const resultBtn = opsIconButtonHtml({
            action: 'jump-list',
            title: '结果',
            icon: window.svgIcon('external-link', 'w-3.5 h-3.5'),
            attrs: `data-query="${esc(query)}"`,
        });
        const deleteBtn = calcState.canDelete ? opsIconButtonHtml({
            action: 'delete-log',
            danger: true,
            title: '有正在计算的：删掉后就可以重新算',
            icon: window.svgIcon('trash', 'w-3.5 h-3.5'),
            attrs: `data-id="${row.id}"`,
        }) : '';
        return `
            <tr class="group hover:bg-app-surface">
                <td class="py-2 px-2 font-mono text-ink-dim whitespace-nowrap">${esc(formatDateTime(row.started_at))}</td>
                <td class="py-2 px-2 font-mono text-ink-dim whitespace-nowrap">${esc(formatDateTime(row.finished_at))}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-ink-dim whitespace-nowrap">${esc(formatDurationSeconds(row))}</td>
                <td class="py-2 px-2 text-ink">${esc(row.operator_name || '-')}</td>
                <td class="py-2 px-2 font-mono">${esc(fmtPeriod(row.year, row.month))}</td>
                <td class="py-2 px-2">${esc(row.location)}</td>
                <td class="py-2 px-2">${esc(row.vehicle_model)}</td>
                <td class="py-2 px-2 font-mono">${esc(versionLabel)}</td>
                <td class="py-2 px-2 text-center ${meta.className}">${esc(meta.label)}</td>
                <td class="py-2 px-2 text-right font-mono">${esc(row.subject_total)}</td>
                <td class="py-2 px-2 text-right font-mono text-ok">${esc(row.ok_count)}</td>
                <td class="py-2 px-2 text-right font-mono text-warn">${esc(row.partial_count)}</td>
                <td class="py-2 px-2 text-right font-mono text-danger">${esc(row.failed_count)}</td>
                <td class="py-2 px-2 text-right font-mono">${esc(row.skipped_approved_count)}</td>
                <td class="py-2 px-1 text-right whitespace-nowrap">
                    <div class="inline-flex items-center justify-end">${reportBtn}${resultBtn}${deleteBtn}</div>
                </td>
            </tr>
        `;
    }).join('');
}

async function deleteAllCalcLogs() {
    if (!calcState.canDelete) return;
    if (!await window.confirmAction('确定删除全部计算历史？只删记录，不影响已经算好的结果。正在计算的删掉之后就可以重新算。')) {
        return;
    }
    try {
        const res = await HttpClient.delete(CALC_LOGS_API);
        const count = res.data?.deleted_count ?? 0;
        showToast(`已删除 ${count} 条`, 'success');
        loadCalcHistory(1);
    } catch (error) {
        /* HttpClient 已 toast */
    }
}

async function deleteCalcLog(logId) {
    if (!calcState.canDelete) return;
    if (!await window.confirmAction('确定删除这条计算记录？正在计算的删掉之后就可以重新算。')) return;
    try {
        await HttpClient.delete(`${CALC_LOGS_API}/${logId}`);
        showToast('已删除计算日志', 'success');
        loadCalcHistory(calcState.history.page);
    } catch (error) {
        /* HttpClient 已 toast */
    }
}

async function startCalculation() {
    if (!calcState.canRun || calcState.isCalculating) return;
    const scope = getScope();
    if (!scope.year || !scope.month || !scope.location || !scope.vehicle_model) {
        showToast('须选定年度、月份、基地、项目', 'warning');
        return;
    }
    calcState.isCalculating = true;
    const startBtn = document.getElementById('lacStartCalcBtn');
    if (startBtn) startBtn.disabled = true;
    showProgress(1, '已提交计算队列');
    try {
        const res = await HttpClient.post(CALC_API, scope);
        const taskId = res.data?.task_id;
        if (!taskId) throw new Error('未返回任务 ID');
        calcState.activeTaskId = taskId;
        startPolling(taskId);
    } catch (error) {
        calcState.isCalculating = false;
        hideProgress();
        validateDataPreparation();
        if (error?.status !== 409) {
            /* toast already */
        }
    }
}

function startPolling(taskId) {
    stopPolling();
    calcState.pollTimer = setInterval(() => pollTask(taskId), POLL_INTERVAL_MS);
    pollTask(taskId);
}

function stopPolling() {
    if (calcState.pollTimer) {
        clearInterval(calcState.pollTimer);
        calcState.pollTimer = null;
    }
    calcState.pollInFlight = false;
}

async function pollTask(taskId) {
    if (calcState.pollInFlight) return;
    calcState.pollInFlight = true;
    try {
        const res = await HttpClient.get(`${CALC_TASK_API}/${taskId}`);
        const task = res.data || {};
        const progress = Number(task.progress) || 0;
        const message = task.message || '';
        showProgress(progress, message);
        if (task.status === 'completed' || task.status === 'failed') {
            stopPolling();
            calcState.isCalculating = false;
            calcState.activeTaskId = null;
            const spinner = document.getElementById('lacCalcProgressSpinner');
            if (spinner) spinner.classList.add('hidden');
            document.getElementById('lacCalcProgressTitle').textContent =
                task.status === 'completed' ? '计算完成' : '计算失败';
            validateDataPreparation();
            loadCalcHistory(1);
            if (task.status === 'completed') {
                showToast(message || '计算完成', 'success');
            }
        }
    } catch (error) {
        console.error('轮询任务失败:', error);
    } finally {
        calcState.pollInFlight = false;
    }
}

function showProgress(percent, message) {
    const panel = document.getElementById('lacCalcProgressPanel');
    panel?.classList.remove('hidden');
    const bar = document.getElementById('lacCalcProgressBar');
    const pct = document.getElementById('lacCalcProgressPercent');
    const msg = document.getElementById('lacCalcProgressMsg');
    const spinner = document.getElementById('lacCalcProgressSpinner');
    if (bar) bar.style.width = `${Math.max(0, Math.min(100, percent))}%`;
    if (pct) pct.textContent = `${Math.round(percent)}%`;
    if (msg) msg.textContent = message || '';
    spinner?.classList.remove('hidden');
}

function hideProgress() {
    document.getElementById('lacCalcProgressPanel')?.classList.add('hidden');
}

function formatDateTime(value) {
    if (!value) return '-';
    try {
        return String(value).replace('T', ' ').slice(0, 19);
    } catch (_) {
        return String(value);
    }
}

export const pageConfig = {
    render: assemblyCostCalcTemplate,
    init,
    destroy,
};
