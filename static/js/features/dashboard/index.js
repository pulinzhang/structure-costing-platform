/**
 * Dashboard Page
 * 管理者看板：本期产出 · 待办决策 · 闭环就绪
 */

import { canAccessPage } from '../../core/permissions.js?v=11';
import { bindFilterBar } from '../../ui/filter-bar.js?v=6';
import { pageLoadingHtml, pageNoticeHtml } from '../../ui/page-loading.js?v=1';
import { dashboardTemplate } from './template.js?v=22';

const DASHBOARD_STATS_API = '/api/dashboard/stats';

/** @type {{ paint: () => void, unbind: () => void } | null} */
let filterBar = null;

let requestSerial = 0;

const dashState = {
    year: null,
    month: null,
    location: '',
    vehicleModel: '',
    loading: false,
};

const SEVERITY_META = {
    critical: { label: '阻断', className: 'text-danger border-danger/40 bg-danger/10' },
    warning: { label: '待办', className: 'text-warn border-warn/40/35 bg-warn/10' },
    info: { label: '提示', className: 'text-ink-muted border-ink-muted/30 bg-ink-muted/10' },
};

const READY_ROWS = [
    { key: 'has_base_price', label: '中标基价', page: 'base-price-download' },
    { key: 'has_policy', label: '加减价政策', page: 'steel-price-policy-download' },
    { key: 'is_scrap_complete', label: '废料月度价', page: 'scrap-price' },
    { key: 'has_process_fee', label: '冲压加工费', page: 'stamping-process-fee' },
    { key: 'has_steel_price', label: '钢材联动价', page: 'steel-price-list' },
    { key: 'has_part_cost', label: '冲压零件价格', page: 'stamping-part-cost' },
];

function esc(value) {
    return typeof window.esc === 'function' ? window.esc(value) : String(value ?? '—');
}

function fmtNum(value, digits = 2) {
    if (value == null || value === '') return '—';
    if (typeof window.fmtNum === 'function') return window.fmtNum(value, digits);
    const n = Number(value);
    return Number.isFinite(n) ? n.toFixed(digits) : '—';
}

function fillSelect(selectEl, values, { selected, blankLabel, format } = {}) {
    if (!selectEl) return;
    const opts = [];
    if (blankLabel != null) {
        opts.push(`<option value="">${esc(blankLabel)}</option>`);
    }
    for (const value of values || []) {
        const label = format ? format(value) : String(value);
        const isSelected = selected != null && String(selected) === String(value);
        opts.push(
            `<option value="${esc(value)}"${isSelected ? ' selected' : ''}>${esc(label)}</option>`
        );
    }
    selectEl.innerHTML = opts.join('');
}

function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

function applyScopeOptions(scope) {
    dashState.year = scope.year;
    dashState.month = scope.month;
    dashState.location = scope.location || '';
    dashState.vehicleModel = scope.vehicle_model || '';

    fillSelect(document.getElementById('dashYear'), scope.years || [], {
        selected: scope.year,
        format: fmtYear,
    });
    fillSelect(document.getElementById('dashMonth'), scope.months || [], {
        selected: scope.month,
        format: fmtMonth,
    });
    fillSelect(document.getElementById('dashLocation'), scope.locations || [], {
        selected: scope.location || '',
        blankLabel: '全部基地',
    });
    fillSelect(document.getElementById('dashVehicle'), scope.vehicle_models || [], {
        selected: scope.vehicle_model || '',
        blankLabel: '全部项目',
    });

    filterBar?.paint();
}

function renderOutcome(outcome, partCost, steelPrice) {
    const o = outcome || {};
    setText('dashPartAvg', fmtNum(o.part_cost_avg));
    setText('dashPartApproved', String(partCost?.approved_count ?? o.part_cost_approved ?? 0));
    setText('dashPartPending', String(partCost?.pending_count ?? o.part_cost_pending ?? 0));
    document.getElementById('dashPartMix')?.classList.toggle('hidden', !dashState.vehicleModel);
    setText('dashPendingTotal', String(o.pending_total ?? 0));
    setText('dashFeePending', String(o.process_fee_pending ?? 0));
    setText('dashSteelPricePending', String(o.steel_price_pending ?? 0));
    setText('dashPartCostPending', String(o.part_cost_pending ?? 0));
    setText('dashFeeZero', String(o.process_fee_zero ?? 0));
    setText('dashFeeAvg', fmtNum(o.process_fee_avg));
    setText('dashSteelAvg', fmtNum(o.steel_price_avg));
    setText('dashSteelApproved', String(steelPrice?.approved_count ?? 0));
    setText('dashSteelPendingCount', String(steelPrice?.pending_count ?? 0));

    const pendingEl = document.getElementById('dashPendingTotal');
    if (pendingEl) {
        pendingEl.classList.toggle('text-warn', (o.pending_total || 0) > 0);
        pendingEl.classList.toggle('text-ok', (o.pending_total || 0) === 0);
    }
}

