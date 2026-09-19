/**
 * 供应商上传 — 同步导入；列：缩写 / 工商名称 / ERP 代码 / 别名
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
            <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
                <div class="px-5 py-3 border-b border-[#222222] flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2.5">
                        ${window.svgIcon('file-earmark-excel', 'w-3.5 h-3.5 text-[#616161]')}
                        <h5 class="text-xs font-semibold text-[#9e9e9e] mb-0">供应商导入</h5>
                    </div>
                    <button type="button"
                            id="supplierUploadTemplateBtn"
                            class="inline-flex items-center gap-1.5 bg-transparent text-[#888888] border border-[#2c2c2c] px-3 py-1.5 text-[11px] font-medium rounded-sm hover:border-[#d32f2f] hover:text-[#d32f2f] transition-all duration-150">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                        下载模板
                    </button>
                </div>
                <div class="p-5">
                    <form id="supplierUploadForm">
                        <div id="supplierUploadZone" class="${UPLOAD_DROPZONE} mb-4" data-dropzone-state="idle">
                            <div id="supplierUploadDropIdle" class="flex flex-col items-center gap-0">
                                ${window.svgIcon('upload', 'w-10 h-10 text-[#616161] mx-auto mb-4')}
                                <h5 id="supplierUploadTitle" class="text-xs font-medium text-[#9e9e9e] mb-1.5">拖拽文件到此处上传</h5>
                                <p id="supplierUploadHint" class="text-[11px] text-[#616161] mb-5">或点击下方按钮选择文件</p>
                                <input type="file" id="supplierUploadFileInput" class="hidden" accept=".xlsx,.xls">
                                <button type="button" id="supplierUploadSelectFileBtn" class="${BTN_FILE_SELECT}">
                                    ${window.svgIcon('folder', 'w-3.5 h-3.5')}
                                    选择文件
                                </button>
                                <p class="text-[10px] text-[#616161] mt-5 mb-0">支持 .xlsx, .xls · 同步导入 · 工商名称须与营业执照一致</p>
                            </div>
                            <div id="supplierUploadProgressPanel" class="hidden text-left w-full">
                                <div class="flex items-center gap-2 min-w-0 mb-3">
                                    ${window.svgIcon('spinner', 'w-4 h-4 text-[#d32f2f]')}
                                    <h5 class="text-xs font-medium text-[#ffffff] truncate mb-0">正在导入供应商...</h5>
                                </div>
                                <div class="h-1.5 w-full bg-[#0a0a0a] border border-[#2c2c2c] overflow-hidden mb-3">
                                    <div class="h-full bg-[#d32f2f] shadow-[0_0_8px_rgba(211,47,47,0.5)] transition-all duration-300 animate-pulse"
                                         style="width: 60%"></div>
                                </div>
                                <p id="supplierUploadProgressMsg" class="text-[11px] text-[#9e9e9e] leading-relaxed mb-0 whitespace-pre-wrap break-words max-h-48 overflow-y-auto">解析并写入数据库，请稍候</p>
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
                                <li><span class="text-[#9e9e9e]">缩写</span>：界面短名，不进工艺列</li>
                                <li><span class="text-[#9e9e9e]">工商名称</span>：须与营业执照一致，将用于签订合同；主键，给下游存</li>
                                <li><span class="text-[#9e9e9e]">ERP 代码</span>：对外身份，不进工艺列</li>
                                <li><span class="text-[#9e9e9e]">别名</span>：可空；同一格可多条（顿号 / 逗号 / 换行）</li>
                            </ul>
                        </div>
                        <div>
                            <h6 class="text-[10px] uppercase tracking-wider text-[#616161] mb-2">写入规则</h6>
                            <ul class="list-disc list-inside text-xs text-[#616161] space-y-1.5">
                                <li>列表导出可直接再导入（含状态列时导入忽略）</li>
                                <li>主键：工商名称。创建后三者不改</li>
                                <li>库里已有工商名称则跳过，不覆盖</li>
                                <li>任一行失败则整单不写入</li>
                                <li>改启用 / 别名请到一览表抽屉</li>
                            </ul>
                        </div>
                        <a href="#/supplier-list" class="block text-[11px] text-[#d32f2f] hover:text-[#ff5252]">打开供应商一览表 →</a>
                    </div>
                </div>
            </div>
        </div>
    `;
}
