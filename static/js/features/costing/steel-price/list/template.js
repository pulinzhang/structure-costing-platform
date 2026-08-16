/**
 * Steel Price List Template
 * 钢材价格计算结果浏览 —Brabus Carbon & Precision Dark
 */

import { pageSizeSelectHtml } from '../../../../page-size.js?v=2';

export function steelPriceListTemplate() {
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
                                    <span id="steelPriceHudTotal">—</span>
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
                                    ￥<span id="steelPriceHudAvg">—</span>
                                </div>
                                <div class="text-[9px] font-mono text-[#FF1E27]/60 mt-1 flex justify-between">
                                    <span>系统自动计算</span>
                                    <span id="steelPriceHudSkuCount">— 条</span>
                                </div>
                            </div>
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3 backdrop-blur-sm"
                                 style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);">
                                <div class="text-[#555555] text-[10px] tracking-wider">待审</div>
                                <div class="text-[18px] font-bold text-[#FFFFFF] mt-1 tabular-nums">
                                    <span id="steelPriceHudPending">—</span>
                                    <span class="text-[10px] text-[#555555] ml-1">条</span>
                                </div>
                            </div>
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3 backdrop-blur-sm"
                                 style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);">
                                <div class="text-[#555555] text-[10px] tracking-wider">已审</div>
                                <div class="text-[18px] font-bold text-[#FFFFFF] mt-1 tabular-nums">
                                    <span id="steelPriceHudApproved">—</span>
                                    <span class="text-[10px] text-[#555555] ml-1">条</span>
                                </div>
                            </div>
                        </div>
                        <div class="flex items-center gap-2 shrink-0 flex-wrap justify-end">
                            <button id="steelPriceBatchApproveButton"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] hover:bg-[#FF1E27]/10 hover:shadow-[0_0_12px_rgba(255,30,39,0.2)] transition-all duration-200">
                                ${window.svgIcon('check-circle', 'w-3 h-3')}
                                批量审核
                            </button>
                            <button id="steelPriceBatchReverseButton"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] hover:bg-[#FF1E27]/10 hover:shadow-[0_0_12px_rgba(255,30,39,0.2)] transition-all duration-200">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                批量反审核                            </button>
                            <button id="steelPriceBatchDeleteButton"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#c62828]/60 hover:text-[#ef5350] hover:bg-[#c62828]/15 hover:shadow-[0_0_12px_rgba(198,40,40,0.2)] transition-all duration-200">
                                ${window.svgIcon('trash', 'w-3 h-3')}
                                批量删除
                            </button>
                            <button id="steelPriceExportButton"
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
                                <span id="steelCapsulePeriod" class="bg-[#1A1A22] border border-[#2A2A35] text-white px-2.5 py-1 rounded-md font-bold">全部期间</span>
                                <span id="steelCapsuleLocation" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部基地</span>
                                <span id="steelCapsuleMill" class="bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md">全部钢厂</span>
                            </div>
                        </div>
                        <div class="flex items-center gap-3 shrink-0">
                            <button type="button" id="steelPriceToggleAdvancedFilter"
                                    class="text-[#6E6E73] hover:text-white transition-colors flex items-center gap-1.5 text-[11px]">
                                <span id="steelPriceAdvancedFilterLabel">展开高级筛选</span>
                                <span id="steelPriceAdvancedFilterCount" class="text-[#555555]">(0)</span>
                            </button>
                            <button type="button" id="steelPriceSearchButton"
                                    class="inline-flex items-center gap-1.5 h-7 px-3 text-[11px] font-semibold rounded-sm text-[#c8c8c8] border border-[#8a2020] transition-all duration-200 hover:text-white"
                                    style="background: linear-gradient(180deg, #3d1515 0%, #2d0f0f 100%); border-color: #6b1a1a; box-shadow: 0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(211,47,47,0.1), 0 0 12px rgba(198,40,40,0.08);">
                                ${window.svgIcon('search', 'w-3 h-3')}
                                查询
                            </button>
                        </div>
                    </div>

                    <!-- 高级筛选面板（默认折叠）-->
                    <div id="steelPriceAdvancedFilterPanel" class="hidden mt-3 pt-3 border-t border-[#1A1A22]">
                        <div class="flex items-end gap-3 flex-wrap">
                            ${filterSelect('steelPriceYear', '年度')}
                            ${filterSelect('steelPriceMonth', '月份')}
                            ${filterSelect('steelPriceLocation', '基地')}
                            ${filterSelect('steelPriceCategory', '钢种')}
                            ${filterInput('steelPriceGrade', '牌号', '输入牌号（模糊）')}
                            ${filterSelect('steelPriceMill', '钢厂')}
                            <button id="steelPriceResetFilterButton"
                                    class="inline-flex items-center gap-1.5 h-8 px-3 text-[11px] font-medium rounded-md bg-transparent text-[#6E6E73] border border-[#2A2A35] hover:bg-[#FF1E27]/10 hover:border-[#FF1E27]/50 hover:text-[#FF1E27] transition-all duration-200">
                                ${window.svgIcon('refresh', 'w-3 h-3')}
                                重置
                            </button>
                        </div>
                    </div>
                </div>

                <div class="overflow-x-auto brabus-bg-grid">
                    <table class="w-full min-w-[2900px] bg-transparent">
                        <thead>
                            <tr class="border-b border-[#17171C] bg-[#0B0B0D]/95">
                                <th class="p-0 w-0"></th>
                                <th class="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">核价维度</th>
                                <th class="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">钢厂</th>
                                <th class="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">钢种</th>
                                <th class="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-[#A1A1A6] whitespace-nowrap">牌号</th>
                                <th class="px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-[0.18em] text-[#A1A1A6] whitespace-nowrap">厚度</th>
                                <th class="px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap border-r border-[#22222A]">宽度</th>
                                <th class="px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">基础价</th>
                                <th class="px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">厚度加价</th>
                                <th class="px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">宽度加价</th>
                                <th class="px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap border-r border-[#22222A]">加工费</th>
                                <th class="px-3 py-3 text-right text-[10px] font-bold uppercase tracking-[0.18em] text-[#FFFFFF]/70 whitespace-nowrap bg-[#14141C] border-x border-[#222230]">最终价/启</th>
                                <th class="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">基价溯源</th>
                                <th class="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">厚度溯源</th>
                                <th class="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">宽度溯源</th>
                                <th class="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">匹配</th>
                                <th class="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6E6E73] whitespace-nowrap">审核</th>
                                <th class="p-0 w-9" aria-label="操作"></th>
                                <th class="px-3 py-3 text-left text-[9px] font-normal tracking-[0.08em] text-[#3a3a3a] whitespace-nowrap">创建人</th>
                                <th class="px-3 py-3 text-left text-[9px] font-normal tracking-[0.08em] text-[#3a3a3a] whitespace-nowrap">创建时间</th>
                                <th class="px-3 py-3 text-left text-[9px] font-normal tracking-[0.08em] text-[#3a3a3a] whitespace-nowrap">最后修改人</th>
                                <th class="px-3 py-3 text-left text-[9px] font-normal tracking-[0.08em] text-[#3a3a3a] whitespace-nowrap">最后修改时间</th>
                            </tr>
                        </thead>
                        <tbody id="steelPriceTableBody" class="bg-transparent"></tbody>
                    </table>
                </div>

                <div class="flex items-center justify-between px-5 py-2.5 border-t border-[#14141A] bg-[#0A0A0E]">
                    <div class="flex items-center gap-3 min-w-0">
                        <span id="steelPriceTotal" class="text-[10px] font-mono text-[#555555]"></span>
                        ${pageSizeSelectHtml('steelPricePageSize')}
                    </div>
                    <div class="flex items-center gap-0.5" id="steelPricePagination"></div>
                </div>

                <div id="steelPriceEmpty" class="hidden flex flex-col items-center justify-center py-14">
                    <div class="w-10 h-10 flex items-center justify-center mb-3 rounded-md bg-[#121218] border border-[#2A2A35]">
                        ${window.svgIcon('clipboard-list', 'w-4 h-4 text-[#555555]')}
                    </div>
                    <h5 class="text-[11px] font-medium text-[#8E8E93] mb-1">暂无钢材价格数据</h5>
                    <p class="text-[10px] text-[#555555]">数据由系统计算写入，或通过 Excel 导入</p>
                </div>

                <div id="steelPriceLoading" class="hidden flex items-center justify-center py-14">
                    <div class="w-5 h-5 border-2 border-[#2A2A35] border-t-[#FF1E27] rounded-full animate-spin"
                         style="box-shadow: 0 0 12px rgba(255,30,39,0.35);"></div>
                </div>
            </div>
        </div>

        <!-- 新增 / 编辑抽屉 -->
        <div class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm transition-opacity duration-300"
             id="editDrawerBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[760px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="editDrawer" style="display:none; max-height: 100vh; box-shadow: -20px 0 60px rgba(0,0,0,0.95);">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0"
                 style="background: linear-gradient(180deg, #1f1f1f 0%, #1a1a1a 100%); border-bottom: 1px solid #333333;">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] flex items-center gap-2.5 uppercase">
                    <span style="width:3px;height:14px;background:#d32f2f;border-radius:1px;display:inline-block;box-shadow: 0 0 8px rgba(211,47,47,0.5);"></span>
                    <span id="editDrawerTitle">编辑钢材价格</span>
                </h5>
                <button type="button" id="closeEditDrawer"
                        class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>

            <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain" id="editDrawerContent">
                <form id="editForm" class="p-6 space-y-5">
                    <input type="hidden" id="editRecordId" value="">

                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-2 block">业务主键</label>
                        <div class="grid grid-cols-4 gap-3">
                            ${editNumber('editYear', '年度', '2000', '2100', '2026')}
                            ${editNumber('editMonth', '月份', '1', '12', '1')}
                            ${editText('editLocation', '基地', '如 芜湖基地')}
                            ${editText('editSteelMill', '钢厂', '如 马钢')}
                            ${editText('editCategoryName', '钢种', '如 冷轧')}
                            ${editText('editGrade', '牌号', '如 DC01')}
                            ${editNumber('editThickness', '厚度', '0', null, '0.8', '0.0001')}
                            ${editNumber('editWidth', '宽度', '0', null, '1250', '0.0001')}
                        </div>
                    </div>

                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-2 block">价格分项</label>
                        <div class="grid grid-cols-3 gap-3">
                            ${editNumber('editBasePrice', '基础价base_price', '0', null, '全', '0.0001')}
                            ${editNumber('editThicknessAdjustment', '厚度加价 thickness_adjustment', null, null, '全', '0.0001')}
                            ${editNumber('editWidthAdjustment', '宽度加价 width_adjustment', null, null, '全', '0.0001')}
                            ${editNumber('editZincAdjustment', '锌层加价 zinc_adjustment', null, null, '全', '0.0001')}
                            ${editNumber('editProcessingFee', '加工费processing_fee', '0', null, '全', '0.0001')}
                            ${editNumber('editOtherAdjustment', '其他调整 other_adjustment', null, null, '全', '0.0001')}
                        </div>
                        <p class="text-[10px] text-[#616161] mt-2">最终价由服务端按分项自动汇总，无需手工填写。</p>
                    </div>

                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">规格 / 备注</label>
                        <div class="grid grid-cols-2 gap-3">
                            ${editText('editSpec', '规格（可选）', '如 1.00*1250.00', false)}
                            <div>
                                <label class="text-[10px] text-[#777777] mb-1 block">备注</label>
                                <textarea id="editRemark" rows="2" maxlength="500"
                                          class="w-full px-3 py-2 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded resize-none"
                                          placeholder="人工备注"></textarea>
                            </div>
                        </div>
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

        <!-- 查看详情抽屉 -->
        <div class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm transition-opacity duration-300"
             id="viewDrawerBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[560px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="viewDrawer" style="display:none; max-height: 100vh; box-shadow: -20px 0 60px rgba(0,0,0,0.95);">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0"
                 style="background: linear-gradient(180deg, #1f1f1f 0%, #1a1a1a 100%); border-bottom: 1px solid #333333;">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] flex items-center gap-2.5 uppercase">
                    <span style="width:3px;height:14px;background:#d32f2f;border-radius:1px;display:inline-block;box-shadow: 0 0 8px rgba(211,47,47,0.5);"></span>
                    价格详情
                </h5>
                <button type="button" id="closeViewDrawer"
                        class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>

            <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain p-6 space-y-4" id="viewDrawerContent">
                <div class="bg-[#111111] border border-[#262626]">
                    <div class="px-4 py-3 bg-[#0c0c0c] border-b border-[#181818]">
                        <h6 class="text-[10px] font-semibold text-[#9e9e9e] tracking-wider uppercase">业务主键</h6>
                    </div>
                    <div class="p-4 grid grid-cols-2 gap-x-6 gap-y-3">
                        ${viewRow('年度', 'view-year')}
                        ${viewRow('月份', 'view-month')}
                        ${viewRow('基地', 'view-location')}
                        ${viewRow('钢厂', 'view-steel-mill')}
                        ${viewRow('钢种', 'view-category-name')}
                        ${viewRow('牌号', 'view-grade')}
                        ${viewRow('厚度', 'view-thickness')}
                        ${viewRow('宽度', 'view-width')}
                        ${viewRow('规格', 'view-spec')}
                    </div>
                </div>

                <div class="bg-[#111111] border border-[#262626]">
                    <div class="px-4 py-3 bg-[#0c0c0c] border-b border-[#181818]">
                        <h6 class="text-[10px] font-semibold text-[#9e9e9e] tracking-wider uppercase">价格分项（对齐VO）</h6>
                    </div>
                    <div class="p-4 grid grid-cols-2 gap-x-6 gap-y-3">
                        ${viewRow('基础价base_price', 'view-base-price')}
                        ${viewRow('厚度加价 thickness_adjustment', 'view-thickness-adjustment')}
                        ${viewRow('宽度加价 width_adjustment', 'view-width-adjustment')}
                        ${viewRow('锌层加价 zinc_adjustment', 'view-zinc-adjustment')}
                        ${viewRow('加工费processing_fee', 'view-processing-fee')}
                        ${viewRow('其他调整 other_adjustment', 'view-other-adjustment')}
                        ${viewRow('最终价 final_price_per_ton', 'view-final-price', true)}
                    </div>
                </div>

                <div class="bg-[#111111] border border-[#262626]">
                    <div class="px-4 py-3 bg-[#0c0c0c] border-b border-[#181818]">
                        <h6 class="text-[10px] font-semibold text-[#9e9e9e] tracking-wider uppercase">溯源信息（Excel / 政策 ID）</h6>
                    </div>
                    <div class="p-4 space-y-3 text-[11px] text-[#9e9e9e]">
                        <div id="view-trace-base" class="leading-relaxed"></div>
                        <div id="view-trace-thickness" class="leading-relaxed"></div>
                        <div id="view-trace-width" class="leading-relaxed"></div>
                        <div id="view-trace-zinc" class="leading-relaxed"></div>
                    </div>
                </div>

                <div class="bg-[#111111] border border-[#262626]">
                    <div class="px-4 py-3 bg-[#0c0c0c] border-b border-[#181818]">
                        <h6 class="text-[10px] font-semibold text-[#9e9e9e] tracking-wider uppercase">审核 / 计算</h6>
                    </div>
                    <div class="p-4 grid grid-cols-2 gap-x-6 gap-y-3">
                        ${viewRow('审核状态', 'view-audit-status')}
                        ${viewRow('审核人', 'view-audited-by')}
                        ${viewRow('审核时间', 'view-audited-at')}
                        ${viewRow('审核意见', 'view-audit-remark')}
                        ${viewRow('反审核人', 'view-reverse-audited-by')}
                        ${viewRow('反审核时间', 'view-reverse-audited-at')}
                        ${viewRow('反审核原因', 'view-reverse-audit-remark')}
                        ${viewRow('匹配状态', 'view-match-status')}
                        ${viewRow('计算批次', 'view-calc-batch-id')}
                        ${viewRow('计算时间', 'view-calculated-at')}
                    </div>
                </div>
            </div>

            <div class="px-6 py-4 border-t border-[#262626] flex items-center justify-end gap-2 shrink-0 flex-wrap">
                <button type="button" id="viewDrawerApproveBtn" class="hidden inline-flex items-center gap-1.5 bg-[#2e7d32] text-white px-3 py-2 text-[11px] font-semibold rounded hover:bg-[#1b5e20] transition-all">通过</button>
                <button type="button" id="viewDrawerRejectBtn" class="hidden inline-flex items-center gap-1.5 bg-transparent text-[#ffb74d] border border-[#f57f17]/40 px-3 py-2 text-[11px] font-medium rounded hover:border-[#f57f17] transition-all">驳回</button>
                <button type="button" id="viewDrawerReverseBtn" class="hidden inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-3 py-2 text-[11px] font-medium rounded hover:border-[#d32f2f] hover:text-[#d32f2f] transition-all">反审核</button>
                <button type="button" id="viewDrawerEditBtn" class="inline-flex items-center gap-1.5 bg-[#d32f2f] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all">
                    ${window.svgIcon('pencil', 'w-3.5 h-3.5')}
                    编辑
                </button>
            </div>
        </div>

        <!-- 删除确认抽屉 -->
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
            <div class="flex-1 min-h-0 overflow-y-auto p-6">
                <input type="hidden" id="deleteRecordId" value="">
                <p class="text-[12px] text-[#9e9e9e] mb-3">确定要删除这条价格记录吗（</p>
                <div class="bg-[#0c0c0c] border border-[#1a1a1a] rounded p-3 text-[11px] text-[#616161]" id="deleteSummary"></div>
                <p class="text-[11px] text-[#c62828] mt-3">已审核通过的记录不可删除，须先反审核。</p>
            </div>
            <div class="px-6 py-4 border-t border-[#262626] flex items-center justify-end gap-2 shrink-0">
                <button type="button" id="cancelDeleteBtn" class="inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-4 py-2 text-[11px] font-medium rounded hover:border-[#9e9e9e] hover:text-white transition-all">取消</button>
                <button type="button" id="confirmDeleteBtn" class="inline-flex items-center gap-1.5 bg-[#c62828] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all">
                    ${window.svgIcon('trash', 'w-3.5 h-3.5')}
                    删除
                </button>
            </div>
        </div>

        <!-- 批量审核 / 反审核抽屉-->
        <div class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm transition-opacity duration-300"
             id="batchAuditDrawerBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[420px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="batchAuditDrawer" style="display:none; max-height: 100vh; box-shadow: -20px 0 60px rgba(0,0,0,0.95);">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0"
                 style="background: linear-gradient(180deg, #1f1f1f 0%, #1a1a1a 100%); border-bottom: 1px solid #333333;">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] flex items-center gap-2.5 uppercase">
                    <span style="width:3px;height:14px;background:#d32f2f;border-radius:1px;display:inline-block;box-shadow: 0 0 8px rgba(211,47,47,0.5);"></span>
                    <span id="batchAuditDrawerTitle">批量审核</span>
                </h5>
                <button type="button" id="closeBatchAuditDrawer"
                        class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-6 space-y-4">
                <input type="hidden" id="batchAuditMode" value="approve">
                <div class="bg-[#0c0c0c] border border-[#1a1a1a] rounded p-3 text-[11px] text-[#9e9e9e]" id="batchAuditFilterSummary"></div>
                <p id="batchAuditHint" class="text-[11px] text-[#616161]">仅按年度、月份、基地批量处理；三者必须同时选择。</p>
                <div>
                    <label class="text-[10px] text-[#777777] mb-1 block" id="batchAuditOperatorLabel">操作人</label>
                    <div id="batchAuditOperatorDisplay"
                         class="w-full h-9 px-3 flex items-center text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] rounded">
                        —                    </div>
                    <p class="text-[10px] text-[#555555] mt-1">取自当前登录用户，无需填写</p>
                </div>
                <div>
                    <label class="text-[10px] text-[#777777] mb-1 block" id="batchAuditRemarkLabel">审核意见</label>
                    <textarea id="batchAuditRemark" rows="4" maxlength="500"
                              class="w-full px-3 py-2 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded resize-none"
                              placeholder="可选填写审核意见"></textarea>
                </div>
            </div>
            <div class="px-6 py-4 border-t border-[#262626] flex items-center justify-end gap-2 shrink-0">
                <button type="button" id="cancelBatchAuditBtn" class="inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-4 py-2 text-[11px] font-medium rounded hover:border-[#9e9e9e] hover:text-white transition-all">取消</button>
                <button type="button" id="confirmBatchAuditBtn" class="inline-flex items-center gap-1.5 bg-[#d32f2f] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all">
                    确认提交
                </button>
            </div>
        </div>
    `;
}

export function renderSteelPriceRows(records) {
    if (!records || !Array.isArray(records) || records.length === 0) return '';
    return records.map((record) => {
        const approved = record.audit_status === 'approved';
        const period = `${esc(record.year)}-${esc(String(record.month).padStart(2, '0'))}`;
        const mill = esc(record.steel_mill) || '—';
        const location = esc(record.location) || '—';
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
        return `
        <tr class="group relative font-mono text-[11px] border-b border-[#17171C] hover:bg-gradient-to-r hover:from-[#FF1E27]/10 hover:via-[#121218] hover:to-transparent transition-all duration-150"
            data-id="${esc(record.id)}">
            <td class="p-0 w-0 relative">
                <div class="absolute left-0 top-0 bottom-0 w-[3px] bg-[#FF1E27] opacity-0 group-hover:opacity-100 transition-all"
                     style="box-shadow: 0 0 10px #FF1E27;"></div>
            </td>
            <td class="${cell} font-sans whitespace-nowrap">
                <div class="font-bold text-white text-[12px] group-hover:text-[#FF1E27] transition-colors">${period}</div>
                <div class="text-[#555555] text-[10px] mt-0.5">${location} · ${mill}</div>
            </td>
            <td class="${cell} ${muted} font-sans text-[11px]">${mill}</td>
            <td class="${cell} ${muted} font-sans text-[11px]">${esc(record.category_name)}</td>
            <td class="${cell} font-sans">
                <span class="inline-block bg-[#181820] text-white font-bold border border-[#2E2E3A] px-2 py-1 rounded text-[11px]"
                      style="box-shadow: 0 1px 2px rgba(0,0,0,0.4);">${esc(record.grade)}</span>
            </td>
            <td class="${cell} text-right font-bold text-white text-[13px] tabular-nums">${formatPrice(record.thickness, 2)}</td>
            <td class="${cell} text-right ${mutedDeep} tabular-nums ${zoneEnd}">${formatWidth(record.width)}</td>
            <td class="${cell} text-right ${muted} tabular-nums">${formatPrice(record.base_price, 2)}</td>
            <td class="${cell} text-right tabular-nums">${formatAdjustment(record.thickness_adjustment)}</td>
            <td class="${cell} text-right tabular-nums">${formatAdjustment(record.width_adjustment)}</td>
            <td class="${cell} text-right ${muted} tabular-nums ${zoneEnd}">${formatPriceOrDash(record.processing_fee)}</td>
            <td class="${finalCell}">${formatPrice(record.final_price_per_ton, 2)}</td>
            <td class="${cell} text-[10px] text-[#555555] max-w-[220px]">${formatTraceCell('base', record)}</td>
            <td class="${cell} text-[10px] text-[#555555] max-w-[220px]">${formatTraceCell('thickness', record)}</td>
            <td class="${cell} text-[10px] text-[#555555] max-w-[220px]">${formatTraceCell('width', record)}</td>
            <td class="${cell} ${muted} text-[11px]">${esc(record.match_status)}</td>
            <td class="${cell}">${auditBadge(record.audit_status)}</td>
            <td class="px-1 py-2 text-center align-middle">
                <div class="inline-flex items-center justify-center gap-0.5 opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto focus-within:opacity-100 focus-within:pointer-events-auto transition-opacity duration-100">
                    <button type="button" class="view-btn inline-flex items-center justify-center w-7 h-7 rounded-sm text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620] transition-all" title="查看详情" aria-label="查看详情">${window.svgIcon('eye', 'w-3.5 h-3.5')}</button>
                    ${(typeof can === 'function' ? can('op:steel-price-list:update') : true) ? `
                    <button type="button" class="edit-btn inline-flex items-center justify-center w-7 h-7 rounded-sm text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620] transition-all ${approved ? 'opacity-30 pointer-events-none' : ''}" title="${approved ? '已审核，不可编辑' : '编辑'}" aria-label="${approved ? '已审核，不可编辑' : '编辑'}">${window.svgIcon('pencil', 'w-3.5 h-3.5')}</button>` : ''}
                    ${(typeof can === 'function' ? can('op:steel-price-list:delete') : true) ? `
                    <button type="button" class="delete-btn inline-flex items-center justify-center w-7 h-7 rounded-sm text-[#555555] hover:text-[#ef5350] hover:bg-[#161620] transition-all ${approved ? 'opacity-30 pointer-events-none' : ''}" title="${approved ? '已审核，不可删除' : '删除'}" aria-label="${approved ? '已审核，不可删除' : '删除'}">${window.svgIcon('trash', 'w-3.5 h-3.5')}</button>` : ''}
                </div>
            </td>
            <td class="${cell} text-[9px] text-[#484848] whitespace-nowrap">${esc(record.created_by)}</td>
            <td class="${cell} text-[9px] text-[#3a3a3a] font-mono whitespace-nowrap">${esc(formatAuditDateTime(record.created_at))}</td>
            <td class="${cell} text-[9px] text-[#484848] whitespace-nowrap">${esc(record.updated_by)}</td>
            <td class="${cell} text-[9px] text-[#3a3a3a] font-mono whitespace-nowrap">${esc(formatAuditDateTime(record.updated_at))}</td>
        </tr>`;
    }).join('');
}

/** 用筛选汇总刷新HUD（均价/ 待审 / 已审均为全量筛选结果，非本页） */
export function updateSteelPriceHud(total, summary) {
    const setText = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    };
    const data = summary && typeof summary === 'object' ? summary : {};
    const avg = data.avg_final_price;
    const avgFixed = formatDecimalFixed(avg, 2, { allowNegative: true });

    setText('steelPriceHudTotal', Number(total || 0).toLocaleString('zh-CN'));
    setText(
        'steelPriceHudAvg',
        avgFixed == null ? '—' : withThousandsSep(avgFixed),
    );
    setText('steelPriceHudSkuCount', `${Number(total || 0).toLocaleString('zh-CN')} 条`);
    setText('steelPriceHudPending', String(data.pending_count ?? 0));
    setText('steelPriceHudApproved', String(data.approved_count ?? 0));
}

/**
 * 同步战术胶囊：期间/ 基地 / 钢厂 + 高级筛选已启用数量
 */
export function updateActiveFilterCapsules() {
    const year = document.getElementById('steelPriceYear')?.value || '';
    const month = document.getElementById('steelPriceMonth')?.value || '';
    const location = document.getElementById('steelPriceLocation')?.value || '';
    const category = document.getElementById('steelPriceCategory')?.value || '';
    const grade = document.getElementById('steelPriceGrade')?.value.trim() || '';
    const mill = document.getElementById('steelPriceMill')?.value || '';

    const periodEl = document.getElementById('steelCapsulePeriod');
    const locationEl = document.getElementById('steelCapsuleLocation');
    const millEl = document.getElementById('steelCapsuleMill');
    const countEl = document.getElementById('steelPriceAdvancedFilterCount');

    const activeCapsule = 'bg-[#1A1A22] border border-[#2A2A35] text-white px-2.5 py-1 rounded-md font-bold';
    const idleCapsule = 'bg-[#1A1A22] border border-[#2A2A35] text-[#8E8E93] px-2.5 py-1 rounded-md';

    if (periodEl) {
        if (year && month) {
            periodEl.textContent = `${year}-${String(month).padStart(2, '0')}`;
            periodEl.className = activeCapsule;
        } else if (year) {
            periodEl.textContent = `${year}年`;
            periodEl.className = activeCapsule;
        } else if (month) {
            periodEl.textContent = `${month}月`;
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

    if (millEl) {
        millEl.textContent = mill || '全部钢厂';
        millEl.className = mill ? activeCapsule : idleCapsule;
    }

    const advancedActive = [category, grade, mill, year, month, location].filter(Boolean).length;
    if (countEl) countEl.textContent = `(${advancedActive})`;
}

/**
 * 列表溯源摘要，字段对齐SteelPriceResponse VO。 * base: base_price_id / base_excel_filename / base_sheet_name / base_excel_row / base_excel_col
 * thickness|width|zinc: *_policy_id / *_ladder_item_id / *_excel_filename / *_sheet_name / *_excel_row / *_excel_col
 */
function formatTraceCell(prefix, record) {
    const filename = record[`${prefix}_excel_filename`];
    const sheet = record[`${prefix}_sheet_name`];
    const row = record[`${prefix}_excel_row`];
    const col = record[`${prefix}_excel_col`];
    const refId = prefix === 'base'
        ? record.base_price_id
        : record[`${prefix}_policy_id`];
    const ladderId = prefix === 'base' ? null : record[`${prefix}_ladder_item_id`];

    if (filename == null && refId == null && ladderId == null && row == null && col == null) {
        return '<span class="text-[#555555]">—</span>';
    }

    const idPart = prefix === 'base'
        ? (refId != null ? `id=${esc(refId)}` : '')
        : [
            refId != null ? `policy=${esc(refId)}` : '',
            ladderId != null ? `item=${esc(ladderId)}` : '',
        ].filter(Boolean).join(' ');

    const excelPart = [
        filename || '',
        sheet || '',
        row != null || col != null ? `R${row ?? '-'}C${col ?? '-'}` : '',
    ].filter(Boolean).join(' / ');

    const text = [idPart, excelPart].filter(Boolean).join(' · ') || '—';
    return `<span class="block truncate" title="${esc(text)}">${text}</span>`;
}

export function renderSteelPricePagination(currentPage, totalPages) {
    if (totalPages <= 1) return '';
    let buttons = `
        <button class="steel-price-page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] ${currentPage === 1 ? 'text-[#333333] cursor-not-allowed' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'} transition-all"
                data-page="${currentPage - 1}" ${currentPage === 1 ? 'disabled' : ''}>
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path></svg>
        </button>`;
    const maxVisible = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);
    if (endPage - startPage < maxVisible - 1) startPage = Math.max(1, endPage - maxVisible + 1);
    if (startPage > 1) {
        buttons += `<button class="steel-price-page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]" data-page="1">1</button>`;
        if (startPage > 2) buttons += `<span class="px-0.5 text-[#333333] text-[9px]">—</span>`;
    }
    for (let i = startPage; i <= endPage; i++) {
        const isActive = i === currentPage;
        buttons += `<button class="steel-price-page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] ${isActive ? 'bg-[#FFFFFF] text-[#0a0a0a] font-bold' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'}" data-page="${i}">${i}</button>`;
    }
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) buttons += `<span class="px-0.5 text-[#333333] text-[9px]">—</span>`;
        buttons += `<button class="steel-price-page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]" data-page="${totalPages}">${totalPages}</button>`;
    }
    buttons += `
        <button class="steel-price-page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] ${currentPage === totalPages ? 'text-[#333333] cursor-not-allowed' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'}"
                data-page="${currentPage + 1}" ${currentPage === totalPages ? 'disabled' : ''}>
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

