/**
 * 月度智能自动核价引擎 — 页面逻辑 (BRABUS Pure Industrial Spec)
 */

import { costingTemplate } from './template.js?v=14';
import {
    DEFAULT_PAGE_SIZE,
    bindPageSizeSelect,
} from '../../../page-size.js?v=2';

const READY_API = '/api/costing/engine/ready';
const RUNS_API = '/api/costing/engine/runs';
const TASK_API = '/api/costing/engine/tasks';
const CASCADE_API = '/api/stamping/filters/cascade';
const POLL_INTERVAL_MS = 1500;
const STORAGE_KEY = 'costing_engine_context';
/** 与后端 _SOFT_UPLOAD_GATE_CODES 对齐：仅提示，不阻断启动 */
const SOFT_GATE_CODES = new Set(['thickness_policy']);

const GATE_LABELS = {
    stamping_process: '冲压工艺',
    tonnage_price: '冲次单价',
    welding_unit_price: '焊接单价',
    bom_snapshot: '材料清单',
    annual_part_price: '年度零件价',
    packaging_transport: '包装运输费',
    base_price: '基准价格',
    thickness_policy: '厚度加减价',
    scrap_price: '废料价',
    system_rates: '系统费率',
    annual_process_fee: '冲压加工费',
    annual_welding_breakdown: '焊接工艺拆解',
    annual_l0_welding_fee: '成品焊接费',
};

/** 中文主标；英文仅作氛围（中文 // EN） */
const STATUS_META = {
    running: { label: '运行中 // RUNNING', className: 'text-[#64b5f6]' },
    succeeded: { label: '核算完成 // SUCCESS', className: 'text-emerald-400 font-bold' },
    partial: { label: '部分完成 // PARTIAL', className: 'text-amber-400' },
    failed: { label: '核算失败 // FAILED', className: 'text-[#FF1E27] font-bold' },
    blocked: { label: '强约束阻断 // BLOCKED', className: 'text-[#FF1E27] font-bold' },
    deleted: { label: '已删除 // DELETED', className: 'text-zinc-600' },
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
    history: {
        page: 1,
        size: DEFAULT_PAGE_SIZE,
        total: 0,
        items: [],
    },
};

export const CostingPage = {
    init() {
        stopPolling();
        bindEvents();
        bindSelectChangeListeners();
        bindPageSizeSelect('engineHistoryPageSize', {
            getSize: () => engineState.history.size,
            setSize: (size) => {
                engineState.history.size = size;
            },
            onChange: () => loadHistory(1),
        });
        applyPermissionUi();
        restoreContext();
        loadLocations().then(() => {
            const ctx = readStoredContext();
            if (ctx?.location) {
                checkReady();
            }
        });
        loadHistory(1);
    },
};

export function destroy() {
    stopPolling();
}

function applyPermissionUi() {
    engineState.canRun = typeof can === 'function' ? can('op:costing:run') : true;
    engineState.canDelete = typeof can === 'function' ? can('op:costing:delete') : true;
    updateStartButton();
}

function bindEvents() {
    document.getElementById('engineReadyBtn')?.addEventListener('click', () => checkReady());
    document.getElementById('engineStartBtn')?.addEventListener('click', () => startRun());
    document.getElementById('engineHistoryBody')?.addEventListener('click', (event) => {
        const btn = event.target.closest('[data-action="delete-run"]');
        if (!btn) return;
        const runId = Number(btn.getAttribute('data-run-id'));
        if (runId) deleteRun(runId);
    });
}

