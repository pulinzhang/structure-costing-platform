/**
 * 总成核价计算页模板
 */

import { paginationBarHtml } from '../../../../ui/page-size.js?v=6';
import { filterSelect, BTN_ABORT, BTN_GHOST } from '../../../../ui/classes.js?v=13';


export function assemblyCostCalcTemplate() {
    return `
        <div class="space-y-4 w-full font-sans antialiased text-ink">

            <div class="flex items-center justify-between pb-2 border-b border-line-subtle">
                <h1 class="text-xs font-bold text-ink tracking-wider">总成核价计算</h1>
            </div>

            <div class="flex items-center justify-between py-2.5 border-y border-app-surface">
                <div class="flex items-end gap-3 flex-wrap px-1">
                    ${filterSelect('lacCalcYear', '年度', true)}
                    ${filterSelect('lacCalcMonth', '月份', true)}
                    ${filterSelect('lacCalcLocation', '基地', true)}
                    ${filterSelect('lacCalcVehicleModel', '项目', true)}

                    <button id="lacCalcResetBtn"
                            class="${BTN_GHOST}">
                        重置
                    </button>
                </div>
            </div>

            <div class="flex items-center justify-between border-b border-line-subtle py-2.5">
                <div class="flex items-center gap-6 flex-wrap">
                    <div>
                        <span class="text-[9px] text-ink-dim block">树根</span>
                        <span id="lacCntTreeRoot" class="text-xs font-mono font-bold text-ink">- <span class="text-[9px] font-normal text-ink-faint">条</span></span>
                    </div>
                    <div class="w-px h-5 bg-app-surface"></div>
                    <div>
                        <span class="text-[9px] text-ink-dim block">主体</span>
                        <span id="lacCntSubject" class="text-xs font-mono font-bold text-ink">- <span class="text-[9px] font-normal text-ink-faint">条</span></span>
                    </div>
                    <div class="w-px h-5 bg-app-surface"></div>
                    <div>
                        <span class="text-[9px] text-ink-dim block">清单对象</span>
                        <span id="lacCntProcObj" class="text-xs font-mono font-bold text-ink">- <span class="text-[9px] font-normal text-ink-faint">条</span></span>
                    </div>
                    <div class="w-px h-5 bg-app-surface"></div>
                    <div>
                        <span class="text-[9px] text-ink-dim block">冲压价</span>
                        <span id="lacCntStamping" class="text-xs font-mono font-bold text-ink">- <span class="text-[9px] font-normal text-ink-faint">条</span></span>
                    </div>
                    <div class="w-px h-5 bg-app-surface"></div>
                    <div>
                        <span class="text-[9px] text-ink-dim block">年度价</span>
                        <span id="lacCntAnnual" class="text-xs font-mono font-bold text-ink">- <span class="text-[9px] font-normal text-ink-faint">条</span></span>
                    </div>
                    <div class="w-px h-5 bg-app-surface"></div>
                    <div>
                        <span class="text-[9px] text-ink-dim block">焊接费</span>
                        <span id="lacCntWelding" class="text-xs font-mono font-bold text-ink">- <span class="text-[9px] font-normal text-ink-faint">条</span></span>
                    </div>
                    <div class="w-px h-5 bg-app-surface"></div>
                    <div>
                        <span class="text-[9px] text-ink-dim block">包装运输</span>
                        <span id="lacCntPackaging" class="text-xs font-mono font-bold text-ink">- <span class="text-[9px] font-normal text-ink-faint">条</span></span>
                    </div>
                </div>

                <div class="flex items-center gap-3">
                    <span class="text-[9px] text-ink-dim">再次计算覆盖未审核；已审核跳过</span>
                    <button id="lacStartCalcBtn"
                            class="${BTN_ABORT}"
                            disabled>
                        开始计算
                    </button>
                </div>
            </div>

            <div id="lacCalcProgressPanel" class="hidden border border-line bg-app-surface px-4 py-3">
                <div class="flex items-center justify-between gap-3 mb-2.5">
                    <div class="flex items-center gap-2 min-w-0">
                        <div id="lacCalcProgressSpinner" class="w-3.5 h-3.5 border-2 border-line border-brand rounded-full animate-spin shrink-0"></div>
                        <h5 id="lacCalcProgressTitle" class="text-xs font-medium text-ink truncate mb-0">正在核算总成价格...</h5>
                    </div>
                    <span id="lacCalcProgressPercent" class="text-xs font-mono tabular-nums text-brand shrink-0">0%</span>
                </div>
                <div class="h-1.5 w-full bg-app-deep border border-line overflow-hidden mb-2">
                    <div id="lacCalcProgressBar"
                         class="h-full bg-brand hud-brand-glow transition-all duration-300"
                         style="width: 0%"></div>
                </div>
                <p id="lacCalcProgressMsg" class="text-[11px] text-ink-muted leading-relaxed mb-0">已提交计算队列</p>
            </div>

            <div id="lacDataReadyErrorBanner" class="hidden text-[10px] text-warn bg-app-hud px-2.5 py-1.5 border-l-2 border-warn/40"></div>

            <div class="pt-2">
                <div class="flex items-center justify-between mb-1.5">
                    <div class="text-[10px] text-ink-dim font-medium">计算历史</div>
                    <div class="flex items-center gap-3">
                        <button id="lacCalcHistoryDeleteAllBtn" type="button"
                                class="hidden text-[9px] text-danger hover:text-danger transition-colors">
                            删除全部
                        </button>
                        <button id="lacCalcHistoryRefreshBtn"
                                class="text-[9px] text-ink-dim hover:text-ink-muted transition-colors">
                            刷新
                        </button>
                    </div>
                </div>
                <div class="bg-app-surface border border-line overflow-hidden">
                    <div class="overflow-x-auto brabus-bg-grid">
                        <table class="w-full text-left border-collapse">
                            <thead>
                                <tr class="bg-app-deep border-b border-line text-[9px] text-ink-faint uppercase tracking-[0.08em]">
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">开始</th>
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">结束</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">耗时</th>
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">操作人</th>
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">年月</th>
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">基地</th>
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">项目</th>
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">版本</th>
                                    <th class="py-2 px-2 font-normal text-center whitespace-nowrap">状态</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">主体</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">成功</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">部分成功</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">失败</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">跳过</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">操作</th>
                                </tr>
                            </thead>
                            <tbody id="lacCalcHistoryBody" class="text-[10px] divide-y divide-line-subtle">
                                <tr>
                                    <td colspan="15" class="py-8 text-center text-ink-faint">加载中..</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    ${paginationBarHtml({ infoId: 'lacCalcHistoryTotal', selectId: 'lacCalcHistoryPageSize', buttonsId: 'lacCalcHistoryPagination', wrapperClass: 'flex items-center justify-between px-3 py-2 border-t border-app-surface bg-app-main' })}
                </div>
            </div>

        </div>
    `;
}


