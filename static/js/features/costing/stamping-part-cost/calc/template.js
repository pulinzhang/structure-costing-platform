/**
 * 冲压零件价格计算页模板
 */

import { paginationBarHtml } from '../../../../ui/page-size.js?v=6';
import { filterSelect, BTN_ABORT } from '../../../../ui/classes.js?v=12';


export function partCostCalcTemplate() {
    return `
        <div class="space-y-4 w-full font-sans antialiased text-ink">

            <div class="flex items-center justify-between pb-2 border-b border-line-subtle">
                <h1 class="text-xs font-bold text-ink tracking-wider">冲压零件价格计算</h1>
            </div>

            <div class="flex items-center justify-between py-2.5 border-y border-app-surface">
                <div class="flex items-end gap-3 flex-wrap px-1">
                    ${filterSelect('calcYear', '年度', true)}
                    ${filterSelect('calcMonth', '月份', true)}
                    ${filterSelect('calcLocation', '基地', true)}
                    ${filterSelect('calcVehicleModel', '项目', true)}

                    <button id="calcResetBtn"
                            class="inline-flex items-center gap-1 h-7 px-3 text-[11px] font-medium text-ink-dim hover:text-ink-muted transition-all duration-150">
                        重置
                    </button>
                </div>
            </div>

            <div class="flex items-center justify-between border-b border-line-subtle py-2.5">
                <div class="flex items-center gap-6 flex-wrap">
                    <div>
                        <span class="text-[9px] text-ink-dim block">匹配零件</span>
                        <span id="cntParts" class="text-xs font-mono font-bold text-ink">- <span class="text-[9px] font-normal text-ink-faint">件</span></span>
                    </div>
                    <div class="w-px h-5 bg-app-surface"></div>
                    <div>
                        <span class="text-[9px] text-ink-dim block">钢材联动价</span>
                        <span id="cntSteel" class="text-xs font-mono font-bold text-ink">- <span class="text-[9px] font-normal text-ink-faint">条</span></span>
                    </div>
                    <div class="w-px h-5 bg-app-surface"></div>
                    <div>
                        <span class="text-[9px] text-ink-dim block">废料月度价</span>
                        <span id="cntScrap" class="text-xs font-mono font-bold text-ink">- <span class="text-[9px] font-normal text-ink-faint">条</span></span>
                    </div>
                    <div class="w-px h-5 bg-app-surface"></div>
                    <div>
                        <span class="text-[9px] text-ink-dim block">加工费</span>
                        <span id="cntFee" class="text-xs font-mono font-bold text-ink">- <span class="text-[9px] font-normal text-ink-faint">条</span></span>
                    </div>
                    <div class="w-px h-5 bg-app-surface"></div>
                    <div>
                        <span class="text-[9px] text-ink-dim block">模具费</span>
                        <span id="cntDieFee" class="text-xs font-mono font-bold text-ink">- <span class="text-[9px] font-normal text-ink-faint">条</span></span>
                    </div>
                    <div class="w-px h-5 bg-app-surface"></div>
                    <div>
                        <span class="text-[9px] text-ink-dim block">检具费</span>
                        <span id="cntGaugeFee" class="text-xs font-mono font-bold text-ink">- <span class="text-[9px] font-normal text-ink-faint">条</span></span>
                    </div>
                </div>

                <div class="flex items-center gap-3">
                    <span id="reCalcNotice" class="text-[9px] text-ink-dim">
                        按零件牌号+料厚取钢材联动价（多钢厂取最低）；再次计算覆盖未审核，已审核跳过
                    </span>
                    <button id="startCalcBtn"
                            class="${BTN_ABORT}">
                        开始计算
                    </button>
                </div>
            </div>

            <div id="calcProgressPanel" class="hidden border border-line bg-app-surface px-4 py-3">
                <div class="flex items-center justify-between gap-3 mb-2.5">
                    <div class="flex items-center gap-2 min-w-0">
                        <div id="calcProgressSpinner" class="w-3.5 h-3.5 border-2 border-line border-brand rounded-full animate-spin shrink-0"></div>
                        <h5 id="calcProgressTitle" class="text-xs font-medium text-ink truncate mb-0">正在核算零件价格...</h5>
                    </div>
                    <span id="calcProgressPercent" class="text-xs font-mono tabular-nums text-brand shrink-0">0%</span>
                </div>
                <div class="h-1.5 w-full bg-app-deep border border-line overflow-hidden mb-2">
                    <div id="calcProgressBar"
                         class="h-full bg-brand hud-brand-glow transition-all duration-300"
                         style="width: 0%"></div>
                </div>
                <p id="calcProgressMsg" class="text-[11px] text-ink-muted leading-relaxed mb-0">已提交计算队列</p>
            </div>

            <div id="dataReadyErrorBanner" class="hidden text-[10px] text-warn bg-app-hud px-2.5 py-1.5 border-l-2 border-warn/40">
                提示：须选定年度、月份、基地、项目。计算覆盖该车各冲压工厂。并确保钢材联动价、废料月度价、加工费与匹配零件均已就绪。模具费、检具费缺档按 0 计入。
            </div>

            <div class="pt-2">
                <div class="flex items-center justify-between mb-1.5">
                    <div class="text-[10px] text-ink-dim font-medium">计算历史</div>
                    <div class="flex items-center gap-3">
                        <button id="calcHistoryDeleteAllBtn" type="button"
                                class="hidden text-[9px] text-danger hover:text-danger transition-colors">
                            删除全部
                        </button>
                        <button id="calcHistoryRefreshBtn"
                                class="text-[9px] text-ink-dim hover:text-ink-muted transition-colors">
                            刷新
                        </button>
                    </div>
                </div>
                <div class="bg-app-surface border border-line overflow-hidden">
                    <div class="overflow-x-auto brabus-bg-grid">
                        <table id="calcHistoryTable" class="w-full text-left border-collapse">
                            <thead>
                                <tr class="bg-app-deep border-b border-line text-[9px] text-ink-faint uppercase tracking-[0.08em]">
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">开始</th>
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">结束</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">耗时</th>
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">创建人</th>
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">年月</th>
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">基地</th>
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">工厂</th>
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">筛选</th>
                                    <th class="py-2 px-2 font-normal text-center whitespace-nowrap">状态</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">零件</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">成功</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">失败</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">跳过</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">操作</th>
                                </tr>
                            </thead>
                            <tbody id="calcHistoryBody" class="text-[10px] divide-y divide-line-subtle">
                                <tr>
                                    <td colspan="14" class="py-8 text-center text-ink-faint">加载中..</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    ${paginationBarHtml({ infoId: 'calcHistoryTotal', selectId: 'partCostCalcHistoryPageSize', buttonsId: 'calcHistoryPagination', wrapperClass: 'flex items-center justify-between px-3 py-2 border-t border-app-surface bg-app-main' })}
                </div>
            </div>

        </div>
    `;
}


