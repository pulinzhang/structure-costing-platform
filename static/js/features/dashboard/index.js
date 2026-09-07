/**
 * Dashboard Page
 * 管理者看板：本期产出 · 待办决策 · 闭环就绪
 */

import { canAccessPage } from '../../permissions.js?v=9';
import { dashboardTemplate } from './template.js?v=9';

const DASHBOARD_STATS_API = '/api/dashboard/stats';

const dashState = {
    year: null,
    month: null,
    location: '',
    vehicleModel: '',
    loading: false,
};

const SEVERITY_META = {
    critical: { label: '阻断', className: 'text-[#ef5350] border-[#ef5350]/40 bg-[#ef5350]/10' },
    warning: { label: '待办', className: 'text-[#ffb74d] border-[#ffb74d]/35 bg-[#ffb74d]/10' },
    info: { label: '提示', className: 'text-[#64b5f6] border-[#64b5f6]/30 bg-[#64b5f6]/10' },
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

    const loc = scope.location || '全部基地';
    const vehicle = scope.vehicle_model || '全部项目';
    setText(
        'dashScopeLabel',
        `${fmtPeriod(scope.year, scope.month)} · ${loc} · ${vehicle}`
    );
    setText('dashOutcomeSub', `${fmtPeriod(scope.year, scope.month)} · ${loc} · ${vehicle}`);
}

