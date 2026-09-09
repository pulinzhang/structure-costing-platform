/**
 * 采购价格 — BRABUS 800 中控交车（协议黑匣）
 */

import { pageSizeSelectHtml } from '../../../page-size.js?v=2';

const HUD_SHELL_STYLE = 'box-shadow:0 4px 20px rgba(0,0,0,0.5);';

const RING_SELECT_IDS = [
    'pcrLocationFilter',
    'pcrVehicleModelFilter',
    'pcrBomVersionFilter',
    'pcrStartYearFilter',
    'pcrStartMonthFilter',
    'pcrEndYearFilter',
    'pcrEndMonthFilter',
    'pcrSupplierFilter',
];

const DRIVE_ACTIVE =
    'flex-1 py-1 text-[10px] rounded-sm bg-[#121218] border border-[#2A2A35] text-[#A1A1A6] font-medium';
const DRIVE_IDLE =
    'flex-1 py-1 text-[10px] rounded-sm border border-transparent text-[#555560] hover:text-[#8E8E93] font-medium';

const IGNITION_STYLE =
    'background-image:linear-gradient(180deg,#320A0E 0%,#1A0507 48%,#0D0203 100%);'
    + 'text-shadow:0 0 8px rgba(255,30,39,0.55);';
const HUD_NUM_STYLE = "font-family:'JetBrains Mono',ui-monospace,monospace;";
const PCR_FX_CSS = `@keyframes pcr-laser-sweep{0%{left:-72px;opacity:1}100%{left:100%;opacity:.2}}`
    + `@keyframes pcr-ignition-breathe{0%,100%{opacity:.35;box-shadow:0 0 4px #FF1E27}50%{opacity:1;box-shadow:0 0 8px #FF1E27}}`
    + `.pcr-laser-track{position:absolute;top:0;left:0;right:0;height:1px;overflow:hidden;pointer-events:none;z-index:2}`
    + `.pcr-laser-spot{position:absolute;top:0;width:72px;height:1px;`
    + `background:linear-gradient(90deg,transparent,#FF1E27,#fff,#FF1E27,transparent);`
    + `animation:pcr-laser-sweep 100ms linear 1 forwards}`
    + `.pcr-ignition-pulse{animation:pcr-ignition-breathe 2s ease-in-out infinite}`
    + `@media (prefers-reduced-motion:reduce){.pcr-laser-spot,.pcr-ignition-pulse{animation:none!important}}`;

function cornerMarks() {
    const arm = 'pointer-events-none absolute w-1 h-1 border-[#FF1E27]';
    return `
        <span class="${arm} top-0 left-0 border-t border-l" aria-hidden="true"></span>
        <span class="${arm} top-0 right-0 border-t border-r" aria-hidden="true"></span>
        <span class="${arm} bottom-0 left-0 border-b border-l" aria-hidden="true"></span>
        <span class="${arm} bottom-0 right-0 border-b border-r" aria-hidden="true"></span>`;
}

const CHIP_FACE = 'flex items-center gap-1 bg-[#101018] border border-[#22222E] rounded px-2 h-7 shrink-0';
const CHIP_TRIGGER =
    'pcr-chip-trigger min-w-0 truncate text-left text-[11px] font-medium bg-transparent border-0 p-0 cursor-pointer focus:outline-none text-[#8E8E93] disabled:opacity-40';
const CHIP_ITEM =
    'pcr-chip-item block w-full text-left px-2.5 py-1.5 text-[11px] text-[#C8C8D0] bg-transparent';
const PCR_CHIP_MENU_CSS = `#pcrChipMenu [role="option"][aria-selected="true"]{background-color:#FF1E27;color:#fff}`
    + `#pcrChipMenu:hover [role="option"][aria-selected="true"]:not(:hover){background-color:transparent;color:#C8C8D0}`
    + `#pcrChipMenu [role="option"]:hover{background-color:#FF1E27;color:#fff}`;
const CHIP_CHEVRON = `<svg class="w-3 h-3 text-[#555555] shrink-0 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>`;

