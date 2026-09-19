/**
 * 月度智能自动核价引擎 — 页面逻辑 (BRABUS Pure Industrial Spec)
 */

import { costingTemplate } from './template.js?v=26';
import {
    DEFAULT_PAGE_SIZE,
    bindPagination,
    paintPagination,
} from '../../../page-size.js?v=3';
import {
    formatDurationSeconds,
    formatTimingLine,
} from '../../../duration.js?v=1';

const READY_API = '/api/costing/engine/ready';
const RUNS_API = '/api/costing/engine/runs';
const TASK_API = '/api/costing/engine/tasks';
const CASCADE_API = '/api/stamping/filters/cascade';
const POLL_INTERVAL_MS = 1500;
const STORAGE_KEY = 'costing_engine_context';
/** 与后端 SOFT_UPLOAD_GATE_CODES 对齐：仅提示，不阻断启动 */
const SOFT_GATE_CODES = new Set([
    'packaging_transport',
    'stamping_process',
    'bom_snapshot',
    'vehicle_model',
]);

/** 核算数据管道阶梯 */
const PIPELINE_STAGES = [
    {
        id: 'ingest',
        zh: '数据摄入',
        gateCodes: [
            'vehicle_model',
            'stamping_process',
            'tonnage_price',
            'welding_unit_price',
            'packaging_transport',
            'annual_part_price',
        ],
    },
    {
        id: 'validate',
        zh: '格式清洗',
        gateCodes: ['base_price', 'thickness_policy', 'scrap_price', 'system_rates'],
    },
    {
        id: 'match',
        zh: 'BOM 匹配',
        gateCodes: ['bom_snapshot'],
    },
    {
        id: 'aggregate',
        zh: '成本归集',
        gateCodes: [
            'annual_process_fee',
            'annual_die_fee',
            'annual_procurement_object',
            'annual_welding_breakdown',
            'annual_welding_fee',
        ],
    },
    {
        id: 'settle',
        zh: '最终核算',
        gateCodes: [],
    },
];

const GATE_LABELS = {
    vehicle_model: '本期有效范围',
    stamping_process: '冲压工艺',
    tonnage_price: '冲次单价',
    die_unit_price: '模具单价',
    welding_unit_price: '焊接单价',
    bom_snapshot: '材料清单',
    annual_part_price: '年度零件价',
    packaging_transport: '包装运输费',
    base_price: '基准价格',
    thickness_policy: '厚度加减价',
    scrap_price: '废料价',
    system_rates: '系统费率',
    annual_process_fee: '冲压加工费',
    annual_die_fee: '冲压模具费',
    annual_procurement_object: '采购对象清单',
    annual_welding_breakdown: '焊接工艺拆解',
    annual_welding_fee: '焊接费',
};

const STATUS_META = {
    running: { label: '运行中', className: 'text-neutral-300' },
    succeeded: { label: '核算完成', className: 'text-neutral-400' },
    partial: { label: '部分完成', className: 'text-amber-500/80' },
    failed: { label: '核算失败', className: 'text-[#FF1E27]' },
    blocked: { label: '强约束阻断', className: 'text-[#FF1E27]' },
    deleted: { label: '已删除', className: 'text-neutral-700' },
};

const STEP_STAGE_META = {
    steel: { label: '钢材联动', page: 'steel-price-calc', action: '去看钢材价' },
    part_cost: { label: '零件核价', page: 'stamping-part-cost-calc', action: '去看零件价' },
    assembly: { label: '总成核价', page: 'assembly-cost-calc', action: '去看计算历史' },
    annual_process_fee: {
        label: '冲压加工费',
        page: 'stamping-process-fee-calc',
        action: '去看加工费',
    },
    annual_die_fee: {
        label: '冲压模具费',
        page: 'stamping-die-fee-calc',
        action: '去看模具费',
    },
    annual_procurement_object: {
        label: '采购对象清单',
        page: 'bom-procurement-object',
        action: '去生成采购对象',
    },
    annual_welding_breakdown: {
        label: '焊接工艺拆解',
        page: 'bom-welding-process-breakdown',
        action: '去看拆解',
    },
    annual_welding_fee: { label: '焊接费', page: 'bom-welding-fee-calc', action: '去看焊接费' },
};

const engineState = {
    canRun: true,
    canDelete: true,
    ready: null,
    isRunning: false,
    isCheckingReady: false,
    isStarting: false,
    isDeleting: false,
    activeTaskId: null,
    activeRunId: null,
    pollTimer: null,
    pollInFlight: false,
    runProgress: 0,
    gatesDetailOpen: false,
    scopeExpanded: new Set(),
    scopeSelected: null,
    history: {
        page: 1,
        size: DEFAULT_PAGE_SIZE,
        total: 0,
        items: [],
    },
    customSelects: new Map(),
};

export const CostingPage = {
    init() {
        stopPolling();
        destroyCustomSelects();
        bindEvents();
        bindSelectChangeListeners();
        mountEngineCustomSelects([
            'engineLocation',
            'engineYear',
            'engineMonth',
        ]);
        bindPagination({
            selectId: 'engineHistoryPageSize',
            buttonsId: 'engineHistoryPager',
            getSize: () => engineState.history.size,
            setSize: (size) => {
                engineState.history.size = size;
            },
            onPage: (page) => loadHistory(page),
        });
        applyPermissionUi();
        restoreContext();
        refreshEngineCustomSelect('engineYear');
        refreshEngineCustomSelect('engineMonth');
        renderPipeline();
        updateIgnitionLed();
        loadLocations().then(() => {
            refreshEngineCustomSelect('engineLocation');
            // 不自动检查就绪：必须用户显式点「检查就绪」后才能启动
        });
        invalidateReady({ keepPanels: true });
        loadHistory(1);
    },
};

export function destroy() {
    stopPolling();
    destroyCustomSelects();
}

function applyPermissionUi() {
    engineState.canRun = typeof can === 'function' ? can('op:costing:run') : true;
    engineState.canDelete = typeof can === 'function' ? can('op:costing:delete') : true;
    document
        .getElementById('engineHistoryDeleteAllBtn')
        ?.classList.toggle('hidden', !engineState.canDelete);
    updateStartButton();
}

/** 自绘下拉：规避 Chrome 原生 option 浅蓝高亮 */
function mountEngineCustomSelects(selectIds) {
    selectIds.forEach((id) => mountEngineCustomSelect(id));
}

function destroyCustomSelects() {
    engineState.customSelects.forEach((api) => api.destroy());
    engineState.customSelects.clear();
    document.removeEventListener('click', onEngineSelectDocClick, true);
    document.removeEventListener('keydown', onEngineSelectKeydown, true);
}

function onEngineSelectDocClick(event) {
    engineState.customSelects.forEach((api) => {
        if (!api.wrap.contains(event.target)) api.close();
    });
}

function onEngineSelectKeydown(event) {
    if (event.key !== 'Escape') return;
    engineState.customSelects.forEach((api) => api.close());
}

function refreshEngineCustomSelect(selectId) {
    const api = engineState.customSelects.get(selectId);
    if (api) api.refresh();
}

