/**
 * Upload Template
 * 上传页面模板
 */

export function uploadTemplate() {
    return `
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
    `;
}
