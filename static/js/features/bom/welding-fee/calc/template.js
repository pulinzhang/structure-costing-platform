/**
 * BOM 焊接费计算页模板
 * 布局对齐钢材联动 / 冲压加工费：筛选 + 就绪统计 + 进度 + 计算历史
 */

import { paginationBarHtml } from '../../../../page-size.js?v=3';

export function l0WeldingFeeCalcTemplate() {
    return `
        <div class="space-y-4 w-full font-sans antialiased text-[#bbb]">

            <div class="flex items-center justify-between pb-2 border-b border-[#222]">
                <h1 class="text-xs font-bold text-[#e0e0e0] tracking-wider">焊接费计算</h1>
                <p class="text-[10px] text-[#555555]">公式与层级无关：有辅助量用辅助量，否则用过程量；长度 mm↔cm，面积 平方≡m2</p>
            </div>

            <div class="flex items-center justify-between py-2.5 border-y border-[#1e1e1e]"
                 style="background: linear-gradient(180deg, #181818 0%, #161616 100%);">
                <div class="flex items-end gap-3 flex-wrap px-1">
                    ${filterSelect('l0wfCalcYear', '年度', true)}
                    ${filterSelect('l0wfCalcLocation', '基地', true)}
                    ${filterSelect('l0wfCalcVehicleModel', '项目', true)}

                    <button id="l0wfCalcResetBtn"
                            class="inline-flex items-center gap-1 h-7 px-3 text-[11px] font-medium text-[#616161] hover:text-[#9e9e9e] transition-all duration-150">
                        重置
                    </button>
                </div>
            </div>

            <div class="flex items-center justify-between border-b border-[#222] py-2.5">
                <div class="flex items-center gap-8">
                    <div>
                        <span class="text-[9px] text-[#666] block">拆解节点</span>
                        <span id="l0wfCntL0" class="text-xs font-mono font-bold text-[#dddddd]">- <span class="text-[9px] font-normal text-[#555]">条</span></span>
                    </div>
                    <div class="w-px h-5 bg-[#222]"></div>
                    <div>
                        <span class="text-[9px] text-[#666] block">焊接单价</span>
                        <span id="l0wfCntUnitPrice" class="text-xs font-mono font-bold text-[#dddddd]">- <span class="text-[9px] font-normal text-[#555]">条</span></span>
                    </div>
                    <div class="w-px h-5 bg-[#222]"></div>
                    <div>
                        <span class="text-[9px] text-[#666] block">工艺行</span>
                        <span id="l0wfCntProcessLines" class="text-xs font-mono font-bold text-[#dddddd]">- <span class="text-[9px] font-normal text-[#555]">行</span></span>
                    </div>
                    <div class="w-px h-5 bg-[#222]"></div>
                    <div title="工艺数为 0 的节点（异常）">
                        <span class="text-[9px] text-[#666] block">无工艺节点（异常）</span>
                        <span id="l0wfCntZeroProcess" class="text-xs font-mono font-bold text-[#dddddd]">- <span class="text-[9px] font-normal text-[#555]">条</span></span>
                    </div>
                </div>

                <div class="flex items-center gap-3">
                    <span id="l0wfReCalcNotice" class="text-[9px] text-[#666]">
                        再次计算覆盖未审核，已审核按行跳过
                    </span>
                    <button id="l0wfStartCalcBtn"
                            class="h-7 px-4 text-[10px] bg-[#b71c1c] hover:bg-[#c62828] text-white font-medium rounded-sm transition-colors disabled:opacity-30 disabled:cursor-not-allowed">
                        开始计算
                    </button>
                </div>
            </div>

            <div id="l0wfCalcProgressPanel" class="hidden border border-[#2c2c2c] bg-[#1a1a1a] px-4 py-3">
                <div class="flex items-center justify-between gap-3 mb-2.5">
                    <div class="flex items-center gap-2 min-w-0">
                        <div id="l0wfCalcProgressSpinner" class="w-3.5 h-3.5 border-2 border-[#2c2c2c] border-t-[#d32f2f] rounded-full animate-spin shrink-0"></div>
                        <h5 id="l0wfCalcProgressTitle" class="text-xs font-medium text-[#ffffff] truncate mb-0">正在计算焊接费…</h5>
                    </div>
                    <span id="l0wfCalcProgressPercent" class="text-xs font-mono tabular-nums text-[#d32f2f] shrink-0">0%</span>
                </div>
                <div class="h-1.5 w-full bg-[#0a0a0a] border border-[#2c2c2c] overflow-hidden mb-2">
                    <div id="l0wfCalcProgressBar"
                         class="h-full bg-[#d32f2f] shadow-[0_0_8px_rgba(211,47,47,0.5)] transition-all duration-300"
                         style="width: 0%"></div>
                </div>
                <p id="l0wfCalcProgressMsg" class="text-[11px] text-[#9e9e9e] leading-relaxed mb-0">已提交计算队列</p>
            </div>

            <div id="l0wfDataReadyErrorBanner" class="hidden text-[10px] text-[#d69e2e] bg-[#1a1710] px-2.5 py-1.5 border-l-2 border-[#d69e2e]">
                提示：须选定年度、基地、项目；并确保存在有效期内的焊接工艺拆解与该年焊接单价。
            </div>

            <div class="pt-2">
                <div class="flex items-center justify-between mb-1.5">
                    <div class="text-[10px] text-[#666] font-medium">计算历史</div>
                    <div class="flex items-center gap-3">
                        <button id="l0wfCalcHistoryDeleteAllBtn" type="button"
                                class="hidden text-[9px] text-[#c62828] hover:text-[#ef5350] transition-colors">
                            删除全部
                        </button>
                        <button id="l0wfCalcHistoryRefreshBtn"
                                class="text-[9px] text-[#616161] hover:text-[#9e9e9e] transition-colors">
                            刷新
                        </button>
                    </div>
                </div>
                <div class="bg-[#1e1e1e] border border-[#2c2c2c] overflow-hidden">
                    <div class="overflow-x-auto">
                        <table class="w-full text-left border-collapse">
                            <thead>
                                <tr class="bg-[#0a0a0a] border-b border-[#2c2c2c] text-[9px] text-[#555] uppercase tracking-[0.08em]">
                                    <th class="py-2 px-2 font-normal whitespace-nowrap">计算时间</th>
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
                            <tbody id="l0wfCalcHistoryBody" class="text-[10px] divide-y divide-[#222222]">
                                <tr>
                                    <td colspan="14" class="py-8 text-center text-[#555]">加载中..</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    ${paginationBarHtml({ infoId: 'l0wfCalcHistoryTotal', selectId: 'l0wfCalcHistoryPageSize', buttonsId: 'l0wfCalcHistoryPagination', wrapperClass: 'flex items-center justify-between px-3 py-2 border-t border-[#1e1e1e] bg-[#141414]' })}
                </div>
            </div>

        </div>
    `;
}

function filterSelect(id, label, required = false) {
    const mark = required ? '<span class="text-[#d32f2f]">*</span>' : '';
    return `<label class="space-y-1">
        <span class="block text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em]">${label}${mark}</span>
        <select id="${id}" class="w-32 h-7 pl-2.5 pr-7 text-[11px] bg-[#0d0d0d] border border-[#272727] text-[#909090] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] rounded-sm">
            <option value="">请选择</option>
        </select>
    </label>`;
}

