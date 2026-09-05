/**
 * Stamping Part Cost List Template
 * 冲压零件价格一览—Brabus Carbon & Precision Dark（HUD 与加工费列表一致）
 */

import { pageSizeSelectHtml } from '../../../../page-size.js?v=2';

export function partCostListTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="bg-[#0A0A0C] border border-[#1A1A22] overflow-hidden w-full max-w-full"
                 style="box-shadow: 0 4px 24px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.02);">

                <!-- HUD 战术数据看板 + 操作 -->
                <div class="px-5 pt-4 pb-3.5 border-b border-[#14141A]"
                     style="background: linear-gradient(135deg, #0E0E12 0%, #121218 45%, #0C0C10 100%);">
                    <div class="flex items-start justify-between gap-4 mb-3">
                        <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 font-mono flex-1 min-w-0">
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3 backdrop-blur-sm"
                                 style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);">
                                <div class="text-[#555555] text-[10px] tracking-wider">核价条数</div>
                                <div class="text-[18px] font-bold text-[#FFFFFF] mt-1 tabular-nums">
                            <span id="costHudTotal" class="text-[#F0F0F2] font-bold tabular-nums">—</span>
                                    <span class="text-[10px] text-[#555555] ml-1">条</span>
                                </div>
                            </div>
                            <!-- 巴博斯霓虹红全本期均价 -->
                            <div class="bg-gradient-to-b from-[#18080A] to-[#0D0708] border border-[#FF1E27]/50 p-3.5 relative overflow-hidden group"
                                 style="box-shadow: 0 0 30px rgba(255,30,39,0.15), inset 0 1px 0 rgba(255,30,39,0.12);">
                                <div class="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-[#FF1E27] to-transparent"
                                     style="box-shadow: 0 0 10px #FF1E27;"></div>
                                <div class="flex justify-between items-start">
                                    <span class="text-[#FF1E27] text-[10px] font-bold tracking-widest">本期均价</span>
                                    <span class="w-2 h-2 rounded-full bg-[#FF1E27] animate-pulse"
                                          style="box-shadow: 0 0 8px #FF1E27;"></span>
                                </div>
                                <div class="text-[26px] font-black text-[#FF1E27] font-mono mt-1 tracking-tight tabular-nums"
                                     style="text-shadow: 0 0 12px rgba(255,30,39,0.7), 0 0 25px rgba(255,30,39,0.3);">
                                ￥<span id="costHudAvg">—</span>
                                </div>
                                <div class="text-[9px] font-mono text-[#FF1E27]/60 mt-1 flex justify-between">
                                    <span>系统自动计算</span>
                                    <span id="costHudSkuCount">— 条</span>
                                </div>
                            </div>
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3 backdrop-blur-sm"
                                 style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);">
                                <div class="text-[#555555] text-[10px] tracking-wider">待审</div>
                                <div class="text-[18px] font-bold text-[#FFFFFF] mt-1 tabular-nums">
                                    <span id="costHudPending">—</span>
                                    <span class="text-[10px] text-[#555555] ml-1">条</span>
                                </div>
                            </div>
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3 backdrop-blur-sm"
                                 style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);">
                                <div class="text-[#555555] text-[10px] tracking-wider">已审</div>
                                <div class="text-[18px] font-bold text-[#FFFFFF] mt-1 tabular-nums">
                                    <span id="costHudApproved">—</span>
                                    <span class="text-[10px] text-[#555555] ml-1">条</span>
                                </div>
                            </div>
                        </div>
                        <div class="flex items-center gap-2 shrink-0 flex-wrap justify-end">
                            <button id="costBatchApproveBtn" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] hover:bg-[#FF1E27]/10 hover:shadow-[0_0_12px_rgba(255,30,39,0.2)] transition-all duration-200">
                                ${window.svgIcon('check-circle', 'w-3 h-3')}
                                批量审核
                            </button>
                            <button id="costBatchReverseBtn" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] hover:bg-[#FF1E27]/10 hover:shadow-[0_0_12px_rgba(255,30,39,0.2)] transition-all duration-200">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                批量反审核
                            </button>
                            <button id="costBatchDeleteBtn" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#c62828]/60 hover:text-[#ef5350] hover:bg-[#c62828]/15 hover:shadow-[0_0_12px_rgba(198,40,40,0.2)] transition-all duration-200">
                                ${window.svgIcon('trash', 'w-3 h-3')}
                                批量删除
                            </button>
                            <button id="costExportBtn" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] hover:bg-[#FF1E27]/10 hover:shadow-[0_0_12px_rgba(255,30,39,0.2)] transition-all duration-200"
                                    title="须选定配套车型；按当前筛选导出冲压零件核价结果（含材料费、加工费、模具费、检具费）">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                导出 Excel
                            </button>
                        </div>
                    </div>
                </div>

                <!-- 战术胶囊筛选栏：默认收起-->
                <div class="px-5 py-3 border-b border-[#14141A]"
                     style="background: linear-gradient(180deg, #0C0C10 0%, #0A0A0E 100%);">
                    <div class="flex items-center justify-between gap-4 bg-[#0C0C10] border border-[#1E1E26] px-4 py-2.5 rounded-xl font-mono text-[11px]"
                         style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.02), 0 0 20px rgba(0,0,0,0.3);">
                        <div class="flex items-center gap-3 min-w-0 flex-1">
                            <span class="text-[#555555] shrink-0 tracking-wider">当前筛选：</span>
                            <div class="flex items-center gap-2 flex-wrap">
                                <span id="costCapsulePeriod" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部期间</span>
                                <span id="costCapsuleLocation" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部基地</span>
                                <span id="costCapsuleSupplier" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部工厂</span>
                                <span id="costCapsuleVehicle" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部车型</span>
                            </div>
                        </div>
                        <div class="flex items-center gap-3 shrink-0">
                            <button type="button" id="costToggleAdvancedFilter"
                                    class="text-[#6E6E73] hover:text-white transition-colors flex items-center gap-1.5 text-[11px]">
                                <span id="costAdvancedFilterLabel">展开高级筛选</span>
                                <span id="costAdvancedFilterCount" class="text-[#555555]">(0)</span>
                            </button>
                            <button type="button" id="costSearchBtn"
                                    class="inline-flex items-center gap-1.5 h-7 px-3 text-[11px] font-semibold rounded-sm text-[#c8c8c8] border border-[#8a2020] transition-all duration-200 hover:text-white"
                                    style="background: linear-gradient(180deg, #3d1515 0%, #2d0f0f 100%); border-color: #6b1a1a; box-shadow: 0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(211,47,47,0.1), 0 0 12px rgba(198,40,40,0.08);">
                                ${window.svgIcon('search', 'w-3 h-3')}
                                查询
                            </button>
                        </div>
                    </div>

                    <!-- 高级筛选面板（默认折叠（-->
                    <div id="costAdvancedFilterPanel" class="hidden mt-3 pt-3 border-t border-[#1A1A22]">
                        <div class="flex items-end gap-3 flex-wrap">
                            ${filterSelect('costYearFilter', '年度')}
                            ${filterSelect('costMonthFilter', '月份')}
                            ${filterSelect('costLocationFilter', '基地')}
                            ${filterSelect('costSupplierFilter', '冲压工厂')}
                            ${filterSelect('costVehicleModelFilter', '配套车型')}
                            ${filterSelect('costAuditFilter', '审核状态')}
                            ${filterInput('costPartNumberFilter', '零件号', '短号或完整零件号')}
                            <button id="costResetBtn" type="button"
                                    class="inline-flex items-center gap-1.5 h-8 px-3 text-[11px] font-medium rounded-md bg-transparent text-[#6E6E73] border border-[#2A2A35] hover:bg-[#FF1E27]/10 hover:border-[#FF1E27]/50 hover:text-[#FF1E27] transition-all duration-200">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>
                        </div>
                        <p class="mt-2 text-[10px] text-[#555555]">批量删除 / 审核 / 反审核须选定年度、月份、基地、冲压工厂。导出须选定配套车型。</p>
                    </div>
                </div>

                <div class="overflow-x-auto bg-[#0A0A0E] brabus-bg-grid">
                    <table id="costDataTable" class="w-full table-fixed bg-transparent border-collapse" style="min-width: 1780px;">
                        <colgroup id="costColgroup">
                            <col style="width:3px">
                            <col style="width:72px">
                            <col style="width:118px">
                            <col style="width:64px">
                            <col style="width:52px">
                            <col style="width:128px">
                            <col style="width:68px">
                            <col style="width:58px">
                            <col style="width:58px">
                            <col style="width:54px">
                            <col style="width:88px">
                            <col style="width:64px">
                            <col class="cost-breakdown-col hidden" style="width:64px">
                            <col class="cost-breakdown-col hidden" style="width:64px">
                            <col class="cost-breakdown-col hidden" style="width:64px">
                            <col class="cost-breakdown-col hidden" style="width:68px">
                            <col style="width:76px">
                            <col style="width:58px">
                            <col style="width:58px">
                            <col style="width:58px">
                            <col style="width:72px">
                            <col style="width:58px">
                            <col style="width:58px">
                            <col style="width:64px">
                            <col style="width:58px">
                            <col style="width:86px">
                            <col style="width:44px">
                            <col style="width:44px">
                            <col style="width:36px">
                        </colgroup>
                        <thead>
                            <tr class="border-b border-[#17171C] bg-[#0B0B0D]/95">
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">年月/基地</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#6E6E73]">零件</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]" title="本月核价快照；下月废料不足可改零件后再算下月">利废</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]" title="工艺含摆剪时，材料核算把系统摆剪吨价加进钢价；金额为当月快照">摆剪</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">材质/规格</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]" title="预估单件材料消耗 M (kg)">消耗</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]" title="零件净量">净量</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]" title="废料重量 O = 材料消耗−净量">废料</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">利用率</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]" title="钢材吨价；P=吨价/1000 为 kg">钢材吨价</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]" title="废料吨价；Q=吨价/1000 为 kg">废料吨价</th>
                                <th class="cost-breakdown-col hidden px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]" title="①钢材采购（含损耗）">①采购</th>
                                <th class="cost-breakdown-col hidden px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]" title="②损耗废料扣除（回收率）">②损耗扣</th>
                                <th class="cost-breakdown-col hidden px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]" title="③边角废料扣除（回收率）">③边角扣</th>
                                <th class="cost-breakdown-col hidden px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]" title="废料扣除合计 ②+③">废料扣合计</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#6E6E73]" title="R = ①−②−③">
                                    <button type="button" id="costToggleBreakdownCols"
                                            class="inline-flex items-center justify-center w-3.5 h-3.5 mr-0.5 align-middle border border-[#22222A] text-[#555555] hover:text-[#FF1E27] hover:border-[#FF1E27]/40 transition-colors"
                                            title="展开成本分项（①采购 / ②损耗扣 / ③边角扣 / 废料扣合计）">+</button>
                                    原材料R
                                </th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">加工费</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]" title="年度模具费最终价（元/件）；无档案为 0">模具费</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]" title="检具费（万元）÷ 分摊万台 = 元/件；无档案为 0">检具费</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]" title="直接成本 = R + 加工费 + 模具费 + 检具费">直接成本</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#484848]" title="直接成本 × 仓储+包装管理费用率">仓储包装</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#484848]" title="直接成本 × 管理费率">管理费</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#484848]" title="直接成本 × 财务费率">财务费</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#484848]" title="直接成本 × 税前利润率">税前利润</th>
                                <th class="px-2 py-2 text-right text-[9px] font-semibold tracking-[0.06em] text-[#FF1E27]/90 bg-[#1A080A]" title="单件成本 = 直接成本 + 仓储包装 + 管理费 + 财务费 + 税前利润">单件成本</th>
                                <th class="px-1 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">核算</th>
                                <th class="px-1 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">审核</th>
                                <th class="p-0 w-9" aria-label="操作"></th>
                            </tr>
                        </thead>
                        <tbody id="costTableBody" class="bg-transparent"></tbody>
                    </table>
                </div>

                <div class="flex items-center justify-between px-5 py-2.5 border-t border-[#14141A] bg-[#0A0A0E]">
                    <div class="flex items-center gap-3 min-w-0">
                        <span id="costPageInfo" class="text-[10px] font-mono text-[#555555]"></span>
                        ${pageSizeSelectHtml('costPageSize')}
                    </div>
                    <div class="flex items-center gap-0.5" id="costPagination"></div>
                </div>

                <div id="costEmpty" class="hidden flex flex-col items-center justify-center py-14">
                    <div class="w-10 h-10 flex items-center justify-center mb-3 rounded-md bg-[#121218] border border-[#2A2A35]">
                        ${window.svgIcon('clipboard-list', 'w-4 h-4 text-[#555555]')}
                    </div>
                    <h5 class="text-[11px] font-medium text-[#8E8E93] mb-1">暂无零件价格数据</h5>
                    <p class="text-[10px] text-[#555555]">请先完成零件价格计算，或调整筛选条件</p>
                </div>

                <div id="costLoading" class="hidden flex items-center justify-center py-14">
                    <div class="w-5 h-5 border-2 border-[#2A2A35] border-t-[#FF1E27] rounded-full animate-spin"
                         style="box-shadow: 0 0 12px rgba(255,30,39,0.35);"></div>
                </div>
            </div>
        </div>

        ${batchAuditDrawerHtml()}
    `;
}

function batchAuditDrawerHtml() {
    return `
        <div class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm transition-opacity duration-300"
             id="costBatchAuditDrawerBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[420px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="costBatchAuditDrawer" style="display:none; max-height: 100vh; box-shadow: -20px 0 60px rgba(0,0,0,0.95);">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0"
                 style="background: linear-gradient(180deg, #1f1f1f 0%, #1a1a1a 100%); border-bottom: 1px solid #333333;">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] flex items-center gap-2.5 uppercase">
                    <span style="width:3px;height:14px;background:#d32f2f;border-radius:1px;display:inline-block;box-shadow: 0 0 8px rgba(211,47,47,0.5);"></span>
                    <span id="costBatchAuditDrawerTitle">批量审核</span>
                </h5>
                <button type="button" id="closeCostBatchAuditDrawer"
                        class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-6 space-y-4">
                <input type="hidden" id="costBatchAuditMode" value="approve">
                <div class="bg-[#0c0c0c] border border-[#1a1a1a] rounded p-3 text-[11px] text-[#9e9e9e]" id="costBatchAuditFilterSummary"></div>
                <p id="costBatchAuditHint" class="text-[11px] text-[#616161]"></p>
                <div>
                    <label class="text-[10px] text-[#777777] mb-1 block" id="costBatchAuditOperatorLabel">操作人</label>
                    <div id="costBatchAuditOperatorDisplay"
                         class="w-full h-9 px-3 flex items-center text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] rounded">
                        —
                    </div>
                    <p class="text-[10px] text-[#555555] mt-1">取自当前登录用户，无需填写</p>
                </div>
                <div>
                    <label class="text-[10px] text-[#777777] mb-1 block" id="costBatchAuditRemarkLabel">审核意见</label>
                    <textarea id="costBatchAuditRemark" rows="4" maxlength="500"
                              class="w-full px-3 py-2 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded resize-none"
                              placeholder="请填写审核意见（必填）"></textarea>
                </div>
            </div>
            <div class="px-6 py-4 border-t border-[#262626] flex items-center justify-end gap-2 shrink-0">
                <button type="button" id="cancelCostBatchAuditBtn" class="inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-4 py-2 text-[11px] font-medium rounded hover:border-[#9e9e9e] hover:text-white transition-all">取消</button>
                <button type="button" id="confirmCostBatchAuditBtn" class="inline-flex items-center gap-1.5 bg-[#d32f2f] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all">
                    确认提交
                </button>
            </div>
        </div>
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