export function procurementContractReportTemplate() {
    return `
        <div class="w-full max-w-full">
            <style>${PCR_FX_CSS}</style>
            <div class="relative overflow-hidden bg-[#08080C] border border-[#FF1E27]/30 rounded-md p-2.5 mb-2 w-full max-w-full"
                 style="${HUD_SHELL_STYLE}">
                <span class="pcr-laser-track" aria-hidden="true"><span class="pcr-laser-spot"></span></span>

                <div class="flex items-center gap-2 pb-2 mb-2 border-b border-[#1A1A24] text-[11px]">
                    <div class="flex items-center gap-2 overflow-x-auto min-w-0 flex-1">
                        ${ringChip('pcrLocationFilter', '基地')}
                        ${ringChip('pcrVehicleModelFilter', '项目')}
                        ${ringChip('pcrBomVersionFilter', '版本')}
                        ${ringPeriodChip('pcrStartYearFilter', 'pcrStartMonthFilter', '开始')}
                        ${ringPeriodChip('pcrEndYearFilter', 'pcrEndMonthFilter', '结束')}
                        <span id="pcrSupplierFilterWrap">${ringChip('pcrSupplierFilter', '供应商', 'max-w-[14rem]')}</span>
                    </div>
                    <button id="pcrResetBtn" type="button"
                            class="shrink-0 inline-flex items-center gap-1 px-2 h-7 text-[11px] text-[#6E6E73] hover:text-white">
                        ${window.svgIcon('refresh', 'w-3 h-3')}
                        重置
                    </button>
                </div>

                <div class="grid grid-cols-12 gap-2 items-stretch">
                    <div class="relative col-span-3 bg-[#0E0E14] border border-[#1E1E2A] rounded min-w-0">
                        ${cornerMarks()}
                        <div class="px-2.5 py-2">
                            <div class="text-[10px] text-[#6E6E73] tracking-wider">单车合计</div>
                            <div class="text-[15px] font-bold text-white tabular-nums tracking-tight leading-none mt-0.5"
                                 style="${HUD_NUM_STYLE}">
                                <span id="pcrHudVehicleTotal">—</span>
                                <span class="text-[10px] text-[#6E6E73] font-normal">元</span>
                            </div>
                        </div>
                        <div class="border-t border-[#181822] px-2.5 py-1">
                            <div id="pcrHudVehicleTotalHint" class="text-[9px] text-[#4A4A55] truncate leading-none">窗口内各月 · 数量×结算价</div>
                        </div>
                    </div>

                    <div class="col-span-5 grid grid-cols-2 gap-2">
                        <div class="bg-[#0E0E14] border border-[#1E1E2A] rounded min-w-0 overflow-hidden">
                            <div class="px-2.5 py-2">
                                <div class="text-[10px] text-[#6E6E73]">零件种数</div>
                                <div class="text-[15px] font-bold text-white mt-0.5 tabular-nums leading-none"
                                     style="${HUD_NUM_STYLE}">
                                    <span id="pcrHudPrice">—</span>
                                    <span class="text-[10px] text-[#6E6E73] font-normal">种</span>
                                </div>
                            </div>
                            <div class="border-t border-[#181822] px-2.5 py-1">
                                <div class="text-[9px] text-[#4A4A55] truncate leading-none">未出结算价 <span id="pcrHudMissing">—</span></div>
                            </div>
                        </div>
                        <div id="pcrHudSupplierCard" class="bg-[#0E0E14] border border-[#1E1E2A] rounded px-2.5 py-2 min-w-0 flex flex-col justify-center">
                            <div class="text-[10px] text-[#6E6E73]">已指定供应商</div>
                            <div class="text-[15px] font-bold text-white mt-0.5 tabular-nums leading-none"
                                 style="${HUD_NUM_STYLE}">
                                <span id="pcrHudSuppliers">—</span>
                                <span class="text-[10px] text-[#6E6E73] font-normal">家</span>
                            </div>
                        </div>
                    </div>

                    <div class="col-span-4 bg-[#0A0A10] border border-[#1E1E2A] rounded p-2.5 flex flex-col justify-between gap-2 min-w-0">
                        <div class="flex w-full bg-[#030305] border border-[#161622] rounded p-0.5" role="group" aria-label="价目视图">
                            <button id="pcrViewProcurementBtn" type="button" class="${DRIVE_ACTIVE}">采购对象</button>
                            <button id="pcrViewAssemblyBtn" type="button" class="${DRIVE_IDLE}">总成</button>
                        </div>
                        <button id="pcrExportBtn" type="button"
                                style="${IGNITION_STYLE}"
                                class="relative w-full py-2 inline-flex items-center justify-center gap-2 border border-[#FF1E27] [border-top-color:rgba(255,255,255,0.2)] text-[#FF1E27] text-[12px] font-black tracking-widest uppercase rounded shadow-[0_0_15px_rgba(255,30,39,0.25)] hover:shadow-[0_0_25px_rgba(255,30,39,0.45)] active:scale-[0.99] transition-all"
                                title="导出《批量零部件价格协议》（不分页、无水印）">
                            ${cornerMarks()}
                            <span class="pcr-ignition-pulse w-1.5 h-1.5 rounded-full bg-[#FF1E27] shrink-0"></span>
                            导出协议
                        </button>
                    </div>
                </div>
            </div>

            <div class="bg-[#0A0A0C] border border-[#1A1A22] overflow-hidden w-full max-w-full">
                <div class="px-4 py-2 border-b border-[#14141A] flex items-center gap-2">
                    <span class="pointer-events-none text-[#8E8E93] shrink-0">
                        ${window.svgIcon('search', 'w-3 h-3')}
                    </span>
                    <input id="pcrPartFilter" type="text" maxlength="100" placeholder="零件号 / 名称"
                           title="模糊匹配零件号或名称" aria-label="零件号或名称"
                           class="h-7 flex-1 min-w-0 bg-transparent text-[11px] text-[#C8C8D0] placeholder:text-[#8E8E93] focus:outline-none">
                    <span id="pcrIdentityHint" class="hidden sm:inline text-[9px] text-[#8A8A93] shrink-0 max-w-md text-right">${pcrIdentityHintHtml(false)}</span>
                </div>
                <div id="pcrQaBanner" class="hidden px-5 py-2 border-b border-[#FF1E27]/30 bg-[#1A080A] text-[11px] text-[#FF1E27] font-mono"></div>

                <div class="relative">
                    <div id="pcrLoading" class="hidden absolute inset-0 z-10 flex items-center justify-center bg-[#0A0A0C]/70">
                        <div class="w-6 h-6 border-2 border-[#FF1E27] border-t-transparent rounded-full animate-spin"></div>
                    </div>
                    <div class="overflow-x-auto bg-[#0A0A0E] brabus-bg-grid pr-4">
                        <table id="pcrTable" class="w-full table-fixed text-left border-collapse bg-transparent tabular-nums"
                               style="min-width: 1100px; font-family:'JetBrains Mono',ui-monospace,monospace;">
                            <colgroup id="pcrColgroup"></colgroup>
                            <thead id="pcrTableHead" class="text-[9px] text-[#8E8E93] uppercase tracking-wider"></thead>
                            <tbody id="pcrTableBody"></tbody>
                        </table>
                    </div>
                    <div id="pcrEmpty" class="hidden px-5 py-10 text-center text-[12px] text-[#555555] font-mono">
                        <div id="pcrEmptyText">正在加载…</div>
                    </div>
                </div>

                <div class="px-5 py-2.5 border-t border-[#14141A] flex items-center justify-between gap-3">
                    <div class="flex items-center gap-3 min-w-0">
                        <span id="pcrPageInfo" class="text-[10px] font-mono text-[#555555]">—</span>
                        ${pageSizeSelectHtml('pcrPageSize')}
                    </div>
                    <div id="pcrPagination" class="flex items-center gap-0.5"></div>
                </div>
            </div>
        </div>
    `;
}

