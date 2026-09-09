/**
 * 采购价格 — 价目表预览（Brabus Carbon HUD）
 */

import { pageSizeSelectHtml } from '../../../page-size.js?v=2';

export function procurementContractReportTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="bg-[#0A0A0C] border border-[#1A1A22] overflow-hidden w-full max-w-full"
                 style="box-shadow: 0 4px 24px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.02);">

                <div class="px-5 pt-4 pb-3.5 border-b border-[#14141A]"
                     style="background: linear-gradient(135deg, #0E0E12 0%, #121218 45%, #0C0C10 100%);">
                    <div class="flex items-start justify-between gap-4 mb-3">
                        <div class="grid grid-cols-2 lg:grid-cols-3 gap-3 font-mono flex-1 min-w-0">
                            <div class="bg-gradient-to-b from-[#18080A] to-[#0D0708] border border-[#FF1E27]/50 p-3.5 relative overflow-hidden"
                                 style="box-shadow: 0 0 30px rgba(255,30,39,0.15), inset 0 1px 0 rgba(255,30,39,0.12);">
                                <div class="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-[#FF1E27] to-transparent"
                                     style="box-shadow: 0 0 10px #FF1E27;"></div>
                                <div class="flex justify-between items-start">
                                    <span class="text-[#FF1E27] text-[10px] font-bold tracking-widest">单车合计</span>
                                    <span class="w-2 h-2 rounded-full bg-[#FF1E27] animate-pulse"
                                          style="box-shadow: 0 0 8px #FF1E27;"></span>
                                </div>
                                <div class="text-[26px] font-black text-[#FF1E27] font-mono mt-1 tracking-tight tabular-nums"
                                     style="text-shadow: 0 0 12px rgba(255,30,39,0.7);">
                                    <span id="pcrHudVehicleTotal">—</span>
                                    <span class="text-[12px] text-[#FF1E27]/70 ml-1">元</span>
                                </div>
                                <div id="pcrHudVehicleTotalHint" class="text-[9px] font-mono text-[#FF1E27]/60 mt-1">窗口内各月 · 数量×结算价</div>
                            </div>
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3"
                                 style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);">
                                <div class="text-[#555555] text-[10px] tracking-wider">零件</div>
                                <div class="text-[18px] font-bold text-[#FFFFFF] mt-1 tabular-nums">
                                    <span id="pcrHudPrice">—</span>
                                    <span class="text-[10px] text-[#555555] ml-1">种</span>
                                </div>
                                <div class="text-[9px] font-mono text-[#555555] mt-1">
                                    未出结算价 <span id="pcrHudMissing">—</span>
                                </div>
                            </div>
                            <div id="pcrHudSupplierCard" class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3"
                                 style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);">
                                <div class="text-[#555555] text-[10px] tracking-wider">已指定供应商</div>
                                <div class="text-[18px] font-bold text-[#FFFFFF] mt-1 tabular-nums">
                                    <span id="pcrHudSuppliers">—</span>
                                    <span class="text-[10px] text-[#555555] ml-1">家</span>
                                </div>
                            </div>
                        </div>
                        <div class="flex flex-col items-end gap-2 shrink-0">
                            <div class="flex items-center gap-1.5" role="group" aria-label="价目视图">
                                <button id="pcrViewProcurementBtn" type="button"
                                        class="px-3 py-1.5 text-[11px] font-medium rounded-md bg-[#1A080A] border border-[#FF1E27]/50 text-[#FF1E27] transition-all">
                                    采购对象
                                </button>
                                <button id="pcrViewAssemblyBtn" type="button"
                                        class="px-3 py-1.5 text-[11px] font-medium rounded-md bg-transparent border border-[#2A2A35] text-[#6E6E73] hover:text-white transition-all">
                                    总成
                                </button>
                            </div>
                            <button id="pcrExportBtn" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] hover:bg-[#FF1E27]/10 hover:shadow-[0_0_12px_rgba(255,30,39,0.2)] transition-all duration-200"
                                    title="导出《批量零部件价格协议》（不分页、无水印）">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                导出协议
                            </button>
                        </div>
                    </div>
                </div>

                <div class="px-5 py-3 border-b border-[#14141A]"
                     style="background: linear-gradient(180deg, #0C0C10 0%, #0A0A0E 100%);">
                    <div class="flex items-center justify-between gap-4 bg-[#0C0C10] border border-[#1E1E26] px-4 py-2.5 rounded-md font-mono text-[11px]"
                         style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.02), 0 0 20px rgba(0,0,0,0.3);">
                        <div class="flex items-center gap-3 min-w-0 flex-1">
                            <span class="text-[#555555] shrink-0 tracking-wider">当前筛选：</span>
                            <div class="flex items-center gap-2 flex-wrap">
                                <span id="pcrCapsulePeriod" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">窗口未定</span>
                                <span id="pcrCapsuleLocation" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部基地</span>
                                <span id="pcrCapsuleVehicle" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部项目</span>
                                <span id="pcrCapsuleSupplier" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部供应商</span>
                                <input id="pcrPartNumberFilter" type="text" maxlength="50" placeholder="零件号"
                                       class="h-7 w-28 px-2 text-[11px] bg-[#0A0A0E] border border-[#2A2A35] text-white placeholder:text-[#555555] rounded-md focus:outline-none focus:border-[#FF1E27]">
                                <input id="pcrPartNameFilter" type="text" maxlength="100" placeholder="零件名称"
                                       class="h-7 w-36 px-2 text-[11px] bg-[#0A0A0E] border border-[#2A2A35] text-white placeholder:text-[#555555] rounded-md focus:outline-none focus:border-[#FF1E27]">
                            </div>
                        </div>
                        <div class="flex items-center gap-3 shrink-0">
                            <button type="button" id="pcrToggleAdvancedFilter"
                                    class="text-[#6E6E73] hover:text-white transition-colors flex items-center gap-1.5 text-[11px]">
                                <span id="pcrAdvancedFilterLabel">展开高级筛选</span>
                                <span id="pcrAdvancedFilterCount" class="text-[#555555]">(0)</span>
                            </button>
                            <button type="button" id="pcrSearchBtn"
                                    class="inline-flex items-center gap-1.5 h-7 px-3 text-[11px] font-semibold rounded-sm text-[#c8c8c8] border border-[#8a2020] transition-all duration-200 hover:text-white"
                                    style="background: linear-gradient(180deg, #3d1515 0%, #2d0f0f 100%); border-color: #6b1a1a; box-shadow: 0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(211,47,47,0.1);">
                                ${window.svgIcon('search', 'w-3 h-3')}
                                查询
                            </button>
                        </div>
                    </div>

                    <div id="pcrAdvancedFilterPanel" class="hidden mt-3 pt-3 border-t border-[#1A1A22]">
                        <div class="flex items-end gap-3 flex-wrap">
                            ${filterSelect('pcrLocationFilter', '基地')}
                            ${filterSelect('pcrVehicleModelFilter', '项目')}
                            ${filterSelect('pcrBomVersionFilter', '版本')}
                            ${filterSelect('pcrStartYearFilter', '开始年')}
                            ${filterSelect('pcrStartMonthFilter', '开始月')}
                            ${filterSelect('pcrEndYearFilter', '结束年')}
                            ${filterSelect('pcrEndMonthFilter', '结束月')}
                            <span id="pcrSupplierFilterWrap">${filterSelect('pcrSupplierFilter', '供应商')}</span>
                            <button id="pcrResetBtn" type="button"
                                    class="inline-flex items-center gap-1.5 h-8 px-3 text-[11px] font-medium rounded-md bg-transparent text-[#6E6E73] border border-[#2A2A35] hover:bg-[#FF1E27]/10 hover:border-[#FF1E27]/50 hover:text-[#FF1E27] transition-all duration-200">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>
                        </div>
                        <p id="pcrAdvancedHint" class="mt-2 text-[10px] text-[#555555]">打开即加载**最近一次核价**的基地 / 项目 / 版本 / 月份。采购对象导出须选定供应商。</p>
                    </div>
                </div>

                <div id="pcrQaBanner" class="hidden px-5 py-2 border-b border-[#FF1E27]/30 bg-[#1A080A] text-[11px] text-[#FF1E27] font-mono"></div>

                <div class="relative">
                    <div id="pcrLoading" class="hidden absolute inset-0 z-10 flex items-center justify-center bg-[#0A0A0C]/70">
                        <div class="w-6 h-6 border-2 border-[#FF1E27] border-t-transparent rounded-full animate-spin"></div>
                    </div>
                    <div class="overflow-x-auto bg-[#0A0A0E] brabus-bg-grid">
                        <table id="pcrTable" class="w-full table-fixed text-left border-collapse bg-transparent"
                               style="min-width: 1100px;">
                            <colgroup id="pcrColgroup"></colgroup>
                            <thead id="pcrTableHead" class="text-[9px] text-[#555555] uppercase tracking-wider"></thead>
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

