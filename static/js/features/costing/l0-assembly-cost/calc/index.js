/**
 * 成品核价计算页
 */

import {
    l0AssemblyCostCalcTemplate,
    renderCalcHistoryPagination,
} from './template.js?v=1';
import {
    DEFAULT_PAGE_SIZE,
    bindPageSizeSelect,
} from '../../../../page-size.js?v=2';

const API_BASE = '/api/costing/l0-assembly-costs';
const CASCADE_API = '/api/bom/filters/cascade';
const CALC_API = `${API_BASE}/calc`;
const CALC_READY_API = `${API_BASE}/calc/ready`;
const CALC_TASK_API = `${API_BASE}/calc/tasks`;
const CALC_LOGS_API = `${API_BASE}/calc/logs`;
const YEARS_API = `${API_BASE}/filters/years`;
const POLL_INTERVAL_MS = 1500;

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
    ready: {
        l0_count: 0,
        stamping_price_count: 0,
        annual_price_count: 0,
        welding_fee_count: 0,
        packaging_fee_count: 0,
        ready: false,
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
    bindPageSizeSelect('lacCalcHistoryPageSize', {
        getSize: () => calcState.history.size,
        setSize: (size) => {
            calcState.history.size = size;
        },
        onChange: () => loadCalcHistory(1),
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
    calcState.canRun = canFn('op:l0-assembly-cost-calc:run');
    calcState.canDelete = canFn('op:l0-assembly-cost-calc:delete');
    if (!calcState.canRun) {
        document.getElementById('lacStartCalcBtn')?.classList.add('hidden');
    }
}

function bindEvents() {
    document.getElementById('lacCalcResetBtn')?.addEventListener('click', resetFilters);
    document.getElementById('lacCalcYear')?.addEventListener('change', () => loadCalcReady());
    document.getElementById('lacCalcMonth')?.addEventListener('change', () => loadCalcReady());
    document.getElementById('lacCalcLocation')?.addEventListener('change', () => {
        resetDependentFilters(['lacCalcVehicleModel', 'lacCalcBomVersion']);
        loadCascadeFilters().then(() => loadCalcReady());
    });
    document.getElementById('lacCalcVehicleModel')?.addEventListener('change', () => {
        resetDependentFilters(['lacCalcBomVersion']);
        loadCascadeFilters().then(() => loadCalcReady());
    });
    document.getElementById('lacCalcBomVersion')?.addEventListener('change', () => loadCalcReady());
    document.getElementById('lacStartCalcBtn')?.addEventListener('click', startCalculation);
    document.getElementById('lacCalcHistoryRefreshBtn')?.addEventListener('click', () => loadCalcHistory(1));
    document.getElementById('lacCalcHistoryPagination')?.addEventListener('click', (event) => {
        const btn = event.target.closest('.lac-calc-history-page-btn');
        if (btn && !btn.disabled) {
            const page = parseInt(btn.dataset.page, 10);
            if (page) loadCalcHistory(page);
        }
    });
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
            window.location.hash = `/l0-assembly-cost${q}`;
        }
    });
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

function fillSelect(id, values = [], preferredValue = null) {
    const select = document.getElementById(id);
    if (!select) return;
    const current = preferredValue != null ? preferredValue : select.value;
    const emptyLabel = select.querySelector('option[value=""]')?.textContent || '请选择';
    select.innerHTML =
        `<option value="">${emptyLabel}</option>` +
        values.map((value) => {
            const text = String(value);
            return `<option value="${esc(text)}"${text === String(current) ? ' selected' : ''}>${esc(text)}</option>`;
        }).join('');
}

function fillMonthOptions() {
    const months = Array.from({ length: 12 }, (_, i) => String(i + 1));
    const currentMonth = String(new Date().getMonth() + 1);
    fillSelect('lacCalcMonth', months, currentMonth);
}