const PERIOD_SELECT_IDS = new Set([
    'pcrStartYearFilter',
    'pcrStartMonthFilter',
    'pcrEndYearFilter',
    'pcrEndMonthFilter',
]);

function ringChip(id, label, triggerClass = 'max-w-[10rem]') {
    return `<div class="${CHIP_FACE}" data-pcr-ring="${id}">
        <span class="text-[#555560] shrink-0">${label}</span>
        <select id="${id}" class="sr-only" tabindex="-1" aria-hidden="true">
            <option value="">请选择</option>
        </select>
        <button type="button" data-pcr-chip="${id}" class="${CHIP_TRIGGER} ${triggerClass} inline-flex items-center gap-1"
                aria-haspopup="listbox" aria-expanded="false">
            <span data-pcr-chip-label class="truncate">请选择</span>
            ${CHIP_CHEVRON}
        </button>
    </div>`;
}

function ringPeriodChip(yearId, monthId, label) {
    return `<div class="${CHIP_FACE}" data-pcr-period="${yearId}">
        <span class="text-[#555560] shrink-0">${label}</span>
        <span data-pcr-ring="${yearId}" class="inline-flex items-center gap-0.5">
            <select id="${yearId}" class="sr-only" tabindex="-1" aria-hidden="true">
                <option value="">年</option>
            </select>
            <button type="button" data-pcr-chip="${yearId}" class="${CHIP_TRIGGER} max-w-[4.5rem] w-[3.6rem] inline-flex items-center"
                    aria-haspopup="listbox" aria-expanded="false">
                <span data-pcr-chip-label class="truncate">年</span>
            </button>
        </span>
        <span data-pcr-ring="${monthId}" class="inline-flex items-center gap-0.5">
            <select id="${monthId}" class="sr-only" tabindex="-1" aria-hidden="true">
                <option value="">月</option>
            </select>
            <button type="button" data-pcr-chip="${monthId}" class="${CHIP_TRIGGER} max-w-[4.25rem] w-[3.4rem] inline-flex items-center"
                    aria-haspopup="listbox" aria-expanded="false">
                <span data-pcr-chip-label class="truncate">月</span>
            </button>
        </span>
        ${CHIP_CHEVRON}
    </div>`;
}

