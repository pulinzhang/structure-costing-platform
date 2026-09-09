/**
 * 采购价格 — BRABUS 800 中控交车（协议黑匣）
 */

import { pageSizeSelectHtml } from '../../../page-size.js?v=2';

const CARBON_MONOLITH_STYLE =
    'background-color:#060608;'
    + 'background-image:repeating-linear-gradient(45deg,rgba(255,255,255,0.025) 0px,rgba(255,255,255,0.025) 1px,transparent 1px,transparent 4px),'
    + 'repeating-linear-gradient(135deg,rgba(255,255,255,0.02) 0px,rgba(255,255,255,0.02) 1px,transparent 1px,transparent 4px);'
    + 'box-shadow:0 10px 40px rgba(255,30,39,0.08), inset 0 1px 0 rgba(255,255,255,0.02);';

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
    'h-7 px-3 text-[11px] rounded-sm bg-[#1C0A0C] border border-[#FF1E27]/40 text-[#FF1E27] font-semibold transition-colors';
const DRIVE_IDLE =
    'h-7 px-3 text-[11px] rounded-sm bg-transparent border border-transparent text-[#6E6E73] hover:text-[#D0D0D5] transition-colors';

const RING_CHEVRON = `<svg class="pointer-events-none absolute right-1.5 top-1/2 -translate-y-1/2 w-3 h-3 text-[#555555]" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>`;

export function procurementContractReportTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="border border-[#FF1E27]/40 overflow-hidden w-full max-w-full"
                 style="${CARBON_MONOLITH_STYLE}">

                <div class="px-5 pt-4 pb-3">
                    <div class="flex items-end gap-3 flex-wrap">
                        ${ringSelect('pcrLocationFilter', '基地')}
                        ${ringSelect('pcrVehicleModelFilter', '项目')}
                        ${ringSelect('pcrBomVersionFilter', '版本')}
                        ${ringPeriod('pcrStartYearFilter', 'pcrStartMonthFilter', '开始年月')}
                        ${ringPeriod('pcrEndYearFilter', 'pcrEndMonthFilter', '结束年月')}
                        <span id="pcrSupplierFilterWrap">${ringSelect('pcrSupplierFilter', '供应商', 'w-52')}</span>
                        <button id="pcrResetBtn" type="button"
                                class="inline-flex items-center gap-1.5 h-8 px-3 text-[11px] font-medium rounded-md bg-transparent text-[#6E6E73] border border-[#2A2A35] hover:text-[#D0D0D5] hover:border-[#3A3A44] transition-colors">
                            ${window.svgIcon('refresh', 'w-3 h-3')}
                            重置
                        </button>
                    </div>
                    <p id="pcrIdentityHint" class="mt-3 text-[9px] leading-relaxed text-[#8A8A93]">${pcrIdentityHintHtml(false)}</p>
                </div>

                <div class="px-5 pb-3.5 flex items-center justify-between gap-5">
                    <div class="grid grid-cols-2 lg:grid-cols-3 gap-4 font-mono flex-1 min-w-0">
                        <div class="bg-[#0A0A0C]/80 border border-[#FF1E27]/30 p-3 relative overflow-hidden">
                            <div class="absolute top-0 left-0 right-0 h-px bg-[#FF1E27]"></div>
                            <span class="text-[#FF1E27] text-[10px] font-bold tracking-widest">单车合计</span>
                            <div class="mt-1 tracking-tight tabular-nums font-black font-mono">
                                <span id="pcrHudVehicleTotal" class="text-[28px] text-[#FF1E27]"
                                      style="text-shadow: 0 0 16px rgba(255,30,39,0.5);">—</span>
                                <span class="text-[12px] text-[#FF1E27]/60 ml-1">元</span>
                            </div>
                            <div id="pcrHudVehicleTotalHint" class="text-[9px] font-mono text-[#8E8E93] mt-1">窗口内各月 · 数量×结算价</div>
                        </div>
                        <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3">
                            <div class="text-[#8E8E93] text-[10px] tracking-wider">零件</div>
                            <div class="text-[18px] font-bold text-[#FFFFFF] mt-1 tabular-nums">
                                <span id="pcrHudPrice">—</span>
                                <span class="text-[10px] text-[#555555] ml-1">种</span>
                            </div>
                            <div class="text-[9px] font-mono text-[#8E8E93] mt-1">
                                未出结算价 <span id="pcrHudMissing">—</span>
                            </div>
                        </div>
                        <div id="pcrHudSupplierCard" class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3">
                            <div class="text-[#8E8E93] text-[10px] tracking-wider">已指定供应商</div>
                            <div class="text-[18px] font-bold text-[#FFFFFF] mt-1 tabular-nums">
                                <span id="pcrHudSuppliers">—</span>
                                <span class="text-[10px] text-[#555555] ml-1">家</span>
                            </div>
                        </div>
                    </div>
                    <div class="flex items-center gap-3 shrink-0 self-center">
                        <div class="flex items-center bg-[#08080C] border border-[#1A1A24] p-0.5" role="group" aria-label="价目视图">
                            <button id="pcrViewProcurementBtn" type="button" class="${DRIVE_ACTIVE}">
                                采购对象
                            </button>
                            <button id="pcrViewAssemblyBtn" type="button" class="${DRIVE_IDLE}">
                                总成
                            </button>
                        </div>
                        <button id="pcrExportBtn" type="button"
                                class="inline-flex items-center gap-1.5 px-4 py-2.5 text-[12px] font-semibold tracking-wide text-[#FF1E27] border border-[#FF1E27]/70 rounded-md bg-gradient-to-b from-[#1A1A22] to-[#0A0A0C] hover:border-[#FF1E27] hover:shadow-[0_0_18px_rgba(255,30,39,0.25)] active:translate-y-px transition-all duration-200"
                                title="导出《批量零部件价格协议》（不分页、无水印）">
                            ${window.svgIcon('download', 'w-3 h-3')}
                            导出协议
                        </button>
                    </div>
                </div>

                <div class="px-5 pb-3 border-t border-[#141418]">
                    <div class="pt-2.5">
                        <div class="relative">
                            <span class="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-[#8E8E93]">
                                ${window.svgIcon('search', 'w-3 h-3')}
                            </span>
                            <input id="pcrPartFilter" type="text" maxlength="100" placeholder="零件号 / 名称"
                                   title="模糊匹配零件号或名称" aria-label="零件号或名称"
                                   class="h-8 w-full pl-8 pr-3 text-[11px] bg-[#030305] border border-[#2A2A35] text-[#C8C8D0] placeholder:text-[#8E8E93] rounded-md focus:outline-none focus:border-[#FF1E27]/40">
                        </div>
                    </div>
                </div>
            </div>

            <div class="bg-[#0A0A0C] border border-[#1A1A22] overflow-hidden w-full max-w-full">
                <div id="pcrQaBanner" class="hidden px-5 py-2 border-b border-[#FF1E27]/30 bg-[#1A080A] text-[11px] text-[#FF1E27] font-mono"></div>

                <div class="relative">
                    <div id="pcrLoading" class="hidden absolute inset-0 z-10 flex items-center justify-center bg-[#0A0A0C]/70">
                        <div class="w-6 h-6 border-2 border-[#FF1E27] border-t-transparent rounded-full animate-spin"></div>
                    </div>
                    <div class="overflow-x-auto bg-[#0A0A0E] brabus-bg-grid pr-4">
                        <table id="pcrTable" class="w-full table-fixed text-left border-collapse bg-transparent"
                               style="min-width: 1100px;">
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

