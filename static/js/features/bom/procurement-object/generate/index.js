/**
 * 采购对象列表生成页
 */

import { DRAWER_CLOSE, DRAWER_SHELL, DRAWER_BACKDROP } from '../../../../ui/classes.js?v=14';
import { opsIconButtonHtml } from '../../../../ui/hud-table.js?v=3';
import {
    procurementObjectGenerateTemplate,
} from './template.js?v=15';
import {
    DEFAULT_PAGE_SIZE,
    bindPagination,
    paintPagination,
} from '../../../../ui/page-size.js?v=11';
import { SECTION_LABELS } from '../labels.js?v=4';
import {
    formatDurationSeconds,
    formatTimingLine,
} from '../../../../domain/duration.js?v=3';
import { loadSnapshotCascade } from '../snapshot-cascade.js?v=5';

const API_BASE = '/api/bom/procurement-objects';
const GENERATE_API = `${API_BASE}/generate`;
const PREP_STATS_API = `${API_BASE}/generate/prep-stats`;
const LOGS_API = `${API_BASE}/generate/logs`;

const STATUS_META = {
    success: { label: '成功', className: 'text-ok' },
    failed: { label: '失败', className: 'text-danger' },
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
    bindPagination({
        selectId: 'poGenHistoryPageSize',
        buttonsId: 'poGenHistoryPagination',
        getSize: () => genState.history.size,
        setSize: (size) => {
            genState.history.size = size;
        },
        onPage: (page) => loadGenHistory(page),
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
}

function val(id) {
    return (document.getElementById(id)?.value || '').trim();
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

function loadCascadeFilters() {
    return loadSnapshotCascade({
        state: genState,
        locationId: 'poGenLocation',
        modelId: 'poGenModel',
        versionId: 'poGenVersion',
    });
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
    el.innerHTML = `${display} <span class="text-[9px] font-normal text-ink-faint">${unit}</span>`;
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
            titleEl.className = 'text-xs font-medium text-ok truncate mb-0';
        } else if (status === 'failed') {
            titleEl.textContent = '生成失败';
            titleEl.className = 'text-xs font-medium text-danger truncate mb-0';
        } else {
            titleEl.textContent = '正在生成采购对象列表...';
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

        const totalEl = document.getElementById('poGenHistoryTotal');
        if (totalEl) totalEl.textContent = `全${genState.history.total} 条`;
        paintPagination('poGenHistoryPagination', 
                genState.history.page,
                genState.history.totalPages,
            );
    } catch (error) {
        console.error('加载生成历史失败:', error);
        body.innerHTML = `<tr><td colspan="11" class="py-8 text-center text-danger">加载失败</td></tr>`;
    }
}

function renderHistoryRows(items) {
    const body = document.getElementById('poGenHistoryBody');
    if (!body) return;
    if (!items.length) {
        body.innerHTML = `<tr><td colspan="11" class="py-8 text-center text-ink-faint">暂无生成记录</td></tr>`;
        return;
    }

    body.innerHTML = items.map((item) => {
        const status = STATUS_META[item.status] || STATUS_META.failed;
        const createdBy = item.created_by || item.operator_name || '-';
        const processBtn = opsIconButtonHtml({
            extraClass: 'po-gen-view-process-btn',
            title: '过程',
            icon: window.svgIcon('file-earmark-text', 'w-3.5 h-3.5'),
            attrs: `data-log-id="${esc(item.id)}"`,
        });
        const resultBtn = item.status === 'failed' ? '' : opsIconButtonHtml({
            extraClass: 'po-gen-view-result-btn',
            title: '结果',
            icon: window.svgIcon('external-link', 'w-3.5 h-3.5'),
            attrs: `data-location="${esc(item.location || '')}" data-model="${esc(item.vehicle_model || '')}" data-version="${esc(item.bom_version || '')}"`,
        });
        return `
            <tr class="group hover:bg-ink/[0.02] transition-colors text-ink-muted">
                <td class="py-2 px-2 font-mono text-ink-dim whitespace-nowrap">${esc(formatDateTime(item.started_at))}</td>
                <td class="py-2 px-2 font-mono text-ink-dim whitespace-nowrap">${esc(formatDateTime(item.finished_at))}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-ink-dim whitespace-nowrap">${esc(formatDurationSeconds(item))}</td>
                <td class="py-2 px-2 text-ink-muted whitespace-nowrap">${esc(createdBy)}</td>
                <td class="py-2 px-2 text-ink-muted whitespace-nowrap">${esc(item.location || '-')}</td>
                <td class="py-2 px-2 text-ink-muted whitespace-nowrap">${esc(item.vehicle_model || '-')}</td>
                <td class="py-2 px-2 font-mono text-ink-muted whitespace-nowrap">${esc(item.bom_version || '-')}</td>
                <td class="py-2 px-2 text-center text-[9px] ${status.className}">${status.label}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-ink-dim">${fmtInt(item.node_count)}</td>
                <td class="py-2 px-2 font-mono text-right tabular-nums text-ink-dim">${fmtInt(item.object_count)}</td>
                <td class="py-2 px-1 text-right whitespace-nowrap">
                    <div class="inline-flex items-center justify-end">${processBtn}${resultBtn}</div>
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
    backdrop.className = DRAWER_BACKDROP;
    const drawer = document.createElement('div');
    drawer.id = 'poGenProcessDrawer';
    drawer.className =
        `${DRAWER_SHELL} w-[640px]`;
    drawer.innerHTML = `
        <div class="px-5 py-3.5 flex items-center justify-between shrink-0 bg-app-surface border-b border-line">
            <h5 class="text-[11px] font-semibold tracking-wider text-ink-muted uppercase">
                生成过程 · ${esc(log.location || '-')} · ${esc(log.vehicle_model || '-')} · ${esc(log.bom_version || '-')}
                <span class="ml-2 normal-case ${status.className}">${status.label}</span>
            </h5>
            <div class="flex items-center gap-0.5 shrink-0">
                ${window.copyProcessReportButtonHtml()}
                <button type="button" id="closePoGenProcessDrawer"
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
            <div>汇总：节点 ${fmtInt(log.node_count)} · ${SECTION_LABELS.object} ${fmtInt(log.object_count)} · ${SECTION_LABELS.other_leaf} ${fmtInt(log.other_leaf_count)} · ${SECTION_LABELS.anomaly} ${fmtInt(log.anomaly_count)}</div>
        </div>
        <div class="flex-1 overflow-y-auto overscroll-contain p-5">
            <pre class="text-[11px] leading-5 font-mono text-ink-muted whitespace-pre-wrap break-words bg-app-main border border-app-elevated p-4">${esc(log.detail_text || '（无过程文本）')}</pre>
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
        showProgress(55, '正在分类并保存');
        const res = await HttpClient.post(GENERATE_API, {
            location,
            vehicle_model: vehicleModel,
            bom_version: bomVersion,
        });
        updateProgress(100, res.message || '已写入采购对象列表', 'completed');
        showToast(res.message || '生成成功', 'success');
        await loadPrepStats();
        await loadGenHistory(1);
    } catch (error) {
        const failMsg = error?.message || '生成失败';
        updateProgress(100, failMsg, 'failed');
        console.error('生成采购对象列表失败', error);
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