function pcrIdentityHintHtml(isAssembly) {
    if (isAssembly) {
        return '打开即加载最近一次核价的基地 / 项目 / 版本 / 月份。总成整包一份协议，不筛供应商。';
    }
    return '打开即加载最近一次核价的基地 / 项目 / 版本 / 月份。采购对象导出<span class="text-[#FF1E27]/70">必须选定供应商</span>。';
}

export function updateRingIndicators() {
    RING_SELECT_IDS.forEach((id) => {
        const select = document.getElementById(id);
        const wrap = document.querySelector(`[data-pcr-ring="${id}"]`);
        if (!select || !wrap) return;
        const isSet = Boolean((select.value || '').trim());
        syncPcrChipFace(id);
        if (PERIOD_SELECT_IDS.has(id)) return;
        wrap.classList.remove('border-[#FF1E27]/40', 'border-[#22222E]');
        wrap.classList.add(isSet ? 'border-[#FF1E27]/40' : 'border-[#22222E]');
    });
    document.querySelectorAll('[data-pcr-period]').forEach((wrap) => {
        const selects = wrap.querySelectorAll('select');
        const isSet = Array.from(selects).some((el) => Boolean((el.value || '').trim()));
        wrap.classList.remove('border-[#FF1E27]/40', 'border-[#22222E]');
        wrap.classList.add(isSet ? 'border-[#FF1E27]/40' : 'border-[#22222E]');
    });
}

export function syncPcrChipFace(id) {
    const select = document.getElementById(id);
    const trigger = document.querySelector(`[data-pcr-chip="${id}"]`);
    if (!select || !trigger) return;
    const opt = select.selectedOptions[0];
    const label = trigger.querySelector('[data-pcr-chip-label]') || trigger;
    label.textContent = opt ? opt.textContent : '请选择';
    trigger.classList.remove('text-white', 'text-[#8E8E93]');
    trigger.classList.add((select.value || '').trim() ? 'text-white' : 'text-[#8E8E93]');
}

let chipMenuEl = null;
let openChipId = null;