function mountEngineCustomSelect(selectId) {
    const select = document.getElementById(selectId);
    if (!select || engineState.customSelects.has(selectId)) return;

    const isSm = select.classList.contains('engine-select-source-sm');
    const wrap = document.createElement('div');
    wrap.className = `engine-select-wrap${isSm ? ' is-sm' : ''}`;
    select.parentNode.insertBefore(wrap, select);
    wrap.appendChild(select);
    select.classList.add('engine-select-native');

    const trigger = document.createElement('button');
    trigger.type = 'button';
    trigger.className = 'engine-select-trigger';
    trigger.setAttribute('aria-haspopup', 'listbox');
    trigger.setAttribute('aria-expanded', 'false');

    const label = document.createElement('span');
    label.className = 'engine-select-label truncate';
    const caret = document.createElement('span');
    caret.className = 'engine-select-caret';
    caret.setAttribute('aria-hidden', 'true');
    trigger.appendChild(label);
    trigger.appendChild(caret);

    const menu = document.createElement('div');
    menu.className = 'engine-select-menu hidden';
    menu.setAttribute('role', 'listbox');

    wrap.appendChild(trigger);
    wrap.appendChild(menu);

    const syncLabel = () => {
        const opt = select.options[select.selectedIndex];
        label.textContent = opt ? opt.textContent : '';
    };

    const rebuildMenu = () => {
        menu.innerHTML = '';
        Array.from(select.options).forEach((opt) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = `engine-select-option${
                opt.value === select.value ? ' is-selected' : ''
            }`;
            btn.setAttribute('role', 'option');
            btn.setAttribute('data-value', opt.value);
            btn.textContent = opt.textContent;
            if (opt.disabled) {
                btn.disabled = true;
                btn.classList.add('opacity-40');
            }
            btn.addEventListener('click', (event) => {
                event.preventDefault();
                event.stopPropagation();
                if (select.value !== opt.value) {
                    select.value = opt.value;
                    select.dispatchEvent(new Event('change', { bubbles: true }));
                }
                syncLabel();
                rebuildMenu();
                close();
            });
            menu.appendChild(btn);
        });
    };

    const close = () => {
        wrap.classList.remove('is-open');
        menu.classList.add('hidden');
        trigger.setAttribute('aria-expanded', 'false');
    };

    const open = () => {
        engineState.customSelects.forEach((other, id) => {
            if (id !== selectId) other.close();
        });
        rebuildMenu();
        wrap.classList.add('is-open');
        menu.classList.remove('hidden');
        trigger.setAttribute('aria-expanded', 'true');
    };

    const toggle = (event) => {
        event.preventDefault();
        event.stopPropagation();
        if (wrap.classList.contains('is-open')) close();
        else open();
    };

    const onNativeChange = () => {
        syncLabel();
        rebuildMenu();
    };

    trigger.addEventListener('click', toggle);
    select.addEventListener('change', onNativeChange);

    if (engineState.customSelects.size === 0) {
        document.addEventListener('click', onEngineSelectDocClick, true);
        document.addEventListener('keydown', onEngineSelectKeydown, true);
    }

    syncLabel();
    rebuildMenu();

    engineState.customSelects.set(selectId, {
        wrap,
        close,
        refresh: () => {
            syncLabel();
            rebuildMenu();
        },
        destroy: () => {
            close();
            trigger.removeEventListener('click', toggle);
            select.removeEventListener('change', onNativeChange);
            if (wrap.parentNode) {
                wrap.parentNode.insertBefore(select, wrap);
                wrap.remove();
            }
            select.classList.remove('engine-select-native');
        },
    });
}

function bindEvents() {
    document.getElementById('engineReadyBtn')?.addEventListener('click', () => checkReady());
    document.getElementById('engineStartBtn')?.addEventListener('click', () => startRun());
    document
        .getElementById('engineHistoryDeleteAllBtn')
        ?.addEventListener('click', () => deleteAllRuns());
    document.getElementById('engineHistoryBody')?.addEventListener('click', (event) => {
        const delBtn = event.target.closest('[data-action="delete-run"]');
        if (delBtn) {
            const runId = Number(delBtn.getAttribute('data-run-id'));
            if (runId) deleteRun(runId);
            return;
        }
        const openBtn = event.target.closest('[data-action="open-run"]');
        if (!openBtn) return;
        const runId = Number(openBtn.getAttribute('data-run-id'));
        if (runId) openRun(runId);
    });
    document.getElementById('engineResultSteps')?.addEventListener('click', (event) => {
        const navBtn = event.target.closest('[data-action="navigate"]');
        if (!navBtn) return;
        const page = navBtn.getAttribute('data-page');
        const queryRaw = navBtn.getAttribute('data-query') || '{}';
        let query = {};
        try {
            query = JSON.parse(queryRaw);
        } catch (_) {
            query = {};
        }
        navigateWithQuery(page, query);
    });
    document.getElementById('engineGateHardList')?.addEventListener('click', (event) => {
        const toggle = event.target.closest('[data-action="toggle-gates-detail"]');
        if (toggle) {
            engineState.gatesDetailOpen = !engineState.gatesDetailOpen;
            renderGateHardList(engineState.ready);
            return;
        }
        const navBtn = event.target.closest('[data-action="navigate"]');
        if (!navBtn) return;
        const page = navBtn.getAttribute('data-page');
        const queryRaw = navBtn.getAttribute('data-query') || '{}';
        let query = {};
        try {
            query = JSON.parse(queryRaw);
        } catch (_) {
            query = {};
        }
        navigateWithQuery(page, query);
    });
    document.getElementById('enginePlanTree')?.addEventListener('click', (event) => {
        const toggle = event.target.closest('[data-action="scope-toggle"]');
        if (toggle) {
            const key = toggle.getAttribute('data-scope-key');
            if (!key) return;
            if (engineState.scopeExpanded.has(key)) {
                engineState.scopeExpanded.delete(key);
            } else {
                engineState.scopeExpanded.add(key);
            }
            engineState.scopeSelected = key;
            renderPlanScope();
            return;
        }
        const select = event.target.closest('[data-action="scope-select"]');
        if (select) {
            const key = select.getAttribute('data-scope-key');
            engineState.scopeSelected = key;
            renderPlanScope();
        }
    });
}

function bindSelectChangeListeners() {
    ['engineLocation', 'engineYear', 'engineMonth'].forEach((id) => {
        document.getElementById(id)?.addEventListener('change', () => {
            persistContext();
            // 账期/基地一变，上次检查结果立即作废
            invalidateReady();
        });
    });
}

function getInputs() {
    return {
        location: document.getElementById('engineLocation')?.value?.trim() || '',
        year: Number(document.getElementById('engineYear')?.value || 0),
        month: Number(document.getElementById('engineMonth')?.value || 0),
    };
}

/** 最近一次检查结果是否对应当前筛选 */
function matchesReadyInputs() {
    const ready = engineState.ready;
    if (!ready) return false;
    const inputs = getInputs();
    const checked = ready.input || {};
    return (
        String(checked.location || '').trim() === inputs.location &&
        Number(checked.year) === inputs.year &&
        Number(checked.month) === inputs.month
    );
}

/** 当前筛选已检查且可启动 */
function isReadyForCurrentInputs() {
    return matchesReadyInputs() && !!engineState.ready?.can_start;
}

/**
 * 作废检查结果（换基地/年月，或进页重置）
 * @param {{ keepPanels?: boolean }} [options] keepPanels=true 时仅清状态、不刷占位文案（进页模板已是占位）
 */
function invalidateReady(options = {}) {
    engineState.ready = null;
    engineState.gatesDetailOpen = false;
    if (!options.keepPanels) {
        resetReadyPanels();
    }
    updateStartButton();
}

function resetReadyPanels() {
    const badge = document.getElementById('engineHardStopBadge');
    if (badge) {
        badge.textContent = '未检查';
        badge.className = 'text-[10px] text-neutral-600';
    }
    const hardList = document.getElementById('engineGateHardList');
    if (hardList) {
        hardList.innerHTML =
            '<div class="py-6 text-[10px] text-neutral-700">请先点击「检查就绪」</div>';
    }
    const annualBadge = document.getElementById('engineAnnualBadge');
    if (annualBadge) {
        annualBadge.textContent = '未检查';
        annualBadge.className = 'text-[10px] text-neutral-600';
    }
    const annualList = document.getElementById('engineGateAnnualList');
    if (annualList) {
        annualList.innerHTML =
            '<div class="py-6 text-[10px] text-neutral-700">请先点击「检查就绪」</div>';
    }
    const scopeSummary = document.getElementById('engineScopeSummary');
    if (scopeSummary) {
        scopeSummary.textContent = '节点 0';
        scopeSummary.className =
            'text-[10px] font-mono text-neutral-600 tabular-nums';
    }
    const tree = document.getElementById('enginePlanTree');
    if (tree) {
        tree.innerHTML =
            '<div class="py-6 text-[10px] text-neutral-700">请先检查就绪</div>';
    }
}