export function renderCostRows(records, breakdownOpen = false) {
    if (!records || !Array.isArray(records) || records.length === 0) return '';
    const breakdownHidden = breakdownOpen ? '' : 'hidden';
    return records.map((row) => {
        const fail = row.calc_status === 'failed';
        const ym = `${esc(row.year)}-${esc(String(row.month).padStart(2, '0'))}`;
        const location = esc(row.location) || '—';
        const supplier = esc(row.stamping_supplier) || '—';
        const num = 'px-2 py-2 font-mono text-[10px] text-right tabular-nums text-[#8E8E93]';
        const actionTitle = fail ? '手工干预' : '查看详情';
        const actionIcon = fail
            ? window.svgIcon('pencil', 'w-3.5 h-3.5')
            : window.svgIcon('eye', 'w-3.5 h-3.5');
        const actionTone = fail
            ? 'text-[#8A3030] hover:text-[#FF1E27]'
            : 'text-[#555555] hover:text-[#C8C8D0]';
        const actionBtn = `
            <button type="button"
                    class="btn-open-detail inline-flex items-center justify-center w-7 h-7 rounded-sm
                           opacity-0 group-hover:opacity-100 focus:opacity-100
                           ${actionTone} hover:bg-[#161620] transition-all duration-100"
                    data-id="${esc(row.id)}" title="${actionTitle}" aria-label="${actionTitle}">
                ${actionIcon}
            </button>`;
        return `
        <tr class="cost-row group relative font-mono text-[11px] border-b border-[#141418] hover:bg-[#161620] transition-colors duration-100">
            <td class="p-0 relative">
                <div class="absolute left-0 top-0 bottom-0 w-[2px] bg-[#FF1E27] opacity-0 group-hover:opacity-70 transition-opacity"></div>
            </td>
            <td class="px-2 py-2 overflow-hidden">
                <div class="font-mono font-semibold text-[#F0F0F2] text-[11px] tabular-nums">${ym}</div>
                <div class="text-[#555555] text-[9px] mt-0.5 leading-tight truncate" title="${location}">${location}</div>
                <div class="text-[#3A3A42] text-[9px] leading-tight truncate" title="${supplier}">${supplier}</div>
            </td>
            <td class="px-2 py-2 overflow-hidden">${partInfoCell(row.part_number, row.part_name)}</td>
            <td class="px-2 py-2 overflow-hidden">${offalCostCell(row)}</td>
            <td class="px-1 py-2 text-center">${swingShearCostCell(row)}</td>
            <td class="px-2 py-2 overflow-hidden">
                <div class="text-[#8E8E93] text-[10px] truncate" title="${esc(row.material || '')}">${esc(row.material || '—')}</div>
                <div class="text-[#F0F0F2] text-[10px] mt-0.5 tabular-nums truncate" title="${esc(row.thickness || '')}">${esc(row.thickness || '—')}</div>
                <div class="text-[#555555] text-[9px] mt-0.5 tabular-nums truncate" title="${esc((row.sheet_length || '—') + ' × ' + (row.sheet_width || '—'))}">${esc(row.sheet_length || '—')} × ${esc(row.sheet_width || '—')}</div>
            </td>
            <td class="${num}" title="${esc(fmtNum(row.blank_weight_kg, 7))}">${fmtNum(row.blank_weight_kg, 3)}</td>
            <td class="${num}" title="${esc(fmtNum(row.finished_total_kg, 7))}">${fmtNum(row.finished_total_kg, 3)}</td>
            <td class="${num}" title="${esc(fmtNum(row.scrap_weight_kg, 7))}">${fmtNum(row.scrap_weight_kg, 3)}</td>
            <td class="${num}">${fmtNum(row.material_utilization_pct, 1)}</td>
            <td class="${num}" title="${esc(row.is_offal_nested ? '利废：成品净重 × 废料单价' : (row.steel_mill || ''))}">
                <div class="text-[#C8C8D0]">${esc(row.steel_ton_price || '—')}</div>
                ${row.is_offal_nested
                    ? `<div class="text-[9px] text-[#ffb74d] font-normal mt-0.5 truncate">废料价</div>`
                    : (row.steel_mill ? `<div class="text-[9px] text-[#555555] font-normal mt-0.5 truncate">${esc(row.steel_mill)}</div>` : '')}
            </td>
            <td class="${num}">${fmtNum(row.scrap_ton_price, 0)}</td>
            <td class="cost-breakdown-col ${breakdownHidden} ${num}">${fmtNum(row.material_amount_sheet, 2)}</td>
            <td class="cost-breakdown-col ${breakdownHidden} ${num}">${fmtNum(row.loss_scrap_deduction, 2)}</td>
            <td class="cost-breakdown-col ${breakdownHidden} ${num}">${fmtNum(row.process_scrap_deduction, 2)}</td>
            <td class="cost-breakdown-col ${breakdownHidden} ${num}">${fmtNum(row.scrap_amount_sheet, 2)}</td>
            <td class="${num} text-[#C8C8D0] font-semibold">${fmtNum(row.material_net_per_part, 2)}</td>
            <td class="${num}">${fmtNum(row.process_fee_amount, 2)}</td>
            <td class="${num}">${fmtNum(row.die_fee_amount, 2)}</td>
            <td class="${num}">${fmtNum(row.gauge_fee_amount, 2)}</td>
            <td class="${num}">${fmtNum(row.direct_cost, 2)}</td>
            <td class="px-2 py-2 font-mono text-[9px] text-right tabular-nums text-[#555555]">${fmtNum(row.finished_warehouse_packaging_fee, 2)}</td>
            <td class="px-2 py-2 font-mono text-[9px] text-right tabular-nums text-[#555555]">${fmtNum(row.finished_management_fee, 2)}</td>
            <td class="px-2 py-2 font-mono text-[9px] text-right tabular-nums text-[#555555]">${fmtNum(row.finished_finance_fee, 2)}</td>
            <td class="px-2 py-2 font-mono text-[9px] text-right tabular-nums text-[#555555]">${fmtNum(row.finished_pretax_profit_fee, 2)}</td>
            <td class="px-2 py-1.5 text-right font-mono font-black tabular-nums text-[12px] text-[#FF1E27] bg-[#1A080A] border-x border-[#FF1E27]/20">
                <span style="text-shadow: 0 0 8px rgba(255,30,39,0.45);">${fmtNum(row.unit_cost, 4)}</span>
            </td>
            <td class="px-1 py-2 text-center">${calcStatusBadge(fail)}</td>
            <td class="px-1 py-2 text-center">${auditBadge(row.audit_status)}</td>
            <td class="px-1 py-2 text-center align-middle">${actionBtn}</td>
        </tr>`;
    }).join('');
}

