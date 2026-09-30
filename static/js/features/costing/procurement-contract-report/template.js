/**
 * 采购价格 — BRABUS 800 中控交车（协议黑匣）
 */

import { HUD_SHELL, BTN_GHOST } from '../../../ui/classes.js?v=14';
import { paginationBarHtml } from '../../../ui/page-size.js?v=11';

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

const VIEW_LABEL = 'pcr-view-toggle__label';
const BENTO_H = 'height:72px;padding:8px';
const MECH_FONT =
    "'Chakra Petch','JetBrains Mono',ui-monospace,Menlo,Consolas,monospace";
const MECH_NUM_STYLE =
    `font-family:${MECH_FONT};font-weight:700;font-variant-numeric:tabular-nums;letter-spacing:-0.5px`;
const KPI_NUM_STYLE = `${MECH_NUM_STYLE};text-shadow:0 0 12px rgb(var(--hud-red) / 0.4)`;
const PCR_FX_CSS = `@keyframes pcr-laser-sweep{0%{left:-72px;opacity:1}100%{left:100%;opacity:.2}}`
    + `@keyframes pcr-ignition-breathe{0%,100%{opacity:.35;box-shadow:0 0 4px rgb(var(--hud-red))}50%{opacity:1;box-shadow:0 0 10px rgb(var(--hud-red))}}`
    + `.pcr-cockpit{overflow:visible}`
    + `.pcr-laser-track{position:absolute;top:0;left:0;right:0;height:1px;overflow:hidden;pointer-events:none;z-index:2}`
    + `.pcr-laser-spot{position:absolute;top:0;width:72px;height:1px;`
    + `background:linear-gradient(90deg,transparent,rgb(var(--hud-red)),rgb(var(--text-on-brand)),rgb(var(--hud-red)),transparent);`
    + `animation:pcr-laser-sweep 100ms linear 1 forwards}`
    + `.pcr-ignition-pulse{animation:pcr-ignition-breathe 2s ease-in-out infinite}`
    + `.pcr-glass{background:rgb(var(--bg-hud) / 0.72);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);border-bottom:1px solid rgb(var(--border-hud))}`
    + `.pcr-bento{background:rgb(var(--bg-elevated));border:1px solid rgb(var(--border-hud));transition:border-color .18s ease,box-shadow .18s ease}`
    + `.pcr-bento:hover{border-color:rgb(var(--hud-red) / 0.38);box-shadow:0 0 18px rgb(var(--hud-red) / 0.12)}`
    + `.pcr-num,#pcrHudVehicleTotal,#pcrHudPrice,#pcrHudSuppliers,#pcrHudMissing{`
    + `font-family:${MECH_FONT}!important;font-weight:700!important;`
    + `font-variant-numeric:tabular-nums lining-nums;letter-spacing:-0.5px}`
    + `.pcr-kpi{font-size:22px;line-height:1}`
    + `.pcr-label{font-size:8px;color:rgb(var(--text-muted));letter-spacing:.12em;line-height:1}`
    + `.pcr-chip{background:rgb(var(--text-main) / 0.03);border:1px solid rgb(var(--border-hud))}`
    + `.pcr-status-idle{background:rgb(var(--text-disabled))}`
    + `.pcr-status-alert{background:rgb(var(--hud-red));box-shadow:0 0 6px rgb(var(--hud-red) / 0.55)}`
    + `.pcr-export{background-image:linear-gradient(90deg,rgb(var(--pcr-ignition-from)) 0%,rgb(var(--pcr-ignition-mid)) 50%,rgb(var(--pcr-ignition-from)) 100%);box-shadow:0 0 18px rgb(var(--hud-red) / var(--pcr-ignition-glow))}`
    + `.pcr-export:hover{filter:brightness(1.25)}`
    + `html[data-theme="light"] .pcr-export:hover{filter:none;background-image:none;background-color:rgb(var(--brabus-red));color:rgb(var(--text-on-brand));border-color:rgb(var(--brabus-red));border-top-color:rgb(var(--brabus-red))}`
    + `.pcr-view-toggle{display:inline-flex;align-items:center;height:1.75rem;padding:0 .75rem;border:1px solid rgb(var(--border-color));border-radius:999px;background:transparent;flex-shrink:0}`
    + `.pcr-view-toggle__label{margin:0;padding:0;border:0;background:transparent;color:rgb(var(--text-muted));font-size:11px;font-weight:500;letter-spacing:.04em;cursor:pointer;line-height:1}`
    + `.pcr-view-toggle__label.is-active{color:rgb(var(--text-main));font-weight:600}`
    + `.pcr-view-toggle__divider{color:rgb(var(--text-disabled));padding:0 .45rem;pointer-events:none;line-height:1}`
    + `.pcr-view-toggle__label:focus-visible{outline:1px solid rgb(var(--border-active));outline-offset:2px}`
    + `.pcr-amt-mark{opacity:0}`
    + `.pcr-amt-cell:hover .pcr-amt-mark,.pcr-amt-cell:focus-within .pcr-amt-mark{opacity:.8}`
    + `@media (max-width:639.98px){html[data-theme="light"] .pcr-ignition-pulse{animation:none;box-shadow:none}html[data-theme="light"] .pcr-bento:hover{box-shadow:none}}`
    + `@media (prefers-reduced-motion:reduce){.pcr-laser-spot,.pcr-ignition-pulse{animation:none!important}.pcr-bento{transition:none}}`;