function persistContext() {
    const inputs = getInputs();
    try {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(inputs));
    } catch (_) {
        /* ignore */
    }
}

function readStoredContext() {
    try {
        const raw = sessionStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : null;
    } catch (_) {
        return null;
    }
}

function restoreContext() {
    const ctx = readStoredContext();
    if (!ctx) return;
    if (ctx.year) {
        const yearEl = document.getElementById('engineYear');
        if (yearEl) yearEl.value = String(ctx.year);
    }
    if (ctx.month) {
        const monthEl = document.getElementById('engineMonth');
        if (monthEl) monthEl.value = String(ctx.month);
    }
    engineState._pendingLocation = ctx.location || '';
}

async function loadLocations() {
    const select = document.getElementById('engineLocation');
    if (!select) return;
    try {
        const res = await HttpClient.get(CASCADE_API, { params: {} });
        const locations = res.data?.locations || [];
        const list = Array.isArray(locations) ? locations : [];
        select.innerHTML = list.length
            ? list.map((loc) => `<option value="${esc(loc)}">${esc(loc)}</option>`).join('')
            : '<option value="">无基地数据</option>';
        if (engineState._pendingLocation && list.includes(engineState._pendingLocation)) {
            select.value = engineState._pendingLocation;
        }
        refreshEngineCustomSelect('engineLocation');
    } catch (_) {
        select.innerHTML = '<option value="">加载失败</option>';
        refreshEngineCustomSelect('engineLocation');
    }
}

async function checkReady() {
    if (engineState.isCheckingReady || engineState.isStarting || engineState.isRunning) {
        return;
    }
    const { location, year, month } = getInputs();
    if (!location || !year || !month) {
        showToast('请选择基地、年度、月份', 'warning');
        return;
    }
    persistContext();
    engineState.isCheckingReady = true;
    setReadyButtonBusy(true);
    updateStartButton();
    try {
        const res = await HttpClient.get(READY_API, {
            params: { location, year, month },
        });
        engineState.ready = res.data;
        renderReady(res.data);
    } catch (_) {
        engineState.ready = null;
    } finally {
        engineState.isCheckingReady = false;
        setReadyButtonBusy(false);
        updateStartButton();
    }
}

function setReadyButtonBusy(busy) {
    const btn = document.getElementById('engineReadyBtn');
    if (!btn) return;
    btn.disabled = !!busy;
    btn.classList.toggle('opacity-50', !!busy);
    btn.classList.toggle('cursor-not-allowed', !!busy);
    btn.setAttribute('aria-busy', busy ? 'true' : 'false');
}

function gateLabel(code) {
    return GATE_LABELS[code] || '待补算项';
}

function formatAnnualScopeKey(scopeKey) {
    const key = String(scopeKey || '').trim();
    if (!key) return '';
    if (key.includes('|')) {
        const [vehicleModel, bomVersion] = key.split('|');
        const project = String(vehicleModel || '').trim();
        const version = String(bomVersion || '').trim();
        if (project && version) return `项目 ${project} · 版本 ${version}`;
        if (project) return `项目 ${project}`;
        if (version) return `版本 ${version}`;
    }
    return `项目 ${key}`;
}

function summarizeGateMessage(item) {
    const msg = (item.message || '').trim();
    if (!msg) return '—';
    return msg
        .replace(/该月有效期内项目\s*(\d+)\s*个/, '有效 $1')
        .replace(/该月有效冲压工艺\s*(\d+)\s*个项目/, '工艺 $1')
        .replace(/已发现\s*(\d+)\s*个项目/, '$1 项目发现')
        .replace(/已发现\s*(\d+)\s*个冲压工厂/, '$1 工厂发现')
        .replace(/冲次单价\s*(\d+)\s*条/, '冲次 $1')
        .replace(/焊接单价\s*(\d+)\s*条/, '焊接 $1')
        .replace(/包装运输费约\s*(\d+)\s*条/, '包装 $1')
        .replace(/厚度政策匹配失败\s*(\d+)\s*项.*/, '厚度缺口 $1')
        .replace(/厚度加减价政策可匹配/, '厚度 OK')
        .replace(/基价覆盖完整，展开\s*(\d+)\s*行/, '基价 $1 行')
        .replace(/含 L0 的 BOM\s*(\d+)\s*版/, 'L0 BOM ×$1');
}

function renderReady(ready) {
    const hardStop = !!ready?.gates?.hard_stop;
    const softTipCount = (ready?.gates?.upload_or_config || []).filter(isSoftTip).length;
    const badge = document.getElementById('engineHardStopBadge');
    if (badge) {
        if (hardStop) {
            badge.textContent = '需处理';
            badge.className = 'text-[10px] text-[#FF1E27]';
        } else if (ready) {
            badge.textContent = softTipCount ? '有提示' : '已就绪';
            badge.className = 'text-[10px] text-neutral-600';
        } else {
            badge.textContent = '未检查';
            badge.className = 'text-[10px] text-neutral-600';
        }
    }

    // 有异常时默认收起通过项；全部通过时也保持折叠摘要
    engineState.gatesDetailOpen = false;
    renderGateHardList(ready);

    const annual = ready?.gates?.annual_derived || [];
    const willCalc = annual.filter((a) => a.will_auto_calc);
    const annualBadge = document.getElementById('engineAnnualBadge');
    if (annualBadge) {
        annualBadge.textContent = willCalc.length
            ? `${willCalc.length} 项`
            : '无待补算';
        annualBadge.className = willCalc.length
            ? 'text-[10px] text-amber-500/80'
            : 'text-[10px] text-neutral-600';
    }
    const annualList = document.getElementById('engineGateAnnualList');
    if (annualList) {
        if (!willCalc.length) {
            annualList.innerHTML =
                '<div class="text-[11px] text-neutral-600 py-1">年度派生数据已齐备</div>';
        } else {
            annualList.innerHTML = willCalc
                .map(
                    (item) => `
                <div class="flex items-center justify-between gap-3 py-2 border-b border-white/5">
                    <div class="min-w-0">
                        <div class="text-[12px] text-amber-500/90">${esc(gateLabel(item.code))}</div>
                        <div class="text-[10px] text-neutral-600 truncate mt-0.5">${esc(formatAnnualScopeKey(item.scope_key))}</div>
                    </div>
                    <span class="text-[10px] text-amber-500/70 shrink-0">待补算</span>
                </div>`
                )
                .join('');
        }
    }

    const vehicles = ready?.plan?.part_cost_scopes || [];
    const l0Scopes = ready?.plan?.l0_scopes || [];
    if (!engineState.scopeExpanded.size) {
        if (vehicles.length) engineState.scopeExpanded.add('branch:vehicle');
        if (l0Scopes.length) engineState.scopeExpanded.add('branch:l0');
    }
    renderPlanScope();

    const scopeSummary = document.getElementById('engineScopeSummary');
    if (scopeSummary) {
        const nodeCount = vehicles.length + l0Scopes.length;
        scopeSummary.textContent = `节点 ${nodeCount}`;
        scopeSummary.className = 'text-[10px] font-mono text-neutral-600 tabular-nums';
    }

    updateReadyStatus();
    renderPipeline();
    updateIgnitionLed();
}

