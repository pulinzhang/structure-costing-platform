/**
 * Dashboard Template
 * 管理者看板 — 本期产出 / 待办决策 / 核价闭环就绪
 */

function actionLink({ page, label, sub }) {
    return `
        <a href="#/${page}" data-page="${page}"
           class="group flex flex-col gap-0.5 px-4 py-3 border border-[#2c2c2c] bg-[#121212] hover:border-[#d32f2f] hover:bg-[#1a080a] transition-colors">
            <span class="text-xs font-medium text-[#F0F0F2] group-hover:text-white">${label}</span>
            <span class="text-[10px] text-[#555555]">${sub}</span>
        </a>
    `;
}

export function dashboardTemplate() {
    return `
        <!-- 作用域 -->
        <div class="flex flex-wrap items-end gap-3 mb-5 px-4 py-3 bg-[#0A0A0C] border border-[#1A1A22]">
            <div class="flex flex-col gap-1">
                <label class="text-[9px] font-medium tracking-[0.08em] text-[#555555] uppercase" for="dashYear">核价年度</label>
                <select id="dashYear"
                    class="h-9 min-w-[6.5rem] px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] transition-all"></select>
            </div>
            <div class="flex flex-col gap-1">
                <label class="text-[9px] font-medium tracking-[0.08em] text-[#555555] uppercase" for="dashMonth">核价月份</label>
                <select id="dashMonth"
                    class="h-9 min-w-[5.5rem] px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] transition-all"></select>
            </div>
            <div class="flex flex-col gap-1">
                <label class="text-[9px] font-medium tracking-[0.08em] text-[#555555] uppercase" for="dashLocation">生产基地</label>
                <select id="dashLocation"
                    class="h-9 min-w-[8rem] px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] transition-all">
                    <option value="">全部基地</option>
                </select>
            </div>
            <div class="flex flex-col gap-1">
                <label class="text-[9px] font-medium tracking-[0.08em] text-[#555555] uppercase" for="dashVehicle">项目</label>
                <select id="dashVehicle"
                    class="h-9 min-w-[8rem] px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] transition-all">
                    <option value="">全部项目</option>
                </select>
            </div>
            <p class="text-[10px] text-[#555555] pb-2 ml-auto font-mono tracking-[0.04em]" id="dashScopeLabel">—</p>
        </div>

        <!-- 本期产出 HUD -->
        <div class="bg-[#0A0A0C] border border-[#1A1A22] mb-5 overflow-hidden"
             style="box-shadow: 0 4px 24px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.02);">
            <div class="px-5 pt-4 pb-4"
                 style="background: linear-gradient(135deg, #0E0E12 0%, #121218 45%, #0C0C10 100%);">
                <div class="flex items-center gap-2 mb-3">
                    <div class="w-0.5 h-3.5 bg-[#FF1E27]"></div>
                    <h3 class="text-[10px] font-semibold uppercase tracking-[0.15em] text-[#616161]">本期核价产出</h3>
                    <span class="text-[10px] font-mono text-[#3A3A42]" id="dashOutcomeSub">—</span>
                </div>
                <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 font-mono">
                    <div class="bg-gradient-to-b from-[#18080A] to-[#0D0708] border border-[#FF1E27]/50 p-3.5 relative overflow-hidden"
                         style="box-shadow: 0 0 30px rgba(255,30,39,0.12), inset 0 1px 0 rgba(255,30,39,0.12);">
                        <div class="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-[#FF1E27] to-transparent"></div>
                        <div class="text-[#FF1E27] text-[10px] font-bold tracking-widest">冲压件均单价</div>
                        <div class="text-[26px] font-black text-[#FF1E27] mt-1 tracking-tight tabular-nums"
                             style="text-shadow: 0 0 12px rgba(255,30,39,0.55);">
                            ¥<span id="dashPartAvg">—</span>
                        </div>
                        <div class="text-[9px] text-[#FF1E27]/60 mt-1" id="dashPartAvgMeta">已审 — · 待审 —</div>
                    </div>
                    <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3">
                        <div class="text-[#555555] text-[10px] tracking-wider">待办合计</div>
                        <div class="text-[22px] font-bold text-[#F0F0F2] mt-1 tabular-nums">
                            <span id="dashPendingTotal" class="text-[#ffb74d]">—</span>
                            <span class="text-[10px] text-[#555555] ml-1">条</span>
                        </div>
                        <div class="text-[9px] text-[#555555] mt-1 font-mono" id="dashPendingBreakdown">加工费 — · 钢价 — · 冲压件 —</div>
                    </div>
                    <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3">
                        <div class="text-[#555555] text-[10px] tracking-wider">加工费待补价</div>
                        <div class="text-[22px] font-bold text-[#F0F0F2] mt-1 tabular-nums">
                            <span id="dashFeeZero">—</span>
                            <span class="text-[10px] text-[#555555] ml-1">条</span>
                        </div>
                        <div class="text-[9px] text-[#555555] mt-1 font-mono" id="dashFeeAvg">件均 —</div>
                    </div>
                    <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3">
                        <div class="text-[#555555] text-[10px] tracking-wider">钢材联动均价</div>
                        <div class="text-[22px] font-bold text-[#F0F0F2] mt-1 tabular-nums">
                            ¥<span id="dashSteelAvg">—</span>
                        </div>
                        <div class="text-[9px] text-[#555555] mt-1 font-mono" id="dashSteelMeta">已审 — · 待审 —</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="grid grid-cols-1 xl:grid-cols-5 gap-5 mb-5">
            <!-- 待办决策 -->
            <div class="xl:col-span-3 bg-[#1e1e1e] border border-[#2c2c2c]">
                <div class="flex items-center justify-between gap-3 px-5 py-3 border-b border-[#222222]">
                    <div class="flex items-center gap-2.5">
                        <div class="w-0.5 h-3.5 bg-[#d32f2f]"></div>
                        <h3 class="text-[10px] font-semibold uppercase tracking-[0.15em] text-[#616161]">待办与风险</h3>
                    </div>
                    <span class="text-[10px] font-mono text-[#555555]" id="dashAttentionCount">0 项</span>
                </div>
                <div id="dashAttentionList" class="divide-y divide-[#1a1a1a] min-h-[12rem]">
                    <div class="px-5 py-8 text-center text-sm text-[#555555]">加载中…</div>
                </div>
            </div>

            <!-- 闭环就绪 -->
            <div class="xl:col-span-2 bg-[#1e1e1e] border border-[#2c2c2c]">
                <div class="flex items-center justify-between gap-3 px-5 py-3 border-b border-[#222222]">
                    <div class="flex items-center gap-2.5">
                        <div class="w-0.5 h-3.5 bg-[#d32f2f]"></div>
                        <h3 class="text-[10px] font-semibold uppercase tracking-[0.15em] text-[#616161]">核价闭环就绪</h3>
                    </div>
                    <span class="text-[10px] font-mono tabular-nums text-[#8E8E93]" id="dashReadyScore">—/6</span>
                </div>
                <div id="dashReadiness" class="p-4 space-y-2"></div>
                <div class="px-5 py-3 border-t border-[#222222] text-[10px] text-[#555555] leading-relaxed" id="dashReadyHint">
                    基价 · 政策 · 废料 · 加工费 · 钢价 · 冲压零件价，六项齐备方可闭环本期冲压核价。
                </div>
            </div>
        </div>

        <!-- 底盘上下文 + 管理者入口 -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-6">
            <div class="bg-[#1e1e1e] border border-[#2c2c2c] p-4">
                <p class="text-[10px] font-semibold uppercase tracking-[0.15em] text-[#616161] mb-3">主数据底盘（随作用域）</p>
                <div id="dashMasterBlock" class="font-mono text-sm text-[#F0F0F2]">—</div>
                <p class="mt-2 text-[10px] text-[#555555]" id="dashBomBlock">BOM —</p>
            </div>
            <div class="lg:col-span-2 bg-[#1e1e1e] border border-[#2c2c2c] p-4">
                <div class="flex items-center gap-2.5 mb-3">
                    <div class="w-0.5 h-3.5 bg-[#d32f2f]"></div>
                    <h3 class="text-[10px] font-semibold uppercase tracking-[0.15em] text-[#616161]">决策入口</h3>
                </div>
                <p class="text-xs text-[#9e9e9e] mb-3 leading-relaxed">
                    优先处理待审与待补价；依据齐备后再发起计算。上传类操作见侧栏各模块。
                </p>
                <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2" id="dashActions">
                    ${actionLink({ page: 'stamping-process-fee', label: '审核加工费', sub: '待审 / 待补价清单' })}
                    ${actionLink({ page: 'steel-price-list', label: '审核钢材联动价', sub: '本期联动价一览' })}
                    ${actionLink({ page: 'stamping-part-cost', label: '审核冲压零件价格', sub: '本期冲压件核价确认' })}
                    ${actionLink({ page: 'steel-price-calc', label: '发起钢材联动计算', sub: '基价 + 政策 → 联动价' })}
                    ${actionLink({ page: 'stamping-part-cost-calc', label: '发起冲压零件价格计算', sub: '材料 + 加工费 + 模具/检具' })}
                    ${actionLink({ page: 'scrap-price', label: '维护废料月度价', sub: '核价扣减依据' })}
                </div>
            </div>
        </div>
    `;
}
