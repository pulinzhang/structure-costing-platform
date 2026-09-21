/**
 * Dashboard Template
 * 管理者看板 — 本期产出 / 待办决策 / 核价闭环就绪
 */

import { HUD_KPI_FOCUS } from '../../ui/classes.js?v=8';

function actionLink({ page, label, sub }) {
    return `
        <a href="#/${page}" data-page="${page}"
           class="group flex flex-col gap-0.5 px-4 py-3 border border-line bg-app-main hover:border-brand hover:bg-brand-hud/10 transition-colors">
            <span class="text-xs font-medium text-ink group-hover:text-ink">${label}</span>
            <span class="text-[10px] text-ink-faint">${sub}</span>
        </a>
    `;
}

export function dashboardTemplate() {
    return `
        <!-- 作用域 -->
        <div class="flex flex-wrap items-end gap-3 mb-5 px-4 py-3 bg-app-hud border border-line-hud">
            <div class="flex flex-col gap-1">
                <label class="text-[9px] font-medium tracking-[0.08em] text-ink-faint uppercase" for="dashYear">核价年度</label>
                <select id="dashYear"
                    class="h-9 min-w-[6.5rem] px-3 text-xs bg-app-deep border border-line text-ink appearance-none cursor-pointer focus:outline-none focus:border-brand-active transition-all"></select>
            </div>
            <div class="flex flex-col gap-1">
                <label class="text-[9px] font-medium tracking-[0.08em] text-ink-faint uppercase" for="dashMonth">核价月份</label>
                <select id="dashMonth"
                    class="h-9 min-w-[5.5rem] px-3 text-xs bg-app-deep border border-line text-ink appearance-none cursor-pointer focus:outline-none focus:border-brand-active transition-all"></select>
            </div>
            <div class="flex flex-col gap-1">
                <label class="text-[9px] font-medium tracking-[0.08em] text-ink-faint uppercase" for="dashLocation">生产基地</label>
                <select id="dashLocation"
                    class="h-9 min-w-[8rem] px-3 text-xs bg-app-deep border border-line text-ink-muted appearance-none cursor-pointer focus:outline-none focus:border-brand-active transition-all">
                    <option value="">全部基地</option>
                </select>
            </div>
            <div class="flex flex-col gap-1">
                <label class="text-[9px] font-medium tracking-[0.08em] text-ink-faint uppercase" for="dashVehicle">项目</label>
                <select id="dashVehicle"
                    class="h-9 min-w-[8rem] px-3 text-xs bg-app-deep border border-line text-ink-muted appearance-none cursor-pointer focus:outline-none focus:border-brand-active transition-all">
                    <option value="">全部项目</option>
                </select>
            </div>
            <p class="text-[10px] text-ink-faint pb-2 ml-auto font-mono tracking-[0.04em]" id="dashScopeLabel">—</p>
        </div>

        <!-- 本期产出 HUD -->
        <div class="bg-app-hud border border-line-hud mb-5 overflow-hidden">
            <div class="px-5 pt-4 pb-4">
                <div class="flex items-center gap-2 mb-3">
                    <div class="w-0.5 h-3.5 bg-brand-hud"></div>
                    <h3 class="text-[10px] font-semibold uppercase tracking-[0.15em] text-ink-dim">本期核价产出</h3>
                    <span class="text-[10px] font-mono text-ink-faint" id="dashOutcomeSub">—</span>
                </div>
                <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 font-mono">
                    <div class="hud-kpi-card-glow ${HUD_KPI_FOCUS}">
                        <div class="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-brand-hud to-transparent hud-kpi-line-glow"></div>
                        <div class="text-brand-hud text-[10px] font-bold tracking-widest">冲压件均单价</div>
                        <div class="text-[26px] font-black text-brand-hud mt-1 tracking-tight tabular-nums">
                            ¥<span id="dashPartAvg">—</span>
                        </div>
                        <div class="text-[9px] text-brand-hud/60 mt-1" id="dashPartAvgMeta">已审 — · 待审 —</div>
                    </div>
                    <div class="bg-app-main/80 border border-line-hud p-3">
                        <div class="text-ink-faint text-[10px] tracking-wider">待办合计</div>
                        <div class="text-[22px] font-bold text-ink mt-1 tabular-nums">
                            <span id="dashPendingTotal" class="text-warn">—</span>
                            <span class="text-[10px] text-ink-faint ml-1">条</span>
                        </div>
                        <div class="text-[9px] text-ink-faint mt-1 font-mono" id="dashPendingBreakdown">加工费 — · 钢价 — · 冲压件 —</div>
                    </div>
                    <div class="bg-app-main/80 border border-line-hud p-3">
                        <div class="text-ink-faint text-[10px] tracking-wider">加工费待补价</div>
                        <div class="text-[22px] font-bold text-ink mt-1 tabular-nums">
                            <span id="dashFeeZero">—</span>
                            <span class="text-[10px] text-ink-faint ml-1">条</span>
                        </div>
                        <div class="text-[9px] text-ink-faint mt-1 font-mono" id="dashFeeAvg">件均 —</div>
                    </div>
                    <div class="bg-app-main/80 border border-line-hud p-3">
                        <div class="text-ink-faint text-[10px] tracking-wider">钢材联动均价</div>
                        <div class="text-[22px] font-bold text-ink mt-1 tabular-nums">
                            ¥<span id="dashSteelAvg">—</span>
                        </div>
                        <div class="text-[9px] text-ink-faint mt-1 font-mono" id="dashSteelMeta">已审 — · 待审 —</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="grid grid-cols-1 xl:grid-cols-5 gap-5 mb-5">
            <!-- 待办决策 -->
            <div class="xl:col-span-3 bg-app-surface border border-line">
                <div class="flex items-center justify-between gap-3 px-5 py-3 border-b border-line-subtle">
                    <div class="flex items-center gap-2.5">
                        <div class="w-0.5 h-3.5 bg-brand"></div>
                        <h3 class="text-[10px] font-semibold uppercase tracking-[0.15em] text-ink-dim">待办与风险</h3>
                    </div>
                    <span class="text-[10px] font-mono text-ink-faint" id="dashAttentionCount">0 项</span>
                </div>
                <div id="dashAttentionList" class="divide-y divide-line-subtle min-h-[12rem]">
                    <div class="px-5 py-8 text-center text-sm text-ink-faint">加载中…</div>
                </div>
            </div>

            <!-- 闭环就绪 -->
            <div class="xl:col-span-2 bg-app-surface border border-line">
                <div class="flex items-center justify-between gap-3 px-5 py-3 border-b border-line-subtle">
                    <div class="flex items-center gap-2.5">
                        <div class="w-0.5 h-3.5 bg-brand"></div>
                        <h3 class="text-[10px] font-semibold uppercase tracking-[0.15em] text-ink-dim">核价闭环就绪</h3>
                    </div>
                    <span class="text-[10px] font-mono tabular-nums text-ink-muted" id="dashReadyScore">—/6</span>
                </div>
                <div id="dashReadiness" class="p-4 space-y-2"></div>
                <div class="px-5 py-3 border-t border-line-subtle text-[10px] text-ink-faint leading-relaxed" id="dashReadyHint">
                    基价 · 政策 · 废料 · 加工费 · 钢价 · 冲压零件价，六项齐备方可闭环本期冲压核价。
                </div>
            </div>
        </div>

        <!-- 底盘上下文 + 管理者入口 -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-6">
            <div class="bg-app-surface border border-line p-4">
                <p class="text-[10px] font-semibold uppercase tracking-[0.15em] text-ink-dim mb-3">主数据底盘（随作用域）</p>
                <div id="dashMasterBlock" class="font-mono text-sm text-ink">—</div>
                <p class="mt-2 text-[10px] text-ink-faint" id="dashBomBlock">BOM —</p>
            </div>
            <div class="lg:col-span-2 bg-app-surface border border-line p-4">
                <div class="flex items-center gap-2.5 mb-3">
                    <div class="w-0.5 h-3.5 bg-brand"></div>
                    <h3 class="text-[10px] font-semibold uppercase tracking-[0.15em] text-ink-dim">决策入口</h3>
                </div>
                <p class="text-xs text-ink-muted mb-3 leading-relaxed">
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
