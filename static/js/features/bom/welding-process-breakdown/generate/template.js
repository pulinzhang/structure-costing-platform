/**
 * BOM 焊接工艺拆解 — 生成页模板（对齐钢价计算布局）
 */

import { paginationBarHtml } from '../../../../ui/page-size.js?v=6';
import { filterSelect, BTN_ABORT, BTN_GHOST } from '../../../../ui/classes.js?v=13';


export function weldingProcessBreakdownGenerateTemplate() {
    return `
        <div class="space-y-4 w-full font-sans antialiased text-ink">

            <div class="flex items-center justify-between pb-2 border-b border-line-subtle">
                <h1 class="text-xs font-bold text-ink tracking-wider">焊接工艺拆解</h1>
                <a href="#/bom-welding-process-breakdown-list"
                   class="text-[10px] text-ink-dim hover:text-brand-hud transition-colors">
                    前往拆解列表 →
                </a>
            </div>

            <div class="flex items-center justify-between py-2.5 border-y border-app-surface">
                <div class="flex items-end gap-3 flex-wrap px-1">
                    ${filterSelect('wpbGenLocation', '基地')}
                    ${filterSelect('wpbGenModel', '项目')}
                    ${filterSelect('wpbGenVersion', '版本')}
                    <button id="wpbGenResetBtn" type="button"
                            class="${BTN_GHOST}">
                        重置
                    </button>
                </div>
            </div>

            <div class="flex items-center justify-between border-b border-line-subtle py-2.5">
                <div class="flex items-center gap-8">
                    <div>
                        <span class="text-[9px] text-ink-dim block">焊接原文节点</span>
                        <span id="cntWeldNodes" class="text-xs font-mono font-bold text-ink">- <span class="text-[9px] font-normal text-ink-faint">条</span></span>
                    </div>
                    <div class="w-px h-5 bg-app-surface"></div>
                    <div>
                        <span class="text-[9px] text-ink-dim block">现有拆解主表</span>
                        <span id="cntBreakdownNodes" class="text-xs font-mono font-bold text-ink">- <span class="text-[9px] font-normal text-ink-faint">条</span></span>
                    </div>
                    <div class="w-px h-5 bg-app-surface"></div>
                    <div>
                        <span class="text-[9px] text-ink-dim block">已审锁定</span>
                        <span id="cntApproved" class="text-xs font-mono font-bold text-ink">- <span class="text-[9px] font-normal text-ink-faint">条</span></span>
                    </div>
                </div>

                <div class="flex items-center gap-3">
                    <span id="reGenNotice" class="text-[9px] text-ink-dim">
                        再次拆解将覆盖未审核数据；已审核范围须先反审核
                    </span>
                    <button id="wpbGenSubmitBtn" type="button"
                            class="${BTN_ABORT}">
                        开始拆解
                    </button>
                </div>
            </div>

            <div id="calcProgressPanel" class="hidden border border-line bg-app-surface px-4 py-3">
                <div class="flex items-center justify-between gap-3 mb-2.5">
                    <div class="flex items-center gap-2 min-w-0">
                        <div id="calcProgressSpinner" class="w-3.5 h-3.5 border-2 border-line border-brand rounded-full animate-spin shrink-0"></div>
                        <h5 id="calcProgressTitle" class="text-xs font-medium text-ink truncate mb-0">正在拆解焊接工艺...</h5>
                    </div>
                    <span id="calcProgressPercent" class="text-xs font-mono tabular-nums text-brand shrink-0">0%</span>
                </div>
                <div class="h-1.5 w-full bg-app-deep border border-line overflow-hidden mb-2">
                    <div id="calcProgressBar"
                         class="h-full bg-brand hud-brand-glow transition-all duration-300"
                         style="width: 0%"></div>
                </div>
                <p id="calcProgressMsg" class="text-[11px] text-ink-muted leading-relaxed mb-0">已提交拆解队列</p>
            </div>

            <div id="dataReadyErrorBanner" class="hidden text-[10px] text-warn bg-app-hud px-2.5 py-1.5 border-l-2 border-warn/40">
                提示：请选定基地 / 项目 / 版本，且材料清单需有焊接原文、无已审拆解。
            </div>

            <div class="pt-2">
                <div class="flex items-center justify-between mb-1.5">
                    <div class="text-[10px] text-ink-dim font-medium">拆解历史</div>
                    <div class="flex items-center gap-3">
                        <button id="calcHistoryDeleteAllBtn" type="button"
                                class="hidden text-[9px] text-danger hover:text-danger transition-colors">
                            删除全部
                        </button>
                        <button id="calcHistoryRefreshBtn" type="button"
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
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">基地</th>
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">项目</th>
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">版本</th>
                                    <th class="py-2 px-2 font-normal text-center whitespace-nowrap">状态</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">主表</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">明细</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">操作</th>
                                </tr>
                            </thead>
                            <tbody id="calcHistoryBody" class="text-[10px] divide-y divide-line-subtle">
                                <tr>
                                    <td colspan="11" class="py-8 text-center text-ink-faint">加载中..</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    ${paginationBarHtml({ infoId: 'calcHistoryTotal', selectId: 'wpbGenHistoryPageSize', buttonsId: 'calcHistoryPagination', wrapperClass: 'flex items-center justify-between px-3 py-2 border-t border-app-surface bg-app-main' })}
                </div>
            </div>

        </div>
    `;
}


