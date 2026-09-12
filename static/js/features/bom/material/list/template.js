/**
 * BOM 材料清单列表 — HUD 密表
 */

import { paginationBarHtml } from '../../../../page-size.js?v=3';

const STATUS_LABEL = {
    draft: { text: '草稿', cls: 'text-[#ffb74d] bg-[#ffb74d]/15' },
    active: { text: '生效', cls: 'text-[#4caf50] bg-[#4caf50]/15' },
    archived: { text: '归档', cls: 'text-[#8E8E93] bg-[#8E8E93]/15' },
};

const STAGE_LABEL = {
    initial: '初始',
    mass: '批量',
};

export function bomMaterialListTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="bg-[#0A0A0C] border border-[#1A1A22] overflow-hidden w-full max-w-full"
                 style="box-shadow: 0 4px 24px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.02);">

                <div class="px-5 pt-4 pb-3.5 border-b border-[#14141A]"
                     style="background: linear-gradient(135deg, #0E0E12 0%, #121218 45%, #0C0C10 100%);">
                    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 font-mono mb-3">
                        ${hudCard('bomMatHudTotal', '清单', '份')}
                        ${hudCard('bomMatHudActive', '生效', '份')}
                        ${hudCard('bomMatHudDraft', '草稿', '份')}
                        ${hudCard('bomMatHudArchived', '归档', '份')}
                        ${hudCard('bomMatHudNodes', '节点合计', '个', true)}
                    </div>
                    <p class="text-[10px] text-[#8E8E93] leading-relaxed">
                        材料清单按<strong class="font-semibold text-[#F0F0F2]">基地 + 项目 + 版本</strong>唯一。
                        操作列可打开产品结构；删除仅针对该行清单（含全部树节点），不可恢复。
                    </p>
                </div>

                <div class="px-5 py-3 border-b border-[#14141A]"
                     style="background: linear-gradient(180deg, #0C0C10 0%, #0A0A0E 100%);">
                    <div class="flex items-center justify-between gap-4 bg-[#0C0C10] border border-[#1E1E26] px-4 py-2.5 rounded-md font-mono text-[11px]"
                         style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.02), 0 0 20px rgba(0,0,0,0.3);">
                        <div class="flex items-center gap-3 min-w-0 flex-1">
                            <span class="text-[#555555] shrink-0 tracking-wider">当前筛选：</span>
                            <div class="flex items-center gap-2 flex-wrap">
                                <span id="bomMatCapsuleLocation" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部基地</span>
                                <span id="bomMatCapsuleModel" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部项目</span>
                                <span id="bomMatCapsuleVersion" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部版本</span>
                                <span id="bomMatCapsuleStatus" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部状态</span>
                            </div>
                        </div>
                        <div class="flex items-center gap-3 shrink-0">
                            <button type="button" id="bomMatToggleAdvancedFilter"
                                    class="text-[#6E6E73] hover:text-white transition-colors flex items-center gap-1.5 text-[11px]">
                                <span id="bomMatAdvancedFilterLabel">展开高级筛选</span>
                            </button>
                            <button type="button" id="btnBomMatFilter"
                                    class="inline-flex items-center gap-1.5 h-7 px-3 text-[11px] font-semibold rounded-sm text-[#c8c8c8] border border-[#8a2020] transition-all"
                                    style="background: linear-gradient(180deg, #3d1515 0%, #2d0f0f 100%);">
                                ${window.svgIcon('search', 'w-3 h-3')}
                                查询
                            </button>
                        </div>
                    </div>

                    <div id="bomMatAdvancedFilterPanel" class="hidden mt-3 pt-3 border-t border-[#1A1A22]">
                        <div class="flex items-end gap-3 flex-wrap">
                            ${filterSelect('bomMatLocationFilter', '基地')}
                            ${filterSelect('bomMatModelFilter', '项目')}
                            ${filterSelect('bomMatVersionFilter', '版本')}
                            ${filterSelect('bomMatStatusFilter', '状态')}
                            <button id="bomMatResetFilterBtn" type="button"
                                    class="inline-flex items-center gap-1.5 h-8 px-3 text-[11px] font-medium rounded-md bg-transparent text-[#6E6E73] border border-[#2A2A35] hover:border-[#FF1E27]/50 hover:text-[#FF1E27] transition-all">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>
                        </div>
                    </div>
                </div>

                <div class="overflow-x-auto brabus-bg-grid">
                    <table class="w-full min-w-[1100px] bg-transparent table-fixed border-collapse">
                        <colgroup>
                            <col style="width:2px">
                            <col style="width:8%">
                            <col style="width:8%">
                            <col style="width:7%">
                            <col style="width:18%">
                            <col style="width:8%">
                            <col style="width:7%">
                            <col style="width:8%">
                            <col style="width:16%">
                            <col style="width:10%">
                            <col style="width:10%">
                        </colgroup>
                        <thead>
                            <tr class="border-b border-[#17171C] bg-[#0B0B0D]/95">
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">基地</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">项目</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">版本</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#6E6E73]">标题 / 顾客</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">阶段</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">状态</th>
                                <th class="px-2 py-2 text-right text-[9px] font-semibold tracking-[0.06em] text-[#FF1E27]/90 bg-[#1A080A]">节点数</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">源文件</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">更新</th>
                                <th class="px-1 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">操作</th>
                            </tr>
                        </thead>
                        <tbody id="bomMatTableBody" class="bg-transparent"></tbody>
                    </table>
                </div>

                ${paginationBarHtml({ infoId: 'bomMatTotalCount', selectId: 'bomMatPageSize', buttonsId: 'bomMatPaginationBtns', wrapperId: 'bomMatPaginationContainer' })}

                <div id="bomMatEmptyState" class="hidden flex flex-col items-center justify-center py-14">
                    <div class="w-10 h-10 flex items-center justify-center mb-3 rounded-md bg-[#121218] border border-[#2A2A35]">
                        ${window.svgIcon('clipboard-list', 'w-4 h-4 text-[#555555]')}
                    </div>
                    <h5 class="text-[11px] font-medium text-[#8E8E93] mb-1">暂无材料清单</h5>
                    <p class="text-[10px] text-[#555555]">请先在「上传材料清单」页导入 Excel</p>
                </div>

                <div id="bomMatLoadingState" class="hidden flex items-center justify-center py-14">
                    <div class="w-5 h-5 border-2 border-[#2A2A35] border-t-[#FF1E27] rounded-full animate-spin"></div>
                </div>
            </div>
        </div>
    `;
}

function hudCard(id, label, unit, warn = false) {
    const border = warn ? 'border-[#ffb74d]/30' : 'border-[#1E1E26]';
    const labelCls = warn ? 'text-[#ffb74d]/80' : 'text-[#555555]';
    const valueCls = warn ? 'text-[#ffb74d]' : 'text-[#FFFFFF]';
    return `
        <div class="bg-[#0D0D11]/80 border ${border} p-3 backdrop-blur-sm"
             style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);">
            <div class="${labelCls} text-[10px] tracking-wider">${label}</div>
            <div class="text-[18px] font-bold ${valueCls} mt-1 tabular-nums">
                <span id="${id}">—</span>
                <span class="text-[10px] text-[#555555] ml-1">${unit}</span>
            </div>
        </div>
    `;
}

function filterSelect(id, label) {
    return `
        <div class="flex flex-col gap-1">
            <label class="text-[9px] tracking-[0.08em] text-[#555555]" for="${id}">${label}</label>
            <select id="${id}"
                    class="h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] transition-all min-w-[7rem]">
                <option value="">全部</option>
            </select>
        </div>
    `;
}

export function updateBomMatHud(summary) {
    const set = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val == null ? '—' : String(val);
    };
    set('bomMatHudTotal', summary?.total_count);
    set('bomMatHudActive', summary?.active_count);
    set('bomMatHudDraft', summary?.draft_count);
    set('bomMatHudArchived', summary?.archived_count);
    set('bomMatHudNodes', summary?.total_node_count);
}

export function updateBomMatCapsules(state) {
    const setCap = (id, emptyLabel, value) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.textContent = value || emptyLabel;
    };
    setCap('bomMatCapsuleLocation', '全部基地', state.location);
    setCap('bomMatCapsuleModel', '全部项目', state.vehicleModel);
    setCap('bomMatCapsuleVersion', '全部版本', state.bomVersion);
    const statusMap = { draft: '草稿', active: '生效', archived: '归档' };
    setCap('bomMatCapsuleStatus', '全部状态', statusMap[state.status] || state.status);
}

export function renderBomMatTableRows(records, options = {}) {
    if (!records.length) return '';
    const canViewStructure = !!options.canViewStructure;
    const canDelete = !!options.canDelete;
    const nodeCell =
        'px-2 py-1.5 text-right font-mono font-black tabular-nums text-[12px] text-[#FF1E27] bg-[#1A080A] border-x border-[#FF1E27]/20';

    return records.map((row) => {
        const status = STATUS_LABEL[row.status] || { text: row.status || '-', cls: 'text-[#8E8E93]' };
        const stage = STAGE_LABEL[row.stage] || row.stage || '—';
        const nodeCount = Number(row.node_count) || 0;
        const title = row.title || '—';
        const customer = row.customer_name || '';
        const source = row.source_filename || '—';
        const updated = formatUpdatedAt(row.updated_at) || '—';
        const updatedBy = row.updated_by || '';

        const structureBtn = canViewStructure ? `
                    <button type="button" data-action="open-structure" data-snapshot-id="${row.id}"
                            class="inline-flex items-center justify-center w-7 h-7 rounded-sm text-[#555555] hover:text-[#FF1E27] hover:bg-[#FF1E27]/10 transition-all"
                            title="产品结构" aria-label="产品结构">
                        ${window.svgIcon('eye', 'w-3.5 h-3.5')}
                    </button>` : '';
        const deleteBtn = canDelete ? `
                    <button type="button" data-action="delete-one" data-snapshot-id="${row.id}"
                            data-location="${esc(row.location)}" data-vehicle-model="${esc(row.vehicle_model)}"
                            data-bom-version="${esc(row.bom_version)}"
                            class="inline-flex items-center justify-center w-7 h-7 rounded-sm text-[#555555] hover:text-[#ef5350] hover:bg-[#c62828]/15 transition-all"
                            title="删除本清单" aria-label="删除本清单">
                        ${window.svgIcon('trash', 'w-3.5 h-3.5')}
                    </button>` : '';
        const ops = (structureBtn || deleteBtn) ? `
                <div class="inline-flex items-center justify-center gap-0.5 opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto focus-within:opacity-100 focus-within:pointer-events-auto transition-opacity duration-100">
                    ${structureBtn}${deleteBtn}
                </div>` : '<span class="text-[#3A3A42]">—</span>';

        return `
            <tr class="group relative font-mono text-[11px] border-b border-[#141418] hover:bg-[#161620] transition-colors duration-100"
                data-snapshot-id="${row.id}">
                <td class="p-0 relative">
                    <div class="absolute left-0 top-0 bottom-0 w-[2px] bg-[#FF1E27] opacity-0 group-hover:opacity-70 transition-opacity"></div>
                </td>
                <td class="px-2 py-2 text-[#8E8E93] truncate">${esc(row.location)}</td>
                <td class="px-2 py-2 text-[#F0F0F2] font-semibold truncate">${esc(row.vehicle_model)}</td>
                <td class="px-2 py-2 text-[#C8C8D0] truncate">${esc(row.bom_version)}</td>
                <td class="px-2 py-2 overflow-hidden">
                    <div class="text-[11px] text-[#F0F0F2] font-semibold truncate" title="${esc(title)}">${esc(title)}</div>
                    ${customer ? `<div class="text-[9px] text-[#555555] mt-0.5 truncate" title="${esc(customer)}">${esc(customer)}</div>` : ''}
                </td>
                <td class="px-2 py-2 text-center text-[10px] text-[#8E8E93]">${esc(stage)}</td>
                <td class="px-2 py-2 text-center">
                    <span class="inline-flex px-1.5 py-0.5 text-[9px] rounded-sm ${status.cls}">${esc(status.text)}</span>
                </td>
                <td class="${nodeCell}" title="节点数 ${nodeCount}">
                    <span style="text-shadow: 0 0 8px rgba(255,30,39,0.45);">${nodeCount}</span>
                </td>
                <td class="px-2 py-2 overflow-hidden">
                    <div class="text-[10px] text-[#8E8E93] truncate" title="${esc(source)}">${esc(source)}</div>
                </td>
                <td class="px-2 py-2 overflow-hidden">
                    <div class="text-[10px] text-[#8E8E93] truncate">${esc(updated)}</div>
                    ${updatedBy ? `<div class="text-[9px] text-[#3A3A42] mt-0.5 truncate">${esc(updatedBy)}</div>` : ''}
                </td>
                <td class="px-1 py-2 text-center">${ops}</td>
            </tr>
        `;
    }).join('');
}

function formatUpdatedAt(value) {
    if (!value) return null;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return String(value).slice(0, 16).replace('T', ' ');
    }
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    const hh = String(date.getHours()).padStart(2, '0');
    const mm = String(date.getMinutes()).padStart(2, '0');
    return `${y}-${m}-${d} ${hh}:${mm}`;
}