function renderOutcome(outcome, partCost, steelPrice) {
    const o = outcome || {};
    setText('dashPartAvg', fmtNum(o.part_cost_avg));
    setText(
        'dashPartAvgMeta',
        `已审 ${partCost?.approved_count ?? o.part_cost_approved ?? 0} · 待审 ${partCost?.pending_count ?? o.part_cost_pending ?? 0}`
            + (dashState.vehicleModel ? ' · 各厂混合' : '')
    );
    setText('dashPendingTotal', String(o.pending_total ?? 0));
    setText(
        'dashPendingBreakdown',
        `加工费 ${o.process_fee_pending ?? 0} · 钢价 ${o.steel_price_pending ?? 0} · 冲压件 ${o.part_cost_pending ?? 0}`
    );
    setText('dashFeeZero', String(o.process_fee_zero ?? 0));
    setText('dashFeeAvg', `件均 ${fmtNum(o.process_fee_avg)}`);
    setText('dashSteelAvg', fmtNum(o.steel_price_avg));
    setText(
        'dashSteelMeta',
        `已审 ${steelPrice?.approved_count ?? 0} · 待审 ${steelPrice?.pending_count ?? 0}`
    );

    const pendingEl = document.getElementById('dashPendingTotal');
    if (pendingEl) {
        pendingEl.classList.toggle('text-[#ffb74d]', (o.pending_total || 0) > 0);
        pendingEl.classList.toggle('text-[#4caf50]', (o.pending_total || 0) === 0);
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
            <div class="px-5 py-10 text-center">
                <p class="text-sm text-[#4caf50] font-medium">本期暂无待办</p>
                <p class="mt-1 text-[10px] text-[#555555]">核价闭环可按就绪清单推进或复核已审结果</p>
            </div>
        `;
        return;
    }

    list.innerHTML = visible
        .map((item) => {
            const meta = SEVERITY_META[item.severity] || SEVERITY_META.info;
            const countBadge =
                item.count != null
                    ? `<span class="font-mono text-[11px] tabular-nums text-[#F0F0F2]">${esc(item.count)}</span>`
                    : '';
            const link =
                item.page && canAccessPage(item.page)
                    ? `<a href="#/${item.page}" data-page="${esc(item.page)}"
                           class="shrink-0 text-[10px] text-[#d32f2f] hover:underline">去处理</a>`
                    : '';
            return `
                <div class="flex items-start gap-3 px-5 py-3.5 hover:bg-[#161616] transition-colors">
                    <span class="mt-0.5 shrink-0 px-1.5 py-0.5 text-[9px] font-semibold tracking-wide border ${meta.className}">
                        ${meta.label}
                    </span>
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2">
                            <p class="text-xs font-medium text-[#F0F0F2] truncate">${esc(item.title)}</p>
                            ${countBadge}
                        </div>
                        <p class="mt-0.5 text-[10px] text-[#8E8E93] leading-relaxed">${esc(item.detail)}</p>
                    </div>
                    ${link}
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
            ? '<span class="text-[#4caf50] font-mono text-[10px]">READY</span>'
            : '<span class="text-[#ffb74d] font-mono text-[10px]">GAP</span>';
        const link = !ok && canGo
            ? `<a href="#/${row.page}" data-page="${row.page}" class="text-[10px] text-[#d32f2f] hover:underline">补齐</a>`
            : '';
        return `
            <div class="flex items-center justify-between gap-2 px-3 py-2 border border-[#222222] bg-[#121212]">
                <span class="text-xs text-[#F0F0F2]">${esc(row.label)}</span>
                <div class="flex items-center gap-2">
                    ${status}
                    ${link}
                </div>
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
    const masterEl = document.getElementById('dashMasterBlock');
    if (masterEl) {
        if (!m.parts) {
            masterEl.innerHTML = canAccessPage('stamping-upload')
                ? `<span class="text-[#8E8E93]">${loc ? esc(loc) + ' ' : ''}尚无工艺零件</span>
                   <a href="#/stamping-upload" data-page="stamping-upload" class="text-[#d32f2f] hover:underline ml-1 text-xs">去上传</a>`
                : `<span class="text-[#8E8E93]">${loc ? esc(loc) + ' ' : ''}尚无工艺零件</span>`;
        } else {
            const scopeTag = loc
                ? `<span class="text-[#555555]">（${esc(loc)}${scope?.vehicle_model ? ' · ' + esc(scope.vehicle_model) : ''}）</span> `
                : `<span class="text-[#555555]">（${scope?.vehicle_model ? esc(scope.vehicle_model) : '全部基地'}）</span> `;
            masterEl.innerHTML = `${scopeTag}<span class="text-[#F0F0F2]">冲压零件 ${esc(m.parts)} · 工序 ${esc(m.processes)} · 项目 ${esc(m.models)}</span>`;
        }
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

    const period = scope ? fmtPeriod(scope.year, scope.month) : '—';
    const bomLoc = loc || '全部';
    const vehicleTag = scope?.vehicle_model ? ` · ${scope.vehicle_model}` : '';
    setText(
        'dashBomBlock',
        `${period} · ${bomLoc}${vehicleTag}：BOM ${b.snapshot_count ?? 0} 版 / ${b.node_count ?? 0} 节点 · 基价 ${y.base_price_count ?? 0} · 政策 ${y.policy_count ?? 0} · ${scrapText}`
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

async function loadStats() {
    if (dashState.loading) return;
    dashState.loading = true;
    try {
        const params = {};
        if (dashState.year != null) params.year = dashState.year;
        if (dashState.month != null) params.month = dashState.month;
        if (dashState.location) params.location = dashState.location;
        if (dashState.vehicleModel) params.vehicle_model = dashState.vehicleModel;
        const res = await HttpClient.get(DASHBOARD_STATS_API, { params });
        renderStats(res.data);
    } catch (error) {
        console.error('加载管理者看板失败:', error);
        const list = document.getElementById('dashAttentionList');
        if (list) {
            list.innerHTML = `<div class="px-5 py-8 text-center text-sm text-[#ef5350]">统计加载失败</div>`;
        }
    } finally {
        dashState.loading = false;
    }
}

function bindScopeEvents() {
    const reload = () => {
        const yearEl = document.getElementById('dashYear');
        const monthEl = document.getElementById('dashMonth');
        const locationEl = document.getElementById('dashLocation');
        const vehicleEl = document.getElementById('dashVehicle');
        dashState.year = yearEl?.value ? Number(yearEl.value) : null;
        dashState.month = monthEl?.value ? Number(monthEl.value) : null;
        dashState.location = locationEl?.value || '';
        dashState.vehicleModel = vehicleEl?.value || '';
        loadStats();
    };
    document.getElementById('dashYear')?.addEventListener('change', reload);
    document.getElementById('dashMonth')?.addEventListener('change', reload);
    document.getElementById('dashLocation')?.addEventListener('change', reload);
    document.getElementById('dashVehicle')?.addEventListener('change', reload);
}

export const DashboardPage = {
    init() {
        applyActionPermissions();
        bindScopeEvents();
        loadStats();
    },
};

export const pageConfig = {
    render: dashboardTemplate,
    init: () => DashboardPage.init(),
};
