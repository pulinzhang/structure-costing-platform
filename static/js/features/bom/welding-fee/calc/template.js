/**
 * BOM 焊接费计算页模板
 * 布局对齐钢材联动 / 冲压加工费：筛选 + 就绪统计 + 进度 + 计算历史
 */

import { paginationBarHtml } from '../../../../ui/page-size.js?v=6';
import { filterSelect, BTN_ABORT, BTN_GHOST } from '../../../../ui/classes.js?v=13';


export function l0WeldingFeeCalcTemplate() {
    return `
        <div class="space-y-4 w-full font-sans antialiased text-ink">

            <div class="flex items-center justify-between pb-2 border-b border-line-subtle">
                <h1 class="text-xs font-bold text-ink tracking-wider">焊接费计算</h1>
                <p class="text-[10px] text-ink-faint">公式与层级无关：有辅助量用辅助量，否则用过程量；长度 mm↔cm，面积 平方≡m2</p>
            </div>

            <div class="flex items-center justify-between py-2.5 border-y border-app-surface">
                <div class="flex items-end gap-3 flex-wrap px-1">
                    ${filterSelect('l0wfCalcYear', '年度', true)}
                    ${filterSelect('l0wfCalcLocation', '基地', true)}
                    ${filterSelect('l0wfCalcVehicleModel', '项目', true)}

                    <button id="l0wfCalcResetBtn"
                            class="${BTN_GHOST}">
                        重置
                    </button>
                </div>
            </div>

            <div class="flex items-center justify-between border-b border-line-subtle py-2.5">
                <div class="flex items-center gap-8">
                    <div>
                        <span class="text-[9px] text-ink-dim block">拆解节点</span>
                        <span id="l0wfCntL0" class="text-xs font-mono font-bold text-ink">- <span class="text-[9px] font-normal text-ink-faint">条</span></span>
                    </div>
                    <div class="w-px h-5 bg-app-surface"></div>
                    <div>
                        <span class="text-[9px] text-ink-dim block">焊接单价</span>
                        <span id="l0wfCntUnitPrice" class="text-xs font-mono font-bold text-ink">- <span class="text-[9px] font-normal text-ink-faint">条</span></span>
                    </div>
                    <div class="w-px h-5 bg-app-surface"></div>
                    <div>
                        <span class="text-[9px] text-ink-dim block">工艺行</span>
                        <span id="l0wfCntProcessLines" class="text-xs font-mono font-bold text-ink">- <span class="text-[9px] font-normal text-ink-faint">行</span></span>
                    </div>
                    <div class="w-px h-5 bg-app-surface"></div>
                    <div title="工艺数为 0 的节点（异常）">
                        <span class="text-[9px] text-ink-dim block">无工艺节点（异常）</span>
                        <span id="l0wfCntZeroProcess" class="text-xs font-mono font-bold text-ink">- <span class="text-[9px] font-normal text-ink-faint">条</span></span>
                    </div>
                </div>

                <div class="flex items-center gap-3">
                    <span id="l0wfReCalcNotice" class="text-[9px] text-ink-dim">
                        再算一次时，没审核的会重写；已经审核的那一行不动。
                    </span>
                    <button id="l0wfStartCalcBtn"
                            class="${BTN_ABORT}">
                        开始计算
                    </button>
                </div>
            </div>

            <div id="l0wfCalcProgressPanel" class="hidden border border-line bg-app-surface px-4 py-3">
                <div class="flex items-center justify-between gap-3 mb-2.5">
                    <div class="flex items-center gap-2 min-w-0">
                        <div id="l0wfCalcProgressSpinner" class="w-3.5 h-3.5 border-2 border-line border-brand rounded-full animate-spin shrink-0"></div>
                        <h5 id="l0wfCalcProgressTitle" class="text-xs font-medium text-ink truncate mb-0">正在计算焊接费…</h5>
                    </div>
                    <span id="l0wfCalcProgressPercent" class="text-xs font-mono tabular-nums text-brand shrink-0">0%</span>
                </div>
                <div class="h-1.5 w-full bg-app-deep border border-line overflow-hidden mb-2">
                    <div id="l0wfCalcProgressBar"
                         class="h-full bg-brand hud-brand-glow transition-all duration-300"
                         style="width: 0%"></div>
                </div>
                <p id="l0wfCalcProgressMsg" class="text-[11px] text-ink-muted leading-relaxed mb-0">已提交计算队列</p>
            </div>

            <div id="l0wfDataReadyErrorBanner" class="hidden text-[10px] text-warn bg-app-hud px-2.5 py-1.5 border-l-2 border-warn/40">
                提示：先选年度、基地、项目。这一年还有效的焊接工艺拆解，以及当年焊接单价，都必须有。
            </div>

            <div class="pt-2">
                <div class="flex items-center justify-between mb-1.5">
                    <div class="text-[10px] text-ink-dim font-medium">计算历史</div>
                    <div class="flex items-center gap-3">
                        <button id="l0wfCalcHistoryDeleteAllBtn" type="button"
                                class="hidden text-[9px] text-danger hover:text-danger transition-colors">
                            删除全部
                        </button>
                        <button id="l0wfCalcHistoryRefreshBtn"
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
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">创建人</th>
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">年度</th>
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">基地</th>
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">项目</th>
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">版本</th>
                                    <th class="py-2 px-2 font-normal text-center whitespace-nowrap">状态</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">成品</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">新增</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">更新</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">失败</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">缺单价</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">跳过</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">操作</th>
                                </tr>
                            </thead>
                            <tbody id="l0wfCalcHistoryBody" class="text-[10px] divide-y divide-line-subtle">
                                <tr>
                                    <td colspan="16" class="py-8 text-center text-ink-faint">加载中..</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    ${paginationBarHtml({ infoId: 'l0wfCalcHistoryTotal', selectId: 'l0wfCalcHistoryPageSize', buttonsId: 'l0wfCalcHistoryPagination', wrapperClass: 'flex items-center justify-between px-3 py-2 border-t border-app-surface bg-app-main' })}
                </div>
            </div>

        </div>
    `;
}