function bindSelectChangeListeners() {
    ['engineLocation', 'engineYear', 'engineMonth'].forEach((id) => {
        document.getElementById(id)?.addEventListener('change', () => {
            persistContext();
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
    } catch (_) {
        select.innerHTML = '<option value="">加载失败</option>';
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
    return GATE_LABELS[code] || code;
}

function summarizeGateMessage(item) {
    const msg = (item.message || '').trim();
    if (!msg) return '—';
    return msg
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
    const badge = document.getElementById('engineHardStopBadge');
    if (badge) {
        const softTipCount = (ready?.gates?.upload_or_config || []).filter(isSoftTip).length;
        if (hardStop) {
            badge.textContent = '强约束未过 // HARD_STOP';
            badge.className =
                'text-[9px] tracking-[0.06em] bg-[#1A080A] text-[#FF1E27] border border-[#FF1E27] px-2 py-0.5 rounded-none shrink-0';
        } else if (ready) {
            badge.textContent = softTipCount ? '已就绪（有提示）' : '已通过 // PASSED';
            badge.className =
                'text-[9px] tracking-[0.06em] bg-[#081A10] text-emerald-400 border border-emerald-500/50 px-2 py-0.5 rounded-none shrink-0';
        } else {
            badge.textContent = '未检查';
            badge.className =
                'text-[9px] tracking-[0.06em] bg-[#121216] text-zinc-500 border border-[#22222A] px-2 py-0.5 rounded-none shrink-0';
        }
    }

    const hardList = document.getElementById('engineGateHardList');
    if (hardList) {
        const items = sortGateItems(ready?.gates?.upload_or_config || []);
        if (!items.length) {
            hardList.innerHTML =
                '<div class="px-3 py-8 text-center text-[10px] tracking-wide text-zinc-600">暂无检查项</div>';
        } else {
            hardList.innerHTML = items.map((item) => renderGateRow(item)).join('');
            hardList.querySelectorAll('[data-action="navigate"]').forEach((btn) => {
                btn.addEventListener('click', () => {
                    const page = btn.getAttribute('data-page');
                    const queryRaw = btn.getAttribute('data-query') || '{}';
                    let query = {};
                    try {
                        query = JSON.parse(queryRaw);
                    } catch (_) {
                        query = {};
                    }
                    navigateWithQuery(page, query);
                });
            });
            requestAnimationFrame(() => scrollGateBlockerIntoView(hardList));
        }
    }

    const annual = ready?.gates?.annual_derived || [];
    const willCalc = annual.filter((a) => a.will_auto_calc);
    const annualBadge = document.getElementById('engineAnnualBadge');
    if (annualBadge) {
        annualBadge.textContent = willCalc.length
            ? `${willCalc.length} 项待补算`
            : '已完成 // COMPLETE';
        annualBadge.className = willCalc.length
            ? 'text-[10px] font-bold tracking-[0.06em] text-amber-400 shrink-0'
            : 'text-[10px] text-zinc-600 shrink-0';
    }
    const annualList = document.getElementById('engineGateAnnualList');
    if (annualList) {
        if (!willCalc.length) {
            annualList.innerHTML =
                '<div class="px-3 py-8 text-center text-[10px] tracking-wide text-zinc-600">年度派生数据已齐备</div>';
        } else {
            annualList.innerHTML = willCalc
                .map(
                    (item) => `
                <div class="flex items-center justify-between gap-3 px-3 py-2 border-b border-[#1A1A22] bg-[#0E0C06]">
                    <div class="flex items-center gap-2 min-w-0">
                        <span class="w-1.5 h-1.5 bg-amber-400 shrink-0"></span>
                        <span class="text-xs font-medium text-amber-400 shrink-0">${esc(gateLabel(item.code))}</span>
                        <span class="text-[9px] font-mono text-zinc-500 uppercase shrink-0">${esc(item.code)}</span>
                        <span class="text-[10px] font-mono text-zinc-400 truncate">${esc(item.scope_key)}</span>
                    </div>
                    <span class="text-[9px] tracking-[0.06em] bg-[#1A1408] text-amber-400 border border-amber-500/40 px-1.5 py-0.5 shrink-0">待补算</span>
                </div>`
                )
                .join('');
        }
    }

    const suppliers = ready?.plan?.part_cost_scopes || [];
    const l0Scopes = ready?.plan?.l0_scopes || [];
    const supplierEl = document.getElementById('enginePlanSuppliers');
    if (supplierEl) {
        supplierEl.innerHTML = suppliers.length
            ? suppliers
                  .map(
                      (s) => `
                <div class="border border-[#1E1E26] bg-[#0A0A0D] px-2.5 py-2 flex items-center gap-2 min-w-0">
                    <span class="w-1.5 h-1.5 bg-[#FF1E27] shrink-0"></span>
                    <span class="text-[11px] font-mono text-white truncate" title="${esc(s.stamping_supplier)}">${esc(s.stamping_supplier)}</span>
                </div>`
                  )
                  .join('')
            : '<div class="border border-dashed border-[#1E1E26] bg-[#0A0A0D] px-2 py-3 text-[10px] text-zinc-600 text-center col-span-full">暂无节点</div>';
    }
    const l0El = document.getElementById('enginePlanL0');
    if (l0El) {
        l0El.innerHTML = l0Scopes.length
            ? l0Scopes
                  .map(
                      (s) => `
                <div class="border border-[#1E1E26] bg-[#0A0A0D] px-2.5 py-2 flex items-center gap-2 min-w-0">
                    <span class="w-1.5 h-1.5 bg-[#FF1E27] shrink-0"></span>
                    <span class="text-[11px] font-mono text-white truncate">${esc(s.vehicle_model)}</span>
                    <span class="text-[10px] font-mono text-zinc-600 shrink-0">/</span>
                    <span class="text-[11px] font-mono text-zinc-400 truncate">${esc(s.bom_version)}</span>
                </div>`
                  )
                  .join('')
            : '<div class="border border-dashed border-[#1E1E26] bg-[#0A0A0D] px-2 py-3 text-[10px] text-zinc-600 text-center col-span-full">暂无节点</div>';
    }

    updateReadyStatus();
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
    const ok = !!item.ok;
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

    const led = hardFail
        ? '<span class="w-2 h-2 bg-[#FF1E27] shrink-0"></span>'
        : soft
          ? '<span class="w-2 h-2 bg-amber-400 shrink-0"></span>'
          : '<span class="w-2 h-2 bg-emerald-400 shrink-0"></span>';

    let actionHtml = '';
    if (nav) {
        const linkClass = soft || hardFail
            ? 'shrink-0 text-[10px] font-bold tracking-[0.06em] text-amber-400 hover:text-amber-300'
            : 'shrink-0 text-[10px] font-bold tracking-[0.06em] text-[#FF1E27] hover:text-white';
        if (canPage) {
            actionHtml = `
                <button type="button"
                        data-action="navigate"
                        data-page="${esc(nav.page)}"
                        data-query='${esc(JSON.stringify(nav.query || {}))}'
                        class="${linkClass}">
                    去处理 →
                </button>`;
        } else {
            actionHtml = '<span class="shrink-0 text-[9px] tracking-wide text-zinc-600">无权限</span>';
        }
    } else if (ok || soft) {
        actionHtml =
            '<span class="shrink-0 text-[9px] tracking-[0.06em] bg-[#081A10] text-emerald-400 border border-emerald-500/40 px-2 py-0.5 rounded-none">已通过 // PASSED</span>';
    }

    const rowClass = hardFail
        ? 'bg-[#14080A] border-l-2 border-l-[#FF1E27]'
        : soft
          ? 'bg-[#1A1408] border-l-2 border-l-amber-400'
          : 'hover:bg-[#0E0E12] border-l-2 border-l-transparent';

    return `
        <div data-gate-role="${role}" data-gate-code="${esc(item.code)}"
             class="flex items-center justify-between gap-3 px-3 py-2 border-b border-[#181820] ${rowClass} transition-colors">
            <div class="flex items-center gap-3 min-w-0 flex-1">
                ${led}
                <div class="min-w-0 flex-1">
                    <div class="flex items-baseline gap-2 min-w-0">
                        <span class="text-xs font-medium text-white shrink-0">${esc(zhTitle)}</span>
                        <span class="text-[9px] font-mono uppercase text-zinc-500 truncate">${esc(item.code)}</span>
                    </div>
                    <p class="text-[10px] font-mono text-zinc-400 truncate mt-0.5" title="${esc(line)}">${esc(line)}</p>
                </div>
            </div>
            ${actionHtml}
        </div>`;
}

function updateReadyStatus() {
    const led = document.getElementById('engineReadyLed');
    const text = document.getElementById('engineReadyStatusText');
    if (!led || !text) return;

    const ready = engineState.ready;
    const hardStop = !!ready?.gates?.hard_stop;
    const canStart = !!ready?.can_start;

    if (!ready) {
        led.className = 'w-2.5 h-2.5 bg-zinc-700 shrink-0';
        text.textContent = '待命';
        text.className = 'text-xs font-bold tracking-[0.06em] text-zinc-500 truncate mt-0.5';
        return;
    }
    if (hardStop || !canStart) {
        led.className = 'w-2.5 h-2.5 bg-[#FF1E27] shrink-0 shadow-[0_0_8px_#FF1E27]';
        text.textContent = '强约束阻断';
        text.className = 'text-xs font-bold tracking-[0.06em] text-[#FF1E27] truncate mt-0.5';
        return;
    }
    led.className =
        'w-2.5 h-2.5 bg-emerald-400 shrink-0 shadow-[0_0_8px_#34D399] animate-pulse';
    text.textContent = '系统就绪';
    text.className = 'text-xs font-bold tracking-[0.06em] text-emerald-400 truncate mt-0.5';
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

    const readyOk = !!engineState.ready?.can_start;
    const canStart =
        readyOk &&
        engineState.canRun &&
        !engineState.isRunning &&
        !engineState.isStarting &&
        !engineState.isCheckingReady;
    btn.disabled = !canStart;
    btn.classList.toggle('hidden', false);

    updateReadyStatus();

    let hintText = '';
    if (!engineState.canRun) {
        hintText = '当前账号无启动权限';
    } else if (!engineState.ready) {
        hintText = '';
    } else if (!readyOk) {
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
                ? 'mt-4 text-[10px] tracking-wide text-emerald-400'
                : 'mt-4 text-[10px] tracking-wide text-zinc-500';
        } else {
            hint.textContent = '';
            hint.classList.add('hidden');
        }
    }

    btn.title = canStart
        ? '启动月度核价引擎'
        : !engineState.canRun
          ? '无启动权限'
          : !readyOk
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
    if (!engineState.ready?.can_start) {
        showToast('请先通过检查就绪', 'warning');
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
        showProgress(0, 'TASK_SUBMITTED // 任务已提交…');
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
    if (bar) bar.style.width = `${Math.max(0, Math.min(100, percent))}%`;
    if (pct) pct.textContent = `${Math.round(percent)}%`;
    if (msgEl) msgEl.textContent = msg || '—';
    spinner?.classList.remove('hidden');
    document.getElementById('engineResultPanel')?.classList.add('hidden');
}

function hideProgressSpinner() {
    document.getElementById('engineProgressSpinner')?.classList.add('hidden');
}

function hideProgressPanel() {
    document.getElementById('engineProgressPanel')?.classList.add('hidden');
}

function showResult(result) {
    hideProgressPanel();
    const panel = document.getElementById('engineResultPanel');
    panel?.classList.remove('hidden');
    const status = result?.status || '—';
    const meta = STATUS_META[status] || { label: status, className: 'text-white' };
    const statusEl = document.getElementById('engineResultStatus');
    if (statusEl) {
        statusEl.textContent = meta.label;
        statusEl.className = `text-sm font-bold tracking-[0.06em] mt-0.5 ${meta.className}`;
    }
    const counts = result?.counts || {};
    const countsEl = document.getElementById('engineResultCounts');
    if (countsEl) {
        countsEl.textContent = `成功 ${counts.succeeded || 0} · 失败 ${counts.failed || 0} · 跳过 ${counts.skipped || 0}`;
    }
    if (result?.run_id) {
        engineState.activeRunId = result.run_id;
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
    const skip = (engineState.history.page - 1) * engineState.history.size;
    try {
        const res = await HttpClient.get(RUNS_API, {
            params: { skip, limit: engineState.history.size },
        });
        const data = res.data || {};
        engineState.history.items = data.items || [];
        engineState.history.total = data.total || 0;
        renderHistory();
    } catch (_) {
        const body = document.getElementById('engineHistoryBody');
        if (body) {
            body.innerHTML = `<tr><td colspan="7" class="px-3 py-8 text-center text-[10px] text-[#FF1E27]">历史加载失败</td></tr>`;
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
        body.innerHTML = `<tr><td colspan="7" class="px-3 py-8 text-center text-[10px] text-zinc-600">暂无运行记录</td></tr>`;
        renderPager();
        return;
    }

    body.innerHTML = items
        .map((row) => {
            const meta = STATUS_META[row.status] || {
                label: row.status,
                className: 'text-zinc-500',
            };
            const deleteBtn = engineState.canDelete
                ? `<button type="button" data-action="delete-run" data-run-id="${row.id}"
                        class="px-2 py-1 text-[10px] text-zinc-500 hover:text-[#FF1E27] transition-colors"
                        title="删除记录（不撤销已算价格）">删除</button>`
                : '';
            return `
            <tr class="group relative text-[11px] border-b border-[#1A1A20] hover:bg-[#0E0E12] transition-colors">
                <td class="px-3 py-2 font-mono text-white font-bold tabular-nums">${esc(row.id)}</td>
                <td class="px-3 py-2 text-zinc-200">${esc(row.location)}</td>
                <td class="px-3 py-2 text-right font-mono text-zinc-400 tabular-nums">${esc(row.year)}-${String(row.month).padStart(2, '0')}</td>
                <td class="px-3 py-2 text-center ${meta.className}">${esc(meta.label)}</td>
                <td class="px-3 py-2 text-zinc-400">${esc(row.created_by || '-')}</td>
                <td class="px-3 py-2 text-[10px] font-mono text-zinc-500 tabular-nums">${esc(formatTs(row.started_at))}</td>
                <td class="px-3 py-2 text-center">${deleteBtn}</td>
            </tr>`;
        })
        .join('');
    renderPager();
}

function renderPager() {
    const pager = document.getElementById('engineHistoryPager');
    if (!pager) return;
    const totalPages = Math.max(
        1,
        Math.ceil(engineState.history.total / engineState.history.size) || 1
    );
    const page = engineState.history.page;
    const buttons = [];
    for (let i = 1; i <= totalPages && i <= 8; i += 1) {
        const active = i === page;
        buttons.push(`
            <button type="button" data-page="${i}"
                class="min-w-[28px] h-7 px-2 text-[10px] font-mono rounded-none transition-colors ${
                    active
                        ? 'bg-[#FF1E27] text-white font-bold border border-[#FF1E27]'
                        : 'bg-[#121216] text-zinc-400 border border-[#22222A] hover:text-white hover:border-[#FF1E27]'
                }">${i}</button>`);
    }
    pager.innerHTML = buttons.join('');
    pager.querySelectorAll('button[data-page]').forEach((btn) => {
        btn.addEventListener('click', () => {
            loadHistory(Number(btn.getAttribute('data-page')));
        });
    });
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

function formatTs(value) {
    if (!value) return '-';
    try {
        return String(value).replace('T', ' ').slice(0, 19);
    } catch (_) {
        return String(value);
    }
}

export const pageConfig = {
    render: costingTemplate,
    init: () => CostingPage.init(),
    destroy: () => destroy(),
};