import { paginationBarHtml } from '../../../../page-size.js?v=3';

export function dieListTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="bg-[#0A0A0C] border border-[#1A1A22] overflow-hidden w-full max-w-full"
                 style="box-shadow: 0 4px 24px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.02);">
                <div class="px-5 pt-4 pb-3.5 border-b border-[#14141A]"
                     style="background: linear-gradient(135deg, #0E0E12 0%, #121218 45%, #0C0C10 100%);">
                    <div class="flex items-start justify-between gap-4 mb-3">
                        <div class="grid grid-cols-2 gap-3 font-mono flex-1 min-w-0">
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3">
                                <div class="text-[#555555] text-[10px] tracking-wider">查询范围</div>
                                <div class="text-[14px] font-bold text-[#FFFFFF] mt-1 truncate" id="dieHudScope">请选择基地与项目</div>
                            </div>
                            <div class="bg-[#0D0D11]/80 border border-[#1E1E26] p-3">
                                <div class="text-[#555555] text-[10px] tracking-wider">零件</div>
                                <div class="text-[18px] font-bold text-[#FFFFFF] mt-1 tabular-nums" id="dieHudTotal">—</div>
                            </div>
                        </div>
                        <div class="flex items-center gap-2 shrink-0 flex-wrap justify-end">
                            <button id="dieBatchDeleteBtn" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#c62828]/60 hover:text-[#ef5350] hover:bg-[#c62828]/15 transition-all">
                                ${window.svgIcon('trash', 'w-3 h-3')}
                                删除本范围
                            </button>
                            <button id="dieExportBtn" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#6E6E73] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] hover:bg-[#FF1E27]/10 transition-all">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                导出 Excel
                            </button>
                        </div>
                    </div>
                </div>
                <div class="px-5 py-3 border-b border-[#14141A]"
                     style="background: linear-gradient(180deg, #0C0C10 0%, #0A0A0E 100%);">
                    <div class="flex items-end gap-3 flex-wrap">
                        <label class="flex flex-col gap-1">
                            <span class="text-[10px] text-[#555555] tracking-wider">基地</span>
                            <select id="dieListLocation" class="h-9 min-w-[140px] px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252]">
                                <option value="">请选择</option>
                            </select>
                        </label>
                        <label class="flex flex-col gap-1">
                            <span class="text-[10px] text-[#555555] tracking-wider">项目</span>
                            <select id="dieListVehicle" class="h-9 min-w-[140px] px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252]">
                                <option value="">请先选择基地</option>
                            </select>
                        </label>
                        <label class="flex flex-col gap-1">
                            <span class="text-[10px] text-[#555555] tracking-wider">零件号</span>
                            <input id="dieListPartNumber" type="text" placeholder="可选"
                                   class="h-9 min-w-[140px] px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252]">
                        </label>
                        <button id="dieListSearchBtn" type="button"
                                class="inline-flex items-center gap-1.5 h-9 px-3 text-[11px] font-semibold rounded-sm text-[#c8c8c8] border border-[#8a2020] hover:text-white"
                                style="background: linear-gradient(180deg, #3d1515 0%, #2d0f0f 100%);">
                            ${window.svgIcon('search', 'w-3 h-3')}
                            查询
                        </button>
                    </div>
                    <p class="mt-2 text-[10px] text-[#555555]">须先选择基地和项目后再查询。删除本范围按基地+项目整包删除。</p>
                </div>
                <div class="overflow-x-auto brabus-bg-grid">
                    <table class="w-full table-fixed bg-transparent border-collapse" style="min-width: 880px;">
                        <colgroup>
                            <col style="width: 8px">
                            <col style="width: 56px">
                            <col style="width: 72px">
                            <col style="width: 180px">
                            <col style="width: 90px">
                            <col style="width: 90px">
                            <col style="width: 90px">
                            <col style="width: 140px">
                            <col style="width: 72px">
                            <col style="width: 56px">
                        </colgroup>
                        <thead>
                            <tr class="border-b border-[#17171C] bg-[#0B0B0D]/95">
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">序号</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#A1A1A6]">短代码</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">零件</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">模具类型</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">模具方式</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">生产方式</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">生失效</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">工序</th>
                                <th class="px-1 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">操作</th>
                            </tr>
                        </thead>
                        <tbody id="dieListTableBody" class="bg-transparent"></tbody>
                    </table>
                </div>
                ${paginationBarHtml({ infoId: 'dieListTotalLabel', selectId: 'dieListPageSize', buttonsId: 'dieListPagination' })}
                <div id="dieListEmpty" class="flex flex-col items-center justify-center py-14">
                    <div class="w-10 h-10 flex items-center justify-center mb-3 rounded-md bg-[#121218] border border-[#2A2A35]">
                        ${window.svgIcon('clipboard-list', 'w-4 h-4 text-[#555555]')}
                    </div>
                    <h5 id="dieListEmptyTitle" class="text-[11px] font-medium text-[#8E8E93] mb-1">请先选择基地和项目</h5>
                    <p id="dieListEmptyHint" class="text-[10px] text-[#555555]">未选齐范围时不会请求列表</p>
                </div>
                <div id="dieListLoading" class="hidden flex items-center justify-center py-14">
                    <div class="w-5 h-5 border-2 border-[#2A2A35] border-t-[#FF1E27] rounded-full animate-spin"></div>
                </div>
            </div>
        </div>
        <div class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm" id="dieDrawerBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[860px] max-w-[96vw] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="dieDrawer" style="display:none; max-height: 100vh; box-shadow: -20px 0 60px rgba(0,0,0,0.95);">
            <div class="px-5 py-3 border-b border-[#222222] flex items-center justify-between">
                <div>
                    <p class="text-[9px] tracking-[0.12em] text-[#555555] mb-0.5">DIE LAYOUT</p>
                    <h5 class="text-xs font-semibold text-[#9e9e9e] mb-0">模具详情</h5>
                </div>
                <button type="button" id="dieDrawerCloseBtn" class="w-7 h-7 text-[#616161] hover:text-white">${window.svgIcon('x-lg', 'w-4 h-4')}</button>
            </div>
            <div class="flex-1 overflow-y-auto p-5" id="dieDrawerContent"></div>
        </div>
    `;
}