function renderGateHardList(ready) {
    const hardList = document.getElementById('engineGateHardList');
    if (!hardList) return;

    const items = sortGateItems(ready?.gates?.upload_or_config || []);
    if (!items.length) {
        hardList.innerHTML =
            '<div class="py-6 text-[10px] text-neutral-700">暂无检查项</div>';
        return;
    }

    const attention = items.filter((item) => isHardFail(item) || isSoftTip(item));
    const passed = items.filter((item) => !isHardFail(item) && !isSoftTip(item));
    const open = engineState.gatesDetailOpen;

    const attentionHtml = attention.length
        ? attention.map((item) => renderGateRow(item)).join('')
        : '';

    const summaryHtml = passed.length
        ? `
        <button type="button"
                data-action="toggle-gates-detail"
                class="w-full text-left py-2 text-[11px] text-neutral-500 hover:text-neutral-300 transition-colors">
            <span class="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500/70 mr-2 align-middle"></span>
            ${passed.length} 项基础约束已校验通过
            <span class="text-neutral-700 ml-2">${open ? '收起明细' : '展开明细'}</span>
        </button>`
        : '';

    const passedDetailHtml =
        open && passed.length
            ? `<div class="mt-1 space-y-0 opacity-60">${passed.map((item) => renderGateRow(item)).join('')}</div>`
            : '';

    if (!attention.length && !passed.length) {
        hardList.innerHTML =
            '<div class="py-6 text-[10px] text-neutral-700">暂无检查项</div>';
        return;
    }

    hardList.innerHTML = `
        <div class="space-y-1">
            ${attentionHtml}
            ${summaryHtml}
            ${passedDetailHtml}
        </div>`;

    if (attention.some(isHardFail)) {
        requestAnimationFrame(() => scrollGateBlockerIntoView(hardList));
    }
}

function isSoftGate(item) {
    return SOFT_GATE_CODES.has(item?.code);
}

function isHardFail(item) {
    return !!item && !item.ok && !isSoftGate(item);
}

function isSoftTip(item) {
    if (!isSoftGate(item)) return false;
    return !!(item.navigate || (item.missing || []).length);
}

function sortGateItems(items) {
    return [...items].sort((a, b) => gateSortRank(a) - gateSortRank(b));
}

function gateSortRank(item) {
    if (isHardFail(item)) return 0;
    if (isSoftTip(item)) return 1;
    return 2;
}

function scrollGateBlockerIntoView(hardList) {
    const blocker = hardList.querySelector('[data-gate-role="hard-fail"]');
    if (!blocker) return;
    blocker.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    document.getElementById('engineGateHardPanel')?.scrollIntoView({
        block: 'nearest',
        behavior: 'smooth',
    });
}

function renderGateRow(item) {
    const soft = isSoftTip(item);
    const hardFail = isHardFail(item);
    const nav = item.navigate;
    const canPage = nav?.page
        ? typeof canAccessPage === 'function'
            ? canAccessPage(nav.page)
            : true
        : false;
    const zhTitle = gateLabel(item.code);
    const summary = summarizeGateMessage(item);
    const missingHint = (item.missing || [])[0] || '';
    const line = missingHint ? `${summary} · ${missingHint}` : summary;
    const role = hardFail ? 'hard-fail' : soft ? 'soft-tip' : 'ok';

    let actionHtml = '';
    if (nav && (hardFail || soft)) {
        if (canPage) {
            actionHtml = `
                <button type="button"
                        data-action="navigate"
                        data-page="${esc(nav.page)}"
                        data-query='${esc(JSON.stringify(nav.query || {}))}'
                        class="shrink-0 text-[10px] ${hardFail ? 'text-[#FF1E27] hover:text-white' : 'text-amber-500/80 hover:text-amber-400'}">
                    去处理 →
                </button>`;
        } else {
            actionHtml = '<span class="shrink-0 text-[9px] text-neutral-700">无权限</span>';
        }
    }

    if (hardFail) {
        return `
        <div data-gate-role="${role}" data-gate-code="${esc(item.code)}"
             class="flex items-start justify-between gap-3 py-2.5 border-b border-white/5 border-l-2 border-l-[#FF1E27] pl-3 -ml-0.5">
            <div class="min-w-0 flex-1">
                <div class="text-[12px] text-white">${esc(zhTitle)}</div>
                <p class="text-[10px] text-neutral-500 truncate mt-0.5" title="${esc(line)}">${esc(line)}</p>
            </div>
            ${actionHtml}
        </div>`;
    }

    if (soft) {
        return `
        <div data-gate-role="${role}" data-gate-code="${esc(item.code)}"
             class="flex items-start justify-between gap-3 py-2.5 border-b border-white/5 border-l-2 border-l-amber-500/60 pl-3 -ml-0.5">
            <div class="min-w-0 flex-1">
                <div class="text-[12px] text-neutral-200">${esc(zhTitle)}</div>
                <p class="text-[10px] text-neutral-500 truncate mt-0.5" title="${esc(line)}">${esc(line)}</p>
            </div>
            ${actionHtml}
        </div>`;
    }

    // 通过项：仅在展开明细中出现，无绿色徽章
    return `
        <div data-gate-role="${role}" data-gate-code="${esc(item.code)}"
             class="flex items-center justify-between gap-3 py-1.5 border-b border-white/5">
            <div class="min-w-0 flex-1">
                <span class="text-[11px] text-neutral-500">${esc(zhTitle)}</span>
                <span class="text-[10px] text-neutral-700 ml-2 truncate">${esc(line)}</span>
            </div>
        </div>`;
}

function updateReadyStatus() {
    const led = document.getElementById('engineReadyLed');
    const text = document.getElementById('engineReadyStatusText');
    if (!led || !text) return;

    const ready = matchesReadyInputs() ? engineState.ready : null;
    const hardStop = !!ready?.gates?.hard_stop;
    const canStart = !!ready?.can_start;

    if (engineState.isRunning || engineState.isStarting) {
        led.className = 'w-1.5 h-1.5 bg-[#FF1E27] shrink-0';
        text.textContent = '引擎点火';
        text.className = 'text-[10px] text-[#FF1E27]/80';
        return;
    }
    if (!ready) {
        led.className = 'w-1.5 h-1.5 bg-neutral-700 shrink-0';
        text.textContent = '待命';
        text.className = 'text-[10px] text-neutral-500';
        return;
    }
    if (hardStop || !canStart) {
        led.className = 'w-1.5 h-1.5 bg-[#FF1E27] shrink-0';
        text.textContent = '强约束阻断';
        text.className = 'text-[10px] text-[#FF1E27]/80';
        return;
    }
    led.className = 'w-1.5 h-1.5 bg-emerald-500/70 shrink-0';
    text.textContent = '系统就绪';
    text.className = 'text-[10px] text-neutral-500';
}

function updateIgnitionLed() {
    const led = document.getElementById('engineIgnitionLed');
    if (!led) return;

    led.classList.remove('engine-ignition-ready', 'engine-ignition-running');

    if (engineState.isRunning || engineState.isStarting) {
        led.className =
            'w-2 h-2 rounded-full bg-emerald-500/80 shrink-0 engine-ignition-running';
        return;
    }

    const canIgnite =
        isReadyForCurrentInputs() &&
        engineState.canRun &&
        !engineState.isCheckingReady;

    if (canIgnite) {
        led.className =
            'w-2 h-2 rounded-full bg-[#FF1E27] shrink-0 engine-ignition-ready';
        return;
    }

    if (matchesReadyInputs() && !engineState.ready.can_start) {
        led.className = 'w-2 h-2 rounded-full bg-[#FF1E27]/35 shrink-0';
        return;
    }

    led.className = 'w-2 h-2 rounded-full bg-neutral-700 shrink-0';
}

/**
 * 门禁 → 管道阶梯状态：idle | pending | active | passed | failed
 */
