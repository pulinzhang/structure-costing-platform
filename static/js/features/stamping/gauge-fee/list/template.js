/**
 * 冲压检具费列表 — Brabus Carbon & Precision Dark
 * 布局对齐零件列表：HUD + 胶囊筛选（默认收起）
 */

import { paginationBarHtml } from '../../../../page-size.js?v=3';
import { moreMenuItemHtml, moreMenuShellHtml } from '../../../../more-menu.js?v=1';
import { partShortCodeCellHtml, partNumberNameCellHtml } from '../../../../part-identity.js?v=3';

function canOp(code) {
    return typeof window.can === 'function' ? window.can(code) : true;
}

function filterSelect(id, label) {
    return `<label class="space-y-1">
        <span class="block text-[9px] font-semibold text-[#555555] uppercase tracking-[0.14em]">${label}</span>
        <select id="${id}" class="w-32 h-8 pl-2.5 pr-7 text-[11px] bg-[#0A0A0E] border border-[#2A2A35] text-[#A1A1A6] appearance-none cursor-pointer focus:outline-none focus:border-[#FF1E27] rounded-md transition-colors">
            <option value="">全部</option>
        </select>
    </label>`;
}

function filterInput(id, label, placeholder) {
    return `<label class="space-y-1">
        <span class="block text-[9px] font-semibold text-[#555555] uppercase tracking-[0.14em]">${label}</span>
        <input id="${id}" placeholder="${placeholder}" autocomplete="off"
               class="h-8 w-36 px-2.5 text-[11px] bg-[#0A0A0E] border border-[#2A2A35] text-[#ffffff] placeholder:text-[#555555] rounded-md focus:outline-none focus:border-[#FF1E27] transition-colors">
    </label>`;
}

