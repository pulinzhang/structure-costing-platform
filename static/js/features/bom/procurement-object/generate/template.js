/**
 * 采购对象清单 — 生成页（对齐冲压零件价格计算壳 + 焊接拆解历史）
 */

import { paginationBarHtml } from '../../../../ui/page-size.js?v=6';
import { filterSelect, BTN_ABORT } from '../../../../ui/classes.js?v=11';

import { SECTION_LABELS } from '../labels.js?v=4';

export function procurementObjectGenerateTemplate() {
    return `
        <div class="space-y-4 w-full font-sans antialiased text-ink">

            <div class="flex items-center justify-between pb-2 border-b border-line-subtle">
                <h1 class="text-xs font-bold text-ink tracking-wider">生成采购对象清单</h1>
                <a href="#/bom-procurement-object-list"
                   class="text-[10px] text-ink-dim hover:text-brand-hud transition-colors">
                    前往采购对象清单 →
                </a>
            </div>

            <div class="flex items-center justify-between py-2.5 border-y border-app-surface">
                <div class="flex items-end gap-3 flex-wrap px-1">
                    ${filterSelect('poGenLocation', '基地', true)}
                    ${filterSelect('poGenModel', '项目', true)}
                    ${filterSelect('poGenVersion', '版本', true)}
                    <button id="poGenResetBtn"
                            class="inline-flex items-center gap-1 h-7 px-3 text-[11px] font-medium text-ink-dim hover:text-ink-muted transition-all duration-150">
                        重置
                    </button>
                </div>
            </div>

            <div class="flex items-center justify-between border-b border-line-subtle py-2.5">
                <div class="flex items-center gap-6 flex-wrap">
                    <div>
                        <span class="text-[9px] text-ink-dim block">BOM 节点</span>
                        <span id="poCntNodes" class="text-xs font-mono font-bold text-ink">- <span class="text-[9px] font-normal text-ink-faint">条</span></span>
                    </div>
                    <div class="w-px h-5 bg-app-surface"></div>
                    <div>
                        <span class="text-[9px] text-ink-dim block">将列入采购对象</span>
                        <span id="poCntObjects" class="text-xs font-mono font-bold text-ink">- <span class="text-[9px] font-normal text-ink-faint">条</span></span>
                    </div>
                    <div class="w-px h-5 bg-app-surface"></div>
                    <div>
                        <span class="text-[9px] text-ink-dim block">${SECTION_LABELS.other_leaf}</span>
                        <span id="poCntOther" class="text-xs font-mono font-bold text-ink">- <span class="text-[9px] font-normal text-ink-faint">条</span></span>
                    </div>
                    <div class="w-px h-5 bg-app-surface"></div>
                    <div>
                        <span class="text-[9px] text-ink-dim block">${SECTION_LABELS.anomaly}</span>
                        <span id="poCntAnomaly" class="text-xs font-mono font-bold text-ink">- <span class="text-[9px] font-normal text-ink-faint">条</span></span>
                    </div>
                    <div class="w-px h-5 bg-app-surface"></div>
                    <div>
                        <span class="text-[9px] text-ink-dim block">已审锁定</span>
                        <span id="poCntApproved" class="text-xs font-mono font-bold text-ink">- <span class="text-[9px] font-normal text-ink-faint">条</span></span>
                    </div>
                </div>

                <div class="flex items-center gap-3">
                    <span id="poGenNotice" class="text-[9px] text-ink-dim">
                        从材料清单树生成采购对象；同一版本再生成带回确认，已审须先反审核
                    </span>
                    <button id="poGenSubmitBtn"
                            class="${BTN_ABORT}">
                        开始生成
                    </button>
                </div>
            </div>

            <p class="text-[9px] text-ink-faint leading-relaxed px-1 -mt-1">
                供货总成无子件，或全部一级件都没有内部号，按退化供货件列入。一级件有内部号才进采购对象。
            </p>

            <div id="poGenProgressPanel" class="hidden border border-line bg-app-surface px-4 py-3">
                <div class="flex items-center justify-between gap-3 mb-2.5">
                    <div class="flex items-center gap-2 min-w-0">
                        <div id="poGenProgressSpinner" class="w-3.5 h-3.5 border-2 border-line border-brand rounded-full animate-spin shrink-0"></div>
                        <h5 id="poGenProgressTitle" class="text-xs font-medium text-ink truncate mb-0">正在生成采购对象清单...</h5>
                    </div>
                    <span id="poGenProgressPercent" class="text-xs font-mono tabular-nums text-brand shrink-0">0%</span>
                </div>
                <div class="h-1.5 w-full bg-app-deep border border-line overflow-hidden mb-2">
                    <div id="poGenProgressBar"
                         class="h-full bg-brand hud-brand-glow transition-all duration-300"
                         style="width: 0%"></div>
                </div>
                <p id="poGenProgressMsg" class="text-[11px] text-ink-muted leading-relaxed mb-0">正在读取材料清单树</p>
            </div>

            <div id="poGenReadyBanner" class="hidden text-[10px] text-warn bg-app-hud px-2.5 py-1.5 border-l-2 border-warn/40"></div>

            <div class="pt-2">
                <div class="flex items-center justify-between mb-1.5">
                    <div class="text-[10px] text-ink-dim font-medium">生成历史</div>
                    <button id="poGenHistoryRefreshBtn" type="button"
                            class="text-[9px] text-ink-dim hover:text-ink-muted transition-colors">
                        刷新
                    </button>
                </div>
                <div class="bg-app-surface border border-line overflow-hidden">
                    <div class="overflow-x-auto brabus-bg-grid">
                        <table id="poGenHistoryTable" class="w-full text-left border-collapse">
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
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">节点</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">采购对象</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">操作</th>
                                </tr>
                            </thead>
                            <tbody id="poGenHistoryBody" class="text-[10px] divide-y divide-line-subtle">
                                <tr>
                                    <td colspan="11" class="py-8 text-center text-ink-faint">加载中..</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    ${paginationBarHtml({ infoId: 'poGenHistoryTotal', selectId: 'poGenHistoryPageSize', buttonsId: 'poGenHistoryPagination', wrapperClass: 'flex items-center justify-between px-3 py-2 border-t border-app-surface bg-app-main' })}
                </div>
            </div>
        </div>
    `;
}