function editText(id, label, placeholder, required = true) {
    return `<div>
        <label class="text-[10px] text-[#777777] mb-1 block">${label}${required ? ' <span class="text-[#d32f2f]">*</span>' : ''}</label>
        <input type="text" id="${id}" ${required ? 'required' : ''} maxlength="100"
               class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] rounded"
               placeholder="${placeholder}">
    </div>`;
}

function editNumber(id, label, min, max, placeholder, step = '1') {
    const minAttr = min != null ? `min="${min}"` : '';
    const maxAttr = max != null ? `max="${max}"` : '';
    return `<div>
        <label class="text-[10px] text-[#777777] mb-1 block">${label} <span class="text-[#d32f2f]">*</span></label>
        <input type="number" id="${id}" ${minAttr} ${maxAttr} step="${step}" required
               class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] rounded"
               placeholder="${placeholder || ''}">
    </div>`;
}

function viewRow(label, id, isHighlight = false) {
    return `<div class="min-w-0">
        <span class="block text-[9px] font-semibold text-[#555555] uppercase tracking-[0.1em] mb-1">${label}</span>
        <span id="${id}" class="block text-xs ${isHighlight ? 'text-[#d32f2f] font-mono' : 'text-[#cccccc]'} truncate"></span>
    </div>`;
}