/**
 * 同步成本分项列显隐（①采购 / ②损耗扣 / ③边角扣 / 废料扣合计）
 * @param {boolean} isOpen
 */
export function syncBreakdownColumnVisibility(isOpen) {
    document.querySelectorAll('.cost-breakdown-col').forEach((el) => {
        el.classList.toggle('hidden', !isOpen);
    });
    const btn = document.getElementById('costToggleBreakdownCols');
    if (btn) {
        btn.textContent = isOpen ? '−' : '+';
        btn.title = isOpen
            ? '收起成本分项'
            : '展开成本分项（①采购 / ②损耗扣 / ③边角扣 / 废料扣合计）';
    }
    const table = document.getElementById('costDataTable');
    if (table) {
                table.style.minWidth = isOpen ? '1780px' : '1520px';
    }
}

/**
 * 企业口语短号：取零件号数字段术4 位（中BOM / 加工费一致）。
 * 例：554002087AA →2087（01006873AA →6873
 */
export function shortPartNumber(partNumber) {
    if (!partNumber) return null;
    const digits = String(partNumber).replace(/\D/g, '');
    if (digits.length < 4) return null;
    return digits.slice(-4);
}

/** 列表单元格：短号主角，完整号 + 零件名次要*/
function partInfoCell(partNumber, partName) {
    const full = partNumber || '';
    const shortNo = shortPartNumber(full);
    const name = partName || '';
    const nameLine = name
        ? `<div class="text-[9px] text-[#555555] mt-0.5 truncate" title="${esc(name)}">${esc(name)}</div>`
        : '';
    if (shortNo) {
        return `
            <div class="text-[14px] font-mono font-bold tabular-nums text-[#F0F0F2] tracking-[0.08em] leading-none"
                 title="${esc(full)}">${esc(shortNo)}</div>
            <div class="text-[9px] font-mono text-[#3A3A42] tracking-wide mt-0.5 truncate" title="${esc(full)}">${esc(full)}</div>
            ${nameLine}`;
    }
    return `
        <div class="text-[10px] font-mono text-[#8E8E93] tracking-wide truncate" title="${esc(full)}">${esc(full) || '—'}</div>
        ${nameLine}`;
}