function ensureChipMenu() {
    if (chipMenuEl) return chipMenuEl;
    chipMenuEl = document.createElement('div');
    chipMenuEl.id = 'pcrChipMenu';
    chipMenuEl.className = 'hidden fixed z-[70] max-h-56 overflow-y-auto bg-[#101018] border border-[#22222E] rounded py-1';
    chipMenuEl.style.boxShadow = '0 8px 24px rgba(0,0,0,0.55)';
    chipMenuEl.setAttribute('role', 'listbox');
    document.body.appendChild(chipMenuEl);
    if (!document.getElementById('pcrChipMenuSkin')) {
        const skin = document.createElement('style');
        skin.id = 'pcrChipMenuSkin';
        skin.textContent = PCR_CHIP_MENU_CSS;
        document.head.appendChild(skin);
    }
    chipMenuEl.addEventListener('click', (event) => {
        const item = event.target.closest('[data-pcr-chip-value]');
        if (!item || !openChipId) return;
        event.preventDefault();
        const select = document.getElementById(openChipId);
        if (!select || select.disabled) return;
        select.value = item.getAttribute('data-pcr-chip-value') || '';
        closePcrChipMenu();
        syncPcrChipFace(select.id);
        select.dispatchEvent(new Event('change', { bubbles: true }));
    });
    return chipMenuEl;
}

function closePcrChipMenu() {
    if (!chipMenuEl) return;
    chipMenuEl.classList.add('hidden');
    chipMenuEl.innerHTML = '';
    if (openChipId) {
        document.querySelector(`[data-pcr-chip="${openChipId}"]`)?.setAttribute('aria-expanded', 'false');
    }
    openChipId = null;
}

function openPcrChipMenu(id) {
    const select = document.getElementById(id);
    const trigger = document.querySelector(`[data-pcr-chip="${id}"]`);
    const menu = ensureChipMenu();
    if (!select || !trigger || select.disabled) return;
    if (openChipId === id) {
        closePcrChipMenu();
        return;
    }
    closePcrChipMenu();
    const selected = select.value;
    menu.innerHTML = Array.from(select.options).map((opt) => {
        const isOn = opt.value === selected;
        return `<button type="button" role="option" aria-selected="${isOn ? 'true' : 'false'}"
            data-pcr-chip-value="${esc(opt.value)}"
            class="${CHIP_ITEM}">${esc(opt.textContent || '')}</button>`;
    }).join('');
    menu.classList.remove('hidden');
    const rect = trigger.getBoundingClientRect();
    const menuWidth = Math.max(rect.width + 48, 160);
    let left = rect.left;
    if (left + menuWidth > window.innerWidth - 8) {
        left = Math.max(8, window.innerWidth - menuWidth - 8);
    }
    menu.style.minWidth = `${menuWidth}px`;
    menu.style.left = `${left}px`;
    menu.style.top = `${rect.bottom + 4}px`;
    openChipId = id;
    trigger.setAttribute('aria-expanded', 'true');
}

function onChipTriggerClick(event) {
    const trigger = event.target.closest('[data-pcr-chip]');
    if (!trigger) return;
    event.preventDefault();
    event.stopPropagation();
    openPcrChipMenu(trigger.getAttribute('data-pcr-chip'));
}

function onChipDocClick(event) {
    if (!openChipId) return;
    if (event.target.closest('#pcrChipMenu') || event.target.closest('[data-pcr-chip]')) return;
    closePcrChipMenu();
}

function onChipKeydown(event) {
    if (event.key === 'Escape') closePcrChipMenu();
}

export function bindPcrChipMenus() {
    ensureChipMenu();
    document.getElementById('pageContent')?.addEventListener('click', onChipTriggerClick);
    document.addEventListener('click', onChipDocClick);
    document.addEventListener('keydown', onChipKeydown);
    window.addEventListener('resize', closePcrChipMenu);
    window.addEventListener('scroll', closePcrChipMenu, true);
    RING_SELECT_IDS.forEach(syncPcrChipFace);
}

export function unbindPcrChipMenus() {
    closePcrChipMenu();
    document.getElementById('pageContent')?.removeEventListener('click', onChipTriggerClick);
    document.removeEventListener('click', onChipDocClick);
    document.removeEventListener('keydown', onChipKeydown);
    window.removeEventListener('resize', closePcrChipMenu);
    window.removeEventListener('scroll', closePcrChipMenu, true);
    chipMenuEl?.remove();
    chipMenuEl = null;
    document.getElementById('pcrChipMenuSkin')?.remove();
}

