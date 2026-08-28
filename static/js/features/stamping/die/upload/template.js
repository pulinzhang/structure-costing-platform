export function dieUploadTemplate() {
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
            <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
                <div class="px-5 py-3 border-b border-[#222222] flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2.5">
                        ${window.svgIcon('clipboard-list', 'w-3.5 h-3.5 text-[#616161]')}
                        <h5 class="text-xs font-semibold text-[#9e9e9e] mb-0">上传冲压模具布点清单</h5>
                    </div>
                    <button type="button"
                            id="dieUploadTemplateBtn"
                            class="inline-flex items-center gap-1.5 bg-transparent text-[#888888] border border-[#2c2c2c] px-3 py-1.5 text-[11px] font-medium rounded-sm hover:border-[#d32f2f] hover:text-[#d32f2f] transition-all duration-150">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                        下载模板
                    </button>
                </div>
                <div class="p-5">
                    <form id="dieUploadForm" enctype="multipart/form-data">
                        <div class="bg-[#161616] border border-[#252525] p-4">
                            <div class="mb-5">
                                <div class="flex items-center gap-2 mb-2.5">
                                    <span class="w-4 h-4 rounded-full bg-[#2a2a2a] flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-[#d32f2f]">1</span>
                                    </span>
                                    <span class="text-[13px] text-[#6b6b6b] font-medium tracking-wide uppercase">选择采购基地</span>
                                </div>
                                <div class="ml-6">
                                    <select id="dieLocation" name="location" required class="upload-input w-[280px] text-[11px]">
                                        <option value="">请选择采购基地</option>
                                    </select>
                                </div>
                            </div>
                            <div class="h-px bg-[#1e1e1e] mx-6 mb-4"></div>
                            <div class="mb-5">
                                <div class="flex items-center gap-2 mb-2.5">
                                    <span class="w-4 h-4 rounded-full bg-[#2a2a2a] flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-[#d32f2f]">2</span>
                                    </span>
                                    <span class="text-[13px] text-[#6b6b6b] font-medium tracking-wide uppercase">选择项目</span>
                                </div>
                                <div class="ml-6">
                                    <select id="dieVehicleModel" name="vehicle_model" required class="upload-input w-[280px] text-[11px]">
                                        <option value="">请先选择基地</option>
                                    </select>
                                    <p class="mt-2 text-[10px] text-[#555555]">须先上传该基地+项目的冲压工艺确认表；选项来自已入库工艺，且须与文件名中的项目一致。</p>
                                </div>
                            </div>
                            <div class="h-px bg-[#1e1e1e] mx-6 mb-4"></div>
                            <div>
                                <div class="flex items-center gap-2 mb-3">
                                    <span class="w-4 h-4 rounded-full bg-[#2a2a2a] flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-[#d32f2f]">3</span>
                                    </span>
                                    <span class="text-[13px] text-[#6b6b6b] font-medium tracking-wide uppercase">上传布点文件</span>
                                </div>
                                <div class="ml-6">
                                    <div id="dieUploadZone" class="upload-dropzone mb-4">
                                        <div id="dieDropIdle" class="flex flex-col items-center gap-0">
                                            <div class="flex items-center gap-3 mb-5 w-full px-3">
                                                <div class="h-px flex-1 bg-[#2a2a2a]"></div>
                                                <div class="w-1.5 h-1.5 border border-[#363636] rotate-45"></div>
                                                <div class="h-px flex-1 bg-[#2a2a2a]"></div>
                                            </div>
                                            <div class="mb-3 relative">
                                                <div class="absolute inset-0 bg-[#d32f2f]/8 blur-xl rounded-full"></div>
                                                <svg class="w-9 h-9 text-[#4a4a4a] relative z-10" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.2">
                                                    <path stroke-linecap="round" stroke-linejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
                                                </svg>
                                            </div>
                                            <h5 id="dieUploadTitle" class="text-[11px] text-[#606060] font-semibold tracking-widest uppercase mb-1">拖拽文件到此处</h5>
                                            <p id="dieUploadHint" class="text-[10px] text-[#3a3a3a] mb-6">或点击下方按钮选择文件</p>
                                            <div class="flex items-center gap-3 mt-1 w-full px-3">
                                                <div class="h-px flex-1 bg-[#2a2a2a]"></div>
                                                <div class="w-1.5 h-1.5 border border-[#363636] rotate-45"></div>
                                                <div class="h-px flex-1 bg-[#2a2a2a]"></div>
                                            </div>
                                            <input type="file" id="dieFileInput" class="hidden" accept=".xlsx,.xls">
                                            <button type="button" id="dieSelectFileBtn" class="btn-file-select">
                                                ${window.svgIcon('folder', 'w-3.5 h-3.5')}
                                                浏览文件
                                            </button>
                                            <p class="text-[10px] text-[#3a3a3a] mt-4 mb-0">.xlsx / .xls<span class="mx-2 text-[#2a2a2a]">|</span>最大 50MB · 仅读 A–AC 列</p>
                                        </div>
                                        <div id="dieProgressPanel" class="hidden text-left w-full">
                                            <div class="flex items-center justify-between gap-3 mb-3">
                                                <div class="flex items-center gap-2 min-w-0">
                                                    ${window.svgIcon('spinner', 'w-4 h-4 text-[#d32f2f]')}
                                                    <h5 id="dieProgressTitle" class="text-xs font-medium text-[#ffffff] truncate mb-0">正在解析模具布点...</h5>
                                                </div>
                                                <span id="dieProgressPercent" class="text-xs font-mono tabular-nums text-[#d32f2f] shrink-0">0%</span>
                                            </div>
                                            <div class="h-1.5 w-full bg-[#0a0a0a] border border-[#2c2c2c] overflow-hidden mb-3">
                                                <div id="dieProgressBar" class="h-full bg-[#d32f2f] shadow-[0_0_8px_rgba(211,47,47,0.5)] transition-all duration-300" style="width: 0%"></div>
                                            </div>
                                            <p id="dieProgressMsg" class="text-[11px] text-[#9e9e9e] leading-relaxed mb-0 whitespace-pre-wrap break-words max-h-48 overflow-y-auto">已提交解析队列</p>
                                        </div>
                                    </div>
                                    <div id="dieFilePreview" class="hidden mb-4"></div>
                                    <div class="flex items-center justify-end gap-3">
                                        <button type="button" id="dieResetButton" class="btn-ghost">
                                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
                                            重置
                                        </button>
                                        <button type="submit" id="dieSubmitBtn" disabled class="btn-upload-submit disabled:opacity-30 disabled:pointer-events-none">
                                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                                            上传
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </form>
                </div>
            </div>
            <div class="space-y-3">
                <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
                    <div class="px-4 py-3 border-b border-[#222222] flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <span style="width:2px;height:12px;background:#d32f2f;border-radius:1px;display:inline-block;box-shadow:0 0 6px rgba(211,47,47,0.4);"></span>
                            <h5 class="text-[11px] font-bold text-[#9e9e9e] mb-0 tracking-widest uppercase">说明</h5>
                        </div>
                    </div>
                    <div class="p-4 space-y-3 text-[11px] text-[#888888] leading-relaxed">
                        <p class="text-[#ffb74d]">必须先上传该基地+项目的冲压工艺确认表（工艺清单），再传模具布点。项目下拉只列出已入库工艺。</p>
                        <p>本表是模具费用计算依据，本期只入库、不算金额。</p>
                        <p>覆盖同一基地+项目；已改的分摊比例会按零件号保留。</p>
                        <p>同一零件的工序号不能重复，否则整单失败并标出 Excel 行号。</p>
                        <p>布点里找不到工艺零件号/工序，或工序已有模具长宽高却没有唯一模具编号，整单失败并列出原因。</p>
                        <p>不导入简图与 AD 列以后的费用。</p>
                    </div>
                </div>
                <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
                    <div class="px-4 py-3 border-b border-[#222222]">
                        <h5 class="text-[11px] font-bold text-[#9e9e9e] mb-0 tracking-widest uppercase">最近上传</h5>
                    </div>
                    <div class="p-4" id="dieRecentUploads">
                        <p class="text-[10px] text-[#4a4a4a] text-center py-5">暂无上传记录</p>
                    </div>
                </div>
            </div>
        </div>
    `;
}