function resolvePipelineStages() {
    const ready = engineState.ready;
    const gates = ready?.gates?.upload_or_config || [];
    const annual = ready?.gates?.annual_derived || [];
    const gateByCode = new Map(gates.map((g) => [g.code, g]));

    const stageHasHardFail = (stage) =>
        stage.gateCodes.some((code) => {
            const item = gateByCode.get(code);
            return item ? isHardFail(item) : false;
        });

    const stageHasSoftTip = (stage) =>
        stage.gateCodes.some((code) => {
            const item = gateByCode.get(code);
            return item ? isSoftTip(item) : false;
        });

    const stageAllOk = (stage) => {
        if (!stage.gateCodes.length) return true;
        return stage.gateCodes.every((code) => {
            const item = gateByCode.get(code);
            if (!item) return true;
            return !isHardFail(item);
        });
    };

    const annualPending = annual.some((a) => a.will_auto_calc);

    if (engineState.isRunning || engineState.isStarting) {
        const pct = Math.max(0, Math.min(100, engineState.runProgress || 0));
        const activeIdx = Math.min(
            PIPELINE_STAGES.length - 1,
            Math.floor((pct / 100) * PIPELINE_STAGES.length)
        );
        return PIPELINE_STAGES.map((stage, idx) => {
            if (idx < activeIdx) return { ...stage, state: 'passed' };
            if (idx === activeIdx) return { ...stage, state: 'active' };
            return { ...stage, state: 'pending' };
        });
    }

    if (!ready) {
        return PIPELINE_STAGES.map((stage) => ({ ...stage, state: 'idle' }));
    }

    if (ready.gates?.hard_stop) {
        let failedSeen = false;
        return PIPELINE_STAGES.map((stage, idx) => {
            if (stage.id === 'settle') {
                return { ...stage, state: 'pending' };
            }
            if (stage.id === 'aggregate') {
                return {
                    ...stage,
                    state: annualPending ? 'pending' : 'passed',
                };
            }
            if (failedSeen) return { ...stage, state: 'pending' };
            if (stageHasHardFail(stage)) {
                failedSeen = true;
                return { ...stage, state: 'failed' };
            }
            if (stageAllOk(stage)) {
                return {
                    ...stage,
                    state: stageHasSoftTip(stage) ? 'soft' : 'passed',
                };
            }
            if (idx === 0) return { ...stage, state: 'failed' };
            return { ...stage, state: 'pending' };
        });
    }

    if (ready.can_start) {
        return PIPELINE_STAGES.map((stage) => {
            if (stage.id === 'aggregate' && annualPending) {
                return { ...stage, state: 'soft' };
            }
            if (stage.id === 'settle') {
                return { ...stage, state: 'passed' };
            }
            if (stageHasSoftTip(stage)) {
                return { ...stage, state: 'soft' };
            }
            return { ...stage, state: 'passed' };
        });
    }

    return PIPELINE_STAGES.map((stage) => ({ ...stage, state: 'pending' }));
}

function renderPipeline() {
    const track = document.getElementById('enginePipelineTrack');
    const statusEl = document.getElementById('enginePipelineStatus');
    if (!track) return;

    const stages = resolvePipelineStages();
    const hasFailed = stages.some((s) => s.state === 'failed');
    const allPassed = stages.every(
        (s) => s.state === 'passed' || s.state === 'soft'
    );

    if (statusEl) {
        if (engineState.isRunning || engineState.isStarting) {
            statusEl.textContent = '运行中';
            statusEl.className = 'text-[10px] text-neutral-500';
        } else if (hasFailed) {
            statusEl.textContent = '阻断';
            statusEl.className = 'text-[10px] text-[#FF1E27]/70';
        } else if (allPassed && engineState.ready?.can_start) {
            statusEl.textContent = '已放行';
            statusEl.className = 'text-[10px] text-neutral-600';
        } else if (engineState.ready) {
            statusEl.textContent = '待放行';
            statusEl.className = 'text-[10px] text-neutral-600';
        } else {
            statusEl.textContent = '待命';
            statusEl.className = 'text-[10px] text-neutral-700';
        }
    }

    // 默认极暗；仅失败/运行中节点略提亮
    const stateStyle = {
        idle: { dot: 'bg-neutral-800', label: 'text-neutral-700', line: 'bg-neutral-800' },
        pending: { dot: 'bg-neutral-800', label: 'text-neutral-600', line: 'bg-neutral-800' },
        active: { dot: 'bg-[#FF1E27]/80', label: 'text-neutral-300', line: 'bg-neutral-800' },
        passed: { dot: 'bg-neutral-700', label: 'text-neutral-600', line: 'bg-neutral-800' },
        soft: { dot: 'bg-amber-700/60', label: 'text-neutral-500', line: 'bg-neutral-800' },
        failed: { dot: 'bg-[#FF1E27]', label: 'text-[#FF1E27]/80', line: 'bg-neutral-800' },
    };

    track.className = 'relative flex items-stretch gap-0 overflow-x-auto py-1';
    track.innerHTML = stages
        .map((stage, idx) => {
            const style = stateStyle[stage.state] || stateStyle.idle;
            const isLast = idx === stages.length - 1;
            const connector = isLast
                ? ''
                : `<div class="flex-1 min-w-[16px] h-px self-center mx-1 ${style.line}"></div>`;
            return `
            <div class="flex items-center min-w-0 flex-1">
                <div class="flex flex-col items-center min-w-[64px] px-0.5">
                    <span class="w-1.5 h-1.5 rounded-full shrink-0 ${style.dot}"></span>
                    <span class="mt-2 text-[9px] tracking-wide ${style.label} whitespace-nowrap">${esc(stage.zh)}</span>
                </div>
                ${connector}
            </div>`;
        })
        .join('');
}

