/**
 * Module Loader
 * 模块加载器 - 加载所有模板模块
 * 
 * 由于浏览器不支持直接导入 .html 文件，需要将 .html 内容嵌入到 .js 文件中
 * 这个文件收集所有模板的导出函数
 * 
 * 图标采用 Heroicons SVG (https://heroicons.com)
 */

// 模板内容直接嵌入
export const templates = {
    dashboard: `
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
            <div class="bg-white border border-slate-200 rounded-lg shadow-sm p-6">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-sm text-slate-500 mb-1">零件总数</p>
                        <p class="text-2xl font-semibold text-slate-900" id="totalParts">-</p>
                    </div>
                    <div class="w-12 h-12 bg-slate-100 rounded-lg flex items-center justify-center">
                        <svg class="w-6 h-6 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"></path></svg>
                    </div>
                </div>
            </div>
            <div class="bg-white border border-slate-200 rounded-lg shadow-sm p-6">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-sm text-slate-500 mb-1">工序总数</p>
                        <p class="text-2xl font-semibold text-slate-900" id="totalProcesses">-</p>
                    </div>
                    <div class="w-12 h-12 bg-slate-100 rounded-lg flex items-center justify-center">
                        <svg class="w-6 h-6 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16"></path></svg>
                    </div>
                </div>
            </div>
            <div class="bg-white border border-slate-200 rounded-lg shadow-sm p-6">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-sm text-slate-500 mb-1">车型数量</p>
                        <p class="text-2xl font-semibold text-slate-900" id="totalModels">-</p>
                    </div>
                    <div class="w-12 h-12 bg-slate-100 rounded-lg flex items-center justify-center">
                        <svg class="w-6 h-6 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"></path></svg>
                    </div>
                </div>
            </div>
            <div class="bg-white border border-slate-200 rounded-lg shadow-sm p-6">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-sm text-slate-500 mb-1">最近上传</p>
                        <p class="text-2xl font-semibold text-slate-900" id="recentUploads">-</p>
                    </div>
                    <div class="w-12 h-12 bg-slate-100 rounded-lg flex items-center justify-center">
                        <svg class="w-6 h-6 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path></svg>
                    </div>
                </div>
            </div>
        </div>

        <div class="bg-white border border-slate-200 rounded-lg shadow-sm p-6">
            <h3 class="text-base font-semibold text-slate-900 mb-4">欢迎使用汽车冲压件自动核价平台</h3>
            <p class="text-sm text-slate-600 mb-4">
                本系统提供冲压件工艺文件上传、零件管理、成本核算和报价生成等功能。
            </p>
            <div class="flex gap-3">
                <a href="#" class="inline-flex items-center justify-center gap-2 bg-slate-900 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-slate-800 transition-colors" data-page="stamping-upload">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                    上传工艺文件
                </a>
                <a href="#" class="inline-flex items-center justify-center gap-2 bg-white text-slate-700 border border-slate-200 rounded-md px-4 py-2 text-sm font-medium hover:bg-slate-50 transition-colors" data-page="stamping-parts">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"></path></svg>
                    查看零件列表
                </a>
            </div>
        </div>
    `,

    upload: `
        <div class="max-w-2xl mx-auto">
            <div class="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden mb-4">
                <div class="px-4 py-3 border-b border-slate-100 bg-slate-50/50 flex items-center gap-2">
                    <svg class="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1M5 17a2 2 0 104 0m-4 0a2 2 0 114 0m6 0a2 2 0 104 0m-4 0a2 2 0 114 0"></path></svg>
                    <h5 class="text-sm font-semibold text-slate-700 mb-0">上传车型冲压工艺文件</h5>
                </div>
                <div class="p-4">
                    <form id="uploadForm">
                        <div class="grid grid-cols-2 gap-4 mb-4">
                            <div class="space-y-1.5">
                                <label for="vehicleModel" class="text-sm font-medium text-slate-700 flex items-center gap-1">
                                    <svg class="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1M5 17a2 2 0 104 0m-4 0a2 2 0 114 0m6 0a2 2 0 104 0m-4 0a2 2 0 114 0"></path></svg>
                                    车型 <span class="text-red-500">*</span>
                                </label>
                                <input type="text"
                                       id="vehicleModel"
                                       name="vehicle_model"
                                       placeholder="例如：H61"
                                       required
                                       class="w-full h-9 px-3 text-sm border border-slate-200 rounded-md bg-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-900/10 focus:border-slate-300 transition-colors">
                            </div>
                            <div class="space-y-1.5">
                                <label for="version" class="text-sm font-medium text-slate-700 flex items-center gap-1">
                                    <svg class="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"></path></svg>
                                    版本 <span class="text-red-500">*</span>
                                </label>
                                <input type="text"
                                       id="version"
                                       name="version"
                                       placeholder="例如：V1.0"
                                       required
                                       class="w-full h-9 px-3 text-sm border border-slate-200 rounded-md bg-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-900/10 focus:border-slate-300 transition-colors">
                            </div>
                        </div>

                        <div id="uploadZone"
                             class="border-2 border-dashed border-slate-300 rounded-lg p-8 text-center bg-slate-50 hover:bg-white hover:border-slate-400 transition-colors cursor-pointer mb-4">
                            <svg class="w-12 h-12 text-slate-400 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path></svg>
                            <h5 id="uploadTitle" class="text-base font-medium text-slate-700 mb-1">拖拽文件到此处上传</h5>
                            <p id="uploadHint" class="text-sm text-slate-400 mb-3">或点击选择文件</p>
                            <input type="file"
                                   id="fileInput"
                                   class="hidden"
                                   accept=".xlsx,.xls">
                            <button type="button"
                                    onclick="document.getElementById('fileInput').click()"
                                    class="inline-flex items-center justify-center gap-2 bg-slate-900 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-slate-800 transition-colors">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path></svg>
                                选择文件
                            </button>
                            <p class="text-xs text-slate-400 mt-3 mb-0">支持格式: .xlsx, .xls (最大 50MB)</p>
                        </div>

                        <div id="filePreview" class="hidden mb-4"></div>

                        <div class="flex items-center justify-end gap-3 pt-2">
                            <button type="button"
                                    onclick="window.resetUploadForm()"
                                    class="inline-flex items-center justify-center gap-2 bg-white text-slate-700 border border-slate-200 rounded-md px-4 py-2 text-sm font-medium hover:bg-slate-50 transition-colors">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
                                重置
                            </button>
                            <button type="submit"
                                    id="submitBtn"
                                    class="inline-flex items-center justify-center gap-2 bg-slate-900 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-slate-800 disabled:opacity-50 disabled:pointer-events-none transition-colors">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                                上传
                            </button>
                        </div>
                    </form>
                </div>
            </div>

            <div class="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden">
                <div class="px-4 py-3 border-b border-slate-100 bg-slate-50/50 flex items-center gap-2">
                    <svg class="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                    <h5 class="text-sm font-semibold text-slate-700 mb-0">上传说明</h5>
                </div>
                <div class="p-4">
                    <h6 class="text-sm font-medium text-slate-700 mb-2">Excel 文件格式要求：</h6>
                    <ul class="list-disc list-inside text-sm text-slate-600 space-y-1 mb-3">
                        <li>文件应包含冲压工艺相关信息（零件号、工序、模具信息等）</li>
                        <li>支持多工作表导入</li>
                        <li>请确保数据从第一行开始，不要有空行</li>
                    </ul>
                    <h6 class="text-sm font-medium text-slate-700 mb-2">支持的字段：</h6>
                    <ul class="list-disc list-inside text-sm text-slate-600 space-y-1">
                        <li>零件号 (Part Number)</li>
                        <li>零件名称 (Part Name)</li>
                        <li>材料 (Material)</li>
                        <li>工序数量 (Process Count)</li>
                        <li>模具数量 (Die Count)</li>
                    </ul>
                </div>
            </div>
        </div>
    `,

    parts: `
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
    `,

    costing: `
        <div class="bg-white border border-slate-200 rounded-lg shadow-sm p-8 text-center">
            <div class="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mx-auto mb-4">
                <svg class="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path></svg>
            </div>
            <h3 class="text-lg font-semibold text-slate-900 mb-2">核价功能开发中</h3>
            <p class="text-sm text-slate-600 mb-6">
                成本核算功能正在开发中，敬请期待...
            </p>
            <button class="inline-flex items-center justify-center gap-2 bg-slate-900 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-slate-800 transition-colors" disabled>
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                即将上线
            </button>
        </div>
    `,

    quotation: `
        <div class="bg-white border border-slate-200 rounded-lg shadow-sm p-8 text-center">
            <div class="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mx-auto mb-4">
                <svg class="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
            </div>
            <h3 class="text-lg font-semibold text-slate-900 mb-2">报价功能开发中</h3>
            <p class="text-sm text-slate-600 mb-6">
                报价单生成功能正在开发中，敬请期待...
            </p>
            <button class="inline-flex items-center justify-center gap-2 bg-slate-900 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-slate-800 transition-colors" disabled>
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                即将上线
            </button>
        </div>
    `,

    settings: `
        <div class="bg-white border border-slate-200 rounded-lg shadow-sm p-6">
            <h3 class="text-base font-semibold text-slate-900 mb-4">系统设置</h3>
            <div class="space-y-4">
                <div>
                    <label class="text-sm font-medium text-slate-700 mb-1 block">应用名称</label>
                    <input type="text" value="汽车冲压件自动核价平台"
                           class="w-full h-9 px-3 text-sm border border-slate-200 rounded-md bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-900/10 focus:border-slate-300 transition-colors">
                </div>
                <div>
                    <label class="text-sm font-medium text-slate-700 mb-1 block">版本</label>
                    <input type="text" value="1.0.0" readonly
                           class="w-full h-9 px-3 text-sm border border-slate-200 rounded-md bg-slate-100 text-slate-500 cursor-not-allowed">
                </div>
            </div>
            <div class="mt-6 pt-4 border-t border-slate-100">
                <button class="inline-flex items-center justify-center gap-2 bg-slate-900 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-slate-800 transition-colors">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                    保存设置
                </button>
            </div>
        </div>
    `,
};

// 页面元数据
export const pageMeta = {
    dashboard: { title: '仪表盘', breadcrumb: '仪表盘' },
    'stamping-upload': { title: '上传工艺文件', breadcrumb: '上传工艺文件' },
    'stamping-parts': { title: '零件列表', breadcrumb: '零件列表' },
    costing: { title: '核价', breadcrumb: '核价' },
    quotation: { title: '报价', breadcrumb: '报价' },
    settings: { title: '系统设置', breadcrumb: '系统设置' },
};
