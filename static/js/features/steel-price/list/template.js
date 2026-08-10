/**
 * Steel Price List Template
 * 钢材价格计算结果浏览 — Brabus Carbon & Precision Dark
 */

export function steelPriceListTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="bg-[#1e1e1e] border border-[#2c2c2c] overflow-hidden w-full max-w-full"
                 style="box-shadow: 0 2px 12px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.03);">

                <div class="flex items-center justify-between px-5 py-3.5 border-b border-[#222222]"
                     style="background: linear-gradient(90deg, #1c1c1c 0%, #1e1e1e 60%);">
                    <div class="flex items-center gap-3">
                        <div class="w-[2px] h-4 bg-[#d32f2f] rounded-[1px] shadow-[0_0_6px_rgba(211,47,47,0.3)]"></div>
                        <h2 class="text-[12px] font-semibold text-[#c8c8c8] tracking-wide">钢材价格表</h2>
                    </div>
                    <div class="flex items-center gap-2">
                        <button id="steelPriceBatchDeleteButton"
                                class="inline-flex items-center gap-1.5 bg-transparent text-[#505050] border border-[#252525] px-3 py-1.5 text-[11px] font-medium rounded-sm hover:bg-[#c62828]/15 hover:border-[#c62828]/60 hover:text-[#d45858] hover:shadow-[0_0_8px_rgba(198,40,40,0.15)] transition-all duration-200"
                                style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);">
                            ${window.svgIcon('trash', 'w-3 h-3')}
                            批量删除
                        </button>
                    </div>
                </div>

                <div class="flex items-center justify-between px-5 py-2.5 border-b border-[#1e1e1e]"
                     style="background: linear-gradient(180deg, #181818 0%, #161616 100%);">
                    <div class="flex items-end gap-3 flex-wrap">
                        ${filterSelect('steelPriceYear', '年度')}
                        ${filterSelect('steelPriceMonth', '月份')}
                        ${filterSelect('steelPriceLocation', '基地')}
                        ${filterSelect('steelPriceCategory', '钢种')}
                        ${filterInput('steelPriceGrade', '牌号', '输入牌号（模糊）')}
                        ${filterSelect('steelPriceMill', '钢厂')}
                        ${filterSelect('steelPriceAuditStatus', '审核状态')}

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

                <div class="overflow-x-auto">
                    <table class="w-full min-w-[2800px]">
                        <thead>
                            <tr style="background: linear-gradient(180deg, #111111 0%, #0e0e0e 100%); border-bottom: 1px solid #222222;">
                                <th class="px-3 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">年度</th>
                                <th class="px-3 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">月份</th>
                                <th class="px-3 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">基地</th>
                                <th class="px-3 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">钢厂</th>
                                <th class="px-3 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">钢种</th>
                                <th class="px-3 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">牌号</th>
                                <th class="px-3 py-2.5 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">厚度</th>
                                <th class="px-3 py-2.5 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">宽度</th>
                                <th class="px-3 py-2.5 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">基础价</th>
                                <th class="px-3 py-2.5 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">厚度加价</th>
                                <th class="px-3 py-2.5 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">宽度加价</th>
                                <th class="px-3 py-2.5 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">加工费</th>
                                <th class="px-3 py-2.5 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">最终价/吨</th>
                                <th class="px-3 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">基价溯源</th>
                                <th class="px-3 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">厚度溯源</th>
                                <th class="px-3 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">宽度溯源</th>
                                <th class="px-3 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">匹配</th>
                                <th class="px-3 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">审核</th>
                                <th class="px-3 py-2.5 text-center text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap w-40">操作</th>
                            </tr>
                        </thead>
                        <tbody id="steelPriceTableBody" class="divide-y divide-[#1d1d1d]"></tbody>
                    </table>
                </div>

                <div class="flex items-center justify-between px-5 py-2 border-t border-[#1e1e1e] bg-[#141414]">
                    <span id="steelPriceTotal" class="text-[10px] text-[#484848]"></span>
                    <div class="flex items-center gap-0.5" id="steelPricePagination"></div>
                </div>

                <div id="steelPriceEmpty" class="hidden flex flex-col items-center justify-center py-10">
                    <div class="w-8 h-8 flex items-center justify-center mb-3 rounded-sm" style="background:#141414; border: 1px solid #222222;">
                        ${window.svgIcon('clipboard-list', 'w-4 h-4 text-[#3a3a3a]')}
                    </div>
                    <h5 class="text-[11px] font-medium text-[#555555] mb-1">暂无钢材价格数据</h5>
                    <p class="text-[10px] text-[#3a3a3a]">数据由系统计算写入，或通过 Excel 导入</p>
                </div>

                <div id="steelPriceLoading" class="hidden flex items-center justify-center py-10">
                    <div class="w-4 h-4 border border-[#252525] border-t-[#d32f2f] rounded-full animate-spin"></div>
                </div>
            </div>
        </div>

        <!-- 新增 / 编辑抽屉 -->
        <div class="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm transition-opacity duration-300"
             id="editDrawerBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-50 w-[760px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
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
                            ${editText('editLocation', '基地', '如: 芜湖基地')}
                            ${editText('editSteelMill', '钢厂', '如: 马钢')}
                            ${editText('editCategoryName', '钢种', '如: 冷轧')}
                            ${editText('editGrade', '牌号', '如: DC01')}
                            ${editNumber('editThickness', '厚度', '0', null, '0.8', '0.0001')}
                            ${editNumber('editWidth', '宽度', '0', null, '1250', '0.0001')}
                        </div>
                    </div>

                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-2 block">价格分项</label>
                        <div class="grid grid-cols-3 gap-3">
                            ${editNumber('editBasePrice', '基础价 base_price', '0', null, '元', '0.0001')}
                            ${editNumber('editThicknessAdjustment', '厚度加价 thickness_adjustment', null, null, '元', '0.0001')}
                            ${editNumber('editWidthAdjustment', '宽度加价 width_adjustment', null, null, '元', '0.0001')}
                            ${editNumber('editZincAdjustment', '锌层加价 zinc_adjustment', null, null, '元', '0.0001')}
                            ${editNumber('editProcessingFee', '加工费 processing_fee', '0', null, '元', '0.0001')}
                            ${editNumber('editOtherAdjustment', '其他调整 other_adjustment', null, null, '元', '0.0001')}
                        </div>
                        <p class="text-[10px] text-[#616161] mt-2">最终价由服务端按分项自动汇总，无需手工填写。</p>
                    </div>

                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">规格 / 备注</label>
                        <div class="grid grid-cols-2 gap-3">
                            ${editText('editSpec', '规格（可选）', '如: 1.00*1250.00', false)}
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
        <div class="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm transition-opacity duration-300"
             id="viewDrawerBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-50 w-[560px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
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
                        <h6 class="text-[10px] font-semibold text-[#9e9e9e] tracking-wider uppercase">价格分项（对齐 VO）</h6>
                    </div>
                    <div class="p-4 grid grid-cols-2 gap-x-6 gap-y-3">
                        ${viewRow('基础价 base_price', 'view-base-price')}
                        ${viewRow('厚度加价 thickness_adjustment', 'view-thickness-adjustment')}
                        ${viewRow('宽度加价 width_adjustment', 'view-width-adjustment')}
                        ${viewRow('锌层加价 zinc_adjustment', 'view-zinc-adjustment')}
                        ${viewRow('加工费 processing_fee', 'view-processing-fee')}
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
        <div class="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm transition-opacity duration-300"
             id="deleteDrawerBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-50 w-[380px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
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
                <p class="text-[12px] text-[#9e9e9e] mb-3">确定要删除这条价格记录吗？</p>
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
    `;
}

export function renderSteelPriceRows(records) {
    if (!records || !Array.isArray(records) || records.length === 0) return '';
    return records.map((record, idx) => {
        const isEven = idx % 2 === 1;
        const approved = record.audit_status === 'approved';
        const cell = 'px-3 py-2.5 text-[11px] border-b border-[#1d1d1d]';
        return `
        <tr class="group transition-colors duration-150" data-id="${esc(record.id)}"
            style="${isEven ? 'background: rgba(255,255,255,0.012);' : ''}">
            <td class="${cell} text-[#686868] font-mono">${esc(record.year)}</td>
            <td class="${cell} text-[#686868] font-mono">${esc(record.month)}</td>
            <td class="${cell} text-[#9e9e9e]">${esc(record.location)}</td>
            <td class="${cell} text-[#9e9e9e]">${esc(record.steel_mill)}</td>
            <td class="${cell} text-[#9e9e9e]">${esc(record.category_name)}</td>
            <td class="${cell} font-medium text-[#b0b0b0]">${esc(record.grade)}</td>
            <td class="${cell} text-right font-mono text-[#9e9e9e]">${formatPrice(record.thickness, 4)}</td>
            <td class="${cell} text-right font-mono text-[#9e9e9e]">${formatPrice(record.width, 2)}</td>
            <td class="${cell} text-right font-mono text-[#9e9e9e]">${formatPrice(record.base_price)}</td>
            <td class="${cell} text-right font-mono text-[#9e9e9e]">${formatPrice(record.thickness_adjustment)}</td>
            <td class="${cell} text-right font-mono text-[#9e9e9e]">${formatPrice(record.width_adjustment)}</td>
            <td class="${cell} text-right font-mono text-[#9e9e9e]">${formatPrice(record.processing_fee)}</td>
            <td class="${cell} text-right font-mono text-[#d32f2f]">${formatPrice(record.final_price_per_ton)}</td>
            <td class="${cell} text-[10px] text-[#777777] max-w-[220px]">${formatTraceCell('base', record)}</td>
            <td class="${cell} text-[10px] text-[#777777] max-w-[220px]">${formatTraceCell('thickness', record)}</td>
            <td class="${cell} text-[10px] text-[#777777] max-w-[220px]">${formatTraceCell('width', record)}</td>
            <td class="${cell} text-[#9e9e9e]">${esc(record.match_status)}</td>
            <td class="${cell}">${auditBadge(record.audit_status)}</td>
            <td class="${cell} text-center">
                <div class="flex items-center justify-center gap-0.5">
                    <button class="view-btn flex items-center justify-center w-7 h-7 rounded-sm text-[#484848] hover:text-[#d32f2f] hover:bg-[#d32f2f]/10 transition-all" title="查看">${window.svgIcon('eye', 'w-3 h-3')}</button>
                    <button class="edit-btn flex items-center justify-center w-7 h-7 rounded-sm text-[#484848] hover:text-[#d32f2f] hover:bg-[#d32f2f]/10 transition-all ${approved ? 'opacity-30 pointer-events-none' : ''}" title="${approved ? '已审核，不可编辑' : '编辑'}">${window.svgIcon('pencil', 'w-3 h-3')}</button>
                    <button class="delete-btn flex items-center justify-center w-7 h-7 rounded-sm text-[#484848] hover:text-[#c62828] hover:bg-[#c62828]/10 transition-all ${approved ? 'opacity-30 pointer-events-none' : ''}" title="${approved ? '已审核，不可删除' : '删除'}">${window.svgIcon('trash', 'w-3 h-3')}</button>
                </div>
            </td>
        </tr>`;
    }).join('');
}

/**
 * 列表溯源摘要，字段对齐 SteelPriceResponse VO。
 * base: base_price_id / base_excel_filename / base_sheet_name / base_excel_row / base_excel_col
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
        if (startPage > 2) buttons += `<span class="px-0.5 text-[#333333] text-[9px]">…</span>`;
    }
    for (let i = startPage; i <= endPage; i++) {
        const isActive = i === currentPage;
        buttons += `<button class="steel-price-page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] ${isActive ? 'bg-[#d32f2f] text-white' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'}" data-page="${i}">${i}</button>`;
    }
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) buttons += `<span class="px-0.5 text-[#333333] text-[9px]">…</span>`;
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
        <span class="block text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em]">${label}</span>
        <select id="${id}" class="w-32 h-7 pl-2.5 pr-7 text-[11px] bg-[#0d0d0d] border border-[#272727] text-[#909090] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] rounded-sm">
            <option value="">全部</option>
        </select>
    </label>`;
}

function filterInput(id, label, placeholder) {
    return `<label class="space-y-1">
        <span class="block text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em]">${label}</span>
        <input id="${id}" placeholder="${placeholder}" class="h-7 w-32 px-2.5 text-[11px] bg-[#0d0d0d] border border-[#272727] text-[#ffffff] placeholder:text-[#616161] rounded-sm focus:outline-none focus:border-[#ff5252]">
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
        pending: 'bg-[#f57f17]/20 text-[#ffb74d]',
        approved: 'bg-[#2e7d32]/20 text-[#4caf50]',
        rejected: 'bg-[#c62828]/20 text-[#ef5350]',
    };
    const label = { pending: '待审', approved: '已通过', rejected: '已驳回' }[status] || status || '-';
    const cls = map[status] || 'bg-[#262626] text-[#9e9e9e]';
    return `<span class="inline-flex items-center px-2 py-0.5 text-[10px] font-semibold rounded ${cls}">${esc(label)}</span>`;
}

function formatPrice(value, digits = 2) {
    const numeric = Number(value);
    if (value === null || value === undefined || Number.isNaN(numeric)) return '-';
    return numeric.toLocaleString('zh-CN', { minimumFractionDigits: digits, maximumFractionDigits: digits });
}
