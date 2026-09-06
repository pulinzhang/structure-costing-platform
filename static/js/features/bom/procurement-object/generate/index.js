/**
 * 采购对象清单生成页
 */

import {
    procurementObjectGenerateTemplate,
    renderPoGenHistoryPagination,
} from './template.js?v=4';
import {
    DEFAULT_PAGE_SIZE,
    bindPageSizeSelect,
} from '../../../../page-size.js?v=2';
import { SECTION_LABELS } from '../labels.js?v=2';

const API_BASE = '/api/bom/procurement-objects';
const CASCADE_API = '/api/bom/filters/cascade';
const GENERATE_API = `${API_BASE}/generate`;
const PREP_STATS_API = `${API_BASE}/generate/prep-stats`;
const LOGS_API = `${API_BASE}/generate/logs`;

const STATUS_META = {
    success: { label: '成功', className: 'text-[#66bb6a]' },
    failed: { label: '失败', className: 'text-[#ef5350]' },
};

const genState = {
    isGenerating: false,
    canGenerate: true,
    location: '',
    vehicleModel: '',
    bomVersion: '',
    stats: {
        node_count: 0,
        object_count: 0,
        other_leaf_count: 0,
        anomaly_count: 0,
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
    bindEvents();
    bindPageSizeSelect('poGenHistoryPageSize', {
        getSize: () => genState.history.size,
        setSize: (size) => {
            genState.history.size = size;
        },
        onChange: () => loadGenHistory(1),
    });
    applyPermissionUi();
    loadCascadeFilters().then(() => loadPrepStats());
    loadGenHistory();
    hideProgress();
}

function destroy() {
    closeProcessDrawer();
}

function applyPermissionUi() {
    const canFn = typeof window.can === 'function' ? window.can : () => true;
    genState.canGenerate = canFn('op:bom-procurement-object:generate');
    const btn = document.getElementById('poGenSubmitBtn');
    if (btn && !genState.canGenerate) btn.classList.add('hidden');
}

function bindEvents() {
    document.getElementById('poGenResetBtn')?.addEventListener('click', resetFilters);
    document.getElementById('poGenLocation')?.addEventListener('change', () => {
        genState.location = val('poGenLocation');
        genState.vehicleModel = '';
        genState.bomVersion = '';
        loadCascadeFilters().then(() => loadPrepStats());
    });
    document.getElementById('poGenModel')?.addEventListener('change', () => {
        genState.vehicleModel = val('poGenModel');
        genState.bomVersion = '';
        loadCascadeFilters().then(() => loadPrepStats());
    });
    document.getElementById('poGenVersion')?.addEventListener('change', () => {
        genState.bomVersion = val('poGenVersion');
        loadPrepStats();
    });
    document.getElementById('poGenSubmitBtn')?.addEventListener('click', startGenerate);
    document.getElementById('poGenHistoryRefreshBtn')?.addEventListener('click', () => loadGenHistory(1));
    document.getElementById('poGenHistoryPagination')?.addEventListener('click', (event) => {
        const btn = event.target.closest('.po-gen-history-page-btn');
        if (btn && !btn.disabled) {
            const page = parseInt(btn.dataset.page, 10);
            if (page) loadGenHistory(page);
        }
    });
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
    if (genState.isGenerating) {
        showToast('生成进行中，请稍候再重置', 'warning');
        return;
    }
    genState.location = '';
    genState.vehicleModel = '';
    genState.bomVersion = '';
    hideProgress();
    loadCascadeFilters().then(() => loadPrepStats());
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
        if (genState.location && genState.vehicleModel && !genState.bomVersion && bomVersions.length === 1) {
            genState.bomVersion = bomVersions[0];
        }
        fillSelect('poGenLocation', locations, genState.location);
        fillSelect('poGenModel', vehicleModels, genState.vehicleModel);
        fillSelect('poGenVersion', bomVersions, genState.bomVersion);
    } catch (error) {
        console.error('加载 BOM 级联筛选失败', error);
    }
}

async function loadPrepStats() {
    const location = genState.location || val('poGenLocation');
    const vehicleModel = genState.vehicleModel || val('poGenModel');
    const bomVersion = genState.bomVersion || val('poGenVersion');
    if (!location || !vehicleModel || !bomVersion) {
        renderPrepStats({
            node_count: 0,
            object_count: 0,
            other_leaf_count: 0,
            anomaly_count: 0,
            approved_count: 0,
            ready: false,
            message: '请选定基地 / 项目 / 版本',
        });
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
    } catch (error) {
        console.error('加载生成就绪统计失败', error);
        renderPrepStats({
            node_count: 0,
            object_count: 0,
            other_leaf_count: 0,
            anomaly_count: 0,
            approved_count: 0,
            ready: false,
            message: '统计加载失败',
        });
    }
}

