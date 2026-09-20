/**
 * 工程变更上传 — 与冲压布点 / 工艺上传同一套舱体。
 */

import {
    BTN_FILE_SELECT,
    BTN_GHOST,
    BTN_UPLOAD_SUBMIT,
    UPLOAD_DROPZONE,
    UPLOAD_INPUT,
} from '../../../ui-classes.js?v=1';

export function engineeringChangeUploadTemplate() {
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
            <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
                <div class="px-5 py-3 border-b border-[#222222] flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2.5">
                        ${window.svgIcon('file-earmark-excel', 'w-3.5 h-3.5 text-[#616161]')}
                        <h5 class="text-xs font-semibold text-[#9e9e9e] mb-0">上传工程变更</h5>
                    </div>
                    <button type="button" id="ecUploadTemplateBtn"
                            class="inline-flex items-center gap-1.5 bg-transparent text-[#888888] border border-[#2c2c2c] px-3 py-1.5 text-[11px] font-medium rounded-sm hover:border-[#d32f2f] hover:text-[#d32f2f] transition-all duration-150">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                        下载模板
                    </button>
                </div>
                <div class="p-5">
                    <form id="ecUploadForm" enctype="multipart/form-data">
                        <div class="bg-[#161616] border border-[#252525] p-4">
                            <div class="mb-5">
                                <div class="flex items-center gap-2 mb-2.5">
                                    <span class="w-4 h-4 rounded-full bg-[#2a2a2a] flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-[#d32f2f]">1</span>
                                    </span>
                                    <span class="text-[13px] text-[#6b6b6b] font-medium tracking-wide uppercase">选择采购基地 / 项目</span>
                                </div>
                                <div class="ml-6">
                                    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                                        <select id="ecUploadLocation" name="location" required class="${UPLOAD_INPUT}">
                                            <option value="">请选择采购基地</option>
                                        </select>
                                        <select id="ecUploadVehicleModel" name="vehicle_model" required class="${UPLOAD_INPUT}">
                                            <option value="">请先选择采购基地</option>
                                        </select>
                                    </div>
                                    <p class="mt-2 text-[10px] text-[#555555]">必选。基地定位投产清单；项目须该生效月可引入，且与工程变更单一致。</p>
                                </div>
                            </div>
                            <div class="h-px bg-[#1e1e1e] mx-6 mb-4"></div>
                            <div class="mb-5">
                                <div class="flex items-center gap-2 mb-2.5">
                                    <span class="w-4 h-4 rounded-full bg-[#2a2a2a] flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-[#d32f2f]">2</span>
                                    </span>
                                    <span class="text-[13px] text-[#6b6b6b] font-medium tracking-wide uppercase">选择生效年月</span>
                                </div>
                                <div class="ml-6">
                                    <div class="flex items-center gap-3">
                                        <select id="ecUploadYear" name="effective_year" required
                                                class="${UPLOAD_INPUT} w-[140px]"></select>
                                        <select id="ecUploadMonth" name="effective_month" required
                                                class="${UPLOAD_INPUT} w-[120px]"></select>
                                    </div>
                                    <p class="mt-2 text-[10px] text-[#555555]">须与工程变更单生效年月一致。从该月起用新树，前一月旧月账仍看见变更前总成。</p>
                                </div>
                            </div>
                            <div class="h-px bg-[#1e1e1e] mx-6 mb-4"></div>
                            <div>
                                <div class="flex items-center gap-2 mb-3">
                                    <span class="w-4 h-4 rounded-full bg-[#2a2a2a] flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-[#d32f2f]">3</span>
                                    </span>
                                    <span class="text-[13px] text-[#6b6b6b] font-medium tracking-wide uppercase">上传变更文件</span>
                                </div>
                                <div class="ml-6">
                                    <div id="ecUploadZone" class="${UPLOAD_DROPZONE} mb-4" data-dropzone-state="idle">
                                        <div id="ecDropIdle" class="flex flex-col items-center gap-0">
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
                                            <h5 id="ecUploadTitle" class="text-[11px] text-[#606060] font-semibold tracking-widest uppercase mb-1">拖拽文件到此处</h5>
                                            <p id="ecUploadHint" class="text-[10px] text-[#3a3a3a] mb-6">或点击下方按钮选择文件</p>
                                            <div class="flex items-center gap-3 mt-1 w-full px-3">
                                                <div class="h-px flex-1 bg-[#2a2a2a]"></div>
                                                <div class="w-1.5 h-1.5 border border-[#363636] rotate-45"></div>
                                                <div class="h-px flex-1 bg-[#2a2a2a]"></div>
                                            </div>
                                            <input type="file" id="ecUploadFileInput" class="hidden" accept=".xlsx,.xls">
                                            <button type="button" id="ecUploadSelectFileBtn" class="${BTN_FILE_SELECT}">
                                                ${window.svgIcon('folder', 'w-3.5 h-3.5')}
                                                浏览文件
                                            </button>
                                            <p class="text-[10px] text-[#3a3a3a] mt-4 mb-0">.xlsx / .xls<span class="mx-2 text-[#2a2a2a]">|</span>最大 50MB · 须含工程变更单、材料清单、工艺确认表</p>
                                        </div>
                                        <div id="ecProgressPanel" class="hidden text-left w-full">
                                            <div class="flex items-center justify-between gap-3 mb-3">
                                                <div class="flex items-center gap-2 min-w-0">
                                                    ${window.svgIcon('spinner', 'w-4 h-4 text-[#d32f2f]')}
                                                    <h5 id="ecProgressTitle" class="text-xs font-medium text-[#ffffff] truncate mb-0">正在解析工程变更...</h5>
                                                </div>
                                                <span id="ecProgressPercent" class="text-xs font-mono tabular-nums text-[#d32f2f] shrink-0">0%</span>
                                            </div>
                                            <div class="h-1.5 w-full bg-[#0a0a0a] border border-[#2c2c2c] overflow-hidden mb-3">
                                                <div id="ecProgressBar" class="h-full bg-[#d32f2f] shadow-[0_0_8px_rgba(211,47,47,0.5)] transition-all duration-300" style="width: 0%"></div>
                                            </div>
                                            <p id="ecProgressMsg" class="text-[11px] text-[#9e9e9e] leading-relaxed mb-0 whitespace-pre-wrap break-words max-h-48 overflow-y-auto">已提交解析队列</p>
                                        </div>
                                    </div>
                                    <div id="ecFilePreview" class="hidden mb-4"></div>
                                    <div id="ecUploadErrorPanel"
                                         class="hidden mb-4 border border-[#5c1a1a] bg-[#1a0808]"
                                         role="alert">
                                        <div class="flex items-start justify-between gap-3 px-3 py-2.5 border-b border-[#3a1515]">
                                            <div class="min-w-0">
                                                <h6 id="ecUploadErrorTitle"
                                                    class="text-[11px] font-semibold text-[#ef5350] mb-0.5 tracking-wide">导入失败</h6>
                                                <p class="text-[10px] text-[#8E8E93] mb-0">请对照提示修改 Excel 后重新上传，可复制全文</p>
                                            </div>
                                            <div class="flex items-center gap-1 shrink-0">
                                                <button type="button"
                                                        id="ecUploadErrorCopyBtn"
                                                        class="px-2 py-1 text-[10px] text-[#9e9e9e] border border-[#2c2c2c] rounded-sm hover:border-[#9e9e9e] hover:text-white transition-all">
                                                    复制
                                                </button>
                                                <button type="button"
                                                        id="ecUploadErrorCloseBtn"
                                                        class="text-[#616161] hover:text-[#ffffff] transition-colors p-1"
                                                        aria-label="关闭错误提示">
                                                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                                                </button>
                                            </div>
                                        </div>
                                        <pre id="ecUploadErrorBody"
                                             class="m-0 px-3 py-3 text-[12px] font-mono leading-relaxed text-[#ffcdd2] whitespace-pre-wrap break-words max-h-[360px] overflow-y-auto select-text"></pre>
                                    </div>
                                    <div class="flex items-center justify-end gap-3">
                                        <button type="button" id="ecUploadResetBtn" class="${BTN_GHOST}">
                                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
                                            重置
                                        </button>
                                        <button type="submit" id="ecUploadSubmitBtn" disabled class="${BTN_UPLOAD_SUBMIT}">
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
                        <p>下载模板即青岛 T28 五种填法样表。整本一次上传，后台解析，本页看进度。</p>
                        <p>工程变更单一行一种改法：完成停止 / 改图 / 增加零件 / 此件不装。同一本可以多行，也可以只有一行。</p>
                        <p>上方基地、项目、生效年月须与 Excel 互校。项目、生效年月必须和工程变更单一致。</p>
                        <p>硬门禁三张表：工程变更单、车身件材料清单、冲压工艺确认表。工程变更不要「零件汇总」；模具按变更单从旧号逻辑建立，简图从工艺确认表抄过去。</p>
                        <p>Excel 只写改了什么；系统种的是完整新树。筛 EC 版本才是数采购件。</p>
                        <p class="text-[#ffb74d]">改图后不要再走投产三页整包覆盖。换号只走本页。</p>
                    </div>
                </div>
                <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
                    <div class="px-4 py-3 border-b border-[#222222] flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <span style="width:2px;height:12px;background:#d32f2f;border-radius:1px;display:inline-block;box-shadow:0 0 6px rgba(211,47,47,0.4);"></span>
                            <h5 class="text-[11px] font-bold text-[#9e9e9e] mb-0 tracking-widest uppercase">最近上传</h5>
                        </div>
                    </div>
                    <div class="p-4" id="ecRecentUploads">
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
