/**
 * 包装运输费列表 — Brabus HUD
 * 批量操作范围 = 基地 + 年度 + 项目
 */

import { paginationBarHtml } from '../../../../page-size.js?v=3';
import { partShortCodeCellHtml, partNumberNameCellHtml } from '../../../../part-identity.js?v=3';

export function formatFee4(value) {
    return formatDecimalFixed(value, 4) ?? '-';
}

export function feeInputValue(value) {
    return formatDecimalFixed(value, 4) ?? '';
}

export function parseFeeInput(raw) {
    return parseDecimalInput(raw, 4);
}

function filterSelect(id, label) {
    return `
        <div class="flex flex-col gap-1 min-w-[120px]">
            <label class="text-[9px] text-[#555555] tracking-wider" for="${id}">${label}</label>
            <select id="${id}"
                    class="h-8 px-2 text-[11px] bg-[#0A0A0E] border border-[#2A2A35] text-[#8E8E93] rounded-md appearance-none cursor-pointer focus:outline-none focus:border-[#FF1E27]">
                <option value="">全部</option>
            </select>
        </div>`;
}

export function pkgTransportFeeTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="bg-[#0A0A0C] border border-[#1A1A22] overflow-hidden w-full max-w-full"
                 style="box-shadow: 0 4px 24px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.02);">

                <div class="px-5 pt-4 pb-3.5 border-b border-[#14141A]"
                     style="background: linear-gradient(135deg, #0E0E12 0%, #121218 45%, #0C0C10 100%);">
                    <div class="flex items-start justify-between gap-4 mb-3">
                        <div class="grid grid-cols-2 lg:grid-cols-3 gap-3 font-mono flex-1 min-w-0">
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3">
                                <div class="text-[#555555] text-[10px] tracking-wider">记录条数</div>
                                <div class="text-[18px] font-bold text-[#FFFFFF] mt-1 tabular-nums">
                                    <span id="pkgHudTotal">—</span>
                                    <span class="text-[10px] text-[#555555] ml-1">条</span>
                                </div>
                            </div>
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3">
                                <div class="text-[#555555] text-[10px] tracking-wider">待审</div>
                                <div class="text-[18px] font-bold text-[#FFFFFF] mt-1 tabular-nums">
                                    <span id="pkgHudPending">—</span>
                                    <span class="text-[10px] text-[#555555] ml-1">条</span>
                                </div>
                            </div>
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3">
                                <div class="text-[#555555] text-[10px] tracking-wider">已审</div>
                                <div class="text-[18px] font-bold text-[#FFFFFF] mt-1 tabular-nums">
                                    <span id="pkgHudApproved">—</span>
                                    <span class="text-[10px] text-[#555555] ml-1">条</span>
                                </div>
                            </div>
                        </div>
                        <div class="flex items-center gap-2 shrink-0 flex-wrap justify-end">
                            <button id="btnBatchApprovePkg" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] transition-all">
                                ${window.svgIcon('check-circle', 'w-3 h-3')} 批量审核
                            </button>
                            <button id="btnBatchReversePkg" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] transition-all">
                                ${window.svgIcon('refresh', 'w-3 h-3')} 批量反审核
                            </button>
                            <button id="btnBatchDeletePkg" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#c62828]/60 hover:text-[#ef5350] transition-all">
                                ${window.svgIcon('trash', 'w-3 h-3')} 批量删除
                            </button>
                            <button id="btnExportPkg" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] transition-all">
                                ${window.svgIcon('download', 'w-3 h-3')} 导出 Excel
                            </button>
                        </div>
                    </div>
                </div>

                <div class="px-5 py-3 border-b border-[#14141A]" style="background: linear-gradient(180deg, #0C0C10 0%, #0A0A0E 100%);">
                    <div class="flex items-center justify-between gap-4 bg-[#0C0C10] border border-[#1E1E26] px-4 py-2.5 rounded-md font-mono text-[11px]">
                        <div class="flex items-center gap-3 min-w-0 flex-1">
                            <span class="text-[#555555] shrink-0 tracking-wider">当前筛选：</span>
                            <div class="flex items-center gap-2 flex-wrap">
                                <span id="pkgCapsuleYear" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部年度</span>
                                <span id="pkgCapsuleLocation" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部基地</span>
                                <span id="pkgCapsuleVehicle" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部项目</span>
                                <span id="pkgCapsuleAudit" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部审核</span>
                                <span id="pkgCapsuleKeyword" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">零件号/名称</span>
                            </div>
                        </div>
                        <div class="flex items-center gap-3 shrink-0">
                            <button type="button" id="pkgToggleAdvancedFilter"
                                    class="text-[#6E6E73] hover:text-white transition-colors flex items-center gap-1.5 text-[11px]">
                                <span id="pkgAdvancedFilterLabel">展开高级筛选</span>
                            </button>
                            <button type="button" id="btnFilterPkg"
                                    class="inline-flex items-center gap-1.5 h-7 px-3 text-[11px] font-semibold rounded-sm text-[#c8c8c8] border border-[#8a2020]"
                                    style="background: linear-gradient(180deg, #3d1515 0%, #2d0f0f 100%);">
                                ${window.svgIcon('search', 'w-3 h-3')} 查询
                            </button>
                        </div>
                    </div>

                    <div id="pkgAdvancedFilterPanel" class="hidden mt-3 pt-3 border-t border-[#1A1A22]">
                        <div class="flex items-end gap-3 flex-wrap">
                            ${filterSelect('pkgYearFilter', '年度')}
                            ${filterSelect('pkgLocationFilter', '基地')}
                            ${filterSelect('pkgVehicleFilter', '项目')}
                            ${filterSelect('pkgAuditStatusFilter', '审核状态')}
                            <div class="flex flex-col gap-1 min-w-[160px]">
                                <label class="text-[9px] text-[#555555] tracking-wider" for="pkgKeywordFilter">零件号/名称</label>
                                <input id="pkgKeywordFilter" type="text" maxlength="100" placeholder="模糊搜索"
                                       class="h-8 px-2 text-[11px] bg-[#0A0A0E] border border-[#2A2A35] text-[#8E8E93] rounded-md focus:outline-none focus:border-[#FF1E27]">
                            </div>
                            <button id="pkgResetFilterBtn" type="button"
                                    class="inline-flex items-center gap-1.5 h-8 px-3 text-[11px] font-medium rounded-md bg-transparent text-[#6E6E73] border border-[#2A2A35] hover:text-[#FF1E27] hover:border-[#FF1E27]/50 transition-all">
                                ${window.svgIcon('refresh', 'w-3 h-3')} 重置
                            </button>
                        </div>
                        <p class="mt-2 text-[10px] text-[#555555]">批量删除 / 审核 / 反审核须同时选定基地、年度和项目。已审核不可删除、不可修改。</p>
                    </div>
                </div>

                <div class="overflow-x-auto brabus-bg-grid">
                    <table class="w-full min-w-[1400px] bg-transparent table-fixed border-collapse">
                        <colgroup>
                            <col style="width:2px">
                            <col style="width:7%">
                            <col style="width:5%">
                            <col style="width:6%">
                            <col style="width:6%">
                            <col style="width:12%">
                            <col style="width:8%">
                            <col style="width:6%">
                            <col style="width:7%">
                            <col style="width:7%">
                            <col style="width:7%">
                            <col style="width:7%">
                            <col style="width:8%">
                            <col style="width:6%">
                            <col style="width:5%">
                        </colgroup>
                        <thead>
                            <tr class="border-b border-[#17171C] bg-[#0B0B0D]/95">
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">基地</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">年份</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">项目</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#A1A1A6]">短代码</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">零件</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">包装类型</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">包装费</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">运输费</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">维护费</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">其它</th>
                                <th class="px-2 py-2 text-right text-[9px] font-semibold tracking-[0.06em] text-[#FF1E27]/90 bg-[#1A080A]">合计</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">审核</th>
                                <th class="p-0 w-9" aria-label="操作"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-normal tracking-[0.08em] text-[#3a3a3a]">创建人</th>
                            </tr>
                        </thead>
                        <tbody id="pkgTransportFeeTableBody" class="bg-transparent"></tbody>
                    </table>
                </div>

                ${paginationBarHtml({ infoId: 'pkgTotalCountPagination', selectId: 'pkgTransportFeePageSize', buttonsId: 'pkgPaginationBtns', wrapperId: 'pkgPaginationContainer' })}

                <div id="pkgEmptyState" class="hidden flex flex-col items-center justify-center py-14">
                    <h5 class="text-[11px] font-medium text-[#8E8E93] mb-1">暂无包装运输费数据</h5>
                    <p class="text-[10px] text-[#555555]">请先在「包装运输费上传」中导入 Excel</p>
                </div>
                <div id="pkgLoadingState" class="hidden flex items-center justify-center py-14">
                    <div class="w-5 h-5 border-2 border-[#2A2A35] border-t-[#FF1E27] rounded-full animate-spin"></div>
                </div>
            </div>
        </div>

        ${batchAuditDrawerHtml()}
        ${detailDrawerHtml()}
        ${editDrawerHtml()}
        ${deleteDrawerHtml()}
    `;
}

function batchAuditDrawerHtml() {
    return `
        <div class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm" id="pkgBatchAuditDrawerBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[420px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="pkgBatchAuditDrawer" style="display:none; max-height:100vh; box-shadow:-20px 0 60px rgba(0,0,0,0.95);">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0 border-b border-[#333333]">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] uppercase flex items-center gap-2.5">
                    <span style="width:3px;height:14px;background:#d32f2f;display:inline-block;"></span>
                    <span id="pkgBatchAuditDrawerTitle">批量审核</span>
                </h5>
                <button type="button" id="closePkgBatchAuditDrawer" class="w-8 h-8 text-[#707070] hover:text-white hover:bg-[#d32f2f] rounded-md">×</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-6 space-y-4">
                <input type="hidden" id="pkgBatchAuditMode" value="approve">
                <div class="bg-[#0c0c0c] border border-[#1a1a1a] rounded p-3 text-[11px] text-[#9e9e9e]" id="pkgBatchAuditFilterSummary"></div>
                <p id="pkgBatchAuditHint" class="text-[11px] text-[#616161]"></p>
                <div>
                    <label class="text-[10px] text-[#777777] mb-1 block">操作人</label>
                    <div id="pkgBatchAuditOperatorDisplay" class="w-full h-9 px-3 flex items-center text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] rounded">—</div>
                </div>
                <div>
                    <label class="text-[10px] text-[#777777] mb-1 block" id="pkgBatchAuditRemarkLabel">审核意见</label>
                    <textarea id="pkgBatchAuditRemark" rows="4" maxlength="500"
                              class="w-full px-3 py-2 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-white rounded resize-none focus:outline-none focus:border-[#ff5252]"
                              placeholder="请填写审核意见（必填）"></textarea>
                </div>
            </div>
            <div class="px-6 py-4 border-t border-[#262626] flex justify-end gap-2 shrink-0">
                <button type="button" id="cancelPkgBatchAuditBtn" class="px-4 py-2 text-[11px] text-[#9e9e9e] border border-[#2c2c2c] rounded">取消</button>
                <button type="button" id="confirmPkgBatchAuditBtn" class="px-4 py-2 text-[11px] bg-[#d32f2f] text-white rounded hover:bg-[#b71c1c]">确认提交</button>
            </div>
        </div>
    `;
}

function detailDrawerHtml() {
    return `
        <div class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm" id="pkgDetailDrawerBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[520px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="pkgDetailDrawer" style="display:none; max-height:100vh; box-shadow:-20px 0 60px rgba(0,0,0,0.95);">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0 border-b border-[#333333]">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] uppercase flex items-center gap-2.5">
                    <span style="width:3px;height:14px;background:#d32f2f;display:inline-block;"></span>
                    包装运输费明细
                </h5>
                <button type="button" id="closePkgDetailDrawer" class="w-8 h-8 text-[#707070] hover:text-white hover:bg-[#d32f2f] rounded-md">×</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-6" id="pkgDetailDrawerBody"></div>
        </div>
    `;
}

function editDrawerHtml() {
    return `
        <div class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm" id="pkgEditDrawerBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[520px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="pkgEditDrawer" style="display:none; max-height:100vh; box-shadow:-20px 0 60px rgba(0,0,0,0.95);">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0 border-b border-[#333333]">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] uppercase flex items-center gap-2.5">
                    <span style="width:3px;height:14px;background:#d32f2f;display:inline-block;"></span>
                    编辑包装运输费
                </h5>
                <button type="button" id="closePkgEditDrawer" class="w-8 h-8 text-[#707070] hover:text-white hover:bg-[#d32f2f] rounded-md">×</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-6 space-y-3">
                <input type="hidden" id="pkgEditId">
                <div class="text-[11px] text-[#9e9e9e]" id="pkgEditScopeHint"></div>
                <div>
                    <label class="text-[10px] text-[#777777] mb-1 block">产品名称</label>
                    <input id="pkgEditPartName" type="text" maxlength="200" class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-white rounded focus:outline-none focus:border-[#ff5252]">
                </div>
                <div>
                    <label class="text-[10px] text-[#777777] mb-1 block">包装类型</label>
                    <input id="pkgEditPackagingType" type="text" maxlength="50" class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-white rounded focus:outline-none focus:border-[#ff5252]">
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="text-[10px] text-[#777777] mb-1 block">单件包装费 *</label>
                        <input id="pkgEditPackagingFee" type="text" class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-white rounded font-mono focus:outline-none focus:border-[#ff5252]">
                    </div>
                    <div>
                        <label class="text-[10px] text-[#777777] mb-1 block">单件运输费 *</label>
                        <input id="pkgEditTransportFee" type="text" class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-white rounded font-mono focus:outline-none focus:border-[#ff5252]">
                    </div>
                    <div>
                        <label class="text-[10px] text-[#777777] mb-1 block">器具维护费 *</label>
                        <input id="pkgEditMaintFee" type="text" class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-white rounded font-mono focus:outline-none focus:border-[#ff5252]">
                    </div>
                    <div>
                        <label class="text-[10px] text-[#777777] mb-1 block">其它费用 *</label>
                        <input id="pkgEditOtherFee" type="text" class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-white rounded font-mono focus:outline-none focus:border-[#ff5252]">
                    </div>
                </div>
                <div>
                    <label class="text-[10px] text-[#777777] mb-1 block">包装运输费合计 *</label>
                    <input id="pkgEditTotal" type="text" class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#FF1E27] rounded font-mono font-semibold focus:outline-none focus:border-[#ff5252]">
                </div>
                <div>
                    <label class="text-[10px] text-[#777777] mb-1 block">备注</label>
                    <textarea id="pkgEditRemark" rows="3" class="w-full px-3 py-2 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-white rounded resize-none focus:outline-none focus:border-[#ff5252]"></textarea>
                </div>
            </div>
            <div class="px-6 py-4 border-t border-[#262626] flex justify-end gap-2 shrink-0">
                <button type="button" id="cancelPkgEditBtn" class="px-4 py-2 text-[11px] text-[#9e9e9e] border border-[#2c2c2c] rounded">取消</button>
                <button type="button" id="confirmPkgEditBtn" class="px-4 py-2 text-[11px] bg-[#d32f2f] text-white rounded hover:bg-[#b71c1c]">保存</button>
            </div>
        </div>
    `;
}

function deleteDrawerHtml() {
    return `
        <div class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm" id="pkgDeleteDrawerBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[420px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="pkgDeleteDrawer" style="display:none; max-height:100vh; box-shadow:-20px 0 60px rgba(0,0,0,0.95);">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0 border-b border-[#333333]">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] uppercase flex items-center gap-2.5">
                    <span style="width:3px;height:14px;background:#d32f2f;display:inline-block;"></span>
                    删除确认
                </h5>
                <button type="button" id="closePkgDeleteDrawer" class="w-8 h-8 text-[#707070] hover:text-white hover:bg-[#d32f2f] rounded-md">×</button>
            </div>
            <div class="flex-1 p-6">
                <input type="hidden" id="pkgDeleteId">
                <p class="text-xs text-[#9e9e9e]" id="pkgDeleteHint">确定删除该条包装运输费吗？此操作不可恢复。</p>
            </div>
            <div class="px-6 py-4 border-t border-[#262626] flex justify-end gap-2 shrink-0">
                <button type="button" id="cancelPkgDeleteBtn" class="px-4 py-2 text-[11px] text-[#9e9e9e] border border-[#2c2c2c] rounded">取消</button>
                <button type="button" id="confirmPkgDeleteBtn" class="px-4 py-2 text-[11px] bg-[#c62828] text-white rounded hover:bg-[#b71c1c]">确认删除</button>
            </div>
        </div>
    `;
}

export function updatePkgHud(summary = {}) {
    const set = (id, v) => {
        const el = document.getElementById(id);
        if (el) el.textContent = v == null ? '—' : String(v);
    };
    set('pkgHudTotal', summary.total_count);
    set('pkgHudPending', summary.pending_count);
    set('pkgHudApproved', summary.approved_count);
}

export function updatePkgFilterCapsules(state) {
    const setCap = (id, text, active) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.textContent = text;
        el.className = active
            ? 'bg-[#1A080A] border border-[#FF1E27]/40 text-[#FF1E27] px-2.5 py-1 rounded-md'
            : 'bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md';
    };
    setCap('pkgCapsuleYear', state.selectedYear ? fmtYear(state.selectedYear) : '全部年度', !!state.selectedYear);
    setCap('pkgCapsuleLocation', state.selectedLocation || '全部基地', !!state.selectedLocation);
    setCap('pkgCapsuleVehicle', state.selectedVehicleModel || '全部项目', !!state.selectedVehicleModel);
    const auditLabel = state.selectedAuditStatus === 'pending'
        ? '待审'
        : state.selectedAuditStatus === 'approved'
            ? '已通过'
            : '全部审核';
    setCap('pkgCapsuleAudit', auditLabel, !!state.selectedAuditStatus);
    setCap('pkgCapsuleKeyword', state.selectedKeyword || '零件号/名称', !!state.selectedKeyword);
}

function auditBadge(status) {
    if (status === 'approved') {
        return '<span class="inline-flex px-1.5 py-0.5 text-[9px] font-medium rounded bg-[#2e7d32]/20 text-[#4caf50]">已通过</span>';
    }
    return '<span class="inline-flex px-1.5 py-0.5 text-[9px] font-medium rounded bg-[#f57f17]/20 text-[#ffb74d]">待审</span>';
}

const numCell = 'px-2 py-2 font-mono text-[10px] text-right tabular-nums text-[#8E8E93]';

export function renderTableRows(records) {
    const canUpdate = typeof can === 'function' ? can('op:bom-packaging-transport-fee:update') : true;
    const canDelete = typeof can === 'function' ? can('op:bom-packaging-transport-fee:delete') : true;

    return records.map((record) => {
        const approved = record.audit_status === 'approved';
        const editBtn = canUpdate && !approved
            ? `<button type="button" data-action="edit" data-id="${record.id}"
                       class="pkg-edit-btn w-7 h-7 inline-flex items-center justify-center text-[#6E6E73] hover:text-[#FF1E27] opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity"
                       title="编辑">${window.svgIcon('pencil', 'w-3.5 h-3.5')}</button>`
            : '';
        const delBtn = canDelete && !approved
            ? `<button type="button" data-action="delete" data-id="${record.id}"
                       class="pkg-delete-btn w-7 h-7 inline-flex items-center justify-center text-[#6E6E73] hover:text-[#ef5350] opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity"
                       title="删除">${window.svgIcon('trash', 'w-3.5 h-3.5')}</button>`
            : '';
        const detailBtn = `<button type="button" data-action="detail" data-id="${record.id}"
                       class="pkg-detail-btn w-7 h-7 inline-flex items-center justify-center text-[#6E6E73] hover:text-white opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity"
                       title="明细">${window.svgIcon('eye', 'w-3.5 h-3.5')}</button>`;

        return `
        <tr class="group relative font-mono text-[11px] border-b border-[#141418] hover:bg-[#161620] transition-colors duration-100">
            <td class="p-0 relative"><div class="absolute left-0 top-0 bottom-0 w-[2px] bg-[#FF1E27] opacity-0 group-hover:opacity-70 transition-opacity"></div></td>
            <td class="px-2 py-2 text-[#F0F0F2] overflow-hidden truncate">${esc(record.location)}</td>
            <td class="px-2 py-2 text-[#8E8E93]">${esc(fmtYear(record.year))}</td>
            <td class="px-2 py-2 text-[#F0F0F2] overflow-hidden truncate">${esc(record.vehicle_model)}</td>
            <td class="px-2 py-2 overflow-hidden whitespace-nowrap">
                ${partShortCodeCellHtml(record.part_number)}
            </td>
            <td class="px-2 py-2 overflow-hidden">
                ${partNumberNameCellHtml(record.part_number, record.part_name)}
            </td>
            <td class="px-2 py-2 text-[#8E8E93] overflow-hidden truncate">${esc(record.packaging_type || '—')}</td>
            <td class="${numCell}">${esc(formatFee4(record.unit_packaging_fee))}</td>
            <td class="${numCell}">${esc(formatFee4(record.unit_transport_fee))}</td>
            <td class="${numCell}">${esc(formatFee4(record.fixture_maint_fee))}</td>
            <td class="${numCell}">${esc(formatFee4(record.other_fee))}</td>
            <td class="px-2 py-1.5 text-right font-mono font-black tabular-nums text-[12px] text-[#FF1E27] bg-[#1A080A] border-x border-[#FF1E27]/20">
                ${esc(formatFee4(record.packaging_transport_total))}
            </td>
            <td class="px-1 py-2 text-center">${auditBadge(record.audit_status)}</td>
            <td class="px-1 py-2 text-center whitespace-nowrap">${detailBtn}${editBtn}${delBtn}</td>
            <td class="px-2 py-2 text-[9px] text-[#3a3a3a] truncate">${esc(record.created_by || '—')}</td>
        </tr>`;
    }).join('');
}


export function renderDetailBody(record) {
    const row = (label, value) => `
        <div class="flex justify-between gap-3 border-b border-[#1a1a1a] py-2">
            <span class="text-[10px] text-[#616161] shrink-0">${label}</span>
            <span class="text-[11px] text-[#e0e0e0] text-right font-mono break-all">${esc(value ?? '—')}</span>
        </div>`;
    return `
        <div class="space-y-1">
            ${row('基地', record.location)}
            ${row('年度', fmtYear(record.year))}
            ${row('项目', record.vehicle_model)}
            ${row('零件号', record.part_number)}
            ${row('产品', record.part_name)}
            ${row('包装类型', record.packaging_type)}
            ${row('单包装数', record.pieces_per_pack)}
            ${row('器具 L×W×H', [record.fixture_length_mm, record.fixture_width_mm, record.fixture_height_mm].every((v) => v == null) ? null : `${record.fixture_length_mm ?? '-'}×${record.fixture_width_mm ?? '-'}×${record.fixture_height_mm ?? '-'}`)}
            ${row('器具总投入', record.total_fixture_qty)}
            ${row('器具单价', formatFee4(record.fixture_unit_price))}
            ${row('投入总金额', formatFee4(record.fixture_invest_amount))}
            ${row('往返运输价', formatFee4(record.round_trip_transport_price))}
            ${row('单件包装费', formatFee4(record.unit_packaging_fee))}
            ${row('单件运输费', formatFee4(record.unit_transport_fee))}
            ${row('器具维护费', formatFee4(record.fixture_maint_fee))}
            ${row('其它费用', formatFee4(record.other_fee))}
            ${row('包装运输费合计', formatFee4(record.packaging_transport_total))}
            ${row('审核状态', record.audit_status === 'approved' ? '已通过' : '待审')}
            ${row('来源文件', record.excel_filename)}
            ${row('工作表', record.sheet_name)}
            ${row('Excel 行号', record.excel_row)}
            ${row('备注', record.remark)}
        </div>`;
}