function renderPrepStats(stats) {
    genState.stats = {
        node_count: Number(stats.node_count) || 0,
        object_count: Number(stats.object_count) || 0,
        other_leaf_count: Number(stats.other_leaf_count) || 0,
        anomaly_count: Number(stats.anomaly_count) || 0,
        approved_count: Number(stats.approved_count) || 0,
        ready: Boolean(stats.ready),
        message: stats.message || '',
    };
    setCountHtml('poCntNodes', genState.stats.node_count, '条');
    setCountHtml('poCntObjects', genState.stats.object_count, '条');
    setCountHtml('poCntOther', genState.stats.other_leaf_count, '条');
    setCountHtml('poCntAnomaly', genState.stats.anomaly_count, '条');
    setCountHtml('poCntApproved', genState.stats.approved_count, '条');
    validateReady();
}

function setCountHtml(id, count, unit) {
    const el = document.getElementById(id);
    if (!el) return;
    const display = Number.isFinite(count) ? Number(count).toLocaleString('zh-CN') : '-';
    el.innerHTML = `${display} <span class="text-[9px] font-normal text-[#555]">${unit}</span>`;
}

function validateReady() {
    const startBtn = document.getElementById('poGenSubmitBtn');
    const banner = document.getElementById('poGenReadyBanner');
    if (!startBtn || genState.isGenerating) return;
    const location = genState.location || val('poGenLocation');
    const vehicleModel = genState.vehicleModel || val('poGenModel');
    const bomVersion = genState.bomVersion || val('poGenVersion');
    const isReady = Boolean(location && vehicleModel && bomVersion) && genState.stats.ready && genState.canGenerate;
    startBtn.disabled = !isReady;
    if (banner) {
        if (genState.stats.message && !genState.stats.ready) {
            banner.textContent = `提示：${genState.stats.message}`;
            banner.classList.remove('hidden');
        } else {
            banner.classList.add('hidden');
        }
    }
}

function updateProgress(progress, msg, status) {
    const pct = Math.max(0, Math.min(100, Number(progress) || 0));
    const bar = document.getElementById('poGenProgressBar');
    const percentEl = document.getElementById('poGenProgressPercent');
    const msgEl = document.getElementById('poGenProgressMsg');
    const titleEl = document.getElementById('poGenProgressTitle');
    const spinner = document.getElementById('poGenProgressSpinner');

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
            titleEl.textContent = '生成完成';
            titleEl.className = 'text-xs font-medium text-[#4caf50] truncate mb-0';
        } else if (status === 'failed') {
            titleEl.textContent = '生成失败';
            titleEl.className = 'text-xs font-medium text-[#ef5350] truncate mb-0';
        } else {
            titleEl.textContent = '正在生成采购对象清单...';
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

function showProgress(progress = 0, msg = '正在读取材料清单树') {
    document.getElementById('poGenProgressPanel')?.classList.remove('hidden');
    updateProgress(progress, msg);
}

function hideProgress() {
    document.getElementById('poGenProgressPanel')?.classList.add('hidden');
    updateProgress(0, '正在读取材料清单树');
}

async function loadGenHistory(page = genState.history.page) {
    const body = document.getElementById('poGenHistoryBody');
    if (!body) return;
    body.innerHTML = `<tr><td colspan="9" class="py-8 text-center text-[#555]">加载中..</td></tr>`;
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

        const totalEl = document.getElementById('poGenHistoryTotal');
        if (totalEl) totalEl.textContent = `全${genState.history.total} 条`;
        const pagination = document.getElementById('poGenHistoryPagination');
        if (pagination) {
            pagination.innerHTML = renderPoGenHistoryPagination(
                genState.history.page,
                genState.history.totalPages,
            );
        }
    } catch (error) {
        console.error('加载生成历史失败:', error);
        body.innerHTML = `<tr><td colspan="9" class="py-8 text-center text-[#ef5350]">加载失败</td></tr>`;
    }
}

function renderHistoryRows(items) {
    const body = document.getElementById('poGenHistoryBody');
    if (!body) return;
    if (!items.length) {
        body.innerHTML = `<tr><td colspan="9" class="py-8 text-center text-[#555]">暂无生成记录</td></tr>`;
        return;
    }

    body.innerHTML = items.map((item) => {
        const status = STATUS_META[item.status] || STATUS_META.failed;
        const started = formatDateTime(item.started_at);
        const createdBy = item.created_by || item.operator_name || '-';
        return `
            <tr class="hover:bg-[#ffffff]/[0.02] transition-colors text-[#999]">
                <td class="py-2 px-2 font-mono text-[#666] whitespace-nowrap">${esc(started)}</td>
                <td class="py-2 px-2 text-[#ccc] whitespace-nowrap">${esc(createdBy)}</td>
                <td class="py-2 px-2 text-[#ccc] whitespace-nowrap">${esc(item.location || '-')}</td>
                <td class="py-2 px-2 text-[#ccc] whitespace-nowrap">${esc(item.vehicle_model || '-')}</td>
                <td class="py-2 px-2 font-mono text-[#ccc] whitespace-nowrap">${esc(item.bom_version || '-')}</td>
                <td class="py-2 px-2 text-center text-[9px] ${status.className}">${status.label}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-[#777]">${fmtInt(item.node_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-[#777]">${fmtInt(item.object_count)}</td>
                <td class="py-2 px-2 text-right whitespace-nowrap">
                    <button type="button" class="po-gen-view-process-btn text-[9px] text-[#777] hover:text-white mr-2"
                            data-log-id="${esc(item.id)}">过程</button>
                    ${item.status === 'failed' ? '' : `
                    <button type="button" class="po-gen-view-result-btn text-[9px] text-[#777] hover:text-white"
                            data-location="${esc(item.location || '')}"
                            data-model="${esc(item.vehicle_model || '')}"
                            data-version="${esc(item.bom_version || '')}">结果</button>
                    `}
                </td>
            </tr>
        `;
    }).join('');

    body.querySelectorAll('.po-gen-view-process-btn').forEach((btn) => {
        btn.addEventListener('click', () => openProcessDrawer(Number(btn.dataset.logId)));
    });
    body.querySelectorAll('.po-gen-view-result-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
            const qs = new URLSearchParams();
            if (btn.dataset.location) qs.set('location', btn.dataset.location);
            if (btn.dataset.model) qs.set('vehicle_model', btn.dataset.model);
            if (btn.dataset.version) qs.set('bom_version', btn.dataset.version);
            const suffix = qs.toString() ? `?${qs.toString()}` : '';
            window.location.hash = `/bom-procurement-object-list${suffix}`;
        });
    });
}

