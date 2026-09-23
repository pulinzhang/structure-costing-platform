/**
 * Steel Price Linked Settlement Template
 * 冲压钢材：基准价与加减价联动计算
 */

import { paginationBarHtml } from '../../../../ui/page-size.js?v=6';
import { filterSelect, BTN_ABORT, BTN_GHOST } from '../../../../ui/classes.js?v=13';


export function steelPriceCalcTemplate() {
    return `
        <div class="space-y-4 w-full font-sans antialiased text-ink">
            
            <div class="flex items-center justify-between pb-2 border-b border-line-subtle">
                <h1 class="text-xs font-bold text-ink tracking-wider">冲压钢材基准价与加减价联动计算</h1>
            </div>

            <div class="flex items-center justify-between py-2.5 border-y border-app-surface">
                <div class="flex items-end gap-3 flex-wrap px-1">
                    ${filterSelect('calcYear', '年度')}
                    ${filterSelect('calcMonth', '月份')}
                    ${filterSelect('calcLocation', '基地')}
                    ${filterSelect('calcVehicle', '项目')}

                    <button id="calcResetBtn"
                            class="${BTN_GHOST}">
                        重置
                    </button>
                </div>
            </div>

            <div class="flex items-center justify-between border-b border-line-subtle py-2.5">
                <div class="flex items-center gap-8">
                    <a href="javascript:void(0)" onclick="openDetailModal('basePrice')" class="group">
                        <span class="text-[9px] text-ink-dim block group-hover:text-ink-muted">中标基价库</span>
                        <span id="cntBasePrice" class="text-xs font-mono font-bold text-ink group-hover:text-ink">- <span class="text-[9px] font-normal text-ink-faint">条</span></span>
                    </a>
                    
                    <div class="w-px h-5 bg-app-surface"></div>

                    <a href="javascript:void(0)" onclick="openDetailModal('adjustRule')" class="group">
                        <span class="text-[9px] text-ink-dim block group-hover:text-ink-muted">厚/宽调价规则</span>
                        <span id="cntAdjustment" class="text-xs font-mono font-bold text-ink group-hover:text-ink">- <span class="text-[9px] font-normal text-ink-faint">条</span></span>
                    </a>

                    <div class="w-px h-5 bg-app-surface"></div>

                    <a href="javascript:void(0)" onclick="openDetailModal('specs')" class="group">
                        <span class="text-[9px] text-ink-dim block group-hover:text-ink-muted">厚度规格行数</span>
                        <span id="cntThicknessRows" class="text-xs font-mono font-bold text-ink group-hover:text-ink">- <span class="text-[9px] font-normal text-ink-faint">表</span></span>
                    </a>
                </div>

                <div class="flex items-center gap-3">
                    <span id="reCalcNotice" class="text-[9px] text-ink-dim">
                        统计可按项目看基价/政策/规格覆盖（一车多厂）；计算仍按基地全量牌号+料厚落库
                    </span>
                    <button id="startCalcBtn"
                            class="${BTN_ABORT}">
                        开始计算
                    </button>
                </div>
            </div>

            <!-- 后台计算进度 -->
            <div id="calcProgressPanel" class="hidden border border-line bg-app-surface px-4 py-3">
                <div class="flex items-center justify-between gap-3 mb-2.5">
                    <div class="flex items-center gap-2 min-w-0">
                        <div id="calcProgressSpinner" class="w-3.5 h-3.5 border-2 border-line border-brand rounded-full animate-spin shrink-0"></div>
                        <h5 id="calcProgressTitle" class="text-xs font-medium text-ink truncate mb-0">正在计算联动钢价...</h5>
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
                提示：当前所选年月缺失中标基价或调价规则，无法计算。
            </div>

            <!-- 计算历史：对齐批次日志字段-->
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
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">核价期</th>
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">基地</th>
                                    <th class="py-2 px-2 font-normal text-center whitespace-nowrap">状态</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">材料</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">命中</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">无基价</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">新增</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">更新</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">失败</th>
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
                    ${paginationBarHtml({ infoId: 'calcHistoryTotal', selectId: 'steelCalcHistoryPageSize', buttonsId: 'calcHistoryPagination', wrapperClass: 'flex items-center justify-between px-3 py-2 border-t border-app-surface bg-app-main' })}
                </div>
            </div>

        </div>
    `;
}


