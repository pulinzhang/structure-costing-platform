/**
 * 冲压模具单价档案 — HUD 密表 + 抽屉增改
 */

import { pageSizeSelectHtml } from '../../../../page-size.js?v=2';

function canOp(code) {
    return typeof window.can === 'function' ? window.can(code) : true;
}

export function dieUnitPriceTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="bg-[#0A0A0C] border border-[#1A1A22] overflow-hidden w-full max-w-full"
                 style="box-shadow: 0 4px 24px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.02);">
                <div class="px-5 pt-4 pb-3.5 border-b border-[#14141A]"
                     style="background: linear-gradient(135deg, #0E0E12 0%, #121218 45%, #0C0C10 100%);">
                    <div class="flex items-start justify-between gap-4 mb-3">
                        <div>
                            <h2 class="text-[13px] font-semibold text-[#F0F0F2] tracking-wide">模具单价</h2>
                            <p class="text-[11px] text-[#555555]">按基地 + 项目维护钢板模 / 级进模单价与分摊台数，不必先有冲压工艺</p>
                        </div>
                        <button type="button" id="dupAddBtn"
                                class="inline-flex items-center gap-1.5 bg-[#FF1E27] text-white px-3 py-1.5 text-[11px] font-semibold rounded hover:bg-[#d32f2f] transition-all">
                            ${window.svgIcon('plus', 'w-3 h-3')}
                            新增
                        </button>
                    </div>
                    <div class="flex items-end gap-3 flex-wrap">
                        <label class="flex flex-col gap-1">
                            <span class="text-[10px] text-[#555555] tracking-wider">基地</span>
                            <select id="dupListLocation"
                                    class="h-9 min-w-[140px] px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252]">
                                <option value="">全部</option>
                            </select>
                        </label>
                        <label class="flex flex-col gap-1">
                            <span class="text-[10px] text-[#555555] tracking-wider">项目</span>
                            <select id="dupListVehicle"
                                    class="h-9 min-w-[140px] px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252]">
                                <option value="">全部</option>
                            </select>
                        </label>
                        <label class="flex flex-col gap-1">
                            <span class="text-[10px] text-[#555555] tracking-wider">状态</span>
                            <select id="dupListStatus"
                                    class="h-9 min-w-[100px] px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252]">
                                <option value="">全部</option>
                                <option value="effective">生效</option>
                                <option value="invalid">失效</option>
                            </select>
                        </label>
                        <button id="dupListSearchBtn" type="button"
                                class="inline-flex items-center gap-1.5 h-9 px-3 text-[11px] font-semibold rounded-sm text-[#c8c8c8] border border-[#8a2020] hover:text-white"
                                style="background: linear-gradient(180deg, #3d1515 0%, #2d0f0f 100%);">
                            ${window.svgIcon('search', 'w-3 h-3')}
                            查询
                        </button>
                    </div>
                </div>

                <div class="overflow-x-auto bg-[#0A0A0E] brabus-bg-grid">
                    <table class="w-full table-fixed bg-transparent border-collapse" style="min-width: 920px;">
                        <colgroup>
                            <col style="width: 8px;">
                            <col style="width: 88px;">
                            <col style="width: 88px;">
                            <col style="width: 120px;">
                            <col style="width: 120px;">
                            <col style="width: 100px;">
                            <col style="width: 72px;">
                            <col style="width: 120px;">
                            <col style="width: 88px;">
                        </colgroup>
                        <thead>
                            <tr class="border-b border-[#17171C] bg-[#0B0B0D]/95">
                                <th class="p-0" aria-hidden="true"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">基地</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">项目</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">钢板模（万/吨）</th>
                                <th class="px-2 py-2 text-right text-[9px] font-semibold tracking-[0.06em] text-[#FF1E27]/90 bg-[#1A080A]">级进模（万/吨）</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">分摊（万台）</th>
                                <th class="px-1 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">状态</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-[#555555]">更新</th>
                                <th class="px-1 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">操作</th>
                            </tr>
                        </thead>
                        <tbody id="dupTableBody"></tbody>
                    </table>
                </div>

                <div id="dupEmptyState" class="hidden flex flex-col items-center justify-center py-16 text-center bg-[#0A0A0E]">
                    <div class="text-[#555555] mb-2">${window.svgIcon('inbox')}</div>
                    <p class="text-[12px] text-[#8E8E93] mb-1">暂无模具单价</p>
                    <p class="text-[11px] text-[#555555]">按基地 + 项目新增档案；新项目可直接填写</p>
                </div>
                <div id="dupLoadingState" class="hidden flex flex-col items-center justify-center py-16 gap-2 bg-[#0A0A0E]">
                    <div class="w-5 h-5 border-2 border-[#2c2c2c] border-t-[#FF1E27] rounded-full animate-spin"></div>
                    <span class="text-[11px] text-[#555555]">加载中</span>
                </div>

                <div class="flex items-center justify-between px-5 py-2.5 border-t border-[#14141A] bg-[#0A0A0E]">
                    <div class="flex items-center gap-3">
                        <span id="dupTotalCount" class="text-[10px] font-mono text-[#555555]"></span>
                        ${pageSizeSelectHtml('dupPageSize')}
                    </div>
                    <div class="flex items-center gap-0.5" id="dupPaginationBtns"></div>
                </div>
            </div>
        </div>

        <div class="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm transition-opacity" id="dupEditBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[420px] bg-[#121215] border-l border-[#2c2c2c]
                    transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="dupEditDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-[#2c2c2c] bg-[#16161a] shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-[#FF1E27]"></span>
                    <h5 class="text-xs font-semibold text-white tracking-wider" id="dupEditTitle">新增模具单价</h5>
                </div>
                <button type="button" id="dupCloseEdit" class="text-[#616161] hover:text-white w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-5">
                <form id="dupEditForm" class="space-y-4">
                    <input type="hidden" id="dupEditId" value="">
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">基地 <span class="text-[#FF1E27]">*</span></label>
                        <select id="dupEditLocation" required
                                class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-[#9e9e9e] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252]">
                            <option value="">请选择</option>
                        </select>
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">项目 <span class="text-[#FF1E27]">*</span></label>
                        <input id="dupEditVehicle" name="vehicle_model" list="dupEditVehicleOptions" required
                               placeholder="已有项目可下拉，新项目请直接填写"
                               class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252]">
                        <datalist id="dupEditVehicleOptions"></datalist>
                        <p id="dupEditScopeHint" class="text-[10px] text-[#616161] mt-1">已有项目可下拉，新项目请直接填写。同一基地+项目只能有一条。</p>
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">钢板模单价（万元/吨） <span class="text-[#FF1E27]">*</span></label>
                        <input type="text" id="dupEditPlatePrice" required inputmode="decimal"
                               class="w-full h-8 px-3 text-xs font-mono bg-[#0a0a0c] border border-[#2c2c2c] text-white placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252]"
                               placeholder="如 3.36" autocomplete="off">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">级进模单价（万元/吨） <span class="text-[#FF1E27]">*</span></label>
                        <input type="text" id="dupEditProgressivePrice" required inputmode="decimal"
                               class="w-full h-8 px-3 text-xs font-mono bg-[#0a0a0c] border border-[#2c2c2c] text-white placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252]"
                               placeholder="如 5.15" autocomplete="off">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">项目分摊数量（万台） <span class="text-[#FF1E27]">*</span></label>
                        <input type="text" id="dupEditAllocQty" required inputmode="numeric"
                               class="w-full h-8 px-3 text-xs font-mono bg-[#0a0a0c] border border-[#2c2c2c] text-white placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252]"
                               placeholder="如 10" value="10" autocomplete="off">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">状态 <span class="text-[#FF1E27]">*</span></label>
                        <select id="dupEditStatus" required
                                class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-[#9e9e9e] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252]">
                            <option value="effective">生效</option>
                            <option value="invalid">失效</option>
                        </select>
                    </div>
                </form>
            </div>
            <div class="px-5 py-3 border-t border-[#2c2c2c] flex items-center justify-end gap-2 bg-[#16161a] shrink-0">
                <button type="button" id="dupCancelEdit"
                        class="px-4 py-1.5 text-xs text-[#9e9e9e] hover:text-white border border-[#2c2c2c] hover:bg-[#262626] transition-all">取消</button>
                <button type="button" id="dupSubmitEdit"
                        class="bg-[#FF1E27] hover:bg-[#d32f2f] text-white px-5 py-1.5 text-xs font-semibold transition-all">保存</button>
            </div>
        </div>

        <div class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm" id="dupDeleteBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[380px] bg-[#1a1a1a] border-l border-[#2a2a2a]
                    transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="dupDeleteDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0 border-b border-[#333333]">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] flex items-center gap-2.5">
                    <span class="w-[3px] h-3.5 bg-[#c62828] inline-block"></span>
                    确认删除
                </h5>
                <button type="button" id="dupCloseDelete" class="w-8 h-8 text-[#707070] hover:text-white">✕</button>
            </div>
            <div class="flex-1 p-6">
                <input type="hidden" id="dupDeleteId" value="">
                <p class="text-[12px] text-[#9e9e9e] mb-2">确定删除 <span id="dupDeleteScope" class="font-mono text-white"></span> 的模具单价？</p>
                <p class="text-[11px] text-[#616161]">只删档案，不影响模具布点。</p>
            </div>
            <div class="px-6 py-4 border-t border-[#262626] flex items-center justify-end gap-2 shrink-0">
                <button type="button" id="dupCancelDelete"
                        class="inline-flex items-center bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-4 py-2 text-[11px] font-medium rounded hover:text-white">取消</button>
                <button type="button" id="dupConfirmDelete"
                        class="inline-flex items-center bg-[#c62828] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c]">删除</button>
            </div>
        </div>
    `;
}

export function renderTableRows(records) {
    if (!records || !records.length) return '';
    const canUpdate = canOp('op:stamping-die-unit-price:update');
    const canDelete = canOp('op:stamping-die-unit-price:delete');
    const numCell = 'px-2 py-2 font-mono text-[10px] text-right tabular-nums text-[#8E8E93]';

    return records
        .map((record) => {
            const isEffective = record.status === 'effective';
            const statusClass = isEffective
                ? 'text-[#4caf50] bg-[#2e7d32]/20 px-1.5 py-0.5'
                : 'text-[#8E8E93] bg-[#262626] px-1.5 py-0.5';
            const updated = formatDateTime(record.updated_at);
            const scope = `${record.location} / ${record.vehicle_model}`;
            return `
        <tr class="group relative font-mono text-[11px] border-b border-[#141418] hover:bg-[#161620] transition-colors duration-100">
            <td class="p-0 relative">
                <div class="absolute left-0 top-0 bottom-0 w-[2px] bg-[#FF1E27] opacity-0 group-hover:opacity-70 transition-opacity"></div>
            </td>
            <td class="px-2 py-2 overflow-hidden">
                <div class="text-[12px] font-semibold text-[#F0F0F2] truncate" title="${esc(record.location)}">${esc(record.location)}</div>
            </td>
            <td class="px-2 py-2 overflow-hidden">
                <div class="text-[14px] font-bold text-[#F0F0F2] truncate" title="${esc(record.vehicle_model)}">${esc(record.vehicle_model)}</div>
            </td>
            <td class="${numCell}">${esc(fmtNum(record.steel_plate_unit_price, 4))}</td>
            <td class="px-2 py-1.5 text-right font-mono font-black tabular-nums text-[12px] text-[#FF1E27] bg-[#1A080A] border-x border-[#FF1E27]/20">${esc(fmtNum(record.progressive_die_unit_price, 4))}</td>
            <td class="${numCell}">${esc(fmtNum(record.allocation_qty, 0))}</td>
            <td class="px-1 py-2 text-center">
                <span class="text-[9px] font-medium ${statusClass}">${esc(record.status_label || record.status)}</span>
            </td>
            <td class="px-2 py-2 text-[9px] text-[#3A3A42] whitespace-nowrap overflow-hidden">
                <div>${esc(record.updated_by || '—')}</div>
                <div>${esc(updated)}</div>
            </td>
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

export function renderPagination(currentPage, totalPages) {
    if (totalPages <= 1) return '';
    let buttons = `
        <button type="button" class="page-btn flex items-center justify-center w-6 h-6 text-[10px] ${currentPage === 1 ? 'text-[#333333] cursor-not-allowed' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'} transition-all"
                data-page="${currentPage - 1}" ${currentPage === 1 ? 'disabled' : ''}>
            ${window.svgIcon('chevron-left', 'w-3 h-3')}
        </button>`;
    const maxVisible = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);
    if (endPage - startPage < maxVisible - 1) startPage = Math.max(1, endPage - maxVisible + 1);
    if (startPage > 1) {
        buttons += `<button type="button" class="page-btn flex items-center justify-center w-6 h-6 text-[10px] text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]" data-page="1">1</button>`;
        if (startPage > 2) buttons += `<span class="px-0.5 text-[#333333] text-[9px]">…</span>`;
    }
    for (let i = startPage; i <= endPage; i += 1) {
        const isActive = i === currentPage;
        buttons += `<button type="button" class="page-btn flex items-center justify-center w-6 h-6 text-[10px] ${isActive ? 'bg-[#FF1E27] text-white' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'}" data-page="${i}">${i}</button>`;
    }
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) buttons += `<span class="px-0.5 text-[#333333] text-[9px]">…</span>`;
        buttons += `<button type="button" class="page-btn flex items-center justify-center w-6 h-6 text-[10px] text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]" data-page="${totalPages}">${totalPages}</button>`;
    }
    buttons += `
        <button type="button" class="page-btn flex items-center justify-center w-6 h-6 text-[10px] ${currentPage === totalPages ? 'text-[#333333] cursor-not-allowed' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'}"
                data-page="${currentPage + 1}" ${currentPage === totalPages ? 'disabled' : ''}>
            ${window.svgIcon('chevron-right', 'w-3 h-3')}
        </button>`;
    return buttons;
}

function formatDateTime(value) {
    if (!value) return '—';
    const text = String(value);
    if (text.length >= 16) return text.slice(0, 16).replace('T', ' ');
    return text;
}