function renderPlanScope() {
    const tree = document.getElementById('enginePlanTree');
    if (!tree) return;

    const ready = engineState.ready;
    if (!ready) {
        tree.innerHTML =
            '<div class="py-6 text-[10px] text-neutral-700">请先检查就绪</div>';
        return;
    }

    const vehicles = ready?.plan?.part_cost_scopes || [];
    const l0Scopes = ready?.plan?.l0_scopes || [];
    const steel = ready?.plan?.steel || {};
    const location = steel.location || ready?.input?.location || '—';
    const period = fmtPeriod(steel.year, steel.month) || '—';

    if (!vehicles.length && !l0Scopes.length) {
        tree.innerHTML =
            '<div class="py-6 text-[10px] text-neutral-700">暂无覆盖节点</div>';
        return;
    }

    const vehicleKey = 'branch:vehicle';
    const l0Key = 'branch:l0';
    const vehicleOpen = engineState.scopeExpanded.has(vehicleKey);
    const l0Open = engineState.scopeExpanded.has(l0Key);

    const branchHeader = (key, title, count, open) => `
        <button type="button"
                data-action="scope-toggle"
                data-scope-key="${esc(key)}"
                class="w-full flex items-center justify-between gap-2 py-1.5 text-left hover:text-neutral-200 transition-colors">
            <div class="flex items-center gap-2 min-w-0">
                <span class="font-mono text-[9px] text-neutral-600 shrink-0">${open ? '▼' : '▶'}</span>
                <span class="text-[12px] text-neutral-300 truncate">${esc(title)}</span>
            </div>
            <span class="text-[10px] font-mono text-neutral-600 tabular-nums shrink-0">${count}</span>
        </button>`;

    const vehicleChildren = vehicleOpen
        ? vehicles
              .map((item, idx) => {
                  const name = item.vehicle_model || '';
                  const key = `vehicle:${name}`;
                  const selected = engineState.scopeSelected === key;
                  return `
                <button type="button"
                        data-action="scope-select"
                        data-scope-key="${esc(key)}"
                        class="w-full pl-5 py-1 flex items-center gap-2 text-left ${
                            selected ? 'text-white' : 'text-neutral-500 hover:text-neutral-300'
                        }">
                    <span class="text-[10px] font-mono text-neutral-700 tabular-nums shrink-0">${String(idx + 1).padStart(2, '0')}</span>
                    <span class="text-[11px] font-mono truncate" title="${esc(name)}">${esc(name)}</span>
                </button>`;
              })
              .join('')
        : '';

    const l0Children = l0Open
        ? l0Scopes
              .map((s) => {
                  const key = `l0:${s.vehicle_model}/${s.bom_version}`;
                  const open = engineState.scopeExpanded.has(key);
                  const selected = engineState.scopeSelected === key;
                  const detail = open
                      ? `
                    <div class="pl-8 py-1.5 space-y-0.5 text-[10px] text-neutral-600">
                        <div class="flex justify-between gap-2">
                            <span>项目</span>
                            <span class="font-mono text-neutral-400">${esc(s.vehicle_model)}</span>
                        </div>
                        <div class="flex justify-between gap-2">
                            <span>BOM 版本</span>
                            <span class="font-mono text-neutral-400">${esc(s.bom_version)}</span>
                        </div>
                        <div class="font-mono text-neutral-700">成品节点 × 1</div>
                    </div>`
                      : '';
                  return `
                <div>
                    <button type="button"
                            data-action="scope-toggle"
                            data-scope-key="${esc(key)}"
                            class="w-full pl-5 py-1 flex items-center justify-between gap-2 text-left ${
                                selected ? 'text-white' : 'text-neutral-500 hover:text-neutral-300'
                            }">
                        <div class="flex items-center gap-2 min-w-0">
                            <span class="font-mono text-[9px] text-neutral-700 shrink-0">${open ? '▼' : '▶'}</span>
                            <span class="text-[11px] font-mono truncate">${esc(s.vehicle_model)} / ${esc(s.bom_version)}</span>
                        </div>
                    </button>
                    ${detail}
                </div>`;
              })
              .join('')
        : '';

    tree.innerHTML = `
        <div class="space-y-1">
            <div class="flex items-baseline justify-between gap-3 py-1 mb-2">
                <div class="min-w-0">
                    <div class="text-[10px] text-neutral-700">生产基地</div>
                    <div class="text-[13px] font-mono text-neutral-200 truncate">${esc(location)}</div>
                </div>
                <div class="text-right shrink-0">
                    <div class="text-[10px] text-neutral-700">账期</div>
                    <div class="text-[12px] font-mono text-neutral-400 tabular-nums">${esc(period)}</div>
                </div>
            </div>
            <div>
                ${branchHeader(vehicleKey, '项目', vehicles.length, vehicleOpen)}
                ${vehicleChildren}
            </div>
            <div class="mt-2">
                ${branchHeader(l0Key, '项目 BOM', l0Scopes.length, l0Open)}
                ${l0Children}
            </div>
        </div>`;
}

/**
 * 确定性审计指纹（前端展示用，非服务端签名）
 */
function auditFingerprint(row) {
    const seed = [
        row.id,
        row.location || '',
        row.year,
        row.month,
        row.status || '',
        row.task_id || '',
        row.started_at || '',
        row.created_by || '',
    ].join('|');
    let hash = 0x811c9dc5;
    for (let i = 0; i < seed.length; i += 1) {
        hash ^= seed.charCodeAt(i);
        hash = Math.imul(hash, 0x01000193);
    }
    const primary = (hash >>> 0).toString(16).toUpperCase().padStart(8, '0');
    const secondary = (
        (Math.imul(Number(row.id) || 1, 0x4b2a) ^ (hash >>> 8)) >>>
        0
    )
        .toString(16)
        .toUpperCase()
        .padStart(8, '0')
        .slice(0, 4);
    return `0x${primary}${secondary}`;
}

function navigateWithQuery(page, query) {
    persistContext();
    const params = new URLSearchParams();
    Object.entries(query || {}).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
            params.set(key, String(value));
        }
    });
    const qs = params.toString();
    window.location.hash = qs ? `/${page}?${qs}` : `/${page}`;
}

function updateStartButton() {
    const btn = document.getElementById('engineStartBtn');
    const hint = document.getElementById('engineStartHint');
    if (!btn) return;

    const readyOk = isReadyForCurrentInputs();
    const canStart =
        readyOk &&
        engineState.canRun &&
        !engineState.isRunning &&
        !engineState.isStarting &&
        !engineState.isCheckingReady;
    btn.disabled = !canStart;
    btn.classList.toggle('hidden', false);

    updateReadyStatus();
    updateIgnitionLed();
    renderPipeline();

    let hintText = '';
    if (!engineState.canRun) {
        hintText = '当前账号无启动权限';
    } else if (!engineState.ready || !matchesReadyInputs()) {
        hintText = engineState.ready
            ? '筛选已变更，请重新点击「检查就绪」'
            : '';
    } else if (!engineState.ready.can_start) {
        hintText = '请先处理红色硬停项后再启动';
    } else if (canStart) {
        const hasSoftTip = (engineState.ready?.gates?.upload_or_config || []).some(isSoftTip);
        hintText = hasSoftTip
            ? '检查已通过，可直接启动（黄色提示可不处理）'
            : '检查已通过，可启动核算引擎';
    }

    if (hint) {
        if (hintText) {
            hint.textContent = hintText;
            hint.classList.remove('hidden');
            hint.className = canStart
                ? 'mt-3 text-[10px] text-neutral-500'
                : 'mt-3 text-[10px] text-neutral-600';
        } else {
            hint.textContent = '';
            hint.classList.add('hidden');
        }
    }

    btn.title = canStart
        ? '启动月度核价引擎'
        : !engineState.canRun
          ? '无启动权限'
          : !engineState.ready
            ? '请先点击「检查就绪」'
            : !matchesReadyInputs()
              ? '筛选已变更，请重新检查就绪'
              : !engineState.ready.can_start
                ? '请先通过硬停检查'
                : '';
}

async function startRun() {
    if (
        engineState.isStarting ||
        engineState.isRunning ||
        engineState.isCheckingReady
    ) {
        return;
    }
    if (!isReadyForCurrentInputs()) {
        showToast(
            engineState.ready
                ? '筛选已变更，请重新检查就绪'
                : '请先通过检查就绪',
            'warning'
        );
        return;
    }
    if (!engineState.canRun) {
        showToast('无启动权限', 'warning');
        return;
    }
    const { location, year, month } = getInputs();
    persistContext();
    engineState.isStarting = true;
    updateStartButton();
    setReadyButtonBusy(true);
    let shouldRecheck = false;
    try {
        const res = await HttpClient.post(RUNS_API, { location, year, month });
        const taskId = res.data?.task_id;
        if (!taskId) {
            showToast('未返回 task_id', 'error');
            return;
        }
        engineState.activeTaskId = taskId;
        engineState.isRunning = true;
        engineState.runProgress = 0;
        showProgress(0, '任务已提交…');
        startPolling(taskId);
        loadHistory(1);
    } catch (error) {
        const data = error?.data;
        if (data?.upload_or_config) {
            engineState.ready = {
                ...(engineState.ready || {}),
                can_start: false,
                gates: {
                    ...(engineState.ready?.gates || {}),
                    hard_stop: true,
                    upload_or_config: data.upload_or_config,
                    annual_derived: engineState.ready?.gates?.annual_derived || [],
                },
            };
            renderReady(engineState.ready);
        } else {
            shouldRecheck = true;
        }
    } finally {
        engineState.isStarting = false;
        if (!engineState.isRunning) {
            setReadyButtonBusy(false);
        }
        updateStartButton();
    }
    if (shouldRecheck) {
        await checkReady();
    }
}