function offalCostCell(row) {
    if (!row.is_offal_nested) {
        return '<span class="text-[#555555]">否</span>';
    }
    const source = row.offal_source ? esc(row.offal_source) : '';
    return `
        <div class="text-[10px] text-[#ffb74d]">是</div>
        <div class="text-[9px] text-[#8E8E93] mt-0.5 truncate" title="${source}">${source || '—'}</div>`;
}

function swingShearCostCell(row) {
    if (!row.has_swing_shear) {
        return '<span class="text-[#555555]">否</span>';
    }
    const fee = fmtNum(row.swing_shear_fee_per_ton, 2);
    return `
        <div class="inline-flex flex-col items-center gap-0.5">
            <span class="inline-flex items-center px-1.5 py-0.5 text-[9px] tracking-wide text-[#90caf9] bg-[#0d1a24] border border-[#90caf9]/30">是</span>
            <span class="text-[9px] font-mono tabular-nums text-[#8E8E93]" title="当月加到钢价上的元/吨">+${esc(fee)}</span>
        </div>`;
}

/** 用筛选汇总刷新HUD（均价/ 待审 / 已审均为全量筛选结果，非本页） */
export function updatePartCostHud(total, summary) {
    const setText = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    };
    const data = summary && typeof summary === 'object' ? summary : {};
    const avg = data.avg_unit_cost;
    const avgFixed = formatDecimalFixed(avg, 4, { allowNegative: true });

    setText('costHudTotal', Number(total || 0).toLocaleString('zh-CN'));
    setText(
        'costHudAvg',
        avgFixed == null ? '—' : withThousandsSep(avgFixed),
    );
    setText('costHudSkuCount', `${Number(total || 0).toLocaleString('zh-CN')} 条`);
    setText('costHudPending', String(data.pending_count ?? 0));
    setText('costHudApproved', String(data.approved_count ?? 0));
}

