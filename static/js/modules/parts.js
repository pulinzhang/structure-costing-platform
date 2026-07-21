/**
 * Parts Template
 * 零件列表页面模板
 */

export function partsTemplate() {
    return `
        <div class="bg-white border border-slate-200 rounded-xl shadow-sm shadow-slate-900/5 p-4 mb-6">
            <div class="flex flex-col lg:flex-row gap-4 items-stretch lg:items-center">
                <div class="flex-1 min-w-0">
                    <div class="relative group">
                        <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                            <svg class="w-5 h-5 text-slate-400 group-focus-within:text-slate-600 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                        </div>
                        <input type="text"
                               id="searchInput"
                               placeholder="搜索零件号或名称..."
                               class="w-full h-11 pl-11 pr-4 text-sm bg-slate-50 border border-slate-200 rounded-lg placeholder:text-slate-400 focus:outline-none focus:bg-white focus:border-slate-400 focus:ring-2 focus:ring-slate-900/10 transition-all">
                    </div>
                </div>

                <div class="flex flex-row flex-wrap gap-3 items-center">
                    <div class="w-44">
                        <select id="vehicleModelFilter"
                                class="w-full h-11 px-4 text-sm bg-slate-50 border border-slate-200 rounded-lg appearance-none cursor-pointer focus:outline-none focus:bg-white focus:border-slate-400 focus:ring-2 focus:ring-slate-900/10 transition-all">
                            <option value="">全部车型</option>
                        </select>
                    </div>

                    <div class="w-36">
                        <select id="versionFilter"
                                class="w-full h-11 px-4 text-sm bg-slate-50 border border-slate-200 rounded-lg appearance-none cursor-pointer focus:outline-none focus:bg-white focus:border-slate-400 focus:ring-2 focus:ring-slate-900/10 transition-all">
                            <option value="">全部版本</option>
                        </select>
                    </div>

                    <div class="hidden lg:block w-px h-8 bg-slate-200"></div>

                    <div class="flex items-center gap-2">
                        <label class="text-sm text-slate-500 whitespace-nowrap">每页</label>
                        <select id="pageSizeSelect"
                                class="w-20 h-11 px-3 text-sm bg-slate-50 border border-slate-200 rounded-lg appearance-none cursor-pointer focus:outline-none focus:bg-white focus:border-slate-400 focus:ring-2 focus:ring-slate-900/10 transition-all">
                            <option value="10">10</option>
                            <option value="20">20</option>
                            <option value="50">50</option>
                            <option value="100">100</option>
                        </select>
                    </div>

                    <div class="flex-shrink-0 text-sm text-slate-500" id="totalCount">
                        共 0 个零件
                    </div>
                </div>
            </div>
        </div>

        <div class="bg-white p-6 md:p-8 rounded-2xl border border-slate-100 shadow-lg shadow-slate-900/5 overflow-hidden">
            <div class="overflow-hidden rounded-xl border border-slate-200">
                <table class="w-full" id="partsTable">
                    <thead>
                        <tr class="bg-slate-50/80 border-b border-slate-200">
                            <th class="px-5 py-4 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">零件号</th>
                            <th class="px-5 py-4 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">零件名称</th>
                            <th class="px-5 py-4 text-center text-xs font-semibold uppercase tracking-wider text-slate-500">车型</th>
                            <th class="px-5 py-4 text-center text-xs font-semibold uppercase tracking-wider text-slate-500">版本</th>
                            <th class="px-5 py-4 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">材料</th>
                            <th class="px-5 py-4 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">厚度(mm)</th>
                            <th class="px-5 py-4 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">重量(kg)</th>
                            <th class="px-5 py-4 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">工序数</th>
                            <th class="px-5 py-4 text-center text-xs font-semibold uppercase tracking-wider text-slate-500">操作</th>
                        </tr>
                    </thead>
                    <tbody id="partsTableBody" class="divide-y divide-slate-100">
                        <tr><td colspan="9">
                            <div class="flex flex-col items-center justify-center py-16 text-slate-400">
                                <div class="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mb-4">
                                    <svg class="w-8 h-8 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"></path></svg>
                                </div>
                                <h5 class="text-slate-600 font-medium mb-1">暂无零件数据</h5>
                                <p class="text-sm text-slate-400">请联系管理员导入工艺文件</p>
                            </div>
                        </td></tr>
                    </tbody>
                </table>
            </div>
            <div class="mt-6 flex items-center justify-between">
                <div class="text-sm text-slate-500"></div>
                <nav>
                    <ul class="flex justify-center mb-0" id="pagination"></ul>
                </nav>
            </div>
        </div>

        <div class="modal fade" id="partDetailModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-lg modal-dialog-centered mx-auto my-4 max-w-2xl w-full">
                <div class="modal-content bg-white rounded-2xl shadow-2xl shadow-slate-900/20 border-0 overflow-hidden">
                    <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                        <h5 class="text-base font-semibold text-slate-900 flex items-center gap-2">
                            <svg class="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                            零件详情
                        </h5>
                        <button type="button" class="p-2 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors" data-bs-dismiss="modal" aria-label="关闭">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                        </button>
                    </div>
                    <div class="modal-body p-6 max-h-[70vh] overflow-y-auto" id="partDetailContent">
                        <div class="flex items-center justify-center py-12">
                            <div class="w-8 h-8 border-2 border-slate-200 border-t-slate-600 rounded-full animate-spin"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}
