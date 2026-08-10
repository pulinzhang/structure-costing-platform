/**
 * Steel Price List Template
 * 钢材价格表格浏览页面 — Brabus Carbon & Precision Dark
 *
 * 抽屉式交互（与冲次费率 tonnage/template.js 对齐）：
 * - 新增 / 编辑  → editDrawer（720px 右侧滑入）
 * - 查看详情     → viewDrawer（520px 右侧滑入）
 * - 删除确认     → deleteDrawer（380px 右侧滑入）
 */

export function steelPriceListTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">

            <!-- 页面主面板：面板头部（标题+按钮） + 表格 -->
            <div class="bg-[#1e1e1e] border border-[#2c2c2c] overflow-hidden w-full max-w-full"
                 style="box-shadow: 0 2px 12px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.03);">

                <!-- 面板头部：标题 + 操作按钮 -->
                <div class="flex items-center justify-between px-5 py-3.5 border-b border-[#222222]"
                     style="background: linear-gradient(90deg, #1c1c1c 0%, #1e1e1e 60%);">
                    <div class="flex items-center gap-3">
                        <div class="w-[2px] h-4 bg-[#d32f2f] rounded-[1px] shadow-[0_0_6px_rgba(211,47,47,0.3)]"></div>
                        <h2 class="text-[12px] font-semibold text-[#c8c8c8] tracking-wide">钢材价格表</h2>
                    </div>
                    <div class="flex items-center gap-2">
                        <button id="btnAddSteelPrice" class="inline-flex items-center gap-1.5 bg-[#d32f2f] text-white px-3 py-1.5 text-[11px] font-semibold rounded-sm hover:bg-[#b71c1c] transition-all duration-150">
                            ${window.svgIcon('plus', 'w-3 h-3')}
                            新增价格
                        </button>
                    </div>
                </div>

                <!-- 工具栏：筛选 -->
                <div class="flex items-center justify-between px-5 py-2.5 border-b border-[#1e1e1e]"
                     style="background: linear-gradient(180deg, #181818 0%, #161616 100%);">
                    <div class="flex items-end gap-3 flex-wrap">
                        ${filterSelect('steelPriceYear', '年度')}
                        ${filterSelect('steelPriceMonth', '月份')}
                        ${filterSelect('steelPriceType', '钢种')}
                        ${filterInput('steelPriceGrade', '牌号', '输入牌号（模糊）')}
                        ${filterSelect('steelPriceMill', '钢厂')}

                        <button id="steelPriceSearchButton"
                                class="inline-flex items-center gap-1 h-7 px-3 text-[11px] font-medium bg-[#242424] text-[#787878] border border-[#272727] rounded-sm hover:border-[#d32f2f] hover:text-[#d32f2f] transition-all duration-150">
                            ${window.svgIcon('search', 'w-3 h-3')}
                            查询
                        </button>
                        <button id="steelPriceResetFilterButton"
                                class="inline-flex items-center gap-1 h-7 px-3 text-[11px] font-medium text-[#616161] hover:text-[#9e9e9e] transition-all duration-150">
                            重置
                        </button>
                    </div>
                </div>

                <!-- 表格区 -->
                <div class="overflow-x-auto">
                    <table class="w-full min-w-[1500px]">
                        <thead>
                            <tr style="background: linear-gradient(180deg, #111111 0%, #0e0e0e 100%); border-bottom: 1px solid #222222;">
                                <th class="px-5 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">年度</th>
                                <th class="px-5 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">月份</th>
                                <th class="px-5 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">钢种</th>
                                <th class="px-5 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">牌号</th>
                                <th class="px-5 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">参考规格</th>
                                <th class="px-5 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">钢厂</th>
                                <th class="px-5 py-2.5 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">中标价</th>
                                <th class="px-5 py-2.5 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">厚度</th>
                                <th class="px-5 py-2.5 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">厚度加减价</th>
                                <th class="px-5 py-2.5 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">加工费</th>
                                <th class="px-5 py-2.5 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">最终价/吨</th>
                                <th class="px-5 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">备注</th>
                                <th class="px-5 py-2.5 text-center text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap w-32">操作</th>
                            </tr>
                        </thead>
                        <tbody id="steelPriceTableBody" class="divide-y divide-[#1d1d1d]">
                            <!-- 动态渲染 -->
                        </tbody>
                    </table>
                </div>

                <!-- 分页：右下角 -->
                <div class="flex items-center justify-between px-5 py-2 border-t border-[#1e1e1e] bg-[#141414]">
                    <span id="steelPriceTotal" class="text-[10px] text-[#484848]"></span>
                    <div class="flex items-center gap-0.5" id="steelPricePagination">
                        <!-- 动态渲染 -->
                    </div>
                </div>

                <!-- 空状态 -->
                <div id="steelPriceEmpty" class="hidden flex flex-col items-center justify-center py-10">
                    <div class="w-8 h-8 flex items-center justify-center mb-3 rounded-sm" style="background:#141414; border: 1px solid #222222;">
                        ${window.svgIcon('clipboard-list', 'w-4 h-4 text-[#3a3a3a]')}
                    </div>
                    <h5 class="text-[11px] font-medium text-[#555555] mb-1">暂无钢材价格数据</h5>
                    <p class="text-[10px] text-[#3a3a3a]">点击上方"新增价格"添加记录</p>
                </div>

                <!-- 加载中 -->
                <div id="steelPriceLoading" class="hidden flex items-center justify-center py-10">
                    <div class="w-4 h-4 border border-[#252525] border-t-[#d32f2f] rounded-full animate-spin"></div>
                </div>
            </div>
        </div>

        <!-- 新增 / 编辑抽屉 -->
        <div class="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm transition-opacity duration-300"
             id="editDrawerBackdrop" style="display:none"></div>

        <div class="fixed inset-y-0 right-0 z-50 w-[720px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="editDrawer" style="display:none; max-height: 100vh; box-shadow: -20px 0 60px rgba(0,0,0,0.95), -8px 0 30px rgba(0,0,0,0.8), 0 0 1px rgba(255,255,255,0.05);">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0"
                 style="background: linear-gradient(180deg, #1f1f1f 0%, #1a1a1a 100%); border-bottom: 1px solid #333333;">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] flex items-center gap-2.5 uppercase">
                    <span style="width:3px;height:14px;background:#d32f2f;border-radius:1px;display:inline-block;box-shadow: 0 0 8px rgba(211,47,47,0.5);"></span>
                    <span id="editDrawerTitle">编辑钢材价格</span>
                </h5>
                <button type="button" id="closeEditDrawer"
                        class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all duration-200 group">
                    <svg class="w-4 h-4 transition-transform duration-200 group-hover:scale-110" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>

            <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain" id="editDrawerContent" style="scrollbar-width: thin; scrollbar-color: #3a3a3a #1a1a1a;">
                <form id="editForm" class="p-6 space-y-5">
                    <input type="hidden" id="editRecordId" value="">

                    <!-- 业务主键区 -->
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-2 block">业务主键</label>
                        <div class="grid grid-cols-4 gap-3">
                            <div>
                                <label class="text-[10px] text-[#777777] mb-1 block">年度 <span class="text-[#d32f2f]">*</span></label>
                                <input type="number" id="editYear" min="2000" max="2100" required
                                       class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded"
                                       placeholder="如: 2026">
                            </div>
                            <div>
                                <label class="text-[10px] text-[#777777] mb-1 block">月份 <span class="text-[#d32f2f]">*</span></label>
                                <input type="number" id="editMonth" min="1" max="12" required
                                       class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded"
                                       placeholder="如: 1">
                            </div>
                            <div>
                                <label class="text-[10px] text-[#777777] mb-1 block">牌号 <span class="text-[#d32f2f]">*</span></label>
                                <input type="text" id="editGrade" required maxlength="100"
                                       class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded"
                                       placeholder="如: DC04">
                            </div>
                            <div>
                                <label class="text-[10px] text-[#777777] mb-1 block">厚度 <span class="text-[#d32f2f]">*</span></label>
                                <input type="number" id="editThickness" min="0" step="0.0001" required
                                       class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded"
                                       placeholder="如: 0.8">
                            </div>
                        </div>
                    </div>

                    <!-- 基本信息 -->
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-2 block">基本信息</label>
                        <div class="grid grid-cols-3 gap-3">
                            <div>
                                <label class="text-[10px] text-[#777777] mb-1 block">钢种 <span class="text-[#d32f2f]">*</span></label>
                                <input type="text" id="editSteelType" required maxlength="50"
                                       class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded"
                                       placeholder="如: 冷轧">
                            </div>
                            <div>
                                <label class="text-[10px] text-[#777777] mb-1 block">参考规格 <span class="text-[#d32f2f]">*</span></label>
                                <input type="text" id="editReferenceSpec" required maxlength="100"
                                       class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded"
                                       placeholder="如: 1.0*1250*C">
                            </div>
                            <div>
                                <label class="text-[10px] text-[#777777] mb-1 block">钢厂 <span class="text-[#d32f2f]">*</span></label>
                                <input type="text" id="editSteelMill" required maxlength="100"
                                       class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded"
                                       placeholder="如: 宝钢">
                            </div>
                        </div>
                    </div>

                    <!-- 价格信息 -->
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-2 block">价格信息</label>
                        <div class="grid grid-cols-4 gap-3">
                            <div>
                                <label class="text-[10px] text-[#777777] mb-1 block">中标价 <span class="text-[#d32f2f]">*</span></label>
                                <input type="number" id="editBidPrice" min="0" step="0.0001" required
                                       class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded"
                                       placeholder="元">
                            </div>
                            <div>
                                <label class="text-[10px] text-[#777777] mb-1 block">厚度加减价 <span class="text-[#d32f2f]">*</span></label>
                                <input type="number" id="editThicknessAdjustment" min="0" step="0.0001" required
                                       class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded"
                                       placeholder="元">
                            </div>
                            <div>
                                <label class="text-[10px] text-[#777777] mb-1 block">加工费 <span class="text-[#d32f2f]">*</span></label>
                                <input type="number" id="editProcessingFee" min="0" step="0.0001" required
                                       class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded"
                                       placeholder="元">
                            </div>
                            <div>
                                <label class="text-[10px] text-[#777777] mb-1 block">最终价/吨 <span class="text-[#d32f2f]">*</span></label>
                                <input type="number" id="editFinalPrice" min="0" step="0.0001" required
                                       class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded"
                                       placeholder="元">
                            </div>
                        </div>
                    </div>

                    <!-- 备注 -->
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">备注</label>
                        <textarea id="editRemark" rows="3" maxlength="500"
                                  class="w-full px-3 py-2 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded resize-none"
                                  placeholder="可填写附加说明，最多 500 字"></textarea>
                    </div>

                    <div class="bg-[#0c0c0c] border border-[#1a1a1a] rounded p-3">
                        <p class="text-[11px] text-[#616161]">
                            <span class="text-[#616161]">说明：</span>
                            (年度 + 月份 + 牌号 + 厚度) 构成业务唯一键，新增时不可与已有记录重复。编辑时该四字段不允许变更。
                        </p>
                    </div>
                </form>
            </div>

            <div class="px-6 py-4 border-t border-[#262626] flex items-center justify-end gap-2 shrink-0" style="background: linear-gradient(0deg, #1a1a1a 0%, #161616 100%);">
                <button type="button" id="cancelEditBtn" class="inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-4 py-2 text-[11px] font-medium rounded hover:border-[#9e9e9e] hover:text-white transition-all">
                    取消
                </button>
                <button type="button" id="submitEditBtn" class="inline-flex items-center gap-1.5 bg-[#d32f2f] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all">
                    ${window.svgIcon('archive', 'w-3.5 h-3.5')}
                    保存
                </button>
            </div>
        </div>

        <!-- 查看详情抽屉 -->
        <div class="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm transition-opacity duration-300"
             id="viewDrawerBackdrop" style="display:none"></div>

        <div class="fixed inset-y-0 right-0 z-50 w-[520px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="viewDrawer" style="display:none; max-height: 100vh; box-shadow: -20px 0 60px rgba(0,0,0,0.95), -8px 0 30px rgba(0,0,0,0.8), 0 0 1px rgba(255,255,255,0.05);">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0"
                 style="background: linear-gradient(180deg, #1f1f1f 0%, #1a1a1a 100%); border-bottom: 1px solid #333333;">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] flex items-center gap-2.5 uppercase">
                    <span style="width:3px;height:14px;background:#d32f2f;border-radius:1px;display:inline-block;box-shadow: 0 0 8px rgba(211,47,47,0.5);"></span>
                    价格详情
                </h5>
                <button type="button" id="closeViewDrawer"
                        class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all duration-200 group">
                    <svg class="w-4 h-4 transition-transform duration-200 group-hover:scale-110" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>

            <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain p-6" id="viewDrawerContent" style="scrollbar-width: thin; scrollbar-color: #3a3a3a #1a1a1a;">
                <div class="bg-[#111111] border border-[#262626]">
                    <div class="px-4 py-3 bg-[#0c0c0c] border-b border-[#181818]">
                        <h6 class="text-[10px] font-semibold text-[#9e9e9e] tracking-wider uppercase">业务主键</h6>
                    </div>
                    <div class="p-4 grid grid-cols-2 gap-x-6 gap-y-3">
                        ${viewRow('年度', 'view-year')}
                        ${viewRow('月份', 'view-month')}
                        ${viewRow('牌号', 'view-grade')}
                        ${viewRow('厚度', 'view-thickness')}
                    </div>
                </div>

                <div class="bg-[#111111] border border-[#262626] mt-4">
                    <div class="px-4 py-3 bg-[#0c0c0c] border-b border-[#181818]">
                        <h6 class="text-[10px] font-semibold text-[#9e9e9e] tracking-wider uppercase">基本信息</h6>
                    </div>
                    <div class="p-4 grid grid-cols-2 gap-x-6 gap-y-3">
                        ${viewRow('钢种', 'view-steel-type')}
                        ${viewRow('参考规格', 'view-reference-spec')}
                        ${viewRow('钢厂', 'view-steel-mill')}
                    </div>
                </div>

                <div class="bg-[#111111] border border-[#262626] mt-4">
                    <div class="px-4 py-3 bg-[#0c0c0c] border-b border-[#181818]">
                        <h6 class="text-[10px] font-semibold text-[#9e9e9e] tracking-wider uppercase">价格信息</h6>
                    </div>
                    <div class="p-4 grid grid-cols-2 gap-x-6 gap-y-3">
                        ${viewRow('中标价', 'view-bid-price')}
                        ${viewRow('厚度加减价', 'view-thickness-adjustment')}
                        ${viewRow('加工费', 'view-processing-fee')}
                        ${viewRow('最终价/吨', 'view-final-price', true)}
                    </div>
                </div>

                <div class="bg-[#111111] border border-[#262626] mt-4">
                    <div class="px-4 py-3 bg-[#0c0c0c] border-b border-[#181818]">
                        <h6 class="text-[10px] font-semibold text-[#9e9e9e] tracking-wider uppercase">备注</h6>
                    </div>
                    <div class="p-4">
                        <p id="view-remark" class="text-xs text-[#9e9e9e] leading-5 break-all"></p>
                    </div>
                </div>

                <div class="bg-[#111111] border border-[#262626] mt-4">
                    <div class="px-4 py-3 bg-[#0c0c0c] border-b border-[#181818]">
                        <h6 class="text-[10px] font-semibold text-[#9e9e9e] tracking-wider uppercase">系统信息</h6>
                    </div>
                    <div class="p-4 grid grid-cols-2 gap-x-6 gap-y-3">
                        ${viewRow('创建时间', 'view-created-at')}
                        ${viewRow('更新时间', 'view-updated-at')}
                    </div>
                </div>
            </div>

            <div class="px-6 py-4 border-t border-[#262626] flex items-center justify-end gap-2 shrink-0" style="background: linear-gradient(0deg, #1a1a1a 0%, #161616 100%);">
                <button type="button" id="viewDrawerEditBtn" class="inline-flex items-center gap-1.5 bg-[#d32f2f] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all">
                    ${window.svgIcon('pencil', 'w-3.5 h-3.5')}
                    编辑
                </button>
            </div>
        </div>

        <!-- 删除确认抽屉 -->
        <div class="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm transition-opacity duration-300"
             id="deleteDrawerBackdrop" style="display:none"></div>

        <div class="fixed inset-y-0 right-0 z-50 w-[380px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="deleteDrawer" style="display:none; max-height: 100vh; box-shadow: -20px 0 60px rgba(0,0,0,0.95), -8px 0 30px rgba(0,0,0,0.8), 0 0 1px rgba(255,255,255,0.05);">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0"
                 style="background: linear-gradient(180deg, #1f1f1f 0%, #1a1a1a 100%); border-bottom: 1px solid #333333;">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] flex items-center gap-2.5 uppercase">
                    <span style="width:3px;height:14px;background:#c62828;border-radius:1px;display:inline-block;box-shadow: 0 0 8px rgba(198,40,40,0.5);"></span>
                    确认删除
                </h5>
                <button type="button" id="closeDeleteDrawer"
                        class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all duration-200 group">
                    <svg class="w-4 h-4 transition-transform duration-200 group-hover:scale-110" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>

            <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain" id="deleteDrawerContent" style="scrollbar-width: thin; scrollbar-color: #3a3a3a #1a1a1a;">
                <input type="hidden" id="deleteRecordId" value="">
                <div class="p-6">
                    <p class="text-[12px] text-[#9e9e9e] mb-3">
                        确定要删除这条价格记录吗？
                    </p>
                    <div class="bg-[#0c0c0c] border border-[#1a1a1a] rounded p-3 text-[11px] text-[#616161]" id="deleteSummary">
                        <!-- 摘要动态填充 -->
                    </div>
                    <p class="text-[11px] text-[#c62828] mt-3">此操作不可撤销。</p>
                </div>
            </div>

            <div class="px-6 py-4 border-t border-[#262626] flex items-center justify-end gap-2 shrink-0" style="background: linear-gradient(0deg, #1a1a1a 0%, #161616 100%);">
                <button type="button" id="cancelDeleteBtn" class="inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-4 py-2 text-[11px] font-medium rounded hover:border-[#9e9e9e] hover:text-white transition-all">
                    取消
                </button>
                <button type="button" id="confirmDeleteBtn" class="inline-flex items-center gap-1.5 bg-[#c62828] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all">
                    ${window.svgIcon('trash', 'w-3.5 h-3.5')}
                    删除
                </button>
            </div>
        </div>
    `;
}

/**
 * 渲染表格行
 * - 偶数行微调背景色，形成精致斑马纹
 * - 操作按钮：查看 / 编辑 / 删除
 */
export function renderSteelPriceRows(records) {
    if (!records || !Array.isArray(records) || records.length === 0) {
        return '';
    }
    return records.map((record, idx) => {
        const isEven = idx % 2 === 1;
        return `
        <tr class="group transition-colors duration-150 cursor-default"
            data-id="${esc(record.id)}"
            style="${isEven ? 'background: rgba(255,255,255,0.012);' : ''}">
            <td class="px-5 py-2.5 text-[11px] text-[#686868] whitespace-nowrap font-mono tracking-wide border-b border-[#1d1d1d]">${esc(record.year)}</td>
            <td class="px-5 py-2.5 text-[11px] text-[#686868] whitespace-nowrap font-mono tracking-wide border-b border-[#1d1d1d]">${esc(record.month)}</td>
            <td class="px-5 py-2.5 text-[11px] text-[#9e9e9e] whitespace-nowrap border-b border-[#1d1d1d]">${esc(record.steel_type)}</td>
            <td class="px-5 py-2.5 text-[11px] font-medium text-[#b0b0b0] whitespace-nowrap border-b border-[#1d1d1d]">${esc(record.grade)}</td>
            <td class="px-5 py-2.5 text-[11px] text-[#9e9e9e] whitespace-nowrap font-mono border-b border-[#1d1d1d]">${esc(record.reference_spec)}</td>
            <td class="px-5 py-2.5 text-[11px] text-[#9e9e9e] whitespace-nowrap border-b border-[#1d1d1d]">${esc(record.steel_mill)}</td>
            <td class="px-5 py-2.5 text-[11px] text-right font-mono tabular-nums text-[#9e9e9e] whitespace-nowrap border-b border-[#1d1d1d]">${formatPrice(record.bid_price)}</td>
            <td class="px-5 py-2.5 text-[11px] text-right font-mono tabular-nums text-[#9e9e9e] whitespace-nowrap border-b border-[#1d1d1d]">${formatPrice(record.thickness, 4)}</td>
            <td class="px-5 py-2.5 text-[11px] text-right font-mono tabular-nums text-[#9e9e9e] whitespace-nowrap border-b border-[#1d1d1d]">${formatPrice(record.thickness_adjustment)}</td>
            <td class="px-5 py-2.5 text-[11px] text-right font-mono tabular-nums text-[#9e9e9e] whitespace-nowrap border-b border-[#1d1d1d]">${formatPrice(record.processing_fee)}</td>
            <td class="px-5 py-2.5 text-[11px] text-right font-mono tabular-nums text-[#d32f2f] whitespace-nowrap border-b border-[#1d1d1d]">
                <span class="shadow-[0_0_8px_rgba(211,47,47,0.2)]">${formatPrice(record.final_price_per_ton)}</span>
            </td>
            <td class="px-5 py-2.5 text-[11px] text-[#616161] max-w-40 border-b border-[#1d1d1d]">
                <span class="block truncate" title="${esc(record.remark)}">${esc(record.remark)}</span>
            </td>
            <td class="px-5 py-2.5 text-center whitespace-nowrap border-b border-[#1d1d1d]">
                <div class="flex items-center justify-center gap-0.5">
                    <button class="view-btn flex items-center justify-center w-7 h-7 rounded-sm text-[#484848] hover:text-[#d32f2f] hover:bg-[#d32f2f]/10 transition-all duration-150 opacity-60 hover:opacity-100" title="查看">
                        ${window.svgIcon('eye', 'w-3 h-3')}
                    </button>
                    <button class="edit-btn flex items-center justify-center w-7 h-7 rounded-sm text-[#484848] hover:text-[#d32f2f] hover:bg-[#d32f2f]/10 transition-all duration-150 opacity-60 hover:opacity-100" title="编辑">
                        ${window.svgIcon('pencil', 'w-3 h-3')}
                    </button>
                    <button class="delete-btn flex items-center justify-center w-7 h-7 rounded-sm text-[#484848] hover:text-[#c62828] hover:bg-[#c62828]/10 transition-all duration-150 opacity-60 hover:opacity-100" title="删除">
                        ${window.svgIcon('trash', 'w-3 h-3')}
                    </button>
                </div>
            </td>
        </tr>`;
    }).join('');
}

/**
 * 渲染分页按钮
 */
export function renderSteelPricePagination(currentPage, totalPages) {
    if (totalPages <= 1) {
        return '';
    }

    let buttons = '';

    buttons += `
        <button class="steel-price-page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] ${currentPage === 1 ? 'text-[#333333] cursor-not-allowed' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'} transition-all duration-150"
                data-page="${currentPage - 1}" ${currentPage === 1 ? 'disabled' : ''}>
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
            </svg>
        </button>
    `;

    const maxVisible = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);
    if (endPage - startPage < maxVisible - 1) {
        startPage = Math.max(1, endPage - maxVisible + 1);
    }

    if (startPage > 1) {
        buttons += `<button class="steel-price-page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323] transition-all duration-150" data-page="1">1</button>`;
        if (startPage > 2) buttons += `<span class="px-0.5 text-[#333333] leading-6 text-[9px]">…</span>`;
    }

    for (let i = startPage; i <= endPage; i++) {
        const isActive = i === currentPage;
        buttons += `
            <button class="steel-price-page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] ${isActive ? 'bg-[#d32f2f] text-white shadow-[0_0_8px_rgba(211,47,47,0.25)]' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'} transition-all duration-150"
                    data-page="${i}">${i}</button>
        `;
    }

    if (endPage < totalPages) {
        if (endPage < totalPages - 1) buttons += `<span class="px-0.5 text-[#333333] leading-6 text-[9px]">…</span>`;
        buttons += `<button class="steel-price-page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323] transition-all duration-150" data-page="${totalPages}">${totalPages}</button>`;
    }

    buttons += `
        <button class="steel-price-page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] ${currentPage === totalPages ? 'text-[#333333] cursor-not-allowed' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'} transition-all duration-150"
                data-page="${currentPage + 1}" ${currentPage === totalPages ? 'disabled' : ''}>
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
            </svg>
        </button>
    `;

    return buttons;
}

// ===== 内部辅助函数 =====

function filterSelect(id, label) {
    return `<label class="space-y-1">
        <span class="block text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em] whitespace-nowrap">${label}</span>
        <select id="${id}" class="w-36 h-7 pl-2.5 pr-7 text-[11px] bg-[#0d0d0d] border border-[#272727] text-[#909090] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] transition-all rounded-sm">
            <option value="">全部</option>
        </select>
    </label>`;
}

function filterInput(id, label, placeholder) {
    return `<label class="space-y-1">
        <span class="block text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em] whitespace-nowrap">${label}</span>
        <input id="${id}" placeholder="${placeholder}" class="h-7 w-36 px-2.5 text-[11px] bg-[#0d0d0d] border border-[#272727] text-[#ffffff] placeholder:text-[#616161] rounded-sm focus:outline-none focus:border-[#ff5252]">
    </label>`;
}

function viewRow(label, id, isHighlight = false) {
    return `<div class="min-w-0">
        <span class="block text-[9px] font-semibold text-[#555555] uppercase tracking-[0.1em] mb-1">${label}</span>
        <span id="${id}" class="block text-xs ${isHighlight ? 'text-[#d32f2f] font-mono tabular-nums tracking-wide drop-shadow-[0_0_8px_rgba(211,47,47,0.15)]' : 'text-[#cccccc]'} truncate"></span>
    </div>`;
}

function formatPrice(value, digits = 2) {
    const numeric = Number(value);
    if (value === null || value === undefined || Number.isNaN(numeric)) return '-';
    return numeric.toLocaleString('zh-CN', { minimumFractionDigits: digits, maximumFractionDigits: digits });
}
