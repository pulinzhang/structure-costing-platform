/**
 * 项目上传 — 基地写在 Excel 列里；同步写入
 */

import {
    BTN_FILE_SELECT,
    BTN_GHOST,
    BTN_UPLOAD_SUBMIT,
    UPLOAD_DROPZONE,
} from '../../../../ui-classes.js?v=1';

export function vehicleModelUploadTemplate() {
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
            <div class="bg-[#0A0A0C] border border-[#1A1A22]"
                 style="box-shadow: 0 4px 24px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.02);">
                <div class="px-5 py-3 border-b border-[#14141A] flex items-center justify-between gap-3"
                     style="background: linear-gradient(135deg, #0E0E12 0%, #121218 45%, #0C0C10 100%);">
                    <div class="flex items-center gap-2.5">
                        <span class="w-1 h-3.5 bg-[#FF1E27]"></span>
                        <h5 class="text-xs font-semibold text-[#F0F0F2] mb-0 tracking-wider">项目补档</h5>
                    </div>
                    <button type="button"
                            id="vmUploadTemplateBtn"
                            class="inline-flex items-center gap-1.5 bg-transparent text-[#8E8E93] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] transition-all">
                        ${window.svgIcon('download', 'w-3 h-3')}
                        下载模板
                    </button>
                </div>
                <div class="p-5">
                    <form id="vmUploadForm">
                        <div id="vmUploadZone" class="${UPLOAD_DROPZONE} mb-4" data-dropzone-state="idle">
                            <div id="vmUploadDropIdle" class="flex flex-col items-center gap-0">
                                ${window.svgIcon('upload', 'w-10 h-10 text-[#616161] mx-auto mb-4')}
                                <h5 id="vmUploadTitle" class="text-xs font-medium text-[#9e9e9e] mb-1.5">拖入 Excel</h5>
                                <p id="vmUploadHint" class="text-[11px] text-[#616161] mb-5">或点下方选择文件</p>
                                <input type="file" id="vmUploadFileInput" class="hidden" accept=".xlsx,.xls">
                                <button type="button" id="vmUploadSelectFileBtn" class="${BTN_FILE_SELECT}">
                                    ${window.svgIcon('folder', 'w-3.5 h-3.5')}
                                    选择文件
                                </button>
                                <p class="text-[10px] text-[#555555] mt-5 mb-0">.xlsx / .xls · 基地写在模板列</p>
                            </div>
                            <div id="vmUploadProgressPanel" class="hidden text-left w-full">
                                <div class="flex items-center gap-2 min-w-0 mb-3">
                                    <span id="vmUploadProgressIcon">${window.svgIcon('spinner', 'w-4 h-4 text-[#FF1E27]')}</span>
                                    <h5 id="vmUploadProgressTitle" class="text-xs font-medium text-[#ffffff] truncate mb-0">正在写入…</h5>
                                </div>
                                <div class="h-1.5 w-full bg-[#0a0a0a] border border-[#2c2c2c] overflow-hidden mb-3">
                                    <div id="vmUploadProgressBar"
                                         class="h-full bg-[#FF1E27] transition-all duration-300 animate-pulse"
                                         style="width: 60%"></div>
                                </div>
                                <p id="vmUploadProgressMsg" class="text-[11px] text-[#9e9e9e] leading-relaxed mb-0 whitespace-pre-wrap break-words max-h-48 overflow-y-auto">解析中</p>
                            </div>
                        </div>
                        <div id="vmUploadFilePreview" class="hidden mb-4"></div>
                        <div class="flex items-center justify-end gap-3">
                            <button type="button" id="vmUploadResetBtn" class="${BTN_GHOST}">重置</button>
                            <button type="submit" id="vmUploadSubmitBtn" disabled class="${BTN_UPLOAD_SUBMIT}">上传</button>
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
                                <li><span class="text-[#9e9e9e]">基地</span>：已启用基地名或别名</li>
                                <li><span class="text-[#9e9e9e]">项目代号</span>：入库大写</li>
                                <li><span class="text-[#9e9e9e]">生效年 / 月</span>：必填</li>
                                <li><span class="text-[#9e9e9e]">失效年 / 月</span>：同空或同有</li>
                                <li><span class="text-[#9e9e9e]">当前供货台数</span>：空视为 0</li>
                            </ul>
                        </div>
                        <div>
                            <h6 class="text-[10px] tracking-wider text-[#555555] mb-2">规则</h6>
                            <ul class="list-disc list-inside text-xs text-[#616161] space-y-1.5">
                                <li>已有基地+代号则跳过</li>
                                <li>任一行失败整单不写</li>
                                <li>改期 / 台数到一览抽屉</li>
                            </ul>
                        </div>
                        <a href="#/vehicle-model-list" class="block text-[11px] text-[#FF1E27] hover:text-[#ff5252]">打开项目一览 →</a>
                    </div>
                </div>
            </div>
        </div>
    `;
}
