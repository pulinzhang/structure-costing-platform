/**
 * BOM 焊接工艺拆解 — 生成页模板（对齐钢价计算布局）
 */

import { paginationBarHtml } from '../../../../page-size.js?v=3';

export function weldingProcessBreakdownGenerateTemplate() {
    return `
        <div class="space-y-4 w-full font-sans antialiased text-[#bbb]">

            <div class="flex items-center justify-between pb-2 border-b border-[#222]">
                <h1 class="text-xs font-bold text-[#e0e0e0] tracking-wider">焊接工艺拆解</h1>
                <a href="#/bom-welding-process-breakdown-list"
                   class="text-[10px] text-[#616161] hover:text-[#FF1E27] transition-colors">
                    前往拆解列表 →
                </a>
            </div>

            <div class="flex items-center justify-between py-2.5 border-y border-[#1e1e1e]"
                 style="background: linear-gradient(180deg, #181818 0%, #161616 100%);">
                <div class="flex items-end gap-3 flex-wrap px-1">
                    ${filterSelect('wpbGenLocation', '基地')}
                    ${filterSelect('wpbGenModel', '项目')}
                    ${filterSelect('wpbGenVersion', '版本')}
                    <button id="wpbGenResetBtn" type="button"
                            class="inline-flex items-center gap-1 h-7 px-3 text-[11px] font-medium text-[#616161] hover:text-[#9e9e9e] transition-all duration-150">
                        重置
                    </button>
                </div>
            </div>

            <div class="flex items-center justify-between border-b border-[#222] py-2.5">
                <div class="flex items-center gap-8">
                    <div>
                        <span class="text-[9px] text-[#666] block">焊接原文节点</span>
                        <span id="cntWeldNodes" class="text-xs font-mono font-bold text-[#dddddd]">- <span class="text-[9px] font-normal text-[#555]">条</span></span>
                    </div>
                    <div class="w-px h-5 bg-[#222]"></div>
                    <div>
                        <span class="text-[9px] text-[#666] block">现有拆解主表</span>
                        <span id="cntBreakdownNodes" class="text-xs font-mono font-bold text-[#dddddd]">- <span class="text-[9px] font-normal text-[#555]">条</span></span>
                    </div>
                    <div class="w-px h-5 bg-[#222]"></div>
                    <div>
                        <span class="text-[9px] text-[#666] block">已审锁定</span>
                        <span id="cntApproved" class="text-xs font-mono font-bold text-[#dddddd]">- <span class="text-[9px] font-normal text-[#555]">条</span></span>
                    </div>
                </div>

                <div class="flex items-center gap-3">
                    <span id="reGenNotice" class="text-[9px] text-[#666]">
                        再次拆解将覆盖未审核数据；已审核范围须先反审核
                    </span>
                    <button id="wpbGenSubmitBtn" type="button"
                            class="h-7 px-4 text-[10px] bg-[#b71c1c] hover:bg-[#c62828] text-white font-medium rounded-sm transition-colors disabled:opacity-30 disabled:cursor-not-allowed">
                        开始拆解
                    </button>
                </div>
            </div>

            <div id="calcProgressPanel" class="hidden border border-[#2c2c2c] bg-[#1a1a1a] px-4 py-3">
                <div class="flex items-center justify-between gap-3 mb-2.5">
                    <div class="flex items-center gap-2 min-w-0">
                        <div id="calcProgressSpinner" class="w-3.5 h-3.5 border-2 border-[#2c2c2c] border-t-[#d32f2f] rounded-full animate-spin shrink-0"></div>
                        <h5 id="calcProgressTitle" class="text-xs font-medium text-[#ffffff] truncate mb-0">正在拆解焊接工艺...</h5>
                    </div>
                    <span id="calcProgressPercent" class="text-xs font-mono tabular-nums text-[#d32f2f] shrink-0">0%</span>
                </div>
                <div class="h-1.5 w-full bg-[#0a0a0a] border border-[#2c2c2c] overflow-hidden mb-2">
                    <div id="calcProgressBar"
                         class="h-full bg-[#d32f2f] shadow-[0_0_8px_rgba(211,47,47,0.5)] transition-all duration-300"
                         style="width: 0%"></div>
                </div>
                <p id="calcProgressMsg" class="text-[11px] text-[#9e9e9e] leading-relaxed mb-0">已提交拆解队列</p>
            </div>

            <div id="dataReadyErrorBanner" class="hidden text-[10px] text-[#d69e2e] bg-[#1a1710] px-2.5 py-1.5 border-l-2 border-[#d69e2e]">
                提示：请选定基地 / 项目 / 版本，且材料清单需有焊接原文、无已审拆解。
            </div>

            <div class="pt-2">
                <div class="flex items-center justify-between mb-1.5">
                    <div class="text-[10px] text-[#666] font-medium">拆解历史</div>
                    <div class="flex items-center gap-3">
                        <button id="calcHistoryDeleteAllBtn" type="button"
                                class="hidden text-[9px] text-[#c62828] hover:text-[#ef5350] transition-colors">
                            删除全部
                        </button>
                        <button id="calcHistoryRefreshBtn" type="button"
                                class="text-[9px] text-[#616161] hover:text-[#9e9e9e] transition-colors">
                            刷新
                        </button>
                    </div>
                </div>
                <div class="bg-[#1e1e1e] border border-[#2c2c2c] overflow-hidden">
                    <div class="overflow-x-auto">
                        <table id="calcHistoryTable" class="w-full text-left border-collapse">
                            <thead>
                                <tr class="bg-[#0a0a0a] border-b border-[#2c2c2c] text-[9px] text-[#555] uppercase tracking-[0.08em]">
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">拆解时间</th>
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
                            <tbody id="calcHistoryBody" class="text-[10px] divide-y divide-[#222222]">
                                <tr>
                                    <td colspan="9" class="py-8 text-center text-[#555]">加载中..</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    ${paginationBarHtml({ infoId: 'calcHistoryTotal', selectId: 'wpbGenHistoryPageSize', buttonsId: 'calcHistoryPagination', wrapperClass: 'flex items-center justify-between px-3 py-2 border-t border-[#1e1e1e] bg-[#141414]' })}
                </div>
            </div>

        </div>
    `;
}

function filterSelect(id, label) {
    return `<label class="space-y-1">
        <span class="block text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em]">${label}</span>
        <select id="${id}" class="w-32 h-7 pl-2.5 pr-7 text-[11px] bg-[#0d0d0d] border border-[#272727] text-[#909090] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] rounded-sm">
            <option value="">请选择</option>
        </select>
    </label>`;
}