function showProgress(percent, msg) {
    const panel = document.getElementById('engineProgressPanel');
    panel?.classList.remove('hidden');
    const bar = document.getElementById('engineProgressBar');
    const pct = document.getElementById('engineProgressPercent');
    const msgEl = document.getElementById('engineProgressMsg');
    const spinner = document.getElementById('engineProgressSpinner');
    engineState.runProgress = Math.max(0, Math.min(100, percent));
    if (bar) bar.style.width = `${engineState.runProgress}%`;
    if (pct) pct.textContent = `${Math.round(engineState.runProgress)}%`;
    if (msgEl) msgEl.textContent = msg || '—';
    spinner?.classList.remove('hidden');
    document.getElementById('engineResultPanel')?.classList.add('hidden');
    renderPipeline();
    updateIgnitionLed();
}

function hideProgressSpinner() {
    document.getElementById('engineProgressSpinner')?.classList.add('hidden');
}

function hideProgressPanel() {
    document.getElementById('engineProgressPanel')?.classList.add('hidden');
}

function showResult(result) {
    hideProgressPanel();
    engineState.runProgress = 100;
    const panel = document.getElementById('engineResultPanel');
    panel?.classList.remove('hidden');
    const status = result?.status || '—';
    const meta = STATUS_META[status] || { label: status, className: 'text-white' };
    const statusEl = document.getElementById('engineResultStatus');
    if (statusEl) {
        statusEl.textContent = meta.label;
        statusEl.className = `text-sm font-bold tracking-[0.06em] mt-0.5 ${meta.className}`;
    }
    const timingEl = document.getElementById('engineResultTiming');
    if (timingEl) {
        const timingText = formatResultTiming(result);
        if (timingText) {
            timingEl.textContent = timingText;
            timingEl.classList.remove('hidden');
        } else {
            timingEl.textContent = '';
            timingEl.classList.add('hidden');
        }
    }
    if (result?.run_id) {
        engineState.activeRunId = result.run_id;
    }
    const groups = classifyEngineSteps(result);
    const headlineEl = document.getElementById('engineResultHeadline');
    if (headlineEl) headlineEl.textContent = engineResultHeadline(groups);
    const stepsEl = document.getElementById('engineResultSteps');
    if (stepsEl) stepsEl.innerHTML = renderEngineStepGroups(result, groups);
    renderPipeline();
    updateIgnitionLed();
}

function classifyEngineSteps(result) {
    const groups = { failed: [], blocked: [], review: [], done: [] };
    const steps = Array.isArray(result?.steps) ? result.steps : [];
    steps.forEach((step) => {
        const message = String(step.message || '');
        if (step.status === 'failed') {
            groups.failed.push(step);
            return;
        }
        if (step.status === 'skipped') {
            if (message.includes('已有结果')) {
                groups.done.push(step);
            } else {
                groups.blocked.push(step);
            }
            return;
        }
        if (message.includes('部分成功') || /\bpartial\b/.test(message)) {
            groups.review.push(step);
            return;
        }
        groups.done.push(step);
    });
    return groups;
}

function engineResultHeadline(groups) {
    const failN = groups.failed.length;
    const blockN = groups.blocked.length;
    const reviewN = groups.review.length;
    if (failN) {
        return failN === 1
            ? `有 1 项核算失败：${formatStepTitle(groups.failed[0])}。请先处理下面清单。`
            : `有 ${failN} 项核算失败，请先处理下面清单。`;
    }
    if (blockN) {
        return `有 ${blockN} 项因上游未完成而未算，不是「已审核跳过」。`;
    }
    if (reviewN) {
        return `核算已跑完，有 ${reviewN} 项需到计算历史核对缺件。`;
    }
    return '本月计划内核算已完成。';
}

function formatStepScope(step) {
    const key = String(step.scope_key || '').trim();
    if (!key) return '';
    if (key.includes('|')) {
        const [vehicleModel, bomVersion] = key.split('|');
        const project = String(vehicleModel || '').trim();
        const version = String(bomVersion || '').trim();
        if (project && version) return `项目 ${project} · 版本 ${version}`;
        if (project) return `项目 ${project}`;
        if (version) return `版本 ${version}`;
    }
    return `项目 ${key}`;
}

function formatStepTitle(step) {
    const meta = STEP_STAGE_META[step.stage] || { label: step.stage || '核算步骤' };
    const scope = formatStepScope(step);
    return scope ? `${meta.label} ${scope}` : meta.label;
}

function stepNavQuery(result, step) {
    const query = {};
    if (result?.year != null) query.year = result.year;
    if (result?.month != null) query.month = result.month;
    if (result?.location) query.location = result.location;
    const key = String(step.scope_key || '');
    if (
        step.stage === 'assembly' ||
        step.stage === 'annual_welding_fee' ||
        step.stage === 'annual_welding_breakdown' ||
        step.stage === 'annual_procurement_object'
    ) {
        const [vehicleModel, bomVersion] = key.split('|');
        if (vehicleModel) query.vehicle_model = vehicleModel;
        if (bomVersion) query.bom_version = bomVersion;
    } else if (
        step.stage === 'part_cost' ||
        step.stage === 'annual_process_fee' ||
        step.stage === 'annual_die_fee'
    ) {
        if (key) query.vehicle_model = key;
    }
    return query;
}

function renderStepRows(result, steps, toneClass) {
    return steps
        .map((step) => {
            const meta = STEP_STAGE_META[step.stage] || {};
            const canPage =
                meta.page && typeof canAccessPage === 'function'
                    ? canAccessPage(meta.page)
                    : Boolean(meta.page);
            const query = stepNavQuery(result, step);
            const action = canPage
                ? `<button type="button" data-action="navigate" data-page="${esc(meta.page)}"
                        data-query='${esc(JSON.stringify(query))}'
                        class="shrink-0 text-[10px] ${toneClass}">${esc(meta.action || '去查看')} →</button>`
                : meta.page
                  ? '<span class="shrink-0 text-[9px] text-neutral-700">无权限</span>'
                  : '';
            const reason = step.message ? esc(step.message) : '';
            return `
            <div class="flex items-start justify-between gap-3 py-2.5 border-b border-white/5">
                <div class="min-w-0">
                    <div class="text-[11px] text-neutral-200">${esc(formatStepTitle(step))}</div>
                    ${reason ? `<div class="text-[10px] text-neutral-600 mt-0.5 leading-relaxed">${reason}</div>` : ''}
                </div>
                ${action}
            </div>`;
        })
        .join('');
}

function renderEngineStepGroups(result, groups) {
    const blocks = [];
    if (groups.failed.length) {
        blocks.push(`
            <div class="mb-4">
                <div class="text-[10px] text-[#FF1E27] mb-1">需要处理 · 失败 ${groups.failed.length}</div>
                ${renderStepRows(result, groups.failed, 'text-[#FF1E27] hover:text-white')}
            </div>`);
    }
    if (groups.blocked.length) {
        blocks.push(`
            <div class="mb-4">
                <div class="text-[10px] text-amber-500/80 mb-1">未执行 · 上游未完成 ${groups.blocked.length}</div>
                ${renderStepRows(result, groups.blocked, 'text-amber-500/80 hover:text-amber-400')}
            </div>`);
    }
    if (groups.review.length) {
        blocks.push(`
            <div class="mb-4">
                <div class="text-[10px] text-amber-500/80 mb-1">需要核对 · 部分成功 ${groups.review.length}</div>
                ${renderStepRows(result, groups.review, 'text-amber-500/80 hover:text-amber-400')}
            </div>`);
    }
    if (groups.done.length && (groups.failed.length || groups.blocked.length || groups.review.length)) {
        blocks.push(`
            <div class="text-[10px] text-neutral-700">其余 ${groups.done.length} 项已完成或已有结果，无需处理。</div>`);
    }
    return blocks.join('');
}