function renderAttention(items) {
    const list = document.getElementById('dashAttentionList');
    const countEl = document.getElementById('dashAttentionCount');
    if (!list) return;

    const visible = (items || []).filter((item) => {
        if (!item.page) return true;
        return canAccessPage(item.page);
    });

    if (countEl) countEl.textContent = `${visible.length} 项`;

    if (!visible.length) {
        list.innerHTML = `
            <div class="dash-attention-empty">
                <p class="dash-attention-clear">本期暂无待办</p>
                <p>核价闭环可按就绪清单推进或复核已审结果</p>
            </div>
        `;
        return;
    }

    list.innerHTML = visible
        .map((item) => {
            const meta = SEVERITY_META[item.severity] || SEVERITY_META.info;
            const countBadge =
                item.count != null
                    ? `<span class="dash-attention-num">${esc(item.count)}</span>`
                    : '';
            const link =
                item.page && canAccessPage(item.page)
                    ? `<a href="#/${item.page}" data-page="${esc(item.page)}" class="dash-attention-link">去处理</a>`
                    : '';
            return `
                <div class="dash-attention-row">
                    <span class="dash-attention-badge ${meta.className}">${meta.label}</span>
                    <div class="dash-attention-body">
                        <div class="dash-attention-title-row">
                            <p class="dash-attention-title">${esc(item.title)}${countBadge}</p>
                            ${link}
                        </div>
                        <p class="dash-attention-detail">${esc(item.detail)}</p>
                    </div>
                </div>
            `;
        })
        .join('');
}

function renderReadiness(readiness) {
    const root = document.getElementById('dashReadiness');
    if (!root) return;
    const r = readiness || {};
    setText('dashReadyScore', `${r.ready_count ?? 0}/${r.total_count ?? 6}`);

    root.innerHTML = READY_ROWS.map((row) => {
        const ok = Boolean(r[row.key]);
        const canGo = canAccessPage(row.page);
        const status = ok
            ? '<span class="dash-ready-state text-ok">已齐</span>'
            : '<span class="dash-ready-state text-warn">缺口</span>';
        const link = !ok && canGo
            ? `<a href="#/${row.page}" data-page="${row.page}" class="dash-ready-link">补齐</a>`
            : '';
        return `
            <div class="dash-ready-row">
                <span class="dash-ready-label">${esc(row.label)}</span>
                <span class="dash-ready-side">${status}${link}</span>
            </div>
        `;
    }).join('');

    const hint = document.getElementById('dashReadyHint');
    if (hint) {
        const ready = r.ready_count ?? 0;
        const total = r.total_count ?? 6;
        if (ready >= total) {
            hint.textContent = '六项已齐：可复核待审清单并关闭本期冲压核价。';
        } else if (ready >= 4) {
            hint.textContent = `已就绪 ${ready}/${total}，优先补齐缺口项后再发起计算或审核。`;
        } else {
            hint.textContent = `就绪偏低（${ready}/${total}）：先补基价 / 政策 / 废料与主数据，再谈产出。`;
        }
    }
}

function renderContext(master, bom, yishiyiyi, scope) {
    const m = master || {};
    const b = bom || {};
    const y = yishiyiyi || {};
    const loc = scope?.location;
    const masterEmpty = document.getElementById('dashMasterEmpty');
    const masterStats = document.getElementById('dashMasterStats');
    if (!m.parts) {
        masterStats?.classList.add('hidden');
        if (masterEmpty) {
            masterEmpty.classList.remove('hidden');
            const where = loc ? esc(loc) + ' ' : '';
            masterEmpty.innerHTML = canAccessPage('stamping-upload')
                ? `<span>${where}尚无工艺零件</span>
                   <a href="#/stamping-upload" data-page="stamping-upload" class="dash-ready-link">去上传</a>`
                : `<span>${where}尚无工艺零件</span>`;
        }
    } else {
        masterEmpty?.classList.add('hidden');
        masterStats?.classList.remove('hidden');
        setText('dashMasterParts', String(m.parts ?? '—'));
        setText('dashMasterProcesses', String(m.processes ?? '—'));
        setText('dashMasterModels', String(m.models ?? '—'));
    }

    let scrapText;
    if (y.scrap_location) {
        scrapText = y.is_scrap_location_filled
            ? `${esc(y.scrap_location)}废料净价 ¥${esc(fmtNum(y.scrap_location_net_price))}`
            : `${esc(y.scrap_location)}废料未录`;
    } else {
        scrapText = y.is_scrap_complete
            ? `废料月齐 ${y.scrap_filled_count}/${y.scrap_required_count}`
            : `废料月 ${y.scrap_filled_count ?? 0}/${y.scrap_required_count ?? 0}`;
    }

    setText(
        'dashBomBlock',
        `材料清单 ${b.snapshot_count ?? 0} 版 · 零件 ${b.node_count ?? 0} 条 · 基价 ${y.base_price_count ?? 0} · 政策 ${y.policy_count ?? 0} · ${scrapText}`
    );
}

