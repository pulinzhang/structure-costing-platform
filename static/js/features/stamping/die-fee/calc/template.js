/**
 * 冲压模具费计算页模板
 */

import { pageSizeSelectHtml } from '../../../../page-size.js?v=2';

export function dieFeeCalcTemplate() {
    return `
        <div class="space-y-4 w-full font-sans antialiased text-[#bbb]">
            <div class="flex items-center justify-between pb-2 border-b border-[#222]">
                <h1 class="text-xs font-bold text-[#e0e0e0] tracking-wider">冲压模具费计算</h1>
            </div>
            <div class="flex items-center justify-between py-2.5 border-y border-[#1e1e1e]"
                 style="background: linear-gradient(180deg, #181818 0%, #161616 100%);">
                <div class="flex items-end gap-3 flex-wrap px-1">
                    <label class="space-y-1">
                        <span class="block text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em]">年度<span class="text-[#d32f2f]">*</span></span>
                        <input id="calcYear" type="number" min="2000" max="2100"
                               class="w-28 h-7 px-2.5 text-[11px] bg-[#0d0d0d] border border-[#272727] text-[#909090] focus:outline-none focus:border-[#ff5252] rounded-sm">
                    </label>
                    ${filterSelect('calcLocation', '基地', true)}
                    ${filterSelect('calcVehicleModel', '项目', true)}
                    <button id="calcResetBtn"
                            class="inline-flex items-center gap-1 h-7 px-3 text-[11px] font-medium text-[#616161] hover:text-[#9e9e9e] transition-all duration-150">
                        重置
                    </button>
                </div>
            </div>
            <div class="flex items-center justify-between border-b border-[#222] py-2.5">
                <div class="flex items-center gap-8">
                    <div>
                        <span class="text-[9px] text-[#666] block">布点零件</span>
                        <span id="cntParts" class="text-xs font-mono font-bold text-[#dddddd]">- <span class="text-[9px] font-normal text-[#555]">件</span></span>
                    </div>
                    <div class="w-px h-5 bg-[#222]"></div>
                    <div>
                        <span class="text-[9px] text-[#666] block">可算件数</span>
                        <span id="cntCalculable" class="text-xs font-mono font-bold text-[#dddddd]">- <span class="text-[9px] font-normal text-[#555]">件</span></span>
                    </div>
                    <div class="w-px h-5 bg-[#222]"></div>
                    <div>
                        <span class="text-[9px] text-[#666] block">生效单价</span>
                        <span id="cntUnitPrice" class="text-xs font-mono font-bold text-[#dddddd]">-</span>
                    </div>
                </div>
                <div class="flex items-center gap-3">
                    <span class="text-[9px] text-[#666]">再次计算将删除该范围未审核结果后重写；已审核禁止计算</span>
                    <button id="startCalcBtn"
                            class="h-7 px-4 text-[10px] bg-[#b71c1c] hover:bg-[#c62828] text-white font-medium rounded-sm transition-colors disabled:opacity-30 disabled:cursor-not-allowed">
                        开始计算
                    </button>
                </div>
            </div>
            <div id="calcProgressPanel" class="hidden border border-[#2c2c2c] bg-[#1a1a1a] px-4 py-3">
                <div class="flex items-center justify-between gap-3 mb-2.5">
                    <div class="flex items-center gap-2 min-w-0">
                        <div id="calcProgressSpinner" class="w-3.5 h-3.5 border-2 border-[#2c2c2c] border-t-[#d32f2f] rounded-full animate-spin shrink-0"></div>
                        <h5 id="calcProgressTitle" class="text-xs font-medium text-[#ffffff] truncate mb-0">正在计算模具费..</h5>
                    </div>
                    <span id="calcProgressPercent" class="text-xs font-mono tabular-nums text-[#d32f2f] shrink-0">0%</span>
                </div>
                <div class="h-1.5 w-full bg-[#0a0a0a] border border-[#2c2c2c] overflow-hidden mb-2">
                    <div id="calcProgressBar" class="h-full bg-[#d32f2f] shadow-[0_0_8px_rgba(211,47,47,0.5)] transition-all duration-300" style="width: 0%"></div>
                </div>
                <p id="calcProgressMsg" class="text-[11px] text-[#9e9e9e] leading-relaxed mb-0">已提交计算队列</p>
            </div>
            <div id="dataReadyErrorBanner" class="hidden text-[10px] text-[#d69e2e] bg-[#1a1710] px-2.5 py-1.5 border-l-2 border-[#d69e2e]">
                须选定年度、基地、项目，并确保有布点与生效模具单价。
            </div>
            <div class="pt-2">
                <div class="flex items-center justify-between mb-1.5">
                    <div class="text-[10px] text-[#666] font-medium">计算历史</div>
                    <button id="calcHistoryRefreshBtn" class="text-[9px] text-[#616161] hover:text-[#9e9e9e] transition-colors">刷新</button>
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
                                    <th class="py-2 px-2 font-normal text-center whitespace-nowrap">状态</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">布点</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">入库</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">跳过</th>
                                    <th class="py-2 px-2 font-normal text-right whitespace-nowrap">操作</th>
                                </tr>
                            </thead>
                            <tbody id="calcHistoryBody" class="text-[10px] divide-y divide-[#222222]">
                                <tr><td colspan="10" class="py-8 text-center text-[#555]">加载中..</td></tr>
                            </tbody>
                        </table>
                    </div>
                    <div class="flex items-center justify-between px-3 py-2 border-t border-[#1e1e1e] bg-[#141414]">
                        <div class="flex items-center gap-3 min-w-0">
                            <span id="calcHistoryTotal" class="text-[10px] text-[#484848]"></span>
                            ${pageSizeSelectHtml('dieFeeCalcHistoryPageSize')}
                        </div>
                        <div class="flex items-center gap-0.5" id="calcHistoryPagination"></div>
                    </div>
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

export function renderCalcHistoryPagination(currentPage, totalPages) {
    if (totalPages <= 1) return '';
    let buttons = '';
    for (let i = 1; i <= totalPages; i += 1) {
        const isActive = i === currentPage;
        buttons += `<button class="calc-history-page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] ${isActive ? 'bg-[#d32f2f] text-white' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'}" data-page="${i}">${i}</button>`;
    }
    return buttons;
}
