/**
 * 采购对象清单列表 — HUD 密表（对齐冲压零件价格一览）
 */

import { pageSizeSelectHtml } from '../../../../page-size.js?v=2';
import { AUDIT_LABELS, CONFIRM_LABELS, KIND_LABELS, SECTION_LABELS } from '../labels.js?v=2';

export function procurementObjectListTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="bg-[#0A0A0C] border border-[#1A1A22] overflow-hidden w-full max-w-full"
                 style="box-shadow: 0 4px 24px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.02);">

                <div class="px-5 pt-4 pb-3.5 border-b border-[#14141A]"
                     style="background: linear-gradient(135deg, #0E0E12 0%, #121218 45%, #0C0C10 100%);">
                    <div class="flex items-start justify-between gap-4 mb-3">
                        <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 font-mono flex-1 min-w-0">
                            <div class="bg-gradient-to-b from-[#18080A] to-[#0D0708] border border-[#FF1E27]/50 p-3.5 relative overflow-hidden">
                                <div class="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-[#FF1E27] to-transparent"
                                     style="box-shadow: 0 0 10px #FF1E27;"></div>
                                <div class="flex justify-between items-start">
                                    <span class="text-[#FF1E27] text-[10px] font-bold tracking-widest">${SECTION_LABELS.object}</span>
                                    <span class="w-2 h-2 rounded-full bg-[#FF1E27] animate-pulse"
                                          style="box-shadow: 0 0 8px #FF1E27;"></span>
                                </div>
                                <div class="text-[26px] font-black text-[#FF1E27] font-mono mt-1 tracking-tight tabular-nums"
                                     style="text-shadow: 0 0 12px rgba(255,30,39,0.7);">
                                    <span id="poHudObject">—</span>
                                    <span class="text-[10px] text-[#FF1E27]/50 ml-1 font-semibold">条</span>
                                </div>
                            </div>
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3"
                                 style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);">
                                <div class="text-[#555555] text-[10px] tracking-wider">${SECTION_LABELS.other_leaf}</div>
                                <div class="text-[18px] font-bold text-[#FFFFFF] mt-1 tabular-nums">
                                    <span id="poHudOther" class="text-[#F0F0F2] font-bold tabular-nums">—</span>
                                    <span class="text-[10px] text-[#555555] ml-1">条</span>
                                </div>
                            </div>
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3">
                                <div class="text-[#555555] text-[10px] tracking-wider">${AUDIT_LABELS.pending}</div>
                                <div class="text-[18px] font-bold text-[#FFFFFF] mt-1 tabular-nums">
                                    <span id="poHudPending">—</span>
                                    <span class="text-[10px] text-[#555555] ml-1">条</span>
                                </div>
                            </div>
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3">
                                <div class="text-[#555555] text-[10px] tracking-wider">${AUDIT_LABELS.approved}</div>
                                <div class="text-[18px] font-bold text-[#FFFFFF] mt-1 tabular-nums">
                                    <span id="poHudApproved">—</span>
                                    <span class="text-[10px] text-[#555555] ml-1">条</span>
                                </div>
                            </div>
                        </div>
                        <div class="flex items-center gap-2 shrink-0 flex-wrap justify-end">
                            <button id="poBatchApproveBtn" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] hover:bg-[#FF1E27]/10 hover:shadow-[0_0_12px_rgba(255,30,39,0.2)] transition-all duration-200">
                                ${window.svgIcon('check-circle', 'w-3 h-3')}
                                批量审核
                            </button>
                            <button id="poBatchReverseBtn" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] hover:bg-[#FF1E27]/10 hover:shadow-[0_0_12px_rgba(255,30,39,0.2)] transition-all duration-200">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                批量反审核
                            </button>
                            <button id="poBatchDeleteBtn" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#c62828]/60 hover:text-[#ef5350] hover:bg-[#c62828]/15 hover:shadow-[0_0_12px_rgba(198,40,40,0.2)] transition-all duration-200">
                                ${window.svgIcon('trash', 'w-3 h-3')}
                                批量删除
                            </button>
                            <button id="poExportBtn" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] hover:bg-[#FF1E27]/10 hover:shadow-[0_0_12px_rgba(255,30,39,0.2)] transition-all duration-200">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                导出 Excel
                            </button>
                        </div>
                    </div>
                    <p id="poQaBanner" class="hidden text-[10px] text-[#ffb74d] mt-1"></p>
                </div>

                <div class="px-5 py-3 border-b border-[#14141A]"
                     style="background: linear-gradient(180deg, #0C0C10 0%, #0A0A0E 100%);">
                    <div class="flex items-center gap-2 mb-3">
                        <button type="button" data-section="" class="po-section-tab h-7 px-3 text-[11px] font-semibold rounded-md border border-[#FF1E27] text-[#FF1E27] bg-[#FF1E27]/10">全部</button>
                        <button type="button" data-section="object" class="po-section-tab h-7 px-3 text-[11px] font-medium rounded-md border border-[#2A2A35] text-[#8E8E93]">${SECTION_LABELS.object}</button>
                        <button type="button" data-section="other_leaf" title="螺母、胶、塑料等非冲压件，仅供核对，不列入采购对象"
                                class="po-section-tab h-7 px-3 text-[11px] font-medium rounded-md border border-[#2A2A35] text-[#8E8E93]">${SECTION_LABELS.other_leaf}</button>
                        <button type="button" data-section="anomaly" class="po-section-tab h-7 px-3 text-[11px] font-medium rounded-md border border-[#2A2A35] text-[#8E8E93]">${SECTION_LABELS.anomaly}</button>
                    </div>
                    <div class="flex items-center justify-between gap-4 bg-[#0C0C10] border border-[#1E1E26] px-4 py-2.5 rounded-md font-mono text-[11px]">
                        <div class="flex items-center gap-3 min-w-0 flex-1">
                            <span class="text-[#555555] shrink-0 tracking-wider">当前筛选：</span>
                            <div class="flex items-center gap-2 flex-wrap">
                                <span id="poCapsuleLocation" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部基地</span>
                                <span id="poCapsuleModel" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部项目</span>
                                <span id="poCapsuleVersion" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部版本</span>
                            </div>
                        </div>
                        <div class="flex items-center gap-3 shrink-0">
                            <button type="button" id="poToggleAdvancedFilter"
                                    class="text-[#6E6E73] hover:text-white transition-colors flex items-center gap-1.5 text-[11px]">
                                <span>展开高级筛选</span>
                            </button>
                            <button type="button" id="poSearchBtn"
                                    class="inline-flex items-center gap-1.5 h-7 px-3 text-[11px] font-semibold rounded-sm text-[#c8c8c8] border border-[#8a2020]"
                                    style="background: linear-gradient(180deg, #3d1515 0%, #2d0f0f 100%);">
                                ${window.svgIcon('search', 'w-3 h-3')}
                                查询
                            </button>
                        </div>
                    </div>
                    <div id="poAdvancedFilterPanel" class="hidden mt-3 pt-3 border-t border-[#1A1A22]">
                        <div class="flex items-end gap-3 flex-wrap">
                            ${filterSelect('poLocationFilter', '基地')}
                            ${filterSelect('poModelFilter', '项目')}
                            ${filterSelect('poVersionFilter', '版本')}
                            ${filterSelect('poKindFilter', '对象种类')}
                            ${filterSelect('poConfirmFilter', '确认')}
                            ${filterSelect('poAuditFilter', '审核')}
                            ${filterSelect('poSupplierFilter', '供应商')}
                            ${filterSelect('poHasSupplierFilter', '对方')}
                            ${filterInput('poPartFilter', '零件号', '零件号或总成')}
                            <button id="poResetBtn" type="button"
                                    class="inline-flex items-center gap-1.5 h-8 px-3 text-[11px] font-medium rounded-md bg-transparent text-[#6E6E73] border border-[#2A2A35] hover:bg-[#FF1E27]/10 hover:border-[#FF1E27]/50 hover:text-[#FF1E27] transition-all duration-200">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>
                        </div>
                        <p class="mt-2 text-[10px] text-[#555555]">批量审核 / 反审核 / 删除须选定基地、项目、版本；不勾选行。</p>
                    </div>
                </div>

                <div class="overflow-x-auto bg-[#0A0A0E] brabus-bg-grid">
                    <table class="w-full table-fixed bg-transparent border-collapse" style="min-width: 1420px;">
                        <colgroup>
                            <col style="width:3px">
                            <col style="width:88px">
                            <col style="width:140px">
                            <col style="width:140px">
                            <col style="width:96px">
                            <col style="width:88px">
                            <col style="width:72px">
                            <col style="width:140px">
                            <col style="width:72px">
                            <col style="width:88px">
                            <col style="width:88px">
                        </colgroup>
                        <thead>
                            <tr class="border-b border-[#17171C] bg-[#0B0B0D]/95">
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">Excel</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">供货总成</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">零件号</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-[#555555]">对象种类</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-[#555555]">材料</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-[#555555]">确认</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-[#555555]">供应商</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-[#555555]">审核</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">操作</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-[#555555]">范围</th>
                            </tr>
                        </thead>
                        <tbody id="poTableBody" class="font-mono text-[11px]"></tbody>
                    </table>
                </div>

                <div class="flex items-center justify-between px-5 py-2.5 border-t border-[#14141A] bg-[#0A0A0E]">
                    <div class="flex items-center gap-3">
                        <span id="poTotalLabel" class="text-[10px] font-mono text-[#555555]"></span>
                        ${pageSizeSelectHtml('poPageSize')}
                    </div>
                    <div class="flex items-center gap-0.5" id="poPagination"></div>
                </div>
            </div>
        </div>
        ${auditDrawerHtml()}
        ${confirmDrawerHtml()}
        ${detailDrawerHtml()}
    `;
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
        <input id="${id}" placeholder="${placeholder}" class="h-8 w-32 px-2.5 text-[11px] bg-[#0A0A0E] border border-[#2A2A35] text-[#ffffff] placeholder:text-[#555555] rounded-md focus:outline-none focus:border-[#FF1E27] transition-colors">
    </label>`;
}

function auditDrawerHtml() {
    return `
        <div id="poBatchAuditDrawerBackdrop" class="hidden fixed inset-0 bg-black/60 z-[80]"></div>
        <div id="poBatchAuditDrawer" class="hidden fixed top-0 right-0 h-full w-[420px] max-w-full bg-[#121212] border-l border-[#1A1A22] z-[85] flex flex-col">
            <div class="px-6 py-4 border-b border-[#262626] flex items-center justify-between">
                <h3 id="poBatchAuditDrawerTitle" class="text-sm font-semibold text-white">批量审核</h3>
                <button type="button" id="poBatchAuditCloseBtn" class="text-[#9e9e9e] hover:text-white">${window.svgIcon('x-lg', 'w-4 h-4')}</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-6 space-y-4">
                <input type="hidden" id="poBatchAuditMode" value="approve">
                <div class="bg-[#0c0c0c] border border-[#1a1a1a] rounded p-3 text-[11px] text-[#9e9e9e]" id="poBatchAuditFilterSummary"></div>
                <p id="poBatchAuditHint" class="text-[11px] text-[#616161]"></p>
                <div>
                    <label class="text-[10px] text-[#777777] mb-1 block">操作人</label>
                    <div id="poBatchAuditOperatorDisplay" class="w-full h-9 px-3 flex items-center text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] rounded">—</div>
                </div>
                <div>
                    <label class="text-[10px] text-[#777777] mb-1 block" id="poBatchAuditRemarkLabel">审核意见<span class="text-[#FF1E27]">*</span></label>
                    <textarea id="poBatchAuditRemark" rows="4" maxlength="500"
                              class="w-full px-3 py-2 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#FF1E27] rounded resize-none"
                              placeholder="请填写审核意见（必填）"></textarea>
                </div>
            </div>
            <div class="px-6 py-4 border-t border-[#262626] flex items-center justify-end gap-2">
                <button type="button" id="poBatchAuditCancelBtn" class="inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-4 py-2 text-[11px] font-medium rounded hover:text-white">取消</button>
                <button type="button" id="poBatchAuditConfirmBtn" class="inline-flex items-center gap-1.5 bg-[#FF1E27] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c]">确认提交</button>
            </div>
        </div>
        <div id="poBatchDeleteDrawerBackdrop" class="hidden fixed inset-0 bg-black/60 z-[80]"></div>
        <div id="poBatchDeleteDrawer" class="hidden fixed top-0 right-0 h-full w-[420px] max-w-full bg-[#121212] border-l border-[#1A1A22] z-[85] flex flex-col">
            <div class="px-6 py-4 border-b border-[#262626] flex items-center justify-between">
                <h3 class="text-sm font-semibold text-white">批量删除</h3>
                <button type="button" id="poBatchDeleteCloseBtn" class="text-[#9e9e9e] hover:text-white">${window.svgIcon('x-lg', 'w-4 h-4')}</button>
            </div>
            <div class="flex-1 p-6 space-y-4">
                <div class="bg-[#0c0c0c] border border-[#1a1a1a] rounded p-3 text-[11px] text-[#9e9e9e]" id="poBatchDeleteSummary"></div>
                <p class="text-[11px] text-[#616161]">仅删除待审采购对象；已审跳过。核对区不删。</p>
            </div>
            <div class="px-6 py-4 border-t border-[#262626] flex items-center justify-end gap-2">
                <button type="button" id="poBatchDeleteCancelBtn" class="inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-4 py-2 text-[11px] font-medium rounded">取消</button>
                <button type="button" id="poBatchDeleteConfirmBtn" class="inline-flex items-center gap-1.5 bg-[#c62828] text-white px-4 py-2 text-[11px] font-semibold rounded">确认删除</button>
            </div>
        </div>
    `;
}

function confirmDrawerHtml() {
    return `
        <div id="poConfirmDrawerBackdrop" class="hidden fixed inset-0 bg-black/60 z-[80]"></div>
        <div id="poConfirmDrawer" class="hidden fixed top-0 right-0 h-full w-[420px] max-w-full bg-[#121212] border-l border-[#1A1A22] z-[85] flex flex-col">
            <div class="px-6 py-4 border-b border-[#262626] flex items-center justify-between">
                <h3 class="text-sm font-semibold text-white">确认采购对象</h3>
                <button type="button" id="poConfirmCloseBtn" class="text-[#9e9e9e] hover:text-white">${window.svgIcon('x-lg', 'w-4 h-4')}</button>
            </div>
            <div class="flex-1 p-6 space-y-4">
                <input type="hidden" id="poConfirmId">
                <div id="poConfirmPart" class="text-[12px] text-[#F0F0F2] font-mono"></div>
                <label class="space-y-1 block">
                    <span class="text-[10px] text-[#777777]">确认状态</span>
                    <select id="poConfirmStatus" class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#FF1E27]">
                        <option value="pending">待定</option>
                        <option value="outsourced">外发</option>
                        <option value="in_house">自制</option>
                    </select>
                </label>
                <label class="space-y-1 block" id="poConfirmSupplierWrap">
                    <span class="text-[10px] text-[#777777]">合同对方</span>
                    <select id="poConfirmSupplier" class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#FF1E27]">
                        <option value="">未指定</option>
                    </select>
                    <p class="text-[10px] text-[#555555]">找不到请到供应商一览补档（#/supplier-list）。自制会清空对方。</p>
                </label>
                <label class="space-y-1 block">
                    <span class="text-[10px] text-[#777777]">确认备注</span>
                    <textarea id="poConfirmRemark" rows="3" class="w-full px-3 py-2 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#FF1E27] rounded resize-none"></textarea>
                </label>
            </div>
            <div class="px-6 py-4 border-t border-[#262626] flex justify-end gap-2">
                <button type="button" id="poConfirmCancelBtn" class="inline-flex items-center bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-4 py-2 text-[11px] rounded">取消</button>
                <button type="button" id="poConfirmSaveBtn" class="inline-flex items-center bg-[#FF1E27] text-white px-4 py-2 text-[11px] font-semibold rounded">保存确认</button>
            </div>
        </div>
    `;
}

function detailDrawerHtml() {
    return `
        <div id="poDetailDrawerBackdrop" class="hidden fixed inset-0 bg-black/60 z-[80]"></div>
        <div id="poDetailDrawer" class="hidden fixed top-0 right-0 h-full w-[480px] max-w-full bg-[#121212] border-l border-[#1A1A22] z-[85] flex flex-col">
            <div class="px-6 py-4 border-b border-[#262626] flex items-center justify-between">
                <h3 class="text-sm font-semibold text-white">采购对象详情</h3>
                <button type="button" id="poDetailCloseBtn" class="text-[#9e9e9e] hover:text-white">${window.svgIcon('x-lg', 'w-4 h-4')}</button>
            </div>
            <div id="poDetailBody" class="flex-1 overflow-y-auto p-6 text-[12px] text-[#c8c8c8] space-y-2 font-mono"></div>
        </div>
    `;
}

export function renderProcurementObjectRows(records, suppliers) {
    if (!records || records.length === 0) {
        return `<tr><td colspan="11" class="py-10 text-center text-[#8E8E93] text-[12px]">暂无数据</td></tr>`;
    }
    const kindLabel = KIND_LABELS;
    const sectionLabel = SECTION_LABELS;
    const confirmLabel = CONFIRM_LABELS;
    const abbrByName = {};
    (suppliers || []).forEach((item) => {
        if (item && item.full_name) abbrByName[item.full_name] = item.abbreviation || '';
    });
    return records.map((row) => {
        const confirmBtn = row.section === 'object'
            ? `<button type="button" data-action="confirm" data-id="${esc(row.id)}"
                    class="inline-flex items-center justify-center w-7 h-7 rounded-sm opacity-0 group-hover:opacity-100 focus:opacity-100 text-[#555555] hover:text-[#FF1E27] hover:bg-[#161620]"
                    title="确认" aria-label="确认">${window.svgIcon('pencil', 'w-3.5 h-3.5')}</button>`
            : '';
        return `
        <tr class="group relative font-mono text-[11px] border-b border-[#141418] hover:bg-[#161620] transition-colors duration-100">
            <td class="p-0 relative">
                <div class="absolute left-0 top-0 bottom-0 w-[2px] bg-[#FF1E27] opacity-0 group-hover:opacity-70 transition-opacity"></div>
            </td>
            <td class="px-2 py-2 overflow-hidden">
                <div class="text-[10px] text-[#8E8E93] truncate" title="${esc(row.excel_filename)}">${esc(row.excel_filename || '—')}</div>
                <div class="text-[9px] text-[#555555]">行 ${esc(row.excel_row ?? '—')}</div>
            </td>
            <td class="px-2 py-2 overflow-hidden">
                <div class="font-semibold text-[#F0F0F2] truncate">${esc(row.l0_part_number)}</div>
                <div class="text-[9px] text-[#555555] truncate" title="${esc(row.l0_part_name)}">${esc(row.l0_part_name || '')}</div>
            </td>
            <td class="px-2 py-2 overflow-hidden">
                <div class="font-semibold text-[#F0F0F2] truncate">${esc(row.part_number)}</div>
                <div class="text-[9px] text-[#555555] truncate">${esc(row.part_name || '')}</div>
            </td>
            <td class="px-2 py-2 text-[10px] text-[#8E8E93]">${esc(kindLabel[row.object_kind] || sectionLabel[row.section] || row.section)}</td>
            <td class="px-2 py-2 overflow-hidden text-[10px] text-[#8E8E93]">
                <div class="truncate">${esc(row.material || '—')}</div>
                <div class="text-[9px] text-[#555555]">${esc(row.thickness_text || '')}</div>
            </td>
            <td class="px-2 py-2 text-[10px] text-[#C8C8D0]">${esc(confirmLabel[row.confirm_status] || row.confirm_status)}</td>
            <td class="px-2 py-2 overflow-hidden text-[10px] text-[#8E8E93]">
                ${row.section === 'object'
                    ? (row.supplier_name
                        ? `<div class="truncate text-[#C8C8D0]" title="${esc(row.supplier_name)}">${esc(abbrByName[row.supplier_name] ? `${abbrByName[row.supplier_name]}（${row.supplier_name}）` : row.supplier_name)}</div>`
                        : `<span class="text-[#555555]">未指定</span>`)
                    : `<span class="text-[#3A3A42]">—</span>`}
            </td>
            <td class="px-2 py-2 text-[10px] text-[#8E8E93]">${esc(AUDIT_LABELS[row.audit_status] || row.audit_status)}</td>
            <td class="px-1 py-2 text-center">
                ${confirmBtn}
                <button type="button" data-action="detail" data-id="${esc(row.id)}"
                        class="inline-flex items-center justify-center w-7 h-7 rounded-sm opacity-0 group-hover:opacity-100 focus:opacity-100 text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620]"
                        title="详情" aria-label="详情">${window.svgIcon('eye', 'w-3.5 h-3.5')}</button>
            </td>
            <td class="px-2 py-2 text-[9px] text-[#555555] truncate">${esc(row.location)} · ${esc(row.vehicle_model)} · ${esc(row.bom_version)}</td>
        </tr>`;
    }).join('');
}

export function renderPoPagination(currentPage, totalPages) {
    if (totalPages <= 1) return '';
    let buttons = `
        <button class="po-page-btn flex items-center justify-center w-6 h-6 text-[10px] ${currentPage === 1 ? 'text-[#2E2E36] cursor-not-allowed' : 'text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620]'}"
                data-page="${currentPage - 1}" ${currentPage === 1 ? 'disabled' : ''}>‹</button>`;
    for (let i = 1; i <= totalPages; i += 1) {
        if (totalPages > 7 && Math.abs(i - currentPage) > 2 && i !== 1 && i !== totalPages) continue;
        const active = i === currentPage;
        buttons += `<button class="po-page-btn flex items-center justify-center w-6 h-6 text-[10px] ${active ? 'bg-[#FF1E27] text-white font-bold' : 'text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620]'}" data-page="${i}">${i}</button>`;
    }
    buttons += `
        <button class="po-page-btn flex items-center justify-center w-6 h-6 text-[10px] ${currentPage === totalPages ? 'text-[#2E2E36] cursor-not-allowed' : 'text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620]'}"
                data-page="${currentPage + 1}" ${currentPage === totalPages ? 'disabled' : ''}>›</button>`;
    return buttons;
}