export function gaugeFeeListTemplate() {
    const canDelete = canOp('op:stamping-gauge-fee:delete');
    const canExport = canOp('op:stamping-gauge-fee:export');
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="bg-[#0A0A0C] border border-[#1A1A22] overflow-hidden w-full max-w-full"
                 style="box-shadow: 0 4px 24px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.02);">

                <div class="px-5 pt-4 pb-3.5 border-b border-[#14141A]"
                     style="background: linear-gradient(135deg, #0E0E12 0%, #121218 45%, #0C0C10 100%);">
                    <div class="flex items-start justify-between gap-4 mb-3">
                        <div class="grid grid-cols-2 gap-3 font-mono flex-1 min-w-0">
                            <div class="bg-gradient-to-b from-[#18080A] to-[#0D0708] border border-[#FF1E27]/50 p-3.5 relative overflow-hidden"
                                 style="box-shadow: 0 0 30px rgba(255,30,39,0.15), inset 0 1px 0 rgba(255,30,39,0.12);">
                                <div class="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-[#FF1E27] to-transparent"
                                     style="box-shadow: 0 0 10px #FF1E27;"></div>
                                <div class="flex justify-between items-start">
                                    <span class="text-[#FF1E27] text-[10px] font-bold tracking-widest">检具费合计</span>
                                    <span class="w-2 h-2 rounded-full bg-[#FF1E27] animate-pulse"
                                          style="box-shadow: 0 0 8px #FF1E27;"></span>
                                </div>
                                <div class="text-[26px] font-black text-[#FF1E27] font-mono mt-1 tracking-tight tabular-nums leading-none"
                                     style="text-shadow: 0 0 12px rgba(255,30,39,0.7), 0 0 25px rgba(255,30,39,0.3);">
                                    <span id="gflHudTotalFee">—</span>
                                    <span class="text-[10px] text-[#FF1E27]/70 ml-1 font-bold">万</span>
                                </div>
                                <div class="text-[9px] font-mono text-[#FF1E27]/60 mt-1">当前筛选</div>
                            </div>
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3 backdrop-blur-sm"
                                 style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);">
                                <div class="text-[#555555] text-[10px] tracking-wider">档案</div>
                                <div class="text-[18px] font-bold text-[#FFFFFF] mt-1 tabular-nums">
                                    <span id="gflHudTotal">—</span>
                                    <span class="text-[10px] text-[#555555] ml-1">条</span>
                                </div>
                                <div class="text-[9px] font-mono text-[#6E6E73] mt-1">
                                    生效 <span id="gflHudEffectiveCount">—</span>
                                    <span class="text-[#3A3A42] mx-1">/</span>
                                    失效 <span id="gflHudInvalidCount">—</span>
                                </div>
                            </div>
                        </div>
                        <div class="flex items-center gap-1.5 shrink-0">
                            ${canDelete ? moreMenuShellHtml({
                                wrapId: 'gflMoreWrap',
                                btnId: 'gflMoreBtn',
                                menuId: 'gflMoreMenu',
                                itemsHtml: moreMenuItemHtml({ id: 'gflDeleteScopeBtn', label: '批量删除', danger: true }),
                            }) : ''}
                            ${canExport ? `
                            <button type="button" id="gflExportBtn"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] hover:bg-[#FF1E27]/10 hover:shadow-[0_0_12px_rgba(255,30,39,0.2)] transition-all duration-200">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                Excel
                            </button>` : ''}
                        </div>
                    </div>
                    <div class="text-[11px] font-mono text-[#555555] truncate">
                        查询范围：<span id="gflHudScope" class="text-[#8E8E93]">全部范围</span>
                    </div>
                </div>

                <div class="px-5 py-3 border-b border-[#14141A]"
                     style="background: linear-gradient(180deg, #0C0C10 0%, #0A0A0E 100%);">
                    <div class="flex items-center justify-between gap-4 bg-[#0C0C10] border border-[#1E1E26] px-4 py-2.5 rounded-md font-mono text-[11px]"
                         style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.02), 0 0 20px rgba(0,0,0,0.3);">
                        <div class="flex items-center gap-3 min-w-0 flex-1">
                            <span class="text-[#555555] shrink-0 tracking-wider">当前筛选：</span>
                            <div class="flex items-center gap-2 flex-wrap">
                                <span id="gflCapsuleLocation" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部基地</span>
                                <span id="gflCapsuleVehicle" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部项目</span>
                                <span id="gflCapsuleStatus" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部状态</span>
                            </div>
                        </div>
                        <div class="flex items-center gap-3 shrink-0">
                            <button type="button" id="gflToggleAdvancedFilter"
                                    class="text-[#6E6E73] hover:text-white transition-colors flex items-center gap-1.5 text-[11px]">
                                <span id="gflAdvancedFilterLabel">展开高级筛选</span>
                                <span id="gflAdvancedFilterCount" class="text-[#555555]">(0)</span>
                            </button>
                            <button type="button" id="gflSearchBtn"
                                    class="inline-flex items-center gap-1.5 h-7 px-3 text-[11px] font-semibold rounded-sm text-[#c8c8c8] border border-[#8a2020] transition-all duration-200 hover:text-white"
                                    style="background: linear-gradient(180deg, #3d1515 0%, #2d0f0f 100%); border-color: #6b1a1a; box-shadow: 0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(211,47,47,0.1), 0 0 12px rgba(198,40,40,0.08);">
                                ${window.svgIcon('search', 'w-3 h-3')}
                                查询
                            </button>
                        </div>
                    </div>
                    <div id="gflAdvancedFilterPanel" class="hidden mt-3 pt-3 border-t border-[#1A1A22]">
                        <div class="flex items-end gap-3 flex-wrap">
                            ${filterSelect('gflLocation', '基地')}
                            ${filterSelect('gflVehicle', '项目')}
                            ${filterInput('gflPartNumber', '零件号', '短号或完整零件号')}
                            <label class="space-y-1">
                                <span class="block text-[9px] font-semibold text-[#555555] uppercase tracking-[0.14em]">状态</span>
                                <select id="gflStatus"
                                        class="w-32 h-8 pl-2.5 pr-7 text-[11px] bg-[#0A0A0E] border border-[#2A2A35] text-[#A1A1A6] appearance-none cursor-pointer focus:outline-none focus:border-[#FF1E27] rounded-md transition-colors">
                                    <option value="">全部</option>
                                    <option value="effective">生效</option>
                                    <option value="invalid">失效</option>
                                </select>
                            </label>
                            <button id="gflResetBtn" type="button"
                                    class="inline-flex items-center gap-1.5 h-8 px-3 text-[11px] font-medium rounded-md bg-transparent text-[#6E6E73] border border-[#2A2A35] hover:bg-[#FF1E27]/10 hover:border-[#FF1E27]/50 hover:text-[#FF1E27] transition-all duration-200">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>
                        </div>
                        <p class="mt-2 text-[10px] text-[#555555]">筛选均可选。批量删除须同时选定基地和项目。</p>
                    </div>
                </div>

                <div class="overflow-x-auto brabus-bg-grid">
                    <table class="w-full table-fixed bg-transparent border-collapse" style="min-width: 1000px;">
                        <colgroup>
                            <col style="width: 8px;">
                            <col style="width: 80px;">
                            <col style="width: 80px;">
                            <col style="width: 72px;">
                            <col style="width: 160px;">
                            <col style="width: 110px;">
                            <col style="width: 110px;">
                            <col style="width: 72px;">
                            <col style="width: 88px;">
                        </colgroup>
                        <thead>
                            <tr class="border-b border-[#17171C] bg-[#0B0B0D]/95">
                                <th class="p-0" aria-hidden="true"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">基地</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">项目</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#A1A1A6]">短代码</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">零件</th>
                                <th class="px-2 py-2 text-right text-[9px] font-semibold tracking-[0.06em] text-[#FF1E27]/90 bg-[#1A080A]">检具费（万）</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">分摊（万台）</th>
                                <th class="px-1 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">状态</th>
                                <th class="p-0 w-9" aria-label="操作"></th>
                            </tr>
                        </thead>
                        <tbody id="gflTableBody"></tbody>
                    </table>
                </div>
                ${paginationBarHtml({ infoId: 'gflTotalCount', selectId: 'gflPageSize', buttonsId: 'gflPaginationBtns' })}
                <div id="gflEmptyState" class="hidden flex flex-col items-center justify-center py-14">
                    <div class="w-10 h-10 flex items-center justify-center mb-3 rounded-md bg-[#121218] border border-[#2A2A35]">
                        ${window.svgIcon('clipboard-list', 'w-4 h-4 text-[#555555]')}
                    </div>
                    <h5 class="text-[11px] font-medium text-[#8E8E93] mb-1">暂无检具费</h5>
                    <p class="text-[10px] text-[#555555]">先选基地 + 项目下载模板并上传</p>
                </div>
                <div id="gflLoadingState" class="hidden flex items-center justify-center py-14">
                    <div class="w-5 h-5 border-2 border-[#2A2A35] border-t-[#FF1E27] rounded-full animate-spin"
                         style="box-shadow: 0 0 12px rgba(255,30,39,0.35);"></div>
                </div>
            </div>
        </div>

        <div class="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm" id="gflEditBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[420px] bg-[#121215] border-l border-[#2c2c2c] transform translate-x-full transition-transform duration-300 flex flex-col"
             id="gflEditDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-[#2c2c2c] bg-[#16161a] shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-[#FF1E27]"></span>
                    <h5 class="text-xs font-semibold text-white tracking-wider">编辑检具费</h5>
                </div>
                <button type="button" id="gflCloseEdit" class="text-[#616161] hover:text-white w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-5">
                <form id="gflEditForm" class="space-y-4">
                    <input type="hidden" id="gflEditId" value="">
                    <p id="gflEditScope" class="text-[11px] font-mono text-[#9e9e9e]"></p>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">检具费（万元） <span class="text-[#FF1E27]">*</span></label>
                        <input type="text" id="gflEditGaugeFee" required inputmode="decimal"
                               class="w-full h-8 px-3 text-xs font-mono bg-[#0a0a0c] border border-[#2c2c2c] text-white placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252]"
                               placeholder="如 0.8" autocomplete="off">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">项目分摊数量（万台） <span class="text-[#FF1E27]">*</span></label>
                        <input type="text" id="gflEditAllocQty" required inputmode="numeric"
                               class="w-full h-8 px-3 text-xs font-mono bg-[#0a0a0c] border border-[#2c2c2c] text-white placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252]"
                               placeholder="如 10" autocomplete="off">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">状态 <span class="text-[#FF1E27]">*</span></label>
                        <select id="gflEditStatus" required
                                class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-[#9e9e9e] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252]">
                            <option value="effective">生效</option>
                            <option value="invalid">失效</option>
                        </select>
                    </div>
                    <p class="text-[10px] text-[#616161]">基地、项目、零件号不可改；名称以模具布点为准。</p>
                </form>
            </div>
            <div class="px-5 py-3 border-t border-[#2c2c2c] flex items-center justify-end gap-2 bg-[#16161a] shrink-0">
                <button type="button" id="gflCancelEdit"
                        class="px-4 py-1.5 text-xs text-[#9e9e9e] hover:text-white border border-[#2c2c2c] hover:bg-[#262626] transition-all">取消</button>
                <button type="button" id="gflSubmitEdit"
                        class="bg-[#FF1E27] hover:bg-[#d32f2f] text-white px-5 py-1.5 text-xs font-semibold transition-all">保存</button>
            </div>
        </div>

        <div class="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm" id="gflDeleteBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[380px] bg-[#121215] border-l border-[#2c2c2c] transform translate-x-full transition-transform duration-300 flex flex-col"
             id="gflDeleteDrawer" style="display:none;">
            <div class="px-5 py-3.5 border-b border-[#2c2c2c] bg-[#16161a]">
                <h5 class="text-xs font-semibold text-white" id="gflDeleteTitle">确认删除</h5>
            </div>
            <div class="p-5 text-[12px] text-[#9e9e9e]">
                <input type="hidden" id="gflDeleteId" value="">
                <input type="hidden" id="gflDeleteMode" value="">
                <p id="gflDeleteHint"></p>
                <p class="mt-2 text-[11px] text-[#616161]">不影响冲压工艺。</p>
            </div>
            <div class="mt-auto px-5 py-3 border-t border-[#2c2c2c] flex justify-end gap-2">
                <button type="button" id="gflCancelDelete" class="px-4 py-1.5 text-xs text-[#9e9e9e] border border-[#2c2c2c]">取消</button>
                <button type="button" id="gflConfirmDelete" class="bg-[#c62828] text-white px-4 py-1.5 text-xs font-semibold">删除</button>
            </div>
        </div>
    `;
}

export function renderTableRows(records) {
    if (!records || !records.length) return '';
    const canUpdate = canOp('op:stamping-gauge-fee:update');
    const canDelete = canOp('op:stamping-gauge-fee:delete');
    const numCell = 'px-2 py-2 font-mono text-[10px] text-right tabular-nums text-[#8E8E93]';
    return records
        .map((record) => {
            const isEffective = record.status === 'effective';
            const statusClass = isEffective
                ? 'text-[#4caf50] bg-[#2e7d32]/20 px-1.5 py-0.5'
                : 'text-[#8E8E93] bg-[#262626] px-1.5 py-0.5';
            const scope = `${record.location} / ${record.vehicle_model} / ${record.part_number}`;
            return `
        <tr class="group relative font-mono text-[11px] border-b border-[#141418] hover:bg-[#161620] transition-colors duration-100">
            <td class="p-0 relative">
                <div class="absolute left-0 top-0 bottom-0 w-[2px] bg-[#FF1E27] opacity-0 group-hover:opacity-70 transition-opacity"></div>
            </td>
            <td class="px-2 py-2 overflow-hidden text-[12px] font-semibold text-[#F0F0F2] truncate" title="${esc(record.location)}">${esc(record.location)}</td>
            <td class="px-2 py-2 overflow-hidden text-[14px] font-bold text-[#F0F0F2] truncate" title="${esc(record.vehicle_model)}">${esc(record.vehicle_model)}</td>
            <td class="px-2 py-2 overflow-hidden whitespace-nowrap">${partShortCodeCellHtml(record.part_number)}</td>
            <td class="px-2 py-2 overflow-hidden">${partNumberNameCellHtml(record.part_number, record.part_name)}</td>
            <td class="px-2 py-1.5 text-right font-mono font-black tabular-nums text-[12px] text-[#FF1E27] bg-[#1A080A] border-x border-[#FF1E27]/20">${esc(fmtNum(record.gauge_fee, 4))}</td>
            <td class="${numCell}">${esc(fmtNum(record.allocation_qty, 0))}</td>
            <td class="px-1 py-2 text-center"><span class="text-[9px] font-medium ${statusClass}">${esc(record.status_label || record.status)}</span></td>
            <td class="px-1 py-2 text-center">
                <div class="inline-flex items-center justify-center gap-0.5 opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto focus-within:opacity-100 focus-within:pointer-events-auto transition-opacity duration-100">
                    ${canUpdate ? `
                    <button type="button" data-action="edit" data-id="${esc(record.id)}"
                            class="inline-flex items-center justify-center w-7 h-7 rounded-sm text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620] transition-all"
                            title="编辑" aria-label="编辑">
                        ${window.svgIcon('pencil', 'w-3.5 h-3.5')}
                    </button>` : ''}
                    ${canDelete ? `
                    <button type="button" data-action="delete" data-id="${esc(record.id)}" data-scope="${esc(scope)}"
                            class="inline-flex items-center justify-center w-7 h-7 rounded-sm text-[#555555] hover:text-[#ef5350] hover:bg-[#161620] transition-all"
                            title="删除" aria-label="删除">
                        ${window.svgIcon('trash', 'w-3.5 h-3.5')}
                    </button>` : ''}
                </div>
            </td>
        </tr>`;
        })
        .join('');
}

export function updateGaugeFeeFilterCapsules() {
    const location = document.getElementById('gflLocation')?.value || '';
    const vehicle = document.getElementById('gflVehicle')?.value || '';
    const part = document.getElementById('gflPartNumber')?.value.trim() || '';
    const status = document.getElementById('gflStatus')?.value || '';
    const statusLabel = { effective: '生效', invalid: '失效' }[status] || '全部状态';
    const activeCapsule = 'bg-[#1A1A22] border border-[#2A2A35] text-white px-2.5 py-1 rounded-md font-bold';
    const idleCapsule = 'bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md';

    const locationEl = document.getElementById('gflCapsuleLocation');
    const vehicleEl = document.getElementById('gflCapsuleVehicle');
    const statusEl = document.getElementById('gflCapsuleStatus');
    const countEl = document.getElementById('gflAdvancedFilterCount');
    const scopeEl = document.getElementById('gflHudScope');

    if (locationEl) {
        locationEl.textContent = location || '全部基地';
        locationEl.className = location ? activeCapsule : idleCapsule;
    }
    if (vehicleEl) {
        vehicleEl.textContent = vehicle || '全部项目';
        vehicleEl.className = vehicle ? activeCapsule : idleCapsule;
    }
    if (statusEl) {
        statusEl.textContent = statusLabel;
        statusEl.className = status ? activeCapsule : idleCapsule;
    }

    const advancedActive = [location, vehicle, part, status].filter(Boolean).length;
    if (countEl) countEl.textContent = `(${advancedActive})`;
    if (scopeEl) {
        const bits = [location, vehicle].filter(Boolean);
        if (part) bits.push(part);
        scopeEl.textContent = bits.length ? bits.join(' · ') : '全部范围';
    }
}

export function updateGaugeFeeHud(summary) {
    const data = summary && typeof summary === 'object' ? summary : {};
    const setText = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    };
    const hasCount = data.total_count != null;
    setText('gflHudTotalFee', hasCount ? fmtNum(data.total_gauge_fee, 4) : '—');
    setText('gflHudEffectiveCount', hasCount ? String(data.effective_count ?? 0) : '—');
    setText('gflHudTotal', hasCount ? String(data.total_count) : '—');
    setText('gflHudInvalidCount', hasCount ? String(data.invalid_count ?? 0) : '—');
}