export function updatePcrViewButtons(view) {
    const isAssembly = view === 'assembly';
    const procurementBtn = document.getElementById('pcrViewProcurementBtn');
    const assemblyBtn = document.getElementById('pcrViewAssemblyBtn');
    if (procurementBtn) procurementBtn.className = isAssembly ? DRIVE_IDLE : DRIVE_ACTIVE;
    if (assemblyBtn) assemblyBtn.className = isAssembly ? DRIVE_ACTIVE : DRIVE_IDLE;
    document.getElementById('pcrHudSupplierCard')?.classList.toggle('hidden', isAssembly);
    document.getElementById('pcrSupplierFilterWrap')?.classList.toggle('hidden', isAssembly);
    const hint = document.getElementById('pcrIdentityHint');
    if (hint) hint.innerHTML = pcrIdentityHintHtml(isAssembly);
}

let vehicleTotalRaf = 0;
let lastHudVehicleTotal = null;

export function cancelPcrHudCountUp() {
    if (vehicleTotalRaf) {
        cancelAnimationFrame(vehicleTotalRaf);
        vehicleTotalRaf = 0;
    }
    lastHudVehicleTotal = null;
}

function prefersReducedMotion() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function lockHudVehicleTotal(el, target) {
    cancelAnimationFrame(vehicleTotalRaf);
    vehicleTotalRaf = 0;
    if (!el) return;
    const numeric = Number(target);
    if (!Number.isFinite(numeric) || prefersReducedMotion()) {
        lastHudVehicleTotal = numeric;
        el.textContent = fmtHudMoney(target);
        return;
    }
    if (lastHudVehicleTotal === numeric) {
        el.textContent = fmtHudMoney(numeric);
        return;
    }
    lastHudVehicleTotal = numeric;
    const durationMs = 300;
    const startedAt = performance.now();
    const tick = (now) => {
        const t = Math.min(1, (now - startedAt) / durationMs);
        const eased = 1 - (1 - t) ** 4;
        const current = t >= 0.97 ? numeric : numeric * eased;
        el.textContent = fmtHudMoney(current);
        if (t < 1) {
            vehicleTotalRaf = requestAnimationFrame(tick);
            return;
        }
        el.textContent = fmtHudMoney(numeric);
        vehicleTotalRaf = 0;
    };
    el.textContent = fmtHudMoney(0);
    vehicleTotalRaf = requestAnimationFrame(tick);
}

export function updatePcrHud(filters) {
    const setText = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value == null ? '—' : String(value);
    };
    const totalEl = document.getElementById('pcrHudVehicleTotal');
    if (!filters) {
        cancelPcrHudCountUp();
        if (totalEl) totalEl.textContent = '—';
        setHudHint(0);
        setText('pcrHudPrice', '—');
        setText('pcrHudMissing', '—');
        setText('pcrHudSuppliers', '—');
        return;
    }
    const total = filters.vehicle_total;
    if (total == null || total === '') {
        cancelPcrHudCountUp();
        if (totalEl) totalEl.textContent = '—';
    } else {
        lockHudVehicleTotal(totalEl, total);
    }
    setHudHint(Number(filters.vehicle_total_skipped) || 0);
    setText('pcrHudPrice', filters.price_row_count ?? 0);
    setText('pcrHudMissing', filters.missing_month_cell_count ?? 0);
    setText('pcrHudSuppliers', filters.specified_supplier_count ?? 0);
}

function setHudHint(skipped) {
    const hint = document.getElementById('pcrHudVehicleTotalHint');
    if (!hint) return;
    const extra = skipped > 0 ? ` · ${skipped}种未计入` : '';
    hint.textContent = `窗口内各月 · 数量×结算价${extra}`;
}

function fmtHudMoney(value) {
    if (typeof window.fmtNum === 'function') return window.fmtNum(value, 2);
    const n = Number(value);
    return Number.isFinite(n) ? n.toFixed(2) : String(value);
}