function applyActionPermissions() {
    const root = document.getElementById('dashActions');
    if (!root) return;
    root.querySelectorAll('a[data-page]').forEach((link) => {
        const page = link.getAttribute('data-page');
        const allowed = canAccessPage(page);
        link.classList.toggle('hidden', !allowed);
        if (!allowed) {
            link.setAttribute('aria-hidden', 'true');
            link.tabIndex = -1;
        }
    });
}

function renderStats(data) {
    if (!data) return;
    applyScopeOptions(data.scope || {});
    renderOutcome(data.outcome, data.part_cost, data.steel_price);
    renderAttention(data.attention || []);
    renderReadiness(data.readiness);
    renderContext(data.master, data.bom, data.yishiyiyi, data.scope);
}

function showPageLoading() {
    const content = document.getElementById('pageContent');
    if (!content) return;
    filterBar?.unbind();
    filterBar = null;
    content.innerHTML = pageLoadingHtml();
}

function isBoardMounted() {
    return !!document.getElementById('dashAttentionList');
}

function mountBoard() {
    const content = document.getElementById('pageContent');
    if (!content) return;
    filterBar?.unbind();
    filterBar = null;
    content.innerHTML = dashboardTemplate();
    applyActionPermissions();
    bindScopeEvents();
}

function showLoadFailure() {
    if (isBoardMounted()) {
        const list = document.getElementById('dashAttentionList');
        if (list) {
            list.innerHTML = `<div class="px-5 py-8 text-center text-sm text-danger">统计加载失败</div>`;
        }
        return;
    }
    const content = document.getElementById('pageContent');
    if (content) content.innerHTML = pageNoticeHtml('统计加载失败');
}

async function loadStats() {
    if (dashState.loading) return;
    const serial = ++requestSerial;
    dashState.loading = true;
    try {
        const params = {};
        if (dashState.year != null) params.year = dashState.year;
        if (dashState.month != null) params.month = dashState.month;
        if (dashState.location) params.location = dashState.location;
        if (dashState.vehicleModel) params.vehicle_model = dashState.vehicleModel;
        const res = await HttpClient.get(DASHBOARD_STATS_API, { params });
        if (serial !== requestSerial) return;
        if (!isBoardMounted()) mountBoard();
        if (serial !== requestSerial) return;
        renderStats(res.data);
    } catch (error) {
        console.error('加载管理者看板失败:', error);
        if (serial !== requestSerial) return;
        showLoadFailure();
    } finally {
        if (serial === requestSerial) dashState.loading = false;
    }
}

function readScopeFromControls() {
    const yearEl = document.getElementById('dashYear');
    const monthEl = document.getElementById('dashMonth');
    const locationEl = document.getElementById('dashLocation');
    const vehicleEl = document.getElementById('dashVehicle');
    dashState.year = yearEl?.value ? Number(yearEl.value) : null;
    dashState.month = monthEl?.value ? Number(monthEl.value) : null;
    dashState.location = locationEl?.value || '';
    dashState.vehicleModel = vehicleEl?.value || '';
}

function resetFilters() {
    const locationEl = document.getElementById('dashLocation');
    const vehicleEl = document.getElementById('dashVehicle');
    if (locationEl) locationEl.value = '';
    if (vehicleEl) vehicleEl.value = '';
    dashState.location = '';
    dashState.vehicleModel = '';
    loadStats();
}

function bindScopeEvents() {
    const reload = () => {
        readScopeFromControls();
        loadStats();
    };
    filterBar = bindFilterBar({
        prefix: 'dash',
        searchId: 'dashBtnSearch',
        resetId: 'dashResetBtn',
        capsules: [
            {
                capsuleId: 'dashCapsulePeriod',
                fieldIds: ['dashYear', 'dashMonth'],
                idleLabel: '全部期间',
                display: () => fmtPeriod(
                    document.getElementById('dashYear')?.value,
                    document.getElementById('dashMonth')?.value,
                ) || '',
            },
            { capsuleId: 'dashCapsuleLocation', fieldId: 'dashLocation', idleLabel: '全部基地' },
            { capsuleId: 'dashCapsuleVehicle', fieldId: 'dashVehicle', idleLabel: '全部项目' },
        ],
        onSearch: reload,
        onReset: resetFilters,
    });
    ['dashYear', 'dashMonth', 'dashLocation', 'dashVehicle'].forEach((id) => {
        document.getElementById(id)?.addEventListener('change', reload);
    });
}

function releaseDashboard() {
    requestSerial += 1;
    dashState.loading = false;
    filterBar?.unbind();
    filterBar = null;
}

export const DashboardPage = {
    init() {
        if (!isBoardMounted()) showPageLoading();
        loadStats();
    },
    destroy: releaseDashboard,
};

export const pageConfig = {
    render: () => pageLoadingHtml(),
    init: () => DashboardPage.init(),
    destroy: () => DashboardPage.destroy(),
};