/**
 * 同步战术胶囊：期间/ 基地 / 工厂 + 高级筛选已启用数量
 */
export function updateCostFilterCapsules() {
    const year = document.getElementById('costYearFilter')?.value || '';
    const month = document.getElementById('costMonthFilter')?.value || '';
    const location = document.getElementById('costLocationFilter')?.value || '';
    const supplier = document.getElementById('costSupplierFilter')?.value || '';
    const vehicle = document.getElementById('costVehicleModelFilter')?.value || '';
    const audit = document.getElementById('costAuditFilter')?.value || '';
    const part = document.getElementById('costPartNumberFilter')?.value.trim() || '';

    const activeCapsule = 'bg-[#1A1A22] border border-[#2A2A35] text-white px-2.5 py-1 rounded-md font-bold';
    const idleCapsule = 'bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md';

    const periodEl = document.getElementById('costCapsulePeriod');
    const locationEl = document.getElementById('costCapsuleLocation');
    const supplierEl = document.getElementById('costCapsuleSupplier');
    const vehicleEl = document.getElementById('costCapsuleVehicle');
    const countEl = document.getElementById('costAdvancedFilterCount');

    if (periodEl) {
        if (year && month) {
            periodEl.textContent = `${year}-${String(month).padStart(2, '0')}`;
            periodEl.className = activeCapsule;
        } else if (year) {
            periodEl.textContent = `${year}年`;
            periodEl.className = activeCapsule;
        } else {
            periodEl.textContent = '全部期间';
            periodEl.className = idleCapsule;
        }
    }
    if (locationEl) {
        locationEl.textContent = location || '全部基地';
        locationEl.className = location ? activeCapsule : idleCapsule;
    }
    if (supplierEl) {
        supplierEl.textContent = supplier || '全部工厂';
        supplierEl.className = supplier ? activeCapsule : idleCapsule;
    }
    if (vehicleEl) {
        vehicleEl.textContent = vehicle || '全部车型';
        vehicleEl.className = vehicle ? activeCapsule : idleCapsule;
    }

    const advancedActive = [year, month, location, supplier, vehicle, audit, part].filter(Boolean).length;
    if (countEl) countEl.textContent = `(${advancedActive})`;
}