export function renderPcrTableHead(months, showSupplier = true) {
    const head = document.getElementById('pcrTableHead');
    const colgroup = document.getElementById('pcrColgroup');
    const table = document.getElementById('pcrTable');
    const monthCols = Array.isArray(months) ? months : [];
    const monthCount = Math.max(monthCols.length, 1);
    const supplierWidth = showSupplier ? 96 : 0;
    if (table) table.style.minWidth = `${892 + supplierWidth + monthCount * 120}px`;

    const widths = ['72px', '90px', '130px', '144px'];
    if (showSupplier) widths.push('96px');
    widths.push('72px', '56px');
    for (let i = 0; i < monthCount; i += 1) widths.push('120px');
    widths.push('56px', '110px', '128px', '100px', '72px');
    if (colgroup) {
        colgroup.innerHTML = widths.map((width) => `<col style="width:${width}">`).join('');
    }

    const th = 'px-2 py-2 font-semibold text-center border-b border-[#1A1A22] text-[#8E8E93]';
    const monthHeaders = monthCols.map((col) => {
        const label = String(col.header || '').replace(/\n/g, ' ');
        return `<th class="${th} text-right">${esc(label)}</th>`;
    }).join('');
    const fallbackMonth = `<th class="${th} text-right">结算价格（元）</th>`;
    const supplierHead = showSupplier ? `<th class="${th} text-left">供应商</th>` : '';
    if (head) {
        head.innerHTML = `
            <tr>
                <th class="${th}">序号</th>
                <th class="${th} text-left">存货编码</th>
                <th class="${th} text-left">零件号</th>
                <th class="${th} text-left">零件名称</th>
                ${supplierHead}
                <th class="${th} text-right">单车数量</th>
                <th class="${th}">计量单位</th>
                ${monthHeaders || fallbackMonth}
                <th class="${th}">单独支付</th>
                <th class="${th} text-right">分摊价格（元/件）</th>
                <th class="${th} text-right pr-4">工装费（元）</th>
                <th class="${th} text-right">分摊数量（件）</th>
                <th class="${th}">备注</th>
            </tr>`;
    }
}

function supplierBadgeCell(row) {
    const full = (row.supplier_name || '').trim();
    if (!full) {
        return '<td class="px-2 py-2 text-[#555555]">—</td>';
    }
    const shortName = (row.supplier_abbreviation || '').trim() || full;
    return `<td class="px-1.5 py-2">
        <span class="inline-block max-w-full truncate px-1.5 py-0.5 text-[10px] text-[#8E8E93] bg-[#101018] border border-[#22222E] rounded"
              title="${esc(full)}">${esc(shortName)}</span>
    </td>`;
}

function cellValue(value) {
    if (value == null || value === '') return '/';
    return String(value);
}

function amountCell(value) {
    const text = cellValue(value);
    const isMissing = text === '/';
    const cls = isMissing
        ? 'px-2 py-2 text-center text-[#555555]'
        : 'px-2 py-2 text-right tabular-nums text-[#C8C8D0]';
    return `<td class="${cls}">${esc(text)}</td>`;
}

function moneyCell(value) {
    if (value == null || value === '' || value === '/') {
        return amountCell('/');
    }
    const fixed = typeof formatDecimalFixed === 'function'
        ? formatDecimalFixed(value, 2, { allowNegative: true })
        : null;
    if (fixed == null) return amountCell('/');
    return `<td class="px-2 py-2 text-right tabular-nums text-[#C8C8D0]">${esc(fixed)}</td>`;
}

function toolingFeeCell(value) {
    if (value == null || value === '' || value === '/') {
        return `<td class="px-2 py-2 pr-4 text-center text-[#555555]">/</td>`;
    }
    const fixed = typeof formatDecimalFixed === 'function'
        ? formatDecimalFixed(value, 2, { allowNegative: true })
        : null;
    if (fixed == null) return `<td class="px-2 py-2 pr-4 text-center text-[#555555]">/</td>`;
    const text = typeof withThousandsSep === 'function' ? withThousandsSep(fixed) : fixed;
    return `<td class="px-2 py-2 pr-4 text-right tabular-nums text-[#C8C8D0]">${esc(text)}</td>`;
}

