/**
 * Stamping Process Fee List Template
 * 冲压加工费计算结果浏览—Brabus Carbon & Precision Dark
 */

import { pageSizeSelectHtml } from '../../../../page-size.js?v=2';

export function processFeeListTemplate() {
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
                                <div class="text-[#555555] text-[10px] tracking-wider">加工费条数</div>
                                <div class="text-[18px] font-bold text-[#FFFFFF] mt-1 tabular-nums">
                                    <span id="feeHudTotal">—</span>
                                    <span class="text-[10px] text-[#555555] ml-1">条</span>
                                </div>
                            </div>
                            <!-- 巴博斯霓虹红光：计算价为 0 -->
                            <div class="bg-gradient-to-b from-[#18080A] to-[#0D0708] border border-[#FF1E27]/50 p-3.5 relative overflow-hidden group"
                                 style="box-shadow: 0 0 30px rgba(255,30,39,0.15), inset 0 1px 0 rgba(255,30,39,0.12);">
                                <div class="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-[#FF1E27] to-transparent"
                                     style="box-shadow: 0 0 10px #FF1E27;"></div>
                                <div class="flex justify-between items-start">
                                    <span class="text-[#FF1E27] text-[10px] font-bold tracking-widest">计算价为 0</span>
                                    <span class="w-2 h-2 rounded-full bg-[#FF1E27] animate-pulse"
                                          style="box-shadow: 0 0 8px #FF1E27;"></span>
                                </div>
                                <div class="text-[26px] font-black text-[#FF1E27] font-mono mt-1 tracking-tight tabular-nums"
                                     style="text-shadow: 0 0 12px rgba(255,30,39,0.7), 0 0 25px rgba(255,30,39,0.3);">
                                    <span id="feeHudZero">—</span>
                                </div>
                                <div class="text-[9px] font-mono text-[#FF1E27]/60 mt-1 flex justify-between">
                                    <span>请手工调价</span>
                                    <span id="feeHudMatchCount">— 条</span>
                                </div>
                            </div>
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3 backdrop-blur-sm"
                                 style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);">
                                <div class="text-[#555555] text-[10px] tracking-wider">待审</div>
                                <div class="text-[18px] font-bold text-[#FFFFFF] mt-1 tabular-nums">
                                    <span id="feeHudPending">—</span>
                                    <span class="text-[10px] text-[#555555] ml-1">条</span>
                                </div>
                            </div>
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3 backdrop-blur-sm"
                                 style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);">
                                <div class="text-[#555555] text-[10px] tracking-wider">已审</div>
                                <div class="text-[18px] font-bold text-[#FFFFFF] mt-1 tabular-nums">
                                    <span id="feeHudApproved">—</span>
                                    <span class="text-[10px] text-[#555555] ml-1">条</span>
                                </div>
                            </div>
                        </div>
                        <div class="flex items-center gap-2 shrink-0 flex-wrap justify-end">
                            <button id="feeBatchApproveBtn" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] hover:bg-[#FF1E27]/10 hover:shadow-[0_0_12px_rgba(255,30,39,0.2)] transition-all duration-200">
                                ${window.svgIcon('check-circle', 'w-3 h-3')}
                                批量审核
                            </button>
                            <button id="feeBatchReverseBtn" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] hover:bg-[#FF1E27]/10 hover:shadow-[0_0_12px_rgba(255,30,39,0.2)] transition-all duration-200">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                批量反审核
                            </button>
                            <button id="feeBatchDeleteBtn" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#c62828]/60 hover:text-[#ef5350] hover:bg-[#c62828]/15 hover:shadow-[0_0_12px_rgba(198,40,40,0.2)] transition-all duration-200">
                                ${window.svgIcon('trash', 'w-3 h-3')}
                                批量删除
                            </button>
                            <button id="feeExportBtn" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] hover:bg-[#FF1E27]/10 hover:shadow-[0_0_12px_rgba(255,30,39,0.2)] transition-all duration-200">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                导出 Excel
                            </button>
                        </div>
                    </div>
                </div>

                <!-- 战术胶囊筛选栏：默认收起，抹平 ERP 模版意-->
                <div class="px-5 py-3 border-b border-[#14141A]"
                     style="background: linear-gradient(180deg, #0C0C10 0%, #0A0A0E 100%);">
                    <div class="flex items-center justify-between gap-4 bg-[#0C0C10] border border-[#1E1E26] px-4 py-2.5 rounded-xl font-mono text-[11px]"
                         style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.02), 0 0 20px rgba(0,0,0,0.3);">
                        <div class="flex items-center gap-3 min-w-0 flex-1">
                            <span class="text-[#555555] shrink-0 tracking-wider">当前筛选：</span>
                            <div class="flex items-center gap-2 flex-wrap">
                                <span id="feeCapsuleYear" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部年度</span>
                                <span id="feeCapsuleLocation" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部基地</span>
                                <span id="feeCapsuleSupplier" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部工厂</span>
                            </div>
                        </div>
                        <div class="flex items-center gap-3 shrink-0">
                            <button type="button" id="feeToggleAdvancedFilter"
                                    class="text-[#6E6E73] hover:text-white transition-colors flex items-center gap-1.5 text-[11px]">
                                <span id="feeAdvancedFilterLabel">展开高级筛选</span>
                                <span id="feeAdvancedFilterCount" class="text-[#555555]">(0)</span>
                            </button>
                            <button type="button" id="feeSearchBtn"
                                    class="inline-flex items-center gap-1.5 h-7 px-3 text-[11px] font-semibold rounded-sm text-[#c8c8c8] border border-[#8a2020] transition-all duration-200 hover:text-white"
                                    style="background: linear-gradient(180deg, #3d1515 0%, #2d0f0f 100%); border-color: #6b1a1a; box-shadow: 0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(211,47,47,0.1), 0 0 12px rgba(198,40,40,0.08);">
                                ${window.svgIcon('search', 'w-3 h-3')}
                                查询
                            </button>
                        </div>
                    </div>

                    <!-- 高级筛选面板（默认折叠）-->
                    <div id="feeAdvancedFilterPanel" class="hidden mt-3 pt-3 border-t border-[#1A1A22]">
                        <div class="flex items-end gap-3 flex-wrap">
                            ${filterSelect('feeYearFilter', '年度')}
                            ${filterSelect('feeLocationFilter', '基地')}
                            ${filterSelect('feeSupplierFilter', '冲压工厂')}
                            ${filterSelect('feeAuditStatusFilter', '审核状态')}
                            ${filterInput('feePartNumberFilter', '零件号, '短号或完整零件号')}
                            <button id="feeResetBtn" type="button"
                                    class="inline-flex items-center gap-1.5 h-8 px-3 text-[11px] font-medium rounded-md bg-transparent text-[#6E6E73] border border-[#2A2A35] hover:bg-[#FF1E27]/10 hover:border-[#FF1E27]/50 hover:text-[#FF1E27] transition-all duration-200">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>
                        </div>
                        <p class="mt-2 text-[10px] text-[#555555]">批量删除 / 审核 / 反审核须选定年度、基地、冲压工厂。</p>
                    </div>
                </div>

                <div class="overflow-x-auto brabus-bg-grid">
                    <table class="w-full min-w-[2400px] bg-transparent">
                        <thead>
                            <tr class="border-b border-[#17171C] bg-[#0B0B0D]/95">
                                <th class="p-0 w-0"></th>
                                <!-- 关注区：零件标识 + 计算结果 / 手工调整 / 最终价 -->
                                <th class="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">核价维度</th>
                                <th class="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-[#A1A1A6] whitespace-nowrap">零件号</th>
                                <th class="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">零件名称</th>
                                <th class="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap border-r border-[#22222A]">车型/版本</th>
                                <th class="px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">工序数</th>
                                <th class="px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">系统计算</th>
                                <th class="px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap border-r border-[#22222A]">手工调整</th>
                                <th class="px-3 py-3 text-right text-[10px] font-bold uppercase tracking-[0.18em] text-[#FFFFFF]/70 whitespace-nowrap bg-[#14141C] border-x border-[#222230]">最终加工费</th>
                                <!-- 次要：材新/ 工艺明细 -->
                                <th class="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">材质</th>
                                <th class="px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">料厚</th>
                                <th class="px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">重量</th>
                                <th class="px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">料片长</th>
                                <th class="px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">料片审</th>
                                <th class="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">模具/工艺</th>
                                <th class="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">备注</th>
                                <th class="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">审核</th>
                                <th class="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">说明</th>
                                <th class="p-0 w-9" aria-label="操作"></th>
                                <th class="px-3 py-3 text-left text-[9px] font-normal tracking-[0.08em] text-[#3a3a3a] whitespace-nowrap">创建交</th>
                                <th class="px-3 py-3 text-left text-[9px] font-normal tracking-[0.08em] text-[#3a3a3a] whitespace-nowrap">创建时间</th>
                                <th class="px-3 py-3 text-left text-[9px] font-normal tracking-[0.08em] text-[#3a3a3a] whitespace-nowrap">最后修改人</th>
                                <th class="px-3 py-3 text-left text-[9px] font-normal tracking-[0.08em] text-[#3a3a3a] whitespace-nowrap">最后修改时间</th>
                            </tr>
                        </thead>
                        <tbody id="feeTableBody" class="bg-transparent"></tbody>
                    </table>
                </div>

                <div class="flex items-center justify-between px-5 py-2.5 border-t border-[#14141A] bg-[#0A0A0E]">
                    <div class="flex items-center gap-3 min-w-0">
                        <span id="feeTotalLabel" class="text-[10px] font-mono text-[#555555]"></span>
                        ${pageSizeSelectHtml('feePageSize')}
                    </div>
                    <div class="flex items-center gap-0.5" id="feePagination"></div>
                </div>

                <div id="feeEmpty" class="hidden flex flex-col items-center justify-center py-14">
                    <div class="w-10 h-10 flex items-center justify-center mb-3 rounded-md bg-[#121218] border border-[#2A2A35]">
                        ${window.svgIcon('clipboard-list', 'w-4 h-4 text-[#555555]')}
                    </div>
                    <h5 class="text-[11px] font-medium text-[#8E8E93] mb-1">暂无加工费数据</h5>
                    <p class="text-[10px] text-[#555555]">请先在「冲压加工费计算」中执行计算</p>
                </div>

                <div id="feeLoading" class="hidden flex items-center justify-center py-14">
                    <div class="w-5 h-5 border-2 border-[#2A2A35] border-t-[#FF1E27] rounded-full animate-spin"
                         style="box-shadow: 0 0 12px rgba(255,30,39,0.35);"></div>
                </div>
            </div>
        </div>

        <!-- 批量审核 / 反审核抽屉-->
        <div class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm transition-opacity duration-300"
             id="feeBatchAuditDrawerBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[420px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="feeBatchAuditDrawer" style="display:none; max-height: 100vh; box-shadow: -20px 0 60px rgba(0,0,0,0.95);">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0"
                 style="background: linear-gradient(180deg, #1f1f1f 0%, #1a1a1a 100%); border-bottom: 1px solid #333333;">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] flex items-center gap-2.5 uppercase">
                    <span style="width:3px;height:14px;background:#d32f2f;border-radius:1px;display:inline-block;box-shadow: 0 0 8px rgba(211,47,47,0.5);"></span>
                    <span id="feeBatchAuditDrawerTitle">批量审核</span>
                </h5>
                <button type="button" id="closeFeeBatchAuditDrawer"
                        class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-6 space-y-4">
                <input type="hidden" id="feeBatchAuditMode" value="approve">
                <div class="bg-[#0c0c0c] border border-[#1a1a1a] rounded p-3 text-[11px] text-[#9e9e9e]" id="feeBatchAuditFilterSummary"></div>
                <p id="feeBatchAuditHint" class="text-[11px] text-[#616161]"></p>
                <div>
                    <label class="text-[10px] text-[#777777] mb-1 block" id="feeBatchAuditOperatorLabel">操作人</label>
                    <div id="feeBatchAuditOperatorDisplay"
                         class="w-full h-9 px-3 flex items-center text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] rounded">
                        —
                    </div>
                    <p class="text-[10px] text-[#555555] mt-1">取自当前登录用户，无需填写</p>
                </div>
                <div>
                    <label class="text-[10px] text-[#777777] mb-1 block" id="feeBatchAuditRemarkLabel">审核意见</label>
                    <textarea id="feeBatchAuditRemark" rows="4" maxlength="500"
                              class="w-full px-3 py-2 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded resize-none"
                              placeholder="可选填写审核意览></textarea>
                </div>
            </div>
            <div class="px-6 py-4 border-t border-[#262626] flex items-center justify-end gap-2 shrink-0">
                <button type="button" id="cancelFeeBatchAuditBtn" class="inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-4 py-2 text-[11px] font-medium rounded hover:border-[#9e9e9e] hover:text-white transition-all">取消</button>
                <button type="button" id="confirmFeeBatchAuditBtn" class="inline-flex items-center gap-1.5 bg-[#d32f2f] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all">
                    确认提交
                </button>
            </div>
        </div>

        <!-- 编辑抽屉：手工调价-->
        <div class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm transition-opacity duration-300"
             id="feeEditDrawerBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[560px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="feeEditDrawer" style="display:none; max-height: 100vh; box-shadow: -20px 0 60px rgba(0,0,0,0.95);">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0"
                 style="background: linear-gradient(180deg, #1f1f1f 0%, #1a1a1a 100%); border-bottom: 1px solid #333333;">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] flex items-center gap-2.5 uppercase">
                    <span style="width:3px;height:14px;background:#d32f2f;border-radius:1px;display:inline-block;box-shadow: 0 0 8px rgba(211,47,47,0.5);"></span>
                    <span id="feeEditDrawerTitle">编辑加工费</span>
                </h5>
                <button type="button" id="closeFeeEditDrawer"
                        class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain" id="feeEditDrawerContent">
                <form id="feeEditForm" class="p-6 space-y-5">
                    <input type="hidden" id="feeEditRecordId" value="">
                    <!-- 关注区：计算价/ 手工调整 / 最终价 置顶 -->
                    <div class="bg-[#111111] border border-[#d32f2f]/30 p-4"
                         style="box-shadow: 0 0 24px rgba(211,47,47,0.08), inset 0 1px 0 rgba(211,47,47,0.06);">
                        <label class="text-[10px] font-semibold text-[#d32f2f] uppercase tracking-[0.1em] mb-3 flex items-center gap-2">
                            <span class="w-0.5 h-3 bg-[#d32f2f] rounded-sm shadow-[0_0_8px_rgba(211,47,47,0.5)]"></span>
                            计算结果 / 手工调整 / 最终价
                        </label>
                        <div class="grid grid-cols-2 gap-3 mb-3">
                            ${viewRow('系统计算加工费', 'fee-edit-processing-fee')}
                            ${viewRow('最终加工费（保存后刷新）', 'fee-edit-final-fee', true)}
                        </div>
                        <div class="grid grid-cols-1 gap-3">
                            <div>
                                <label class="text-[10px] text-[#777777] mb-1 block">手工调整单价 <span class="text-[#616161]">（留空则回退系统计算）</span></label>
                                <input type="number" id="feeEditManualPrice" step="0.001" min="0"
                                       class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] rounded"
                                       placeholder="可空">
                            </div>
                            <div>
                                <label class="text-[10px] text-[#777777] mb-1 block">备注</label>
                                <textarea id="feeEditRemark" rows="3" maxlength="1000"
                                          class="w-full px-3 py-2 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded resize-none"
                                          placeholder="调整理由 / 原因"></textarea>
                            </div>
                        </div>
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-2 block">零件基本信息（只读）</label>
                        <div class="grid grid-cols-2 gap-3">
                            ${viewRow('年度', 'fee-edit-year')}
                            ${viewRow('基地', 'fee-edit-location')}
                            ${viewRow('冲压工厂', 'fee-edit-supplier')}
                            ${partNumberViewBlock('fee-edit')}
                            ${viewRow('车型', 'fee-edit-vehicle')}
                            ${viewRow('版本', 'fee-edit-version')}
                        </div>
                    </div>
                </form>
            </div>
            <div class="px-6 py-4 border-t border-[#262626] flex items-center justify-end gap-2 shrink-0">
                <button type="button" id="cancelFeeEditBtn" class="inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-4 py-2 text-[11px] font-medium rounded hover:border-[#9e9e9e] hover:text-white transition-all">取消</button>
                <button type="button" id="submitFeeEditBtn" class="inline-flex items-center gap-1.5 bg-[#d32f2f] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all">
                    ${window.svgIcon('archive', 'w-3.5 h-3.5')}
                    保存
                </button>
            </div>
        </div>

        <!-- 查看详情抽屉 -->
        <div class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm transition-opacity duration-300"
             id="feeViewDrawerBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[640px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="feeViewDrawer" style="display:none; max-height: 100vh; box-shadow: -20px 0 60px rgba(0,0,0,0.95);">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0"
                 style="background: linear-gradient(180deg, #1f1f1f 0%, #1a1a1a 100%); border-bottom: 1px solid #333333;">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] flex items-center gap-2.5 uppercase">
                    <span style="width:3px;height:14px;background:#d32f2f;border-radius:1px;display:inline-block;box-shadow: 0 0 8px rgba(211,47,47,0.5);"></span>
                    加工费详情
                </h5>
                <button type="button" id="closeFeeViewDrawer"
                        class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain p-6 space-y-4" id="feeViewDrawerContent">
                <!-- 关注区：零件标识 + 加工费结果-->
                <div class="bg-[#111111] border border-[#262626]">
                    <div class="px-4 py-3 bg-[#0c0c0c] border-b border-[#181818]">
                        <h6 class="text-[10px] font-semibold text-[#9e9e9e] tracking-wider uppercase">零件基本信息</h6>
                    </div>
                    <div class="p-4 grid grid-cols-2 gap-x-6 gap-y-3">
                        ${viewRow('年度', 'fee-view-year')}
                        ${viewRow('基地', 'fee-view-location')}
                        ${viewRow('冲压工厂', 'fee-view-supplier')}
                        ${partNumberViewBlock('fee-view')}
                        ${viewRow('零件名称', 'fee-view-part-name')}
                        ${viewRow('车型', 'fee-view-vehicle')}
                        ${viewRow('版本', 'fee-view-version')}
                        ${viewRow('序号', 'fee-view-seq-no')}
                    </div>
                </div>
                <div class="bg-[#111111] border border-[#d32f2f]/30"
                     style="box-shadow: 0 0 24px rgba(211,47,47,0.08), inset 0 1px 0 rgba(211,47,47,0.06);">
                    <div class="px-4 py-3 bg-[#0c0c0c] border-b border-[#181818] flex items-center gap-2">
                        <span class="w-0.5 h-3 bg-[#d32f2f] rounded-sm shadow-[0_0_8px_rgba(211,47,47,0.5)]"></span>
                        <h6 class="text-[10px] font-semibold text-[#d32f2f] tracking-wider uppercase">计算结果 / 手工调整 / 最终价</h6>
                    </div>
                    <div class="p-4 grid grid-cols-2 gap-x-6 gap-y-3">
                        ${viewRow('工序数', 'fee-view-process-count')}
                        ${viewRow('系统计算', 'fee-view-processing-fee')}
                        ${viewRow('手工调整', 'fee-view-manual-price')}
                        ${viewRow('最终加工费', 'fee-view-final-fee', true)}
                        ${viewRow('计算失败原因', 'fee-view-fail-reason')}
                        ${viewRow('备注', 'fee-view-remark')}
                    </div>
                </div>
                <div class="bg-[#111111] border border-[#262626]">
                    <div class="px-4 py-3 bg-[#0c0c0c] border-b border-[#181818] flex items-center gap-2">
                        <span class="w-0.5 h-3 bg-[#d32f2f] rounded-sm shadow-[0_0_8px_rgba(211,47,47,0.5)]"></span>
                        <h6 class="text-[10px] font-semibold text-[#d32f2f] tracking-wider uppercase">工序单价溯源</h6>
                    </div>
                    <div class="overflow-x-auto" id="feeViewProcessItems">
                        <div class="px-4 py-6 text-[11px] text-[#616161]">加载中..</div>
                    </div>
                </div>
                <!-- 材料 / 工艺快照：自动化着重显示-->
                <div class="bg-[#111111] border border-[#262626]">
                    <div class="px-4 py-3 bg-[#0c0c0c] border-b border-[#181818]">
                        <h6 class="text-[10px] font-semibold text-[#9e9e9e] tracking-wider uppercase">材料 / 工艺快照</h6>
                    </div>
                    <div class="p-4 space-y-4">
                        <div class="border border-[#d32f2f]/35 bg-[#0c0c0c] p-3"
                             style="box-shadow: 0 0 20px rgba(211,47,47,0.08), inset 0 1px 0 rgba(211,47,47,0.06);">
                            <div class="flex items-center gap-2 mb-2">
                                <span class="w-0.5 h-3 bg-[#d32f2f] rounded-sm shadow-[0_0_8px_rgba(211,47,47,0.5)]"></span>
                                <span class="text-[9px] font-semibold text-[#d32f2f] uppercase tracking-[0.12em]">关键工艺</span>
                            </div>
                            <div class="grid grid-cols-2 gap-x-6 gap-y-3">
                                ${viewRow('工艺方法', 'fee-view-process-method')}
                                ${viewRow('自动匹', 'fee-view-automation', true)}
                            </div>
                        </div>
                        <div class="grid grid-cols-2 gap-x-6 gap-y-3">
                            ${viewRow('材质', 'fee-view-material')}
                            ${viewRow('料厚', 'fee-view-thickness')}
                            ${viewRow('零件重量', 'fee-view-part-weight')}
                            ${viewRow('料片长', 'fee-view-sheet-length')}
                            ${viewRow('料片审', 'fee-view-sheet-width')}
                            ${viewRow('可制件数', 'fee-view-parts-per-sheet')}
                            ${viewRow('板料类型', 'fee-view-sheet-type')}
                            ${viewRow('模具类型', 'fee-view-die-type')}
                            ${viewRow('来源文件', 'fee-view-excel-filename')}
                            ${viewRow('零件备注', 'fee-view-part-remark')}
                        </div>
                    </div>
                </div>
                <div class="bg-[#111111] border border-[#262626]">
                    <div class="px-4 py-3 bg-[#0c0c0c] border-b border-[#181818]">
                        <h6 class="text-[10px] font-semibold text-[#9e9e9e] tracking-wider uppercase">审核 / 元数据</h6>
                    </div>
                    <div class="p-4 grid grid-cols-2 gap-x-6 gap-y-3">
                        ${viewRow('审核状态', 'fee-view-audit-status')}
                        ${viewRow('审核交', 'fee-view-audited-by')}
                        ${viewRow('审核时间', 'fee-view-audited-at')}
                        ${viewRow('审核意见', 'fee-view-audit-remark')}
                        ${viewRow('反审核人', 'fee-view-reverse-by')}
                        ${viewRow('反审核时间', 'fee-view-reverse-at')}
                        ${viewRow('反审核意览', 'fee-view-reverse-remark')}
                        ${viewRow('创建交', 'fee-view-created-by')}
                        ${viewRow('创建时间', 'fee-view-created-at')}
                        ${viewRow('修改交', 'fee-view-updated-by')}
                        ${viewRow('修改时间', 'fee-view-updated-at')}
                    </div>
                </div>
            </div>
            <div class="px-6 py-4 border-t border-[#262626] flex items-center justify-end gap-2 shrink-0 flex-wrap">
                <button type="button" id="feeViewDrawerEditBtn" class="inline-flex items-center gap-1.5 bg-[#d32f2f] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all">
                    ${window.svgIcon('pencil', 'w-3.5 h-3.5')}
                    编辑
                </button>
            </div>
        </div>
    `;
}

export function renderFeeRows(records) {
    if (!records || !Array.isArray(records) || records.length === 0) return '';
    return records.map((row) => {
        const approved = row.audit_status === 'approved';
        const isZero = Number(row.processing_fee) === 0;
        const failHint = row.calc_fail_reason
            ? `<span class="text-[#FF1E27]" title="${esc(row.calc_fail_reason)}">计算失败</span>`
            : (isZero
                ? '<span class="text-[#FF1E27]">计算价为 0</span>'
                : '<span class="text-[#555555]">—</span>');
        const cell = 'p-3 border-b border-[#17171C] font-mono text-[11px]';
        const muted = 'text-[#8E8E93]';
        const mutedDeep = 'text-[#6E6E73]';
        const zoneEnd = 'border-r border-[#22222A]';
        const finalCell = [
            'p-3 text-right font-mono font-bold tabular-nums text-[13px]',
            'text-[#FFFFFF] bg-[#14141C]',
            'border-b border-[#17171C] border-l border-r border-[#222230]',
            'group-hover:bg-[#1A1A26] transition-colors',
        ].join(' ');
        const canUpdate = typeof can === 'function' ? can('op:stamping-process-fee:update') : true;

        return `
        <tr class="group relative font-mono text-[11px] border-b border-[#17171C] hover:bg-gradient-to-r hover:from-[#FF1E27]/10 hover:via-[#121218] hover:to-transparent transition-all duration-150"
            data-id="${esc(row.id)}">
            <td class="p-0 w-0 relative">
                <div class="absolute left-0 top-0 bottom-0 w-[3px] bg-[#FF1E27] opacity-0 group-hover:opacity-100 transition-all"
                     style="box-shadow: 0 0 10px #FF1E27;"></div>
            </td>
            <td class="${cell} font-sans whitespace-nowrap">
                <div class="font-bold text-white text-[12px] group-hover:text-[#FF1E27] transition-colors">${esc(row.year)}</div>
                <div class="text-[#555555] text-[10px] mt-0.5">${esc(row.location)} · ${esc(row.stamping_supplier)}</div>
            </td>
            <td class="${cell} font-sans whitespace-nowrap">
                ${partNumberCell(row.part_number)}
            </td>
            <td class="${cell} ${muted} font-sans">${esc(row.part_name)}</td>
            <td class="${cell} ${muted} font-sans ${zoneEnd}">${esc(row.vehicle_model)} / ${esc(row.version)}</td>
            <td class="${cell} text-right ${muted} tabular-nums">${esc(row.process_count)}</td>
            <td class="${cell} text-right tabular-nums ${isZero ? 'text-[#FF1E27]' : muted}">${formatNum(row.processing_fee, 3)}</td>
            <td class="${cell} text-right ${muted} tabular-nums ${zoneEnd}">${formatNum(row.manual_unit_price, 3)}</td>
            <td class="${finalCell}">${formatNum(row.final_processing_fee, 3)}</td>
            <td class="${cell} ${muted} font-sans">${esc(row.material)}</td>
            <td class="${cell} text-right ${mutedDeep} tabular-nums">${formatNum(row.thickness, 4)}</td>
            <td class="${cell} text-right ${mutedDeep} tabular-nums">${formatNum(row.part_weight, 4)}</td>
            <td class="${cell} text-right ${mutedDeep} tabular-nums">${formatNum(row.sheet_length, 2)}</td>
            <td class="${cell} text-right ${mutedDeep} tabular-nums">${formatNum(row.sheet_width, 2)}</td>
            <td class="${cell} ${muted} font-sans">
                <div>${esc(row.die_type)}</div>
                <div class="text-[10px] text-[#555555] mt-0.5">${esc(row.process_method)}</div>
            </td>
            <td class="${cell} text-[10px] text-[#555555] max-w-[160px] truncate" title="${esc(row.remark || '')}">${esc(row.remark)}</td>
            <td class="${cell}">${auditBadge(row.audit_status)}</td>
            <td class="${cell}">${failHint}</td>
            <td class="px-1 py-2 text-center align-middle">
                <div class="inline-flex items-center justify-center gap-0.5 opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto focus-within:opacity-100 focus-within:pointer-events-auto transition-opacity duration-100">
                    <button type="button" class="view-btn inline-flex items-center justify-center w-7 h-7 rounded-sm text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620] transition-all" title="查看详情" aria-label="查看详情">${window.svgIcon('eye', 'w-3.5 h-3.5')}</button>
                    ${canUpdate ? `
                    <button type="button" class="edit-btn inline-flex items-center justify-center w-7 h-7 rounded-sm text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620] transition-all ${approved ? 'opacity-30 pointer-events-none' : ''}" title="${approved ? '已审核，不可编辑' : '编辑'}" aria-label="${approved ? '已审核，不可编辑' : '编辑'}">${window.svgIcon('pencil', 'w-3.5 h-3.5')}</button>` : ''}
                </div>
            </td>
            <td class="${cell} text-[9px] text-[#484848] whitespace-nowrap">${esc(row.created_by)}</td>
            <td class="${cell} text-[9px] text-[#3a3a3a] font-mono whitespace-nowrap">${esc(formatAuditDateTime(row.created_at))}</td>
            <td class="${cell} text-[9px] text-[#484848] whitespace-nowrap">${esc(row.updated_by)}</td>
            <td class="${cell} text-[9px] text-[#3a3a3a] font-mono whitespace-nowrap">${esc(formatAuditDateTime(row.updated_at))}</td>
        </tr>`;
    }).join('');
}

/** 用筛选汇总刷新HUD（零价/ 待审 / 已审均为全量筛选结果，非本页） */
export function updateFeeHud(total, summary) {
    const setText = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    };
    const data = summary && typeof summary === 'object' ? summary : {};

    setText('feeHudTotal', Number(total || 0).toLocaleString('zh-CN'));
    setText('feeHudZero', String(data.zero_count ?? 0));
    setText('feeHudMatchCount', `${Number(total || 0).toLocaleString('zh-CN')} 条`);
    setText('feeHudPending', String(data.pending_count ?? 0));
    setText('feeHudApproved', String(data.approved_count ?? 0));
}

/**
 * 同步战术胶囊：年度/ 基地 / 工厂 + 高级筛选已启用数量
 */
export function updateFeeFilterCapsules() {
    const year = document.getElementById('feeYearFilter')?.value || '';
    const location = document.getElementById('feeLocationFilter')?.value || '';
    const supplier = document.getElementById('feeSupplierFilter')?.value || '';
    const audit = document.getElementById('feeAuditStatusFilter')?.value || '';
    const part = document.getElementById('feePartNumberFilter')?.value.trim() || '';

    const activeCapsule = 'bg-[#1A1A22] border border-[#2A2A35] text-white px-2.5 py-1 rounded-md font-bold';
    const idleCapsule = 'bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md';

    const yearEl = document.getElementById('feeCapsuleYear');
    const locationEl = document.getElementById('feeCapsuleLocation');
    const supplierEl = document.getElementById('feeCapsuleSupplier');
    const countEl = document.getElementById('feeAdvancedFilterCount');

    if (yearEl) {
        yearEl.textContent = year ? `${year}年` : '全部年度';
        yearEl.className = year ? activeCapsule : idleCapsule;
    }
    if (locationEl) {
        locationEl.textContent = location || '全部基地';
        locationEl.className = location ? activeCapsule : idleCapsule;
    }
    if (supplierEl) {
        supplierEl.textContent = supplier || '全部工厂';
        supplierEl.className = supplier ? activeCapsule : idleCapsule;
    }

    const advancedActive = [year, location, supplier, audit, part].filter(Boolean).length;
    if (countEl) countEl.textContent = `(${advancedActive})`;
}

export function renderFeePagination(currentPage, totalPages) {
    if (totalPages <= 1) return '';
    let buttons = `
        <button type="button" data-fee-page="${currentPage - 1}" ${currentPage === 1 ? 'disabled' : ''}
                class="fee-page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] ${currentPage === 1 ? 'text-[#333333] cursor-not-allowed' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'} transition-all">
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path></svg>
        </button>`;
    const maxVisible = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);
    if (endPage - startPage < maxVisible - 1) startPage = Math.max(1, endPage - maxVisible + 1);
    if (startPage > 1) {
        buttons += `<button type="button" data-fee-page="1" class="fee-page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]">1</button>`;
        if (startPage > 2) buttons += `<span class="px-0.5 text-[#333333] text-[9px]">—</span>`;
    }
    for (let i = startPage; i <= endPage; i++) {
        const isActive = i === currentPage;
        buttons += `<button type="button" data-fee-page="${i}"
            class="fee-page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] ${isActive ? 'bg-[#FFFFFF] text-[#0a0a0a] font-bold' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'}">${i}</button>`;
    }
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) buttons += `<span class="px-0.5 text-[#333333] text-[9px]">—</span>`;
        buttons += `<button type="button" data-fee-page="${totalPages}" class="fee-page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]">${totalPages}</button>`;
    }
    buttons += `
        <button type="button" data-fee-page="${currentPage + 1}" ${currentPage === totalPages ? 'disabled' : ''}
                class="fee-page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] ${currentPage === totalPages ? 'text-[#333333] cursor-not-allowed' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'} transition-all">
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>
        </button>`;
    return buttons;
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

function viewRow(label, id, isHighlight = false) {
    return `<div class="min-w-0">
        <span class="block text-[9px] font-semibold text-[#555555] uppercase tracking-[0.1em] mb-1">${label}</span>
        <span id="${id}" class="block text-xs ${isHighlight ? 'text-[#d32f2f] font-mono' : 'text-[#cccccc]'} truncate"></span>
    </div>`;
}

/**
 * 企业口语短号：取零件号数字段术4 位（中BOM 一致）。
 * 例：554002087AA →2087（01006873AA →6873
 */
export function shortPartNumber(partNumber) {
    if (!partNumber) return null;
    const digits = String(partNumber).replace(/\D/g, '');
    if (digits.length < 4) return null;
    return digits.slice(-4);
}

/** 列表单元格：短号主角，完整号次要 */
function partNumberCell(partNumber) {
    const full = partNumber || '';
    const shortNo = shortPartNumber(full);
    if (shortNo) {
        return `
            <div class="text-[18px] font-mono font-bold tabular-nums text-white tracking-[0.14em] leading-none
                        drop-shadow-[0_0_16px_rgba(211,47,47,0.18)] group-hover:text-[#FF1E27] transition-colors"
                 title="${esc(full)}">${esc(shortNo)}</div>
            <div class="text-[10px] font-mono text-[#555555] tracking-wider mt-1">${esc(full)}</div>`;
    }
    return `<div class="text-xs font-mono text-[#8E8E93] tracking-wider" title="${esc(full)}">${esc(full) || '—'}</div>`;
}

/** 抽屉：短史+ 完整零件号*/
function partNumberViewBlock(prefix) {
    return `<div class="min-w-0">
        <span class="block text-[9px] font-semibold text-[#555555] uppercase tracking-[0.1em] mb-1">零件号</span>
        <span id="${prefix}-part-short"
              class="block text-xl font-mono font-bold tabular-nums text-white tracking-[0.14em] drop-shadow-[0_0_16px_rgba(211,47,47,0.18)]"></span>
        <span id="${prefix}-part-number" class="block text-[11px] font-mono text-[#616161] tracking-wider mt-0.5 truncate"></span>
    </div>`;
}

function auditBadge(status) {
    const map = {
        pending: 'bg-[#1C1C22] text-[#8E8E93] border border-[#2A2A32]',
        approved: 'bg-[#1C1C22] text-[#8E8E93] border border-[#2A2A32]',
        rejected: 'bg-[#1C1C22] text-[#8E8E93] border border-[#2A2A32]',
    };
    const label = { pending: '待审', approved: '已通过', rejected: '已驳回 }[status] || status || '-';
    const cls = map[status] || 'bg-[#1C1C22] text-[#8E8E93] border border-[#2A2A32]';
    return `<span class="inline-flex items-center px-2 py-0.5 text-[10px] font-sans rounded-sm ${cls}">${esc(label)}</span>`;
}

function formatAuditDateTime(value) {
    if (!value) return '-';
    const text = String(value);
    if (text.length >= 19) return text.slice(0, 19).replace('T', ' ');
    return text;
}

function formatNum(value, digits = 2) {
    const numeric = Number(value);
    if (value === null || value === undefined || Number.isNaN(numeric)) return '-';
    return numeric.toLocaleString('zh-CN', {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
    });
}
