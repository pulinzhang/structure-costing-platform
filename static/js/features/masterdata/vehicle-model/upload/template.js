/**
 * 项目上传 — 基地写在 Excel 列里，页面不选手选；同步导入
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
            <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
                <div class="px-5 py-3 border-b border-[#222222] flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2.5">
                        ${window.svgIcon('file-earmark-excel', 'w-3.5 h-3.5 text-[#616161]')}
                        <h5 class="text-xs font-semibold text-[#9e9e9e] mb-0">项目导入</h5>
                    </div>
                    <button type="button"
                            id="vmUploadTemplateBtn"
                            class="inline-flex items-center gap-1.5 bg-transparent text-[#888888] border border-[#2c2c2c] px-3 py-1.5 text-[11px] font-medium rounded-sm hover:border-[#d32f2f] hover:text-[#d32f2f] transition-all duration-150">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                        下载模板
                    </button>
                </div>
                <div class="p-5">
                    <form id="vmUploadForm">
                        <div id="vmUploadZone" class="${UPLOAD_DROPZONE} mb-4" data-dropzone-state="idle">
                            <div id="vmUploadDropIdle" class="flex flex-col items-center gap-0">
                                ${window.svgIcon('upload', 'w-10 h-10 text-[#616161] mx-auto mb-4')}
                                <h5 id="vmUploadTitle" class="text-xs font-medium text-[#9e9e9e] mb-1.5">拖拽文件到此处上传</h5>
                                <p id="vmUploadHint" class="text-[11px] text-[#616161] mb-5">或点击下方按钮选择文件</p>
                                <input type="file" id="vmUploadFileInput" class="hidden" accept=".xlsx,.xls">
                                <button type="button" id="vmUploadSelectFileBtn" class="${BTN_FILE_SELECT}">
                                    ${window.svgIcon('folder', 'w-3.5 h-3.5')}
                                    选择文件
                                </button>
                                <p class="text-[10px] text-[#616161] mt-5 mb-0">支持 .xlsx, .xls · 同步导入 · 基地写在模板列里</p>
                            </div>
                            <div id="vmUploadProgressPanel" class="hidden text-left w-full">
                                <div class="flex items-center gap-2 min-w-0 mb-3">
                                    ${window.svgIcon('spinner', 'w-4 h-4 text-[#d32f2f]')}
                                    <h5 class="text-xs font-medium text-[#ffffff] truncate mb-0">正在导入项目...</h5>
                                </div>
                                <div class="h-1.5 w-full bg-[#0a0a0a] border border-[#2c2c2c] overflow-hidden mb-3">
                                    <div class="h-full bg-[#d32f2f] shadow-[0_0_8px_rgba(211,47,47,0.5)] transition-all duration-300 animate-pulse"
                                         style="width: 60%"></div>
                                </div>
                                <p id="vmUploadProgressMsg" class="text-[11px] text-[#9e9e9e] leading-relaxed mb-0">解析并写入数据库，请稍候</p>
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
                <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
                    <div class="px-4 py-3 border-b border-[#222222] flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <span class="w-0.5 h-3 bg-[#d32f2f] shadow-[0_0_8px_rgba(211,47,47,0.5)]"></span>
                            <h5 class="text-[11px] font-bold text-[#9e9e9e] mb-0 tracking-widest uppercase">格式说明</h5>
                        </div>
                    </div>
                    <div class="p-4 space-y-4">
                        <div>
                            <h6 class="text-[10px] uppercase tracking-wider text-[#616161] mb-2">模板列</h6>
                            <ul class="list-disc list-inside text-xs text-[#616161] space-y-1.5">
                                <li><span class="text-[#9e9e9e]">基地</span>：已登记且已启用的规范名或别名</li>
                                <li><span class="text-[#9e9e9e]">项目代号</span>：入库一律大写</li>
                                <li><span class="text-[#9e9e9e]">生效年 / 生效月</span>：必填</li>
                                <li><span class="text-[#9e9e9e]">失效年 / 失效月</span>：同空或同有</li>
                                <li><span class="text-[#9e9e9e]">当前供货台数</span>：单位台，空视为 0</li>
                            </ul>
                        </div>
                        <div>
                            <h6 class="text-[10px] uppercase tracking-wider text-[#616161] mb-2">写入规则</h6>
                            <ul class="list-disc list-inside text-xs text-[#616161] space-y-1.5">
                                <li>主键：基地 + 项目代号</li>
                                <li>库里已有则跳过，不覆盖生效/失效/供货台数</li>
                                <li>任一行失败则整单不写入</li>
                                <li>改期或改台数请到一览表抽屉</li>
                            </ul>
                        </div>
                        <a href="#/vehicle-model-list" class="block text-[11px] text-[#d32f2f] hover:text-[#ff5252]">打开项目一览表 →</a>
                    </div>
                </div>
            </div>
        </div>
    `;
}
