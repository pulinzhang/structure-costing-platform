/**
 * 供应商上传 — 核价厂档补录；列：缩写 / 全称 / 对外代码 / 别名
 */

import {
    BTN_FILE_SELECT,
    BTN_GHOST,
    BTN_UPLOAD_SUBMIT,
    UPLOAD_DROPZONE,
} from '../../../../ui-classes.js?v=1';

export function supplierUploadTemplate() {
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
            <div class="bg-[#0A0A0C] border border-[#1A1A22]"
                 style="box-shadow: 0 4px 24px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.02);">
                <div class="px-5 py-3 border-b border-[#14141A] flex items-center justify-between gap-3"
                     style="background: linear-gradient(135deg, #0E0E12 0%, #121218 45%, #0C0C10 100%);">
                    <div class="flex items-center gap-2.5">
                        <span class="w-1 h-3.5 bg-[#FF1E27]"></span>
                        <h5 class="text-xs font-semibold text-[#F0F0F2] mb-0 tracking-wider">供应商补档</h5>
                    </div>
                    <button type="button"
                            id="supplierUploadTemplateBtn"
                            class="inline-flex items-center gap-1.5 bg-transparent text-[#8E8E93] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] transition-all">
                        ${window.svgIcon('download', 'w-3 h-3')}
                        下载模板
                    </button>
                </div>
                <div class="p-5">
                    <form id="supplierUploadForm">
                        <div id="supplierUploadZone" class="${UPLOAD_DROPZONE} mb-4" data-dropzone-state="idle">
                            <div id="supplierUploadDropIdle" class="flex flex-col items-center gap-0">
                                ${window.svgIcon('upload', 'w-10 h-10 text-[#616161] mx-auto mb-4')}
                                <h5 id="supplierUploadTitle" class="text-xs font-medium text-[#9e9e9e] mb-1.5">拖入 Excel</h5>
                                <p id="supplierUploadHint" class="text-[11px] text-[#616161] mb-5">或点下方选择文件</p>
                                <input type="file" id="supplierUploadFileInput" class="hidden" accept=".xlsx,.xls">
                                <button type="button" id="supplierUploadSelectFileBtn" class="${BTN_FILE_SELECT}">
                                    ${window.svgIcon('folder', 'w-3.5 h-3.5')}
                                    选择文件
                                </button>
                                <p class="text-[10px] text-[#555555] mt-5 mb-0">.xlsx / .xls · 同步写入</p>
                            </div>
                            <div id="supplierUploadProgressPanel" class="hidden text-left w-full">
                                <div class="flex items-center gap-2 min-w-0 mb-3">
                                    <span id="supplierUploadProgressIcon">${window.svgIcon('spinner', 'w-4 h-4 text-[#FF1E27]')}</span>
                                    <h5 id="supplierUploadProgressTitle" class="text-xs font-medium text-[#ffffff] truncate mb-0">正在写入…</h5>
                                </div>
                                <div class="h-1.5 w-full bg-[#0a0a0a] border border-[#2c2c2c] overflow-hidden mb-3">
                                    <div id="supplierUploadProgressBar"
                                         class="h-full bg-[#FF1E27] transition-all duration-300 animate-pulse"
                                         style="width: 60%"></div>
                                </div>
                                <p id="supplierUploadProgressMsg" class="text-[11px] text-[#9e9e9e] leading-relaxed mb-0 whitespace-pre-wrap break-words max-h-48 overflow-y-auto">解析中</p>
                            </div>
                        </div>
                        <div id="supplierUploadFilePreview" class="hidden mb-4"></div>
                        <div class="flex items-center justify-end gap-3">
                            <button type="button" id="supplierUploadResetBtn" class="${BTN_GHOST}">重置</button>
                            <button type="submit" id="supplierUploadSubmitBtn" disabled class="${BTN_UPLOAD_SUBMIT}">上传</button>
                        </div>
                    </form>
                </div>
            </div>
            <div class="space-y-3">
                <div class="bg-[#0A0A0C] border border-[#1A1A22]">
                    <div class="px-4 py-3 border-b border-[#14141A] flex items-center gap-2">
                        <span class="w-1 h-3 bg-[#FF1E27]"></span>
                        <h5 class="text-[11px] font-semibold text-[#8E8E93] mb-0 tracking-wider">要点</h5>
                    </div>
                    <div class="p-4 space-y-4">
                        <div>
                            <h6 class="text-[10px] tracking-wider text-[#555555] mb-2">列</h6>
                            <ul class="list-disc list-inside text-xs text-[#616161] space-y-1.5">
                                <li><span class="text-[#9e9e9e]">缩写</span>：上屏短名</li>
                                <li><span class="text-[#9e9e9e]">全称</span>：与执照一致，落库主键</li>
                                <li><span class="text-[#9e9e9e]">对外代码</span>：对接码，不进工艺列</li>
                                <li><span class="text-[#9e9e9e]">别名</span>：可空，吸收表头乱写</li>
                            </ul>
                        </div>
                        <div>
                            <h6 class="text-[10px] tracking-wider text-[#555555] mb-2">规则</h6>
                            <ul class="list-disc list-inside text-xs text-[#616161] space-y-1.5">
                                <li>已有全称则跳过，不覆盖</li>
                                <li>任一行失败整单不写</li>
                                <li>改启用 / 别名到一览抽屉</li>
                            </ul>
                        </div>
                        <a href="#/supplier-list" class="block text-[11px] text-[#FF1E27] hover:text-[#ff5252]">打开供应商一览 →</a>
                    </div>
                </div>
            </div>
        </div>
    `;
}