async function loadYearOptions() {
    try {
        const res = await HttpClient.get(YEARS_API);
        const years = Array.isArray(res.data) ? res.data.slice() : [];
        const currentYear = new Date().getFullYear();
        // 仅当上游尚无任何年度时，才回退当前自然年（就绪检查会提示缺数据）
        if (!years.length) years.push(currentYear);
        const preferred = years.includes(currentYear) ? currentYear : years[0];
        fillSelect('lacCalcYear', years, String(preferred));
    } catch (error) {
        const currentYear = new Date().getFullYear();
        fillSelect('lacCalcYear', [currentYear], String(currentYear));
    }
}

async function loadCascadeFilters() {
    try {
        const params = {
            location: val('lacCalcLocation'),
            vehicle_model: val('lacCalcVehicleModel'),
        };
        const res = await HttpClient.get(CASCADE_API, { params });
        const filters = res.data || {};
        fillSelect('lacCalcLocation', filters.locations || []);
        fillSelect('lacCalcVehicleModel', filters.vehicle_models || []);
        fillSelect('lacCalcBomVersion', filters.bom_versions || []);
    } catch (error) {
        console.error('加载 BOM 级联筛选失败:', error);
    }
}

function resetFilters() {
    if (calcState.isCalculating) {
        showToast('计算进行中，请稍候再重置', 'warning');
        return;
    }
    ['lacCalcLocation', 'lacCalcVehicleModel', 'lacCalcBomVersion'].forEach((id) => {
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
        bom_version: val('lacCalcBomVersion'),
    };
}

async function loadCalcReady() {
    const scope = getScope();
    if (!scope.year || !scope.month || !scope.location || !scope.vehicle_model || !scope.bom_version) {
        calcState.ready = {
            l0_count: 0,
            stamping_price_count: 0,
            annual_price_count: 0,
            welding_fee_count: 0,
            packaging_fee_count: 0,
            ready: false,
        };
        setReadyCounts(calcState.ready);
        validateDataPreparation();
        return;
    }
    try {
        const res = await HttpClient.get(CALC_READY_API, { params: scope });
        const data = res.data || {};
        calcState.ready = {
            l0_count: Number(data.l0_count) || 0,
            stamping_price_count: Number(data.stamping_price_count) || 0,
            annual_price_count: Number(data.annual_price_count) || 0,
            welding_fee_count: Number(data.welding_fee_count) || 0,
            packaging_fee_count: Number(data.packaging_fee_count) || 0,
            ready: Boolean(data.ready),
            message: data.message || null,
        };
        setReadyCounts(calcState.ready);
        validateDataPreparation();
    } catch (error) {
        console.error('加载计算就绪统计失败:', error);
        calcState.ready = {
            l0_count: 0,
            stamping_price_count: 0,
            annual_price_count: 0,
            welding_fee_count: 0,
            packaging_fee_count: 0,
            ready: false,
        };
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
        scope.year && scope.month && scope.location && scope.vehicle_model && scope.bom_version,
    );
    const isReady = isScopeSelected && calcState.ready.ready;
    startBtn.disabled = !isReady;
    if (isReady) errorBanner?.classList.add('hidden');
    else errorBanner?.classList.remove('hidden');
}

function setReadyCounts(ready) {
    setCountHtml('lacCntL0', ready.l0_count, '条');
    setCountHtml('lacCntStamping', ready.stamping_price_count, '条');
    setCountHtml('lacCntAnnual', ready.annual_price_count, '条');
    setCountHtml('lacCntWelding', ready.welding_fee_count, '条');
    setCountHtml('lacCntPackaging', ready.packaging_fee_count, '条');
}

function setCountHtml(id, count, unit) {
    const el = document.getElementById(id);
    if (!el) return;
    const display = Number.isFinite(count) ? Number(count).toLocaleString('zh-CN') : '-';
    el.innerHTML = `${display} <span class="text-[9px] font-normal text-[#555]">${unit}</span>`;
}

async function loadCalcHistory(page = calcState.history.page) {
    const body = document.getElementById('lacCalcHistoryBody');
    if (!body) return;
    body.innerHTML = `<tr><td colspan="13" class="py-8 text-center text-[#555]">加载中..</td></tr>`;
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
        const pagination = document.getElementById('lacCalcHistoryPagination');
        if (pagination) {
            pagination.innerHTML = renderCalcHistoryPagination(
                calcState.history.page,
                calcState.history.totalPages,
            );
        }
    } catch (error) {
        body.innerHTML = `<tr><td colspan="13" class="py-8 text-center text-[#ef5350]">${esc(error.message || '加载失败')}</td></tr>`;
    }
}