export function renderCostPagination(currentPage, totalPages) {
    if (totalPages <= 1) return '';
    let buttons = `
        <button class="cost-page-btn flex items-center justify-center w-6 h-6 text-[10px] ${currentPage === 1 ? 'text-[#2E2E36] cursor-not-allowed' : 'text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620]'} transition-all"
                data-page="${currentPage - 1}" ${currentPage === 1 ? 'disabled' : ''}>
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path></svg>
        </button>`;
    const maxVisible = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);
    if (endPage - startPage < maxVisible - 1) startPage = Math.max(1, endPage - maxVisible + 1);
    if (startPage > 1) {
        buttons += `<button class="cost-page-btn flex items-center justify-center w-6 h-6 text-[10px] text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620]" data-page="1">1</button>`;
        if (startPage > 2) buttons += `<span class="px-0.5 text-[#2E2E36] text-[9px]">—</span>`;
    }
    for (let i = startPage; i <= endPage; i++) {
        const isActive = i === currentPage;
        buttons += `<button class="cost-page-btn flex items-center justify-center w-6 h-6 text-[10px] ${isActive ? 'bg-[#E8E8ED] text-[#0A0A0C] font-bold' : 'text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620]'}" data-page="${i}">${i}</button>`;
    }
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) buttons += `<span class="px-0.5 text-[#2E2E36] text-[9px]">—</span>`;
        buttons += `<button class="cost-page-btn flex items-center justify-center w-6 h-6 text-[10px] text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620]" data-page="${totalPages}">${totalPages}</button>`;
    }
    buttons += `
        <button class="cost-page-btn flex items-center justify-center w-6 h-6 text-[10px] ${currentPage === totalPages ? 'text-[#2E2E36] cursor-not-allowed' : 'text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620]'}"
                data-page="${currentPage + 1}" ${currentPage === totalPages ? 'disabled' : ''}>
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>
        </button>`;
    return buttons;
}

/** 无错即隐：成功不占视觉；失败才露「失败。*/
function calcStatusBadge(isFailed) {
    if (!isFailed) return '';
    return `<span class="text-[#FF1E27] font-bold text-[9px] px-1 bg-[#FF1E27]/10 border border-[#FF1E27]/25">失败</span>`;
}

/** 待审留白；已通过/驳回才轻核*/
function auditBadge(status) {
    if (!status || status === 'pending') return '';
    if (status === 'approved') {
        return `<span class="text-[9px] text-[#555555]">已审</span>`;
    }
    if (status === 'rejected') {
        return `<span class="text-[9px] text-[#ef5350]">驳回</span>`;
    }
    return `<span class="text-[9px] text-[#555555]">${esc(status)}</span>`;
}