function cornerMarks() {
    const arm = 'pointer-events-none absolute w-1 h-1 border-brand-hud';
    return `
        <span class="${arm} top-0 left-0 border-t border-l" aria-hidden="true"></span>
        <span class="${arm} top-0 right-0 border-t border-r" aria-hidden="true"></span>
        <span class="${arm} bottom-0 left-0 border-b border-l" aria-hidden="true"></span>
        <span class="${arm} bottom-0 right-0 border-b border-r" aria-hidden="true"></span>`;
}

const CHIP_FACE = 'pcr-chip flex items-center gap-1 rounded px-2 h-7 shrink-0';
const CHIP_TRIGGER =
    'pcr-chip-trigger min-w-0 truncate text-left text-[11px] font-medium bg-transparent border-0 p-0 cursor-pointer focus:outline-none text-ink-muted disabled:opacity-40';
const CHIP_ITEM =
    'pcr-chip-item block w-full text-left px-2.5 py-1.5 text-[11px] bg-transparent';
const CHIP_CHEVRON = `<svg class="w-3 h-3 text-ink-faint shrink-0 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 9l-7 7-7-7"></path></svg>`;

export function procurementContractReportTemplate() {
    return `
        <div class="w-full max-w-full">
            <style>${PCR_FX_CSS}</style>
            <div class="${HUD_SHELL} pcr-cockpit relative rounded-md p-2.5 mb-2">
                <span class="pcr-laser-track" aria-hidden="true"><span class="pcr-laser-spot"></span></span>

                <div class="pcr-glass flex flex-col gap-2 -mx-2.5 px-2.5 py-1.5 mb-2 text-[11px] sm:flex-row sm:items-center">
                    <div class="flex flex-wrap items-center gap-2 min-w-0 w-full sm:flex-1 sm:flex-nowrap sm:overflow-x-auto">
                        ${ringChip('pcrLocationFilter', '基地')}
                        ${ringChip('pcrVehicleModelFilter', '项目')}
                        ${ringChip('pcrBomVersionFilter', '版本')}
                        ${ringPeriodChip('pcrStartYearFilter', 'pcrStartMonthFilter', '开始')}
                        ${ringPeriodChip('pcrEndYearFilter', 'pcrEndMonthFilter', '结束')}
                        <span id="pcrSupplierFilterWrap">${ringChip('pcrSupplierFilter', '供应商', 'max-w-[14rem]')}</span>
                    </div>
                    <div class="pcr-view-toggle" role="group" aria-label="价目视图">
                        <button type="button" id="pcrViewProcurementBtn" class="${VIEW_LABEL} is-active">采购对象</button>
                        <span class="pcr-view-toggle__divider" aria-hidden="true">|</span>
                        <button type="button" id="pcrViewAssemblyBtn" class="${VIEW_LABEL}">总成</button>
                    </div>
                    <button id="pcrResetBtn" type="button"
                            class="${BTN_GHOST} shrink-0">
                        ${window.svgIcon('refresh', 'w-3 h-3')}
                        重置
                    </button>
                </div>

                <div class="grid grid-cols-1 gap-2 items-stretch sm:grid-cols-2 lg:grid-cols-12">
                    <div class="pcr-bento relative col-span-1 rounded min-w-0 flex flex-col justify-center sm:col-span-2 lg:col-span-4"
                         style="${BENTO_H}">
                        ${cornerMarks()}
                        <div class="pcr-label">单车合计</div>
                        <div class="pcr-kpi text-ink mt-0.5">
                            <span id="pcrHudVehicleTotal" style="${KPI_NUM_STYLE}">—</span>
                            <span class="pcr-label align-top ml-0.5">元</span>
                        </div>
                        <div id="pcrHudVehicleTotalHint" class="text-[9px] text-ink-muted truncate leading-none mt-0.5">窗口内各月 · 数量×结算价</div>
                    </div>

                    <div class="col-span-1 grid grid-cols-2 gap-2 lg:col-span-4">
                        <div id="pcrHudPriceCard" class="pcr-bento rounded min-w-0 flex flex-col justify-center"
                             style="${BENTO_H}">
                            <div class="pcr-label">零件种数</div>
                            <div class="flex items-baseline gap-1.5 mt-0.5">
                                <span id="pcrHudStatusLamp" class="pcr-status-idle w-1.5 h-1.5 rounded-full shrink-0 translate-y-[-1px]"></span>
                                <div class="pcr-kpi text-ink">
                                    <span id="pcrHudPrice" class="pcr-num" style="${MECH_NUM_STYLE}">—</span>
                                    <span class="pcr-label">种</span>
                                </div>
                            </div>
                            <div class="text-[9px] text-ink-muted truncate leading-none mt-0.5">未出结算价 <span id="pcrHudMissing" class="pcr-num" style="${MECH_NUM_STYLE}">—</span></div>
                        </div>
                        <div id="pcrHudSupplierCard" class="pcr-bento rounded min-w-0 flex flex-col justify-center"
                             style="${BENTO_H}">
                            <div class="pcr-label">已指定供应商</div>
                            <div class="pcr-kpi text-ink mt-0.5">
                                <span id="pcrHudSuppliers" class="pcr-num" style="${MECH_NUM_STYLE}">—</span>
                                <span class="pcr-label">家</span>
                            </div>
                        </div>
                    </div>

                    <div class="col-span-1 rounded min-w-0 border border-line-hud sm:col-span-2 lg:col-span-4"
                         style="${BENTO_H}">
                        <button id="pcrExportBtn" type="button"
                                class="pcr-export relative w-full h-full inline-flex items-center justify-center gap-2 border border-brand-hud [border-top-color:rgb(var(--hairline)/0.35)] text-brand-hud text-[12px] font-black tracking-widest uppercase rounded active:scale-[0.99] transition-all"
                                title="导出《批量零部件价格协议》（不分页、无水印）">
                            ${cornerMarks()}
                            <span class="pcr-ignition-pulse w-2 h-2 rounded-full bg-brand-hud shrink-0 shadow-[0_0_10px_rgb(var(--hud-red))]"></span>
                            <span>导出协议</span>
                        </button>
                    </div>
                </div>
            </div>

            <div class="overflow-hidden w-full max-w-full border border-line-hud">
                <div class="flex items-center gap-2 h-8 px-3 border-b border-line-hud">
                    <span class="pointer-events-none text-ink-muted shrink-0">
                        ${window.svgIcon('search', 'w-3 h-3')}
                    </span>
                    <input id="pcrPartFilter" type="text" maxlength="100" placeholder="零件号 / 名称"
                           title="打开即加载最近一次核价范围。模糊匹配零件号或名称。" aria-label="零件号或名称"
                           class="h-7 w-56 max-w-[40%] min-w-0 bg-transparent text-[11px] text-ink-muted placeholder:text-ink-muted focus:outline-none">
                    <span id="pcrIdentityHint" class="hidden sm:inline text-[9px] text-ink-muted truncate min-w-0 flex-1 text-right">${pcrIdentityHintHtml(false)}</span>
                </div>
                <div id="pcrQaBanner" class="hidden px-5 py-2 border-b border-brand-hud/30 bg-brand-hud/10 text-[11px] text-brand-hud font-mono"></div>

                <div class="relative">
                    <div id="pcrLoading" class="hidden absolute inset-0 z-10 flex items-center justify-center bg-app-hud/70">
                        <div class="w-6 h-6 border-2 border-brand-hud border-t-transparent rounded-full animate-spin"></div>
                    </div>
                    <div class="overflow-x-auto brabus-bg-grid pr-4">
                        <table id="pcrTable" class="w-full table-fixed text-left border-collapse bg-transparent tabular-nums"
                               style="min-width: 1100px;">
                            <colgroup id="pcrColgroup"></colgroup>
                            <thead id="pcrTableHead" class="text-[9px] text-ink-muted uppercase tracking-wider"></thead>
                            <tbody id="pcrTableBody"></tbody>
                        </table>
                    </div>
                    <div id="pcrEmpty" class="hidden px-5 py-10 text-center text-[12px] text-ink-faint font-mono">
                        <div id="pcrEmptyText">正在加载…</div>
                    </div>
                </div>

                ${paginationBarHtml({
                    infoId: 'pcrPageInfo',
                    selectId: 'pcrPageSize',
                    buttonsId: 'pcrPagination',
                    wrapperClass: 'px-5 py-2.5 border-t border-line-subtle flex items-center justify-between gap-3',
                })}
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
        <span class="text-ink-muted text-[10px] shrink-0">${label}</span>
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
        <span class="text-ink-muted text-[10px] shrink-0">${label}</span>
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
        return '打开就带出最近一次核价的基地、项目和月份（版本默认全部）。总成签一份协议，不按供应商筛选。导出必须选全部版本。';
    }
    return '打开就带上最近一次核价的基地、项目、月份（版本默认全部）。导出采购对象<span class="text-brand-hud/70">必须先选供应商</span>，并且版本要选全部。';
}

export function updateRingIndicators() {
    RING_SELECT_IDS.forEach((id) => {
        const select = document.getElementById(id);
        const wrap = document.querySelector(`[data-pcr-ring="${id}"]`);
        if (!select || !wrap) return;
        const isSet = Boolean((select.value || '').trim());
        syncPcrChipFace(id);
        if (PERIOD_SELECT_IDS.has(id)) return;
        wrap.classList.remove('border-brand-hud/40', 'border-line-subtle');
        wrap.classList.add(isSet ? 'border-brand-hud/40' : 'border-line-subtle');
    });
    document.querySelectorAll('[data-pcr-period]').forEach((wrap) => {
        const selects = wrap.querySelectorAll('select');
        const isSet = Array.from(selects).some((el) => Boolean((el.value || '').trim()));
        wrap.classList.remove('border-brand-hud/40', 'border-line-subtle');
        wrap.classList.add(isSet ? 'border-brand-hud/40' : 'border-line-subtle');
    });
}

export function syncPcrChipFace(id) {
    const select = document.getElementById(id);
    const trigger = document.querySelector(`[data-pcr-chip="${id}"]`);
    if (!select || !trigger) return;
    const opt = select.selectedOptions[0];
    const label = trigger.querySelector('[data-pcr-chip-label]') || trigger;
    label.textContent = opt ? opt.textContent : '请选择';
    trigger.classList.remove('text-ink', 'text-ink-muted');
    trigger.classList.add((select.value || '').trim() ? 'text-ink' : 'text-ink-muted');
}

let chipMenuEl = null;
let openChipId = null;

function ensureChipMenu() {
    if (chipMenuEl) return chipMenuEl;
    chipMenuEl = document.createElement('div');
    chipMenuEl.id = 'pcrChipMenu';
    chipMenuEl.className = 'hud-select-menu hidden fixed z-[70] max-h-56 overflow-y-auto py-1';
    chipMenuEl.setAttribute('role', 'listbox');
    document.body.appendChild(chipMenuEl);
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
}

export function updatePcrViewButtons(view) {
    const isAssembly = view === 'assembly';
    const procurementBtn = document.getElementById('pcrViewProcurementBtn');
    const assemblyBtn = document.getElementById('pcrViewAssemblyBtn');
    if (procurementBtn) procurementBtn.classList.toggle('is-active', !isAssembly);
    if (assemblyBtn) assemblyBtn.classList.toggle('is-active', isAssembly);
    document.getElementById('pcrHudSupplierCard')?.classList.toggle('hidden', isAssembly);
    document.getElementById('pcrHudPriceCard')?.classList.toggle('col-span-2', isAssembly);
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
        updateStatusLamp(null);
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
    updateStatusLamp(filters);
}

function updateStatusLamp(filters) {
    const lamp = document.getElementById('pcrHudStatusLamp');
    if (!lamp) return;
    const missing = filters ? Number(filters.missing_month_cell_count) || 0 : 0;
    lamp.className = missing > 0
        ? 'pcr-status-alert w-1.5 h-1.5 rounded-full shrink-0 translate-y-[-1px]'
        : 'pcr-status-idle w-1.5 h-1.5 rounded-full shrink-0 translate-y-[-1px]';
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

    const th = 'px-2 py-2 font-semibold text-center border-b border-line-hud text-ink-muted';
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
        return '<td class="px-2 py-2 text-ink-faint">—</td>';
    }
    const shortName = (row.supplier_abbreviation || '').trim() || full;
    return `<td class="px-1.5 py-2">
        <span class="inline-block max-w-full truncate px-1.5 py-0.5 text-[10px] text-ink-muted bg-app-hud border border-line-subtle rounded"
              title="${esc(full)}">${esc(shortName)}</span>
    </td>`;
}

function cellValue(value) {
    if (value == null || value === '') return '/';
    return String(value);
}

function mechNum(text) {
    return `<span class="pcr-num" style="${MECH_NUM_STYLE}">${esc(text)}</span>`;
}

function amountCell(value) {
    const text = cellValue(value);
    const isMissing = text === '/';
    const cls = isMissing
        ? 'px-2 py-2 text-center text-ink-faint'
        : 'px-2 py-2 text-right text-ink-muted';
    return `<td class="${cls}">${isMissing ? esc(text) : mechNum(text)}</td>`;
}

function moneyCell(value) {
    if (value == null || value === '' || value === '/') {
        return amountCell('/');
    }
    const fixed = typeof formatDecimalFixed === 'function'
        ? formatDecimalFixed(value, 2, { allowNegative: true })
        : null;
    if (fixed == null) return amountCell('/');
    return `<td class="px-2 py-2 text-right text-ink-muted">${mechNum(fixed)}</td>`;
}

function restoreHit(row, year, month) {
    const partNumber = row.part_number || '';
    if (!partNumber || year == null || year === '' || month == null || month === '') return '';
    return `<button type="button"
            class="btn-open-restore absolute inset-0 z-[1] cursor-pointer bg-transparent border-0 p-0"
            data-year="${esc(year)}"
            data-month="${esc(month)}"
            data-part-number="${esc(partNumber)}"
            title="计算过程"
            aria-label="计算过程"></button>
        <span class="pcr-amt-mark pointer-events-none absolute right-0 bottom-0 w-1.5 h-1.5 border-r border-b border-brand-hud"
              aria-hidden="true"></span>`;
}

function monthAmountCell(value, row, year, month) {
    const hit = restoreHit(row, year, month);
    if (value == null || value === '' || value === '/') {
        return `<td class="pcr-amt-cell relative px-2 py-2 text-center text-ink-faint">${esc('/')}${hit}</td>`;
    }
    const fixed = typeof formatDecimalFixed === 'function'
        ? formatDecimalFixed(value, 2, { allowNegative: true })
        : null;
    if (fixed == null) {
        return `<td class="pcr-amt-cell relative px-2 py-2 text-center text-ink-faint">${esc('/')}${hit}</td>`;
    }
    return `<td class="pcr-amt-cell relative px-2 py-2 text-right text-ink-muted">${mechNum(fixed)}${hit}</td>`;
}

function toolingFeeCell(value) {
    if (value == null || value === '' || value === '/') {
        return `<td class="px-2 py-2 pr-4 text-center text-ink-faint">/</td>`;
    }
    const fixed = typeof formatDecimalFixed === 'function'
        ? formatDecimalFixed(value, 2, { allowNegative: true })
        : null;
    if (fixed == null) return `<td class="px-2 py-2 pr-4 text-center text-ink-faint">/</td>`;
    const text = typeof withThousandsSep === 'function' ? withThousandsSep(fixed) : fixed;
    return `<td class="px-2 py-2 pr-4 text-right text-ink-muted">${mechNum(text)}</td>`;
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
            ? (months || []).map((col) => monthAmountCell(
                byMonth[`${col.year}-${col.month}`],
                row,
                col.year,
                col.month,
            )).join('')
            : monthAmountCell(
                row.month_amounts?.[0]?.should_cost,
                row,
                row.month_amounts?.[0]?.year,
                row.month_amounts?.[0]?.month,
            );
        return `
        <tr class="group relative text-[11px] border-b border-line-subtle hover:bg-app-rowhover transition-colors duration-100">
            <td class="px-2 py-2 text-center text-ink relative">
                <div class="absolute left-0 top-0 bottom-0 w-[2px] bg-brand-hud opacity-0 group-hover:opacity-70 transition-opacity"></div>
                ${mechNum(row.seq_label || '')}
            </td>
            <td class="px-2 py-2 text-ink-muted truncate" title="${esc(row.internal_number || '')}">${esc(row.internal_number || '—')}</td>
            <td class="px-2 py-2 text-ink truncate" title="${esc(row.part_number || '')}">${esc(row.part_number || '')}</td>
            <td class="px-2 py-2 text-ink-muted truncate" title="${esc(row.part_name || '')}">${esc(row.part_name || '—')}</td>
            ${showSupplier ? supplierBadgeCell(row) : ''}
            <td class="px-2 py-2 text-right text-ink-muted">${mechNum(cellValue(row.vehicle_qty))}</td>
            <td class="px-2 py-2 text-center text-ink-muted">${esc(row.qty_unit || '件')}</td>
            ${monthHtml}
            <td class="px-2 py-2 text-center text-ink-muted">${esc(row.pay_tooling_separately || 'N')}</td>
            ${moneyCell(row.tooling_alloc_price)}
            ${toolingFeeCell(row.tooling_fee)}
            ${amountCell(row.tooling_alloc_qty)}
            <td class="px-2 py-2 text-center text-ink-faint">—</td>
        </tr>`;
    }).join('');
}