async function openProcessDrawer(logId) {
    if (!logId) return;
    try {
        const response = await HttpClient.get(`${LOGS_API}/${logId}`);
        showProcessDrawer(response.data || {});
    } catch (error) {
        console.error('加载生成过程失败:', error);
    }
}

function showProcessDrawer(log) {
    closeProcessDrawer();
    const status = STATUS_META[log.status] || STATUS_META.failed;
    const backdrop = document.createElement('div');
    backdrop.id = 'poGenProcessBackdrop';
    backdrop.className = 'fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm';
    const drawer = document.createElement('div');
    drawer.id = 'poGenProcessDrawer';
    drawer.className =
        'fixed inset-y-0 right-0 z-[85] w-[640px] max-w-[95vw] bg-[#1a1a1a] border-l border-[#2a2a2a] flex flex-col';
    drawer.innerHTML = `
        <div class="px-5 py-3.5 flex items-center justify-between shrink-0 bg-[#1f1f1f] border-b border-[#333333]">
            <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] uppercase">
                生成过程 · ${esc(log.location || '-')} · ${esc(log.vehicle_model || '-')} · ${esc(log.bom_version || '-')}
                <span class="ml-2 normal-case ${status.className}">${status.label}</span>
            </h5>
            <div class="flex items-center gap-0.5 shrink-0">
                ${window.copyProcessReportButtonHtml()}
                <button type="button" id="closePoGenProcessDrawer"
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
            <div>汇总：节点 ${fmtInt(log.node_count)} · ${SECTION_LABELS.object} ${fmtInt(log.object_count)} · ${SECTION_LABELS.other_leaf} ${fmtInt(log.other_leaf_count)} · ${SECTION_LABELS.anomaly} ${fmtInt(log.anomaly_count)}</div>
        </div>
        <div class="flex-1 overflow-y-auto overscroll-contain p-5">
            <pre class="text-[11px] leading-5 font-mono text-[#9e9e9e] whitespace-pre-wrap break-words bg-[#111111] border border-[#262626] p-4">${esc(log.detail_text || '（无过程文本）')}</pre>
        </div>
    `;
    document.body.appendChild(backdrop);
    document.body.appendChild(drawer);
    window.bindProcessReportCopy(drawer);
    backdrop.addEventListener('click', closeProcessDrawer);
    document.getElementById('closePoGenProcessDrawer')?.addEventListener('click', closeProcessDrawer);
}

function closeProcessDrawer() {
    document.getElementById('poGenProcessBackdrop')?.remove();
    document.getElementById('poGenProcessDrawer')?.remove();
}

async function startGenerate() {
    if (genState.isGenerating || !genState.canGenerate) return;
    const location = genState.location || val('poGenLocation');
    const vehicleModel = genState.vehicleModel || val('poGenModel');
    const bomVersion = genState.bomVersion || val('poGenVersion');
    if (!location || !vehicleModel || !bomVersion) {
        showToast('须选定基地、项目、版本', 'warning');
        return;
    }
    genState.isGenerating = true;
    const startBtn = document.getElementById('poGenSubmitBtn');
    if (startBtn) startBtn.disabled = true;
    showProgress(15, '正在读取材料清单树');
    try {
        showProgress(55, '正在分类并落库');
        const res = await HttpClient.post(GENERATE_API, {
            location,
            vehicle_model: vehicleModel,
            bom_version: bomVersion,
        });
        updateProgress(100, res.message || '已写入采购对象清单', 'completed');
        showToast(res.message || '生成成功', 'success');
        await loadPrepStats();
        await loadGenHistory(1);
    } catch (error) {
        const failMsg = error?.message || '生成失败';
        updateProgress(100, failMsg, 'failed');
        console.error('生成采购对象清单失败', error);
        loadGenHistory(1);
    } finally {
        genState.isGenerating = false;
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
    render: procurementObjectGenerateTemplate,
    init,
    destroy,
};