async function openRun(runId) {
    try {
        const res = await HttpClient.get(`${RUNS_API}/${runId}`);
        const run = res.data || {};
        const summary = run.summary_json || {};
        showResult({
            status: run.status || summary.status,
            location: run.location,
            year: run.year,
            month: run.month,
            run_id: run.id,
            started_at: run.started_at,
            finished_at: run.finished_at,
            duration_seconds: run.duration_seconds,
            steps: (run.steps && run.steps.length ? run.steps : summary.steps) || [],
        });
        document.getElementById('engineResultPanel')?.scrollIntoView({
            block: 'nearest',
            behavior: 'smooth',
        });
    } catch (_) {
        /* toast 由 HttpClient 统一拦截 */
    }
}

function startPolling(taskId) {
    stopPolling();
    engineState.pollTimer = setInterval(() => fetchTaskProgress(taskId), POLL_INTERVAL_MS);
    fetchTaskProgress(taskId);
}

function stopPolling() {
    if (engineState.pollTimer) {
        clearInterval(engineState.pollTimer);
        engineState.pollTimer = null;
    }
    engineState.pollInFlight = false;
}

async function fetchTaskProgress(taskId) {
    if (engineState.pollInFlight) return;
    engineState.pollInFlight = true;
    try {
        const res = await HttpClient.get(`${TASK_API}/${taskId}`);
        const data = res.data || {};
        const progress = Number(data.progress || 0);
        const msg = data.msg || '';
        showProgress(progress, msg);

        if (data.status === 'completed' || data.status === 'failed') {
            stopPolling();
            engineState.isRunning = false;
            engineState.isStarting = false;
            hideProgressSpinner();
            setReadyButtonBusy(false);
            const result = data.result || {};
            if (data.status === 'failed' && !result.status) {
                result.status = 'failed';
            }
            showResult(result);
            updateStartButton();
            loadHistory(1);
            if (result.status === 'succeeded') {
                showToast('核价引擎运行成功', 'success');
            } else if (result.status === 'partial') {
                showToast('核价引擎部分完成', 'warning');
            } else if (data.status === 'failed' || result.status === 'failed') {
                showToast(msg || '核价引擎运行失败', 'error');
            }
        }
    } catch (_) {
        /* toast 由 HttpClient 统一拦截 */
    } finally {
        engineState.pollInFlight = false;
    }
}

async function loadHistory(page) {
    engineState.history.page = page || 1;
    try {
        const res = await HttpClient.get(RUNS_API, {
            params: {
                page: engineState.history.page,
                size: engineState.history.size,
            },
        });
        const data = res.data || {};
        engineState.history.items = data.items || [];
        engineState.history.total = data.total || 0;
        renderHistory();
    } catch (_) {
        const body = document.getElementById('engineHistoryBody');
        if (body) {
            body.innerHTML = `<tr><td colspan="9" class="px-2 py-8 text-center text-[10px] text-[#FF1E27]/80">历史加载失败</td></tr>`;
        }
    }
}

function renderHistory() {
    const body = document.getElementById('engineHistoryBody');
    const totalEl = document.getElementById('engineHistoryTotal');
    if (totalEl) totalEl.textContent = `共 ${engineState.history.total} 条`;
    if (!body) return;

    const items = engineState.history.items;
    if (!items.length) {
        body.innerHTML = `<tr><td colspan="9" class="px-2 py-8 text-center text-[10px] text-neutral-700">暂无运行记录</td></tr>`;
        renderPager();
        return;
    }

    body.innerHTML = items
        .map((row) => {
            const meta = STATUS_META[row.status] || {
                label: row.status,
                className: 'text-neutral-600',
            };
            const fingerprint = auditFingerprint(row);
            const viewBtn = `<button type="button" data-action="open-run" data-run-id="${row.id}"
                        class="px-2 py-1 text-[10px] text-neutral-500 hover:text-white transition-colors">查看</button>`;
            const deleteBtn = engineState.canDelete
                ? `<button type="button" data-action="delete-run" data-run-id="${row.id}"
                        class="px-2 py-1 text-[10px] text-neutral-600 hover:text-[#FF1E27] transition-colors"
                        title="删除记录（不撤销已算价格）">删除</button>`
                : '';
            return `
            <tr class="engine-history-row group font-mono text-[11px] border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                <td class="px-2 py-2.5 overflow-hidden">
                    <div class="text-[13px] text-neutral-200 tabular-nums">#${esc(row.id)}</div>
                    <div class="engine-audit-hash text-[9px] text-neutral-700 mt-0.5 truncate" title="${esc(fingerprint)}">
                        ${esc(fingerprint)}
                    </div>
                </td>
                <td class="px-2 py-2.5 text-neutral-400 overflow-hidden truncate" title="${esc(row.location)}">${esc(row.location)}</td>
                <td class="px-2 py-2.5 text-right text-[10px] text-neutral-500 tabular-nums">${esc(fmtPeriod(row.year, row.month))}</td>
                <td class="px-2 py-2.5 text-center text-[10px] ${meta.className}">${esc(meta.label)}</td>
                <td class="px-2 py-2.5 text-[10px] text-neutral-500 overflow-hidden truncate">${esc(row.created_by || '-')}</td>
                <td class="px-2 py-2.5 text-[10px] text-neutral-600 tabular-nums">${esc(formatTs(row.started_at))}</td>
                <td class="px-2 py-2.5 text-[10px] text-neutral-600 tabular-nums">${esc(formatTs(row.finished_at))}</td>
                <td class="px-2 py-2.5 text-right text-[10px] text-neutral-400 tabular-nums">${esc(formatDurationSeconds(row))}</td>
                <td class="px-2 py-2.5 text-center">${viewBtn}${deleteBtn}</td>
            </tr>`;
        })
        .join('');
    renderPager();
}

function renderPager() {
    const totalPages = Math.max(
        1,
        Math.ceil(engineState.history.total / engineState.history.size) || 1
    );
    paintPagination('engineHistoryPager', engineState.history.page, totalPages);
}

async function deleteRun(runId) {
    if (engineState.isDeleting) return;
    const ok = window.confirm(
        '确认删除该引擎 Run？\n用于清理中断/卡住任务；不会撤销已写入的钢材/零件/L0 等业务价格。'
    );
    if (!ok) return;
    engineState.isDeleting = true;
    try {
        await HttpClient.delete(`${RUNS_API}/${runId}`);
        showToast('已删除 Run 记录', 'success');
        if (engineState.activeRunId === runId) {
            stopPolling();
            engineState.isRunning = false;
            engineState.isStarting = false;
            setReadyButtonBusy(false);
            updateStartButton();
        }
        loadHistory(engineState.history.page);
    } catch (_) {
        /* toasted */
    } finally {
        engineState.isDeleting = false;
    }
}

async function deleteAllRuns() {
    if (!engineState.canDelete) {
        showToast('无删除权限', 'warning');
        return;
    }
    if (engineState.isDeleting) return;
    const ok = window.confirm(
        '确认删除全部引擎运行历史？\n用于清理中断/卡住任务；不会撤销已写入的钢材/零件/L0 等业务价格。'
    );
    if (!ok) return;
    engineState.isDeleting = true;
    try {
        const res = await HttpClient.delete(RUNS_API);
        const count = res.data?.deleted_count ?? 0;
        showToast(`已删除 ${count} 条 Run 记录`, 'success');
        stopPolling();
        engineState.isRunning = false;
        engineState.isStarting = false;
        engineState.activeRunId = null;
        engineState.activeTaskId = null;
        setReadyButtonBusy(false);
        updateStartButton();
        loadHistory(1);
    } catch (_) {
        /* toasted */
    } finally {
        engineState.isDeleting = false;
    }
}

function formatTs(value) {
    if (!value) return '-';
    try {
        return String(value).replace('T', ' ').slice(0, 19);
    } catch (_) {
        return String(value);
    }
}

function formatResultTiming(result) {
    return formatTimingLine(result, formatTs);
}

export const pageConfig = {
    render: costingTemplate,
    init: () => CostingPage.init(),
    destroy: () => destroy(),
};