const PERIOD_SELECT_CLASS =
    'h-8 pl-3 pr-6 text-[11px] bg-transparent border-0 text-[#8E8E93] appearance-none cursor-pointer focus:outline-none';

function ringSelect(id, label, widthClass = 'w-32') {
    const extraStyle = id === 'pcrSupplierFilter' ? 'min-width:13rem;' : '';
    return `<label class="space-y-1 min-w-0">
        <span class="block text-[9px] font-semibold text-[#7A7A85] uppercase tracking-[0.14em]">${label}</span>
        <span class="relative block" data-pcr-ring="${id}">
            <span data-pcr-ring-dot class="hidden absolute left-1.5 top-1/2 -translate-y-1/2 w-[2px] h-[2px] rounded-full bg-[#FF1E27]"></span>
            <select id="${id}" style="${extraStyle}" class="${widthClass} h-8 pl-4 pr-7 text-[11px] bg-[#0A0A0C] border border-[#2A2A35] text-[#8E8E93] appearance-none cursor-pointer focus:outline-none focus:border-[#FF1E27]/40 rounded-md transition-colors">
                <option value="">请选择</option>
            </select>
            ${RING_CHEVRON}
        </span>
    </label>`;
}

function ringPeriod(yearId, monthId, label) {
    return `<div class="space-y-1 min-w-0">
        <span class="block text-[9px] font-semibold text-[#7A7A85] uppercase tracking-[0.14em]">${label}</span>
        <span class="flex h-8 items-stretch rounded-md border border-[#2A2A35] bg-[#0A0A0C] overflow-hidden" data-pcr-period="${yearId}">
            <span class="relative" data-pcr-ring="${yearId}">
                <span data-pcr-ring-dot class="hidden absolute left-1.5 top-1/2 -translate-y-1/2 w-[2px] h-[2px] rounded-full bg-[#FF1E27]"></span>
                <select id="${yearId}" class="w-[4.75rem] ${PERIOD_SELECT_CLASS}">
                    <option value="">年</option>
                </select>
                ${RING_CHEVRON}
            </span>
            <span class="w-px self-stretch bg-[#2A2A35]" aria-hidden="true"></span>
            <span class="relative" data-pcr-ring="${monthId}">
                <span data-pcr-ring-dot class="hidden absolute left-1.5 top-1/2 -translate-y-1/2 w-[2px] h-[2px] rounded-full bg-[#FF1E27]"></span>
                <select id="${monthId}" class="w-[4.25rem] ${PERIOD_SELECT_CLASS}">
                    <option value="">月</option>
                </select>
                ${RING_CHEVRON}
            </span>
        </span>
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
        const dot = wrap.querySelector('[data-pcr-ring-dot]');
        dot?.classList.toggle('hidden', !isSet);
        select.classList.remove('text-white', 'text-[#8E8E93]', 'border-[#FF1E27]/40', 'border-[#2A2A35]');
        if (PERIOD_SELECT_IDS.has(id)) {
            select.classList.add(isSet ? 'text-white' : 'text-[#8E8E93]');
            return;
        }
        if (isSet) {
            select.classList.add('text-white', 'border-[#FF1E27]/40');
        } else {
            select.classList.add('text-[#8E8E93]', 'border-[#2A2A35]');
        }
    });
    document.querySelectorAll('[data-pcr-period]').forEach((wrap) => {
        const selects = wrap.querySelectorAll('select');
        const isSet = Array.from(selects).some((el) => Boolean((el.value || '').trim()));
        wrap.classList.remove('border-[#FF1E27]/40', 'border-[#2A2A35]');
        wrap.classList.add(isSet ? 'border-[#FF1E27]/40' : 'border-[#2A2A35]');
    });
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

export function updatePcrHud(filters) {
    const setText = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value == null ? '—' : String(value);
    };
    if (!filters) {
        setText('pcrHudVehicleTotal', '—');
        setText('pcrHudVehicleTotalHint', '窗口内各月汇总');
        setText('pcrHudPrice', '—');
        setText('pcrHudMissing', '—');
        setText('pcrHudSuppliers', '—');
        return;
    }
    const total = filters.vehicle_total;
    if (total == null || total === '') {
        setText('pcrHudVehicleTotal', '—');
    } else {
        setText('pcrHudVehicleTotal', fmtHudMoney(total));
    }
    const skipped = Number(filters.vehicle_total_skipped) || 0;
    let hint = '窗口内各月 · 数量×结算价';
    if (skipped > 0) hint = `${hint} · ${skipped} 种未计入`;
    setText('pcrHudVehicleTotalHint', hint);
    setText('pcrHudPrice', filters.price_row_count ?? 0);
    setText('pcrHudMissing', filters.missing_month_cell_count ?? 0);
    setText('pcrHudSuppliers', filters.specified_supplier_count ?? 0);
}

function fmtHudMoney(value) {
    if (typeof window.fmtNum === 'function') return window.fmtNum(value, 2);
    const n = Number(value);
    return Number.isFinite(n) ? n.toFixed(2) : String(value);
}

export function renderPcrTableHead(months) {
    const head = document.getElementById('pcrTableHead');
    const colgroup = document.getElementById('pcrColgroup');
    const table = document.getElementById('pcrTable');
    const monthCols = Array.isArray(months) ? months : [];
    const monthCount = Math.max(monthCols.length, 1);
    if (table) table.style.minWidth = `${1040 + monthCount * 120}px`;

    const widths = ['72px', '90px', '130px', '144px', '148px', '72px', '56px'];
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
    if (head) {
        head.innerHTML = `
            <tr>
                <th class="${th}">序号</th>
                <th class="${th} text-left">存货编码</th>
                <th class="${th} text-left">零件号</th>
                <th class="${th} text-left">零件名称</th>
                <th class="${th} text-left">供应商</th>
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

export function renderPcrRows(rows, months) {
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
        <tr class="group relative font-mono text-[11px] border-b border-[#141418] hover:bg-[#161620] transition-colors duration-100">
            <td class="px-2 py-2 text-center text-[#F0F0F2] tabular-nums relative">
                <div class="absolute left-0 top-0 bottom-0 w-[2px] bg-[#FF1E27] opacity-0 group-hover:opacity-70 transition-opacity"></div>
                ${esc(row.seq_label || '')}
            </td>
            <td class="px-2 py-2 text-[#8E8E93] truncate" title="${esc(row.internal_number || '')}">${esc(row.internal_number || '—')}</td>
            <td class="px-2 py-2 text-[#F0F0F2] truncate" title="${esc(row.part_number || '')}">${esc(row.part_number || '')}</td>
            <td class="px-2 py-2 text-[#8E8E93] truncate" title="${esc(row.part_name || '')}">${esc(row.part_name || '—')}</td>
            <td class="px-2 py-2 text-[#C8C8D0] truncate" title="${esc(row.supplier_name || '')}">${esc(row.supplier_name || '—')}</td>
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