function filterSelect(id, label, widthClass = 'w-32') {
    const extraStyle = id === 'pcrSupplierFilter' ? 'min-width:13rem;' : '';
    return `<label class="space-y-1">
        <span class="block text-[9px] font-semibold text-[#555555] uppercase tracking-[0.14em]">${label}</span>
        <select id="${id}" style="${extraStyle}" class="${widthClass} h-8 pl-2.5 pr-7 text-[11px] bg-[#0A0A0E] border border-[#2A2A35] text-[#A1A1A6] appearance-none cursor-pointer focus:outline-none focus:border-[#FF1E27] rounded-md transition-colors">
            <option value="">请选择</option>
        </select>
    </label>`;
}

export function updatePcrViewButtons(view) {
    const isAssembly = view === 'assembly';
    const active = 'px-3 py-1.5 text-[11px] font-medium rounded-md bg-[#1A080A] border border-[#FF1E27]/50 text-[#FF1E27] transition-all';
    const idle = 'px-3 py-1.5 text-[11px] font-medium rounded-md bg-transparent border border-[#2A2A35] text-[#6E6E73] hover:text-white transition-all';
    const procurementBtn = document.getElementById('pcrViewProcurementBtn');
    const assemblyBtn = document.getElementById('pcrViewAssemblyBtn');
    if (procurementBtn) procurementBtn.className = isAssembly ? idle : active;
    if (assemblyBtn) assemblyBtn.className = isAssembly ? active : idle;
    document.getElementById('pcrHudSupplierCard')?.classList.toggle('hidden', isAssembly);
    document.getElementById('pcrCapsuleSupplier')?.classList.toggle('hidden', isAssembly);
    document.getElementById('pcrSupplierFilterWrap')?.classList.toggle('hidden', isAssembly);
    const hint = document.getElementById('pcrAdvancedHint');
    if (hint) {
        hint.textContent = isAssembly
            ? '打开即加载最近一次核价的基地 / 项目 / 版本 / 月份。总成整包一份协议，不筛供应商。'
            : '打开即加载最近一次核价的基地 / 项目 / 版本 / 月份。采购对象导出须选定供应商。';
    }
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

export function updatePcrFilterCapsules() {
    const startYear = document.getElementById('pcrStartYearFilter')?.value || '';
    const startMonth = document.getElementById('pcrStartMonthFilter')?.value || '';
    const endYear = document.getElementById('pcrEndYearFilter')?.value || '';
    const endMonth = document.getElementById('pcrEndMonthFilter')?.value || '';
    const location = document.getElementById('pcrLocationFilter')?.value || '';
    const vehicle = document.getElementById('pcrVehicleModelFilter')?.value || '';
    const version = document.getElementById('pcrBomVersionFilter')?.value || '';
    const supplier = document.getElementById('pcrSupplierFilter')?.value || '';
    const partNumber = document.getElementById('pcrPartNumberFilter')?.value?.trim() || '';
    const partName = document.getElementById('pcrPartNameFilter')?.value?.trim() || '';

    const active = 'bg-[#1A1A22] border border-[#2A2A35] text-white px-2.5 py-1 rounded-md font-bold';
    const idle = 'bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md';

    const periodEl = document.getElementById('pcrCapsulePeriod');
    if (periodEl) {
        const startText = fmtPeriod(startYear, startMonth);
        const endText = fmtPeriod(endYear, endMonth);
        if (startText && endText) {
            periodEl.textContent = startText === endText ? startText : `${startText}～${endText}`;
            periodEl.className = active;
        } else {
            periodEl.textContent = '窗口未定';
            periodEl.className = idle;
        }
    }
    const locationEl = document.getElementById('pcrCapsuleLocation');
    if (locationEl) {
        locationEl.textContent = location || '全部基地';
        locationEl.className = location ? active : idle;
    }
    const vehicleEl = document.getElementById('pcrCapsuleVehicle');
    if (vehicleEl) {
        vehicleEl.textContent = vehicle ? (version ? `${vehicle}/${version}` : vehicle) : '全部项目';
        vehicleEl.className = vehicle ? active : idle;
    }
    const supplierEl = document.getElementById('pcrCapsuleSupplier');
    if (supplierEl) {
        supplierEl.textContent = supplier || '全部供应商';
        supplierEl.className = supplier ? active : idle;
    }
    const countEl = document.getElementById('pcrAdvancedFilterCount');
    if (countEl) {
        const advancedActive = [
            startYear, startMonth, endYear, endMonth, location, vehicle, version, supplier,
            partNumber, partName,
        ].filter(Boolean).length;
        countEl.textContent = `(${advancedActive})`;
    }
}

export function renderPcrTableHead(months) {
    const head = document.getElementById('pcrTableHead');
    const colgroup = document.getElementById('pcrColgroup');
    const table = document.getElementById('pcrTable');
    const monthCols = Array.isArray(months) ? months : [];
    const monthCount = Math.max(monthCols.length, 1);
    if (table) table.style.minWidth = `${1120 + monthCount * 120}px`;

    const widths = ['72px', '110px', '130px', '180px', '160px', '72px', '56px'];
    for (let i = 0; i < monthCount; i += 1) widths.push('120px');
    widths.push('56px', '110px', '120px', '100px', '72px');
    if (colgroup) {
        colgroup.innerHTML = widths.map((width) => `<col style="width:${width}">`).join('');
    }

    const th = 'px-2 py-2 font-semibold text-center border-b border-[#1A1A22] text-[#555555]';
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
                <th class="${th} text-right">工装费（元）</th>
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
        return amountCell('/');
    }
    const fixed = typeof formatDecimalFixed === 'function'
        ? formatDecimalFixed(value, 2, { allowNegative: true })
        : null;
    if (fixed == null) return amountCell('/');
    const text = typeof withThousandsSep === 'function' ? withThousandsSep(fixed) : fixed;
    return `<td class="px-2 py-2 text-right tabular-nums text-[#C8C8D0]">${esc(text)}</td>`;
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

export function renderPcrPagination(currentPage, totalPages) {
    if (totalPages <= 1) return '';
    let buttons = `
        <button class="pcr-page-btn flex items-center justify-center w-6 h-6 text-[10px] ${currentPage === 1 ? 'text-[#2E2E36] cursor-not-allowed' : 'text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620]'} transition-all"
                data-page="${currentPage - 1}" ${currentPage === 1 ? 'disabled' : ''}>
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path></svg>
        </button>`;
    const maxVisible = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);
    if (endPage - startPage < maxVisible - 1) startPage = Math.max(1, endPage - maxVisible + 1);
    if (startPage > 1) {
        buttons += `<button class="pcr-page-btn flex items-center justify-center w-6 h-6 text-[10px] text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620]" data-page="1">1</button>`;
        if (startPage > 2) buttons += `<span class="px-0.5 text-[#2E2E36] text-[9px]">—</span>`;
    }
    for (let i = startPage; i <= endPage; i += 1) {
        const isActive = i === currentPage;
        buttons += `<button class="pcr-page-btn flex items-center justify-center w-6 h-6 text-[10px] ${isActive ? 'bg-[#FF1E27] text-white font-bold' : 'text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620]'}" data-page="${i}">${i}</button>`;
    }
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) buttons += `<span class="px-0.5 text-[#2E2E36] text-[9px]">—</span>`;
        buttons += `<button class="pcr-page-btn flex items-center justify-center w-6 h-6 text-[10px] text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620]" data-page="${totalPages}">${totalPages}</button>`;
    }
    buttons += `
        <button class="pcr-page-btn flex items-center justify-center w-6 h-6 text-[10px] ${currentPage === totalPages ? 'text-[#2E2E36] cursor-not-allowed' : 'text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620]'}"
                data-page="${currentPage + 1}" ${currentPage === totalPages ? 'disabled' : ''}>
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>
        </button>`;
    return buttons;
}
