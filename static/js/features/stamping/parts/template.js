/**
 * Parts Template
 * 零件列表页面 — Brabus Carbon & Precision Dark
 */

export function partsTemplate() {
    return `
        <!-- 筛选栏 -->
        <div class="bg-[#1e1e1e] border border-[#2c2c2c] p-3 mb-3">
            <div class="flex flex-col lg:flex-row gap-3 items-stretch lg:items-center">
                <div class="flex-1 min-w-0">
                    <div class="relative">
                        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <svg class="w-3.5 h-3.5 text-[#616161]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                        </div>
                        <input type="text"
                               id="searchInput"
                               placeholder="搜索零件号或名称..."
                               class="w-full h-9 pl-9 pr-4 text-xs bg-[#0a0a0a] border border-[#2c2c2c] placeholder:text-[#616161] text-[#ffffff] focus:outline-none focus:border-[#ff5252] transition-all">
                    </div>
                </div>

                <div class="flex flex-row flex-wrap gap-2 items-center">
                    <select id="vehicleModelFilter"
                            class="w-36 h-9 pl-3 pr-8 text-xs bg-[#0a0a0a] border border-[#2c2c2c] appearance-none cursor-pointer text-[#9e9e9e] focus:outline-none focus:border-[#ff5252] transition-all">
                        <option value="">全部车型</option>
                    </select>

                    <select id="versionFilter"
                            class="w-28 h-9 pl-3 pr-8 text-xs bg-[#0a0a0a] border border-[#2c2c2c] appearance-none cursor-pointer text-[#9e9e9e] focus:outline-none focus:border-[#ff5252] transition-all">
                        <option value="">全部版本</option>
                    </select>

                    <div class="hidden lg:block w-px h-6 bg-[#222222]"></div>

                    <div class="flex items-center gap-1.5">
                        <label class="text-[10px] text-[#616161] whitespace-nowrap">每页</label>
                        <select id="pageSizeSelect"
                                class="w-16 h-9 px-2 text-xs bg-[#0a0a0a] border border-[#2c2c2c] appearance-none cursor-pointer text-[#9e9e9e] focus:outline-none focus:border-[#ff5252] transition-all">
                            <option value="10">10</option>
                            <option value="20">20</option>
                            <option value="50">50</option>
                            <option value="100">100</option>
                        </select>
                    </div>

                    <div class="text-[10px] text-[#616161] whitespace-nowrap" id="totalCount">
                        共 0 个零件
                    </div>
                </div>
            </div>
        </div>

        <!-- 表格面板 -->
        <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
            <div class="overflow-x-auto">
                <table class="w-full" id="partsTable">
                    <thead>
                        <tr class="bg-[#0a0a0a] border-b border-[#2c2c2c]">
                            <th class="px-4 py-3 text-center text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161] whitespace-nowrap w-14">图纸</th>
                            <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161] whitespace-nowrap">零件号</th>
                            <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161] whitespace-nowrap">零件名称</th>
                            <th class="px-4 py-3 text-center text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161] whitespace-nowrap">车型</th>
                            <th class="px-4 py-3 text-center text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161] whitespace-nowrap">版本</th>
                            <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161] whitespace-nowrap">材料</th>
                            <th class="px-4 py-3 text-right text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161] whitespace-nowrap">厚度</th>
                            <th class="px-4 py-3 text-right text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161] whitespace-nowrap">重量</th>
                            <th class="px-4 py-3 text-right text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161] whitespace-nowrap">工序</th>
                            <th class="px-4 py-3 text-center text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161] whitespace-nowrap">操作</th>
                        </tr>
                    </thead>
                    <tbody id="partsTableBody" class="divide-y divide-[#222222]">
                        <tr>
                            <td colspan="10">
                                <div class="flex flex-col items-center justify-center py-14">
                                    <div class="w-10 h-10 bg-[#262626] flex items-center justify-center mb-3">
                                        <svg class="w-5 h-5 text-[#616161]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"></path></svg>
                                    </div>
                                    <h5 class="text-xs font-medium text-[#9e9e9e] mb-1">暂无零件数据</h5>
                                    <p class="text-[11px] text-[#616161]">请联系管理员导入工艺文件</p>
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div class="flex items-center justify-between px-4 py-3 border-t border-[#222222]">
                <div></div>
                <nav>
                    <ul class="flex justify-center mb-0" id="pagination"></ul>
                </nav>
            </div>
        </div>

        <!-- 详情弹窗 -->
        <div class="modal fade" id="partDetailModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-lg modal-dialog-centered mx-auto my-4 max-w-2xl w-full">
                <div class="modal-content bg-[#1e1e1e] border border-[#2c2c2c]">
                    <div class="px-5 py-3 border-b border-[#222222] flex items-center justify-between">
                        <h5 class="text-xs font-semibold text-[#9e9e9e] flex items-center gap-2">
                            <svg class="w-3.5 h-3.5 text-[#616161]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                            零件详情
                        </h5>
                        <button type="button" class="text-[#616161] hover:text-[#9e9e9e] transition-colors" data-bs-dismiss="modal" aria-label="关闭">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                        </button>
                    </div>
                    <div class="modal-body p-5 max-h-[65vh] overflow-y-auto" id="partDetailContent">
                        <div class="flex items-center justify-center py-12">
                            <div class="w-6 h-6 border border-[#2c2c2c] border-t-[#d32f2f] rounded-full animate-spin"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 零件详情抽屉（图纸 + 信息 + 工序，表格保持可见） -->
        <div class="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm transition-opacity duration-300"
             id="partDrawerBackdrop" style="display:none"></div>

        <div class="fixed inset-y-0 right-0 z-50 w-[640px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="partDrawer" style="display:none; max-height: 100vh; box-shadow: -20px 0 60px rgba(0,0,0,0.95), -8px 0 30px rgba(0,0,0,0.8), 0 0 1px rgba(255,255,255,0.05);">
            <!-- 拖拽条 -->
            <div class="absolute left-0 top-0 bottom-0 w-1.5 cursor-ew-resize hover:bg-[#d32f2f]/50 transition-colors z-10"></div>

            <!-- 头部（固定不滚动） -->
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0"
                 style="background: linear-gradient(180deg, #1f1f1f 0%, #1a1a1a 100%); border-bottom: 1px solid #333333;">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] flex items-center gap-2.5 uppercase" id="partDrawerTitle">
                    <span style="width:3px;height:14px;background:#d32f2f;border-radius:1px;display:inline-block;box-shadow: 0 0 8px rgba(211,47,47,0.5);"></span>
                    零件详情
                </h5>
                <button type="button" id="closePartDrawer"
                        class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all duration-200 group">
                    <svg class="w-4 h-4 transition-transform duration-200 group-hover:scale-110" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>

            <!-- 可滚动内容区 -->
            <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain" id="partDrawerContent" style="scrollbar-width: thin; scrollbar-color: #3a3a3a #1a1a1a;">
                <div class="flex items-center justify-center py-16">
                    <div class="w-7 h-7 border-2 border-[#2a2a2a] border-t-[#d32f2f] rounded-full animate-spin"></div>
                </div>
            </div>
        </div>

    `;
}