function auditBadge(status) {
    const map = {
        pending: 'bg-[#1C1C22] text-[#8E8E93] border border-[#2A2A32]',
        approved: 'bg-[#1C1C22] text-[#8E8E93] border border-[#2A2A32]',
        rejected: 'bg-[#1C1C22] text-[#8E8E93] border border-[#2A2A32]',
    };
    const label = { pending: '待审', approved: '已通过', rejected: '已驳回' }[status] || status || '-';
    const cls = map[status] || 'bg-[#1C1C22] text-[#8E8E93] border border-[#2A2A32]';
    return `<span class="inline-flex items-center px-2 py-0.5 text-[10px] font-sans rounded-sm ${cls}">${esc(label)}</span>`;
}

function formatAuditDateTime(value) {
    if (!value) return '-';
    const text = String(value);
    if (text.length >= 19) return text.slice(0, 19).replace('T', ' ');
    return text;
}

function formatPrice(value, digits = 2) {
    const fixed = formatDecimalFixed(value, digits, { allowNegative: true });
    return fixed == null ? '-' : withThousandsSep(fixed);
}

/** 加工费：为 0 时显示 -- */
function formatPriceOrDash(value, digits = 2) {
    const fixed = formatDecimalFixed(value, digits, { allowNegative: true });
    if (fixed == null || compareDecimalStrings(fixed, '0', digits) === 0) {
        return '--';
    }
    return withThousandsSep(fixed);
}

/**
 * 厚度/宽度加价（单色冷灰）
 * 有值→#A1A1A6 带正负号；无值→#444 -
 */
function formatAdjustment(value, digits = 2) {
    const fixed = formatDecimalFixed(value, digits, { allowNegative: true });
    if (fixed == null || compareDecimalStrings(fixed, '0', digits) === 0) {
        return '<span class="text-[#444444]">-</span>';
    }
    const absText = withThousandsSep(fixed.startsWith('-') ? fixed.slice(1) : fixed);
    const signed = fixed.startsWith('-') ? `-${absText}` : `+${absText}`;
    return `<span class="text-[#A1A1A6]">${signed}</span>`;
}

/** 宽度：整数、无千分位 */
function formatWidth(value) {
    return formatDecimalFixed(value, 0) ?? '-';
}
