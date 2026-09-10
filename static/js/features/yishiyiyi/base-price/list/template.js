/**
 * Steel Base Price Download Template
 * 基准价格导出页面
 */

import {
    DEFAULT_PREVIEW_PAGE_SIZE,
    PREVIEW_PAGE_SIZE_OPTIONS,
    pageSizeSelectHtml,
} from '../../../../page-size.js?v=2';

export function basePriceDownloadTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <!-- 页面主面板 -->
            <div class="bg-[#1e1e1e] border border-[#2c2c2c] overflow-hidden w-full max-w-full"
                 style="box-shadow: 0 2px 12px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.03);">

                <!-- 面板头部：标题 -->
                <div class="flex items-center justify-between px-5 py-3.5 border-b border-[#222222]"
                     style="background: linear-gradient(90deg, #1c1c1c 0%, #1e1e1e 60%);">
                    <div class="flex items-center gap-3">
                        <div class="w-[2px] h-4 bg-[#d32f2f] rounded-[1px] shadow-[0_0_6px_rgba(211,47,47,0.3)]"></div>
                        <h2 class="text-[12px] font-semibold text-[#c8c8c8] tracking-wide">基准价格导出</h2>
                    </div>
                    <div class="flex items-center gap-2">
                        <button id="btnDeleteBasePrice"
                                class="inline-flex items-center gap-1.5 bg-transparent text-[#505050] border border-[#252525] px-3 py-1.5 text-[11px] font-medium rounded-sm hover:bg-[#c62828]/15 hover:border-[#c62828]/60 hover:text-[#d45858] hover:shadow-[0_0_8px_rgba(198,40,40,0.15)] transition-all duration-200"
                                style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);">
                            ${window.svgIcon('trash', 'w-3 h-3')}
                            删除
                        </button>
                        <button id="btnExportBasePrice"
                                class="inline-flex items-center gap-1.5 bg-transparent text-[#505050] border border-[#252525] px-3 py-1.5 text-[11px] font-medium rounded-sm hover:bg-[#d32f2f]/10 hover:border-[#d32f2f]/60 hover:text-[#d32f2f] hover:shadow-[0_0_8px_rgba(211,47,47,0.15)] transition-all duration-200"
                                style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);">
                            ${window.svgIcon('download', 'w-3 h-3')}
                            导出 Excel
                        </button>
                    </div>
                </div>

                <!-- 筛选工具栏 -->
                <div class="flex items-center justify-between px-5 py-2.5 border-b border-[#1e1e1e]"
                     style="background: linear-gradient(180deg, #181818 0%, #161616 100%);">
                    <div class="flex items-end gap-3 flex-wrap">
                        ${filterSelect('basePriceDownloadYear', '年度')}
                        ${filterSelect('basePriceDownloadMonth', '月份')}
                        ${filterSelect('basePriceDownloadLocation', '基地')}
                        ${filterSelect('basePriceDownloadMill', '钢厂')}
                        ${filterSelect('basePriceDownloadCategory', '钢种大类')}
                        ${filterInputWithDatalist('basePriceDownloadGrade', '牌号', 'basePriceGradeOptions')}
                    </div>
                    <div class="flex items-center gap-2">
                        <button id="btnPreviewBasePrice"
                                class="inline-flex items-center gap-1.5 h-7 px-3 text-[11px] font-semibold rounded-sm text-[#c8c8c8] border border-[#8a2020] transition-all duration-200 hover:text-white"
                                style="background: linear-gradient(180deg, #3d1515 0%, #2d0f0f 100%); border-color: #6b1a1a; box-shadow: 0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(211,47,47,0.1), 0 0 12px rgba(198,40,40,0.08);">
                            ${window.svgIcon('search', 'w-3 h-3')}
                            查询
                        </button>
                    </div>
                </div>

                <!-- 提示信息 -->
                <div class="px-5 py-3 border-b border-[#1e1e1e]" style="background: linear-gradient(180deg, #181818 0%, #161616 100%);">
                    <div class="bg-[#0c0c0c] border border-[#1a1a1a] rounded p-3">
                        <p class="text-[11px] text-[#888888] leading-5">
                            <span class="text-[#9e9e9e] font-medium">说明：</span>
                            筛选条件为年度、月份、基地、钢厂、钢种大类、牌号。基准价格表记录每个基地、每个钢厂、每个牌号在每个月的到厂原卷承兑价格。
                        </p>
                    </div>
                </div>

                <!-- 预览区域 -->
                <div class="p-5">
                    <!-- 已选条件 -->
                    <div class="mb-3 px-3 py-2 rounded-sm relative"
                         style="background: linear-gradient(180deg, #0f0f0f 0%, #0c0c0c 100%); border: 1px solid #1a1a1a; box-shadow: inset 0 1px 3px rgba(0,0,0,0.4);">
                        <div class="absolute top-0 left-0 right-0 h-px" style="background: linear-gradient(90deg, transparent 0%, #2a2a2a 50%, transparent 100%);"></div>
                        <div class="flex items-center gap-2 text-[11px]">
                            <span class="text-[#484848]">已选条件：</span>
                            <span id="selectedBasePriceConditions" class="text-[#888888] ml-2 font-medium tracking-wide">请选择筛选条件</span>
                        </div>
                        <div class="absolute bottom-0 left-0 right-0 h-px" style="background: linear-gradient(90deg, transparent 0%, #151515 50%, transparent 100%);"></div>
                    </div>

                    <!-- 预览表格 -->
                    <div class="bg-[#141414] border border-[#222222] rounded-sm overflow-hidden"
                         style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.02), 0 2px 8px rgba(0,0,0,0.3);">
                        <div class="overflow-x-auto max-h-[400px]">
                            <table class="w-full min-w-[1200px]">
                                <thead>
                                    <tr class="border-b border-[#1e1e1e]" style="background: linear-gradient(180deg, #0c0c0c 0%, #0a0a0a 100%);">
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">ID</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">年度</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">月份</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">基地</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">钢厂</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">钢种大类</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">牌号</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">规格</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">厚度</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">宽度</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">基准价格</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">加工费</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">文件名</th>
                                        <th class="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">表页</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">行号</th>
                                        <th class="px-3 py-2 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#3a3a3a] whitespace-nowrap">列号</th>
                                    </tr>
                                </thead>
                                <tbody id="basePricePreviewBody" class="divide-y divide-[#1a1a1a]">
                                    <tr>
                                        <td colspan="16" class="px-4 py-8 text-center text-[#616161] text-xs">
                                            请选择条件后点击"查询"查看数据
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- 分页 -->
                    <div class="flex items-center justify-between mt-4 gap-3">
                        <div class="flex items-center gap-3 min-w-0">
                            <div class="text-[11px] text-[#616161]">
                                共 <span id="basePriceRecordCount" class="text-[#9e9e9e] font-mono">0</span> 条记录
                            </div>
                            ${pageSizeSelectHtml('basePricePageSize', DEFAULT_PREVIEW_PAGE_SIZE, PREVIEW_PAGE_SIZE_OPTIONS)}
                        </div>
                        <div class="flex items-center gap-0.5" id="basePricePagination"></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 加载遮罩 -->
        <div id="basePriceDownloadLoading" class="hidden fixed inset-0 z-[80] bg-black/60 backdrop-blur-sm flex items-center justify-center">
            <div class="bg-[#1e1e1e] border border-[#2c2c2c] rounded p-6 flex flex-col items-center gap-3"
                 style="box-shadow: 0 4px 24px rgba(0,0,0,0.8);">
                <div class="w-6 h-6 border-2 border-[#2c2c2c] border-t-[#d32f2f] rounded-full animate-spin"></div>
                <span class="text-[11px] text-[#9e9e9e]">正在生成 Excel...</span>
            </div>
        </div>
    `;
}

// ===== 辅助函数 =====

function filterSelect(id, label) {
    return `<label class="space-y-1">
        <span class="block text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em] whitespace-nowrap">${label}</span>
        <select id="${id}" class="w-36 h-7 pl-2.5 pr-7 text-[11px] bg-[#0d0d0d] border border-[#272727] text-[#909090] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] transition-all rounded-sm">
            <option value="">全部</option>
        </select>
    </label>`;
}

function filterInputWithDatalist(id, label, datalistId) {
    return `<label class="space-y-1">
        <span class="block text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em] whitespace-nowrap">${label}</span>
        <input type="text" id="${id}" list="${datalistId}"
               class="w-44 h-7 pl-2.5 pr-3 text-[11px] bg-[#0d0d0d] border border-[#272727] text-[#909090] placeholder:text-[#505050] focus:outline-none focus:border-[#ff5252] focus:text-[#d0d0d0] transition-all rounded-sm"
               placeholder="输入搜索或选择牌号">
        <datalist id="${datalistId}"></datalist>
    </label>`;
}
