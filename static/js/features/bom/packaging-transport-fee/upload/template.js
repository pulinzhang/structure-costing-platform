/**
 * 包装运输费上传 — 模板
 * 基地 + 年度 + 项目必选；支持生产样例表或平台扁平模板
 */

export function pkgTransportFeeUploadTemplate() {
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
            <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
                <div class="px-5 py-3 border-b border-[#222222] flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2.5">
                        ${window.svgIcon('file-earmark-excel', 'w-3.5 h-3.5 text-[#616161]')}
                        <h5 class="text-xs font-semibold text-[#9e9e9e] mb-0">包装运输费导入</h5>
                    </div>
                    <button type="button"
                            id="pkgTransportFeeUploadTemplateBtn"
                            class="inline-flex items-center gap-1.5 bg-transparent text-[#888888] border border-[#2c2c2c] px-3 py-1.5 text-[11px] font-medium rounded-sm hover:border-[#d32f2f] hover:text-[#d32f2f] transition-all duration-150">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                        下载模板
                    </button>
                </div>
                <div class="p-5">
                    <form id="pkgTransportFeeUploadForm">
                        <div class="bg-[#161616] border border-[#252525] p-4">
                            <div class="mb-5">
                                <div class="flex items-center gap-2 mb-2.5">
                                    <span class="w-4 h-4 rounded-full bg-[#2a2a2a] flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-[#d32f2f]">1</span>
                                    </span>
                                    <span class="text-[13px] text-[#6b6b6b] font-medium tracking-wide uppercase">选择基地 / 年度 / 项目</span>
                                </div>
                                <div class="ml-6 grid grid-cols-1 sm:grid-cols-3 gap-3">
                                    <div>
                                        <label for="pkgTransportFeeUploadLocation" class="upload-label">
                                            采购基地 <span class="text-[#d32f2f]">*</span>
                                        </label>
                                        <select id="pkgTransportFeeUploadLocation" name="location" required class="upload-input w-full text-[11px]">
                                            <option value="">请选择采购基地</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label for="pkgTransportFeeUploadYear" class="upload-label">
                                            年度 <span class="text-[#d32f2f]">*</span>
                                        </label>
                                        <input type="text" id="pkgTransportFeeUploadYear" name="year" placeholder="例如：2026" required pattern="[0-9]{4}" maxlength="4" class="upload-input w-full">
                                    </div>
                                    <div>
                                        <label for="pkgTransportFeeUploadVehicleModel" class="upload-label">
                                            项目 <span class="text-[#d32f2f]">*</span>
                                        </label>
                                        <select id="pkgTransportFeeUploadVehicleModel" name="vehicle_model" required class="upload-input w-full text-[11px]">
                                            <option value="">请先选择采购基地</option>
                                        </select>
                                    </div>
                                </div>
                                <p id="pkgTransportFeeUploadScopeHint" class="ml-6 mt-1.5 text-[11px] text-[#616161]">
                                    基地 / 项目取自已上传的材料清单；唯一键 = 基地 + 年度 + 项目 + 零件号
                                </p>
                                <div id="pkgTransportFeeUploadNoBomBanner" class="hidden ml-6 mt-2 text-[10px] text-[#d69e2e] bg-[#1a1710] px-2.5 py-1.5 border-l-2 border-[#d69e2e]">
                                    尚未上传材料清单，或当前账号无对应清单数据。请先在「上传材料清单」导入 BOM 后再上传包装运输费。
                                </div>
                            </div>

                            <div class="h-px bg-[#1e1e1e] mx-6 mb-4"></div>

                            <div>
                                <div class="flex items-center gap-2 mb-3">
                                    <span class="w-4 h-4 rounded-full bg-[#2a2a2a] flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-[#d32f2f]">2</span>
                                    </span>
                                    <span class="text-[13px] text-[#6b6b6b] font-medium tracking-wide uppercase">上传包装运输费表</span>
                                </div>
                                <div class="ml-6">
                                    <div id="pkgTransportFeeUploadZone" class="upload-dropzone mb-4">
                                        <div id="pkgTransportFeeUploadDropIdle" class="flex flex-col items-center gap-0">
                                            <div class="mb-3 relative">
                                                <div class="absolute inset-0 bg-[#d32f2f]/8 blur-xl rounded-full"></div>
                                                <svg class="w-9 h-9 text-[#4a4a4a] relative z-10" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.2">
                                                    <path stroke-linecap="round" stroke-linejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
                                                </svg>
                                            </div>
                                            <h5 id="pkgTransportFeeUploadTitle" class="text-[11px] text-[#606060] font-semibold tracking-widest uppercase mb-1">拖拽文件到此处</h5>
                                            <p id="pkgTransportFeeUploadHint" class="text-[10px] text-[#3a3a3a] mb-6">或点击下方按钮选择文件</p>
                                            <input type="file" id="pkgTransportFeeUploadFileInput" class="hidden" accept=".xlsx">
                                            <button type="button" id="pkgTransportFeeUploadSelectFileBtn" class="btn-file-select">
                                                ${window.svgIcon('folder', 'w-3.5 h-3.5')}
                                                浏览文件
                                            </button>
                                            <p class="text-[10px] text-[#3a3a3a] mt-4 mb-0">仅 .xlsx · 同步导入（读已算好的费用，不重算公式）</p>
                                        </div>
                                        <div id="pkgTransportFeeUploadProgressPanel" class="hidden text-left w-full">
                                            <div class="flex items-center gap-2 mb-3">
                                                ${window.svgIcon('spinner', 'w-4 h-4 text-[#d32f2f]')}
                                                <h5 class="text-xs font-medium text-[#ffffff] truncate mb-0">正在导入包装运输费...</h5>
                                            </div>
                                            <div class="h-1.5 w-full bg-[#0a0a0a] border border-[#2c2c2c] overflow-hidden mb-3">
                                                <div class="h-full bg-[#d32f2f] shadow-[0_0_8px_rgba(211,47,47,0.5)] animate-pulse" style="width: 60%"></div>
                                            </div>
                                            <p id="pkgTransportFeeUploadProgressMsg" class="text-[11px] text-[#9e9e9e] mb-0">解析并写入数据库，请稍候</p>
                                        </div>
                                    </div>
                                    <div id="pkgTransportFeeUploadFilePreview" class="hidden mb-4"></div>
                                    <div class="flex items-center justify-end gap-3">
                                        <button type="button" id="pkgTransportFeeUploadResetBtn" class="btn-ghost">重置</button>
                                        <button type="submit" id="pkgTransportFeeUploadSubmitBtn" disabled class="btn-upload-submit disabled:opacity-30 disabled:pointer-events-none">上传</button>
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
                            <h5 class="text-[11px] font-bold text-[#9e9e9e] mb-0 tracking-widest uppercase">格式说明</h5>
                        </div>
                        <span class="text-[10px] text-[#4d4d4d] tracking-wider">SPEC</span>
                    </div>
                    <div class="p-4 space-y-4">
                        <div>
                            <h6 class="text-[10px] uppercase tracking-wider text-[#616161] mb-2">支持版式</h6>
                            <ul class="list-disc list-inside text-xs text-[#616161] space-y-1.5">
                                <li><span class="text-[#9e9e9e]">生产样例</span>：含「料号」「包装类型」「包装运输费合计」</li>
                                <li><span class="text-[#9e9e9e]">平台模板</span>：扁平单表头（可点下载）</li>
                            </ul>
                        </div>
                        <div>
                            <h6 class="text-[10px] uppercase tracking-wider text-[#616161] mb-2">核价取价</h6>
                            <ul class="list-disc list-inside text-xs text-[#616161] space-y-1.5">
                                <li>只认 <span class="text-[#9e9e9e]">包装运输费合计</span></li>
                                <li>分项：单件包装费 / 单件运输费 / 维护费 / 其它费用</li>
                            </ul>
                        </div>
                        <div>
                            <h6 class="text-[10px] uppercase tracking-wider text-[#616161] mb-2">写入规则</h6>
                            <ul class="list-disc list-inside text-xs text-[#616161] space-y-1.5">
                                <li>同键更新；已审核跳过</li>
                                <li>系统不重算 Excel 公式</li>
                            </ul>
                        </div>
                    </div>
                </div>

                <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
                    <div class="px-4 py-3 border-b border-[#222222] flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <span style="width:2px;height:12px;background:#d32f2f;border-radius:1px;display:inline-block;box-shadow:0 0 6px rgba(211,47,47,0.4);"></span>
                            <h5 class="text-[11px] font-bold text-[#9e9e9e] mb-0 tracking-widest uppercase">最近上传</h5>
                        </div>
                    </div>
                    <div class="p-4" id="pkgTransportFeeRecentUploads">
                        <div class="text-center py-5">
                            <div class="w-8 h-8 bg-[#1a1a1a] border border-[#2a2a2a] flex items-center justify-center mx-auto mb-2.5">
                                <svg class="w-4 h-4 text-[#4a4a4a]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
                            </div>
                            <p class="text-[10px] text-[#4a4a4a]">暂无上传记录</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}
