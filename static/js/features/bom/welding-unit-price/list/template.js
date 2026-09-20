/**
 * Welding Unit Price List Template
 * 焊接单价列表 — Brabus HUD（与冲次单价列表对齐）
 * 数据来自上传，无「新增」入口；批量操作范围 = 上传条件（基地 + 年度）
 *
 * 单价一律按十进制字符串处理（不经 Number/parseFloat）。
 */

import { paginationBarHtml } from '../../../../page-size.js?v=3';
import { moreMenuItemHtml, moreMenuShellHtml } from '../../../../more-menu.js?v=1';

/** 格式化为固定 4 位小数字符串；非法值返回 '-'。 */
export function formatUnitPrice4(value) {
    return formatDecimalFixed(value, 4) ?? '-';
}

export function unitPriceInputValue(value) {
    return formatDecimalFixed(value, 4) ?? '';
}

/** 校验并规范输入为 4 位小数字符串；失败返回 null。 */
export function parseUnitPriceInput(raw) {
    return parseDecimalInput(raw, 4);
}

export function weldingUnitPriceTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="bg-[#0A0A0C] border border-[#1A1A22] overflow-hidden w-full max-w-full"
                 style="box-shadow: 0 4px 24px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.02);">

                <div class="px-5 pt-4 pb-3.5 border-b border-[#14141A]"
                     style="background: linear-gradient(135deg, #0E0E12 0%, #121218 45%, #0C0C10 100%);">
                    <div class="flex items-start justify-between gap-4 mb-3">
                        <div class="grid grid-cols-2 lg:grid-cols-3 gap-3 font-mono flex-1 min-w-0">
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3 backdrop-blur-sm"
                                 style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);">
                                <div class="text-[#555555] text-[10px] tracking-wider">记录条数</div>
                                <div class="text-[18px] font-bold text-[#FFFFFF] mt-1 tabular-nums">
                                    <span id="weldingHudTotal">—</span>
                                    <span class="text-[10px] text-[#555555] ml-1">条</span>
                                </div>
                            </div>
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3 backdrop-blur-sm"
                                 style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);">
                                <div class="text-[#555555] text-[10px] tracking-wider">待审</div>
                                <div class="text-[18px] font-bold text-[#FFFFFF] mt-1 tabular-nums">
                                    <span id="weldingHudPending">—</span>
                                    <span class="text-[10px] text-[#555555] ml-1">条</span>
                                </div>
                            </div>
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3 backdrop-blur-sm"
                                 style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);">
                                <div class="text-[#555555] text-[10px] tracking-wider">已审</div>
                                <div class="text-[18px] font-bold text-[#FFFFFF] mt-1 tabular-nums">
                                    <span id="weldingHudApproved">—</span>
                                    <span class="text-[10px] text-[#555555] ml-1">条</span>
                                </div>
                            </div>
                        </div>
                        <div class="flex items-center gap-1.5 shrink-0">
                            ${moreMenuShellHtml({
                                wrapId: 'weldingMoreWrap',
                                btnId: 'weldingMoreBtn',
                                menuId: 'weldingMoreMenu',
                                itemsHtml: [
                                    moreMenuItemHtml({ id: 'btnBatchApproveWelding', label: '批量审核' }),
                                    moreMenuItemHtml({ id: 'btnBatchReverseWelding', label: '批量反审核' }),
                                    moreMenuItemHtml({ id: 'btnBatchDeleteWeldingUnitPrice', label: '批量删除', danger: true }),
                                ].join(''),
                            })}
                            <button id="btnExportWeldingUnitPrice" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] hover:bg-[#FF1E27]/10 hover:shadow-[0_0_12px_rgba(255,30,39,0.2)] transition-all duration-200">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                Excel
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
                                <span id="weldingCapsuleYear" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部年度</span>
                                <span id="weldingCapsuleLocation" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部基地</span>
                                <span id="weldingCapsuleAudit" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部审核</span>
                            </div>
                        </div>
                        <div class="flex items-center gap-3 shrink-0">
                            <button type="button" id="weldingToggleAdvancedFilter"
                                    class="text-[#6E6E73] hover:text-white transition-colors flex items-center gap-1.5 text-[11px]">
                                <span id="weldingAdvancedFilterLabel">展开高级筛选</span>
                                <span id="weldingAdvancedFilterCount" class="text-[#555555]">(0)</span>
                            </button>
                            <button type="button" id="btnFilter"
                                    class="inline-flex items-center gap-1.5 h-7 px-3 text-[11px] font-semibold rounded-sm text-[#c8c8c8] border border-[#8a2020] transition-all duration-200 hover:text-white"
                                    style="background: linear-gradient(180deg, #3d1515 0%, #2d0f0f 100%); border-color: #6b1a1a; box-shadow: 0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(211,47,47,0.1), 0 0 12px rgba(198,40,40,0.08);">
                                ${window.svgIcon('search', 'w-3 h-3')}
                                查询
                            </button>
                        </div>
                    </div>

                    <div id="weldingAdvancedFilterPanel" class="hidden mt-3 pt-3 border-t border-[#1A1A22]">
                        <div class="flex items-end gap-3 flex-wrap">
                            ${filterSelect('yearFilter', '年度')}
                            ${filterSelect('locationFilter', '基地')}
                            ${filterSelect('auditStatusFilter', '审核状态')}
                            <button id="weldingResetFilterBtn" type="button"
                                    class="inline-flex items-center gap-1.5 h-8 px-3 text-[11px] font-medium rounded-md bg-transparent text-[#6E6E73] border border-[#2A2A35] hover:bg-[#FF1E27]/10 hover:border-[#FF1E27]/50 hover:text-[#FF1E27] transition-all duration-200">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>
                        </div>
                        <p class="mt-2 text-[10px] text-[#555555]">批量删除 / 审核 / 反审核须同时选定基地和年度（与上传条件对等）。已审核记录不可删除、不可修改。</p>
                    </div>
                </div>

                <div class="overflow-x-auto brabus-bg-grid">
                    <table class="w-full min-w-[1280px] bg-transparent table-fixed border-separate border-spacing-0">
                        <colgroup>
                            <col style="width:2px">
                            <col style="width:9%">
                            <col style="width:7%">
                            <col style="width:12%">
                            <col style="width:8%">
                            <col style="width:11%">
                            <col style="width:10%">
                            <col style="width:8%">
                            <col style="width:7%">
                            <col style="width:9%">
                            <col style="width:11%">
                            <col style="width:8%">
                        </colgroup>
                        <thead>
                            <tr class="border-b border-[#17171C] bg-[#0B0B0D]/95">
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">基地</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">年份</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">名称</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">单位</th>
                                <th class="px-2 py-2 text-right text-[9px] font-semibold tracking-[0.06em] text-[#FF1E27]/90 bg-[#1A080A]">费用</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">备注</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">审核</th>
                                <th class="px-2 py-2 text-left text-[9px] font-normal tracking-[0.08em] text-[#3a3a3a]">创建人</th>
                                <th class="px-2 py-2 text-left text-[9px] font-normal tracking-[0.08em] text-[#3a3a3a]">创建时间</th>
                                <th class="px-2 py-2 text-left text-[9px] font-normal tracking-[0.08em] text-[#3a3a3a]">修改人</th>
                                <th class="p-0 w-9 sticky right-0 z-[3] bg-[#0B0B0D]" aria-label="操作"></th>
                            </tr>
                        </thead>
                        <tbody id="weldingUnitPriceTableBody" class="bg-transparent"></tbody>
                    </table>
                </div>

                ${paginationBarHtml({ infoId: 'totalCountPagination', selectId: 'weldingUnitPricePageSize', buttonsId: 'paginationBtns', wrapperId: 'paginationContainer' })}

                <div id="emptyState" class="hidden flex flex-col items-center justify-center py-14">
                    <div class="w-10 h-10 flex items-center justify-center mb-3 rounded-md bg-[#121218] border border-[#2A2A35]">
                        ${window.svgIcon('clipboard-list', 'w-4 h-4 text-[#555555]')}
                    </div>
                    <h5 class="text-[11px] font-medium text-[#8E8E93] mb-1">暂无焊接单价数据</h5>
                    <p class="text-[10px] text-[#555555]">请先在「焊接单价上传」中导入 Excel</p>
                </div>

                <div id="loadingState" class="hidden flex items-center justify-center py-14">
                    <div class="w-5 h-5 border-2 border-[#2A2A35] border-t-[#FF1E27] rounded-full animate-spin"
                         style="box-shadow: 0 0 12px rgba(255,30,39,0.35);"></div>
                </div>
            </div>
        </div>

        ${batchAuditDrawerHtml('welding')}
        ${editDrawerHtml()}
        ${deleteDrawerHtml()}
    `;
}

function batchAuditDrawerHtml(prefix) {
    return `
        <div class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm transition-opacity duration-300"
             id="${prefix}BatchAuditDrawerBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[420px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="${prefix}BatchAuditDrawer" style="display:none; max-height: 100vh; box-shadow: -20px 0 60px rgba(0,0,0,0.95);">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0"
                 style="background: linear-gradient(180deg, #1f1f1f 0%, #1a1a1a 100%); border-bottom: 1px solid #333333;">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] flex items-center gap-2.5 uppercase">
                    <span style="width:3px;height:14px;background:#d32f2f;border-radius:1px;display:inline-block;box-shadow: 0 0 8px rgba(211,47,47,0.5);"></span>
                    <span id="${prefix}BatchAuditDrawerTitle">批量审核</span>
                </h5>
                <button type="button" id="close${prefix.charAt(0).toUpperCase() + prefix.slice(1)}BatchAuditDrawer"
                        class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-6 space-y-4">
                <input type="hidden" id="${prefix}BatchAuditMode" value="approve">
                <div class="bg-[#0c0c0c] border border-[#1a1a1a] rounded p-3 text-[11px] text-[#9e9e9e]" id="${prefix}BatchAuditFilterSummary"></div>
                <p id="${prefix}BatchAuditHint" class="text-[11px] text-[#616161]"></p>
                <div>
                    <label class="text-[10px] text-[#777777] mb-1 block" id="${prefix}BatchAuditOperatorLabel">操作人</label>
                    <div id="${prefix}BatchAuditOperatorDisplay"
                         class="w-full h-9 px-3 flex items-center text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] rounded">—</div>
                    <p class="text-[10px] text-[#555555] mt-1">取自当前登录用户，无需填写</p>
                </div>
                <div>
                    <label class="text-[10px] text-[#777777] mb-1 block" id="${prefix}BatchAuditRemarkLabel">审核意见</label>
                    <textarea id="${prefix}BatchAuditRemark" rows="4" maxlength="500"
                              class="w-full px-3 py-2 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded resize-none"
                              placeholder="请填写审核意见（必填）"></textarea>
                </div>
            </div>
            <div class="px-6 py-4 border-t border-[#262626] flex items-center justify-end gap-2 shrink-0">
                <button type="button" id="cancel${prefix.charAt(0).toUpperCase() + prefix.slice(1)}BatchAuditBtn" class="inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-4 py-2 text-[11px] font-medium rounded hover:border-[#9e9e9e] hover:text-white transition-all">取消</button>
                <button type="button" id="confirm${prefix.charAt(0).toUpperCase() + prefix.slice(1)}BatchAuditBtn" class="inline-flex items-center gap-1.5 bg-[#d32f2f] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all">确认提交</button>
            </div>
        </div>
    `;
}

function editDrawerHtml() {
    return `
        <div class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm transition-opacity duration-300"
             id="editDrawerBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[560px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="editDrawer" style="display:none; max-height: 100vh; box-shadow: -20px 0 60px rgba(0,0,0,0.95);">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0"
                 style="background: linear-gradient(180deg, #1f1f1f 0%, #1a1a1a 100%); border-bottom: 1px solid #333333;">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] flex items-center gap-2.5 uppercase" id="editDrawerTitle">
                    <span style="width:3px;height:14px;background:#d32f2f;border-radius:1px;display:inline-block;box-shadow: 0 0 8px rgba(211,47,47,0.5);"></span>
                    编辑费用
                </h5>
                <button type="button" id="closeEditDrawer"
                        class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto" id="editDrawerContent">
                <form id="editForm" class="p-6 space-y-5">
                    <input type="hidden" id="editRecordId" value="">
                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="text-[10px] text-[#777777] mb-1 block">基地</label>
                            <input type="text" id="editLocation" disabled
                                   class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] rounded">
                        </div>
                        <div>
                            <label class="text-[10px] text-[#777777] mb-1 block">年份</label>
                            <input type="number" id="editYear" disabled
                                   class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] rounded">
                        </div>
                    </div>
                    <div>
                        <label class="text-[10px] text-[#777777] mb-1 block">名称</label>
                        <input type="text" id="editItemName" disabled
                               class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] rounded">
                    </div>
                    <div>
                        <label class="text-[10px] text-[#777777] mb-1 block">单位 <span class="text-[#d32f2f]">*</span></label>
                        <input type="text" id="editUnit" required maxlength="20"
                               class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] rounded focus:outline-none focus:border-[#ff5252]"
                               placeholder="如 个 / CM / MM / 平方" autocomplete="off">
                    </div>
                    <div>
                        <label class="text-[10px] text-[#777777] mb-1 block">费用 <span class="text-[#d32f2f]">*</span></label>
                        <input type="text" id="editUnitPrice" inputmode="decimal" required
                               class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] font-mono rounded focus:outline-none focus:border-[#ff5252]"
                               placeholder="保留4位小数，如 0.0999" autocomplete="off">
                    </div>
                    <div>
                        <label class="text-[10px] text-[#777777] mb-1 block">备注</label>
                        <input type="text" id="editRemark" maxlength="500"
                               class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] rounded focus:outline-none focus:border-[#ff5252]"
                               placeholder="可选" autocomplete="off">
                    </div>
                </form>
            </div>
            <div class="px-6 py-4 border-t border-[#262626] flex items-center justify-end gap-2 shrink-0">
                <button type="button" id="cancelEditBtn" class="inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-4 py-2 text-[11px] font-medium rounded hover:border-[#9e9e9e] hover:text-white transition-all">取消</button>
                <button type="button" id="submitEditBtn" class="inline-flex items-center gap-1.5 bg-[#d32f2f] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all">
                    ${window.svgIcon('archive', 'w-3.5 h-3.5')}
                    保存
                </button>
            </div>
        </div>
    `;
}

function deleteDrawerHtml() {
    return `
        <div class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm transition-opacity duration-300"
             id="deleteDrawerBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[380px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="deleteDrawer" style="display:none; max-height: 100vh; box-shadow: -20px 0 60px rgba(0,0,0,0.95);">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0"
                 style="background: linear-gradient(180deg, #1f1f1f 0%, #1a1a1a 100%); border-bottom: 1px solid #333333;">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] flex items-center gap-2.5 uppercase">
                    <span style="width:3px;height:14px;background:#c62828;border-radius:1px;display:inline-block;"></span>
                    确认删除
                </h5>
                <button type="button" id="closeDeleteDrawer"
                        class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
            <div class="flex-1 p-6">
                <input type="hidden" id="deleteRecordId" value="">
                <p class="text-[12px] text-[#9e9e9e] mb-3">确定删除这条未审核记录吗？</p>
                <p class="text-[11px] text-[#616161]">已审核记录不可删除。此操作不可撤销。</p>
            </div>
            <div class="px-6 py-4 border-t border-[#262626] flex items-center justify-end gap-2 shrink-0">
                <button type="button" id="cancelDeleteBtn" class="inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-4 py-2 text-[11px] font-medium rounded hover:border-[#9e9e9e] hover:text-white transition-all">取消</button>
                <button type="button" id="confirmDeleteBtn" class="inline-flex items-center gap-1.5 bg-[#c62828] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all">
                    ${window.svgIcon('trash', 'w-3.5 h-3.5')}
                    删除
                </button>
            </div>
        </div>
    `;
}

function filterSelect(id, label) {
    return `<label class="space-y-1">
        <span class="block text-[9px] font-semibold text-[#555555] uppercase tracking-[0.14em]">${label}</span>
        <select id="${id}" class="w-36 h-8 pl-2.5 pr-7 text-[11px] bg-[#0A0A0E] border border-[#2A2A35] text-[#A1A1A6] appearance-none cursor-pointer focus:outline-none focus:border-[#FF1E27] rounded-md transition-colors">
            <option value="">全部</option>
        </select>
    </label>`;
}

export function updateWeldingHud(summary) {
    const data = summary && typeof summary === 'object' ? summary : {};
    const setText = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    };
    setText('weldingHudTotal', String(data.total_count ?? '—'));
    setText('weldingHudPending', String(data.pending_count ?? '—'));
    setText('weldingHudApproved', String(data.approved_count ?? '—'));
}

export function updateWeldingFilterCapsules() {
    const location = document.getElementById('locationFilter')?.value || '';
    const year = document.getElementById('yearFilter')?.value || '';
    const audit = document.getElementById('auditStatusFilter')?.value || '';
    const active = 'bg-[#1A1A22] border border-[#2A2A35] text-white px-2.5 py-1 rounded-md font-bold';
    const idle = 'bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md';
    const auditLabel = { pending: '待审', approved: '已通过' }[audit] || '全部审核';

    const locEl = document.getElementById('weldingCapsuleLocation');
    const yearEl = document.getElementById('weldingCapsuleYear');
    const auditEl = document.getElementById('weldingCapsuleAudit');
    const countEl = document.getElementById('weldingAdvancedFilterCount');
    if (locEl) {
        locEl.textContent = location || '全部基地';
        locEl.className = location ? active : idle;
    }
    if (yearEl) {
        yearEl.textContent = year ? fmtYear(year) : '全部年度';
        yearEl.className = year ? active : idle;
    }
    if (auditEl) {
        auditEl.textContent = auditLabel;
        auditEl.className = audit ? active : idle;
    }
    if (countEl) countEl.textContent = `(${[location, year, audit].filter(Boolean).length})`;
}

export function renderTableRows(records) {
    if (!records || !Array.isArray(records) || records.length === 0) return '';
    const canUpdate = typeof can === 'function' ? can('op:bom-welding-unit-price:update') : true;
    const canDelete = typeof can === 'function' ? can('op:bom-welding-unit-price:delete') : true;

    return records.map((record) => {
        const approved = record.audit_status === 'approved';
        return `
        <tr class="group relative font-mono text-[11px] border-b border-[#141418] hover:bg-[#161620] transition-colors duration-100"
            data-id="${esc(record.id)}">
            <td class="p-0 relative">
                <div class="absolute left-0 top-0 bottom-0 w-[2px] bg-[#FF1E27] opacity-0 group-hover:opacity-70 transition-opacity"></div>
            </td>
            <td class="px-2 py-2 overflow-hidden">
                <div class="font-semibold text-[#F0F0F2]">${esc(record.location)}</div>
            </td>
            <td class="px-2 py-2 text-[#8E8E93] tabular-nums">${esc(fmtYear(record.year))}</td>
            <td class="px-2 py-2 overflow-hidden">
                <div class="text-[#C8C8D0] truncate" title="${esc(record.item_name)}">${esc(record.item_name)}</div>
            </td>
            <td class="px-2 py-2 text-[#8E8E93] overflow-hidden truncate">${esc(record.unit)}</td>
            <td class="px-2 py-1.5 text-right font-mono font-black tabular-nums text-[12px] text-[#FF1E27] bg-[#1A080A] border-x border-[#FF1E27]/20">
                ${esc(formatUnitPrice4(record.unit_price))}
            </td>
            <td class="px-2 py-2 text-[10px] text-[#555555] overflow-hidden truncate" title="${esc(record.remark || '')}">${esc(record.remark || '—')}</td>
            <td class="px-2 py-2 text-center">${auditBadge(record.audit_status)}</td>
            <td class="px-2 py-2 text-[9px] text-[#484848] whitespace-nowrap overflow-hidden">${esc(record.created_by)}</td>
            <td class="px-2 py-2 text-[9px] text-[#3a3a3a] whitespace-nowrap overflow-hidden">${esc(formatAuditDateTime(record.created_at))}</td>
            <td class="px-2 py-2 text-[9px] text-[#484848] whitespace-nowrap overflow-hidden">${esc(record.updated_by)}</td>
            <td class="px-1 py-2 text-center sticky right-0 z-[2] brabus-bg-grid group-hover:bg-[#161620]">
                <div class="inline-flex items-center justify-center gap-0.5 opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto focus-within:opacity-100 focus-within:pointer-events-auto transition-opacity duration-100">
                    ${canUpdate ? `
                    <button type="button" class="edit-btn inline-flex items-center justify-center w-7 h-7 rounded-sm text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620] transition-all ${approved ? 'opacity-30 pointer-events-none' : ''}"
                            title="${approved ? '已审核，不可编辑' : '编辑'}" aria-label="${approved ? '已审核，不可编辑' : '编辑'}">
                        ${window.svgIcon('pencil', 'w-3.5 h-3.5')}
                    </button>` : ''}
                    ${canDelete && !approved ? `
                    <button type="button" class="delete-btn inline-flex items-center justify-center w-7 h-7 rounded-sm text-[#555555] hover:text-[#ef5350] hover:bg-[#161620] transition-all"
                            title="删除" aria-label="删除">
                        ${window.svgIcon('trash', 'w-3.5 h-3.5')}
                    </button>` : ''}
                </div>
            </td>
        </tr>`;
    }).join('');
}


function auditBadge(status) {
    const label = { pending: '待审', approved: '已通过' }[status] || status || '-';
    return `<span class="inline-flex items-center px-2 py-0.5 text-[10px] font-sans rounded-sm bg-[#1C1C22] text-[#8E8E93] border border-[#2A2A32]">${esc(label)}</span>`;
}

function formatAuditDateTime(value) {
    if (!value) return '-';
    const text = String(value);
    if (text.length >= 19) return text.slice(0, 19).replace('T', ' ');
    return text;
}