function renderHistoryRows(items) {
    const body = document.getElementById('lacCalcHistoryBody');
    if (!body) return;
    if (!items.length) {
        body.innerHTML = `<tr><td colspan="13" class="py-8 text-center text-[#555]">暂无计算历史</td></tr>`;
        return;
    }
    body.innerHTML = items.map((row) => {
        const meta = STATUS_META[row.status] || { label: row.status, className: 'text-[#9e9e9e]' };
        const started = row.started_at ? String(row.started_at).replace('T', ' ').slice(0, 19) : '-';
        const query = `?year=${encodeURIComponent(row.year)}&month=${encodeURIComponent(row.month)}&location=${encodeURIComponent(row.location)}&vehicle_model=${encodeURIComponent(row.vehicle_model)}&bom_version=${encodeURIComponent(row.bom_version)}`;
        return `
            <tr class="hover:bg-[#1a1a1a]">
                <td class="py-2 px-2 font-mono text-[#8E8E93] whitespace-nowrap">${esc(started)}</td>
                <td class="py-2 px-2 text-[#c0c0c0]">${esc(row.operator_name || '-')}</td>
                <td class="py-2 px-2 font-mono">${esc(`${row.year}-${String(row.month).padStart(2, '0')}`)}</td>
                <td class="py-2 px-2">${esc(row.location)}</td>
                <td class="py-2 px-2">${esc(row.vehicle_model)}</td>
                <td class="py-2 px-2 font-mono">${esc(row.bom_version)}</td>
                <td class="py-2 px-2 text-center ${meta.className}">${esc(meta.label)}</td>
                <td class="py-2 px-2 text-right font-mono">${esc(row.l0_total)}</td>
                <td class="py-2 px-2 text-right font-mono text-[#66bb6a]">${esc(row.ok_count)}</td>
                <td class="py-2 px-2 text-right font-mono text-[#ffb74d]">${esc(row.partial_count)}</td>
                <td class="py-2 px-2 text-right font-mono text-[#ef5350]">${esc(row.failed_count)}</td>
                <td class="py-2 px-2 text-right font-mono">${esc(row.skipped_approved_count)}</td>
                <td class="py-2 px-2 text-right whitespace-nowrap">
                    <button data-action="jump-list" data-query="${esc(query)}"
                            class="text-[10px] text-[#9e9e9e] hover:text-white mr-2">结果</button>
                    ${calcState.canDelete ? `<button data-action="delete-log" data-id="${row.id}" class="text-[10px] text-[#ef5350] hover:text-[#ff8a80]" title="含计算中：删除可释放锁">删除</button>` : ''}
                </td>
            </tr>
        `;
    }).join('');
}

async function deleteCalcLog(logId) {
    if (!calcState.canDelete) return;
    if (!window.confirm('确认删除该计算日志？计算中的记录删除后将释放锁，可重新提交。')) return;
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
    if (!scope.year || !scope.month || !scope.location || !scope.vehicle_model || !scope.bom_version) {
        showToast('须选定年度、月份、基地、项目、BOM 版本', 'warning');
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

export const pageConfig = {
    render: l0AssemblyCostCalcTemplate,
    init,
    destroy,
};