export function renderPcrRows(rows, months, showSupplier = true) {
    if (!rows || !rows.length) return '';
    const monthKeys = (months || []).map((col) => `${col.year}-${col.month}`);
    return rows.map((row) => {
        const byMonth = {};
        (row.month_amounts || []).forEach((cell) => {
            byMonth[`${cell.year}-${cell.month}`] = cell.should_cost;
        });
        const monthHtml = monthKeys.length
            ? monthKeys.map((key) => moneyCell(byMonth[key])).join('')
            : moneyCell(row.month_amounts?.[0]?.should_cost);
        return `
        <tr class="group relative text-[11px] border-b border-[#141418] hover:bg-[#161620] transition-colors duration-100">
            <td class="px-2 py-2 text-center text-[#F0F0F2] tabular-nums relative">
                <div class="absolute left-0 top-0 bottom-0 w-[2px] bg-[#FF1E27] opacity-0 group-hover:opacity-70 transition-opacity"></div>
                ${esc(row.seq_label || '')}
            </td>
            <td class="px-2 py-2 text-[#8E8E93] truncate" title="${esc(row.internal_number || '')}">${esc(row.internal_number || '—')}</td>
            <td class="px-2 py-2 text-[#F0F0F2] truncate" title="${esc(row.part_number || '')}">${esc(row.part_number || '')}</td>
            <td class="px-2 py-2 text-[#8E8E93] truncate" title="${esc(row.part_name || '')}">${esc(row.part_name || '—')}</td>
            ${showSupplier ? supplierBadgeCell(row) : ''}
            <td class="px-2 py-2 text-right tabular-nums text-[#C8C8D0]">${esc(cellValue(row.vehicle_qty))}</td>
            <td class="px-2 py-2 text-center text-[#8E8E93]">${esc(row.qty_unit || '件')}</td>
            ${monthHtml}
            <td class="px-2 py-2 text-center text-[#8E8E93]">${esc(row.pay_tooling_separately || 'N')}</td>
            ${moneyCell(row.tooling_alloc_price)}
            ${toolingFeeCell(row.tooling_fee)}
            ${amountCell(row.tooling_alloc_qty)}
            <td class="px-2 py-2 text-center text-[#555555]">—</td>
        </tr>`;
    }).join('');
}

function pageBtnClass(isActive, isDisabled) {
    const base = 'pcr-page-btn flex items-center justify-center w-6 h-6 text-[10px] border border-transparent box-border';
    if (isDisabled) return `${base} text-[#2E2E36] cursor-not-allowed`;
    if (isActive) return `${base} border-[#FF1E27] text-white bg-transparent`;
    return `${base} text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620]`;
}

export function renderPcrPagination(currentPage, totalPages) {
    if (totalPages <= 1) return '';
    let buttons = `
        <button class="${pageBtnClass(false, currentPage === 1)}"
                data-page="${currentPage - 1}" ${currentPage === 1 ? 'disabled' : ''}>
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path></svg>
        </button>`;
    const maxVisible = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);
    if (endPage - startPage < maxVisible - 1) startPage = Math.max(1, endPage - maxVisible + 1);
    if (startPage > 1) {
        buttons += `<button class="${pageBtnClass(false, false)}" data-page="1">1</button>`;
        if (startPage > 2) buttons += `<span class="px-0.5 text-[#2E2E36] text-[9px]">—</span>`;
    }
    for (let i = startPage; i <= endPage; i += 1) {
        buttons += `<button class="${pageBtnClass(i === currentPage, false)}" data-page="${i}">${i}</button>`;
    }
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) buttons += `<span class="px-0.5 text-[#2E2E36] text-[9px]">—</span>`;
        buttons += `<button class="${pageBtnClass(false, false)}" data-page="${totalPages}">${totalPages}</button>`;
    }
    buttons += `
        <button class="${pageBtnClass(false, currentPage === totalPages)}"
                data-page="${currentPage + 1}" ${currentPage === totalPages ? 'disabled' : ''}>
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>
        </button>`;
    return buttons;
}
