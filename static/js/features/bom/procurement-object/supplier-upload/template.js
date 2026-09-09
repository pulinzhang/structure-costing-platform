/**
 * 采购对象批量上传供应商
 */

import {
    BTN_FILE_SELECT,
    BTN_GHOST,
    BTN_UPLOAD_SUBMIT,
    UPLOAD_DROPZONE,
    UPLOAD_INPUT,
    UPLOAD_LABEL,
} from '../../../../ui-classes.js?v=1';

export function procurementObjectSupplierUploadTemplate() {
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
            <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
                <div class="px-5 py-3 border-b border-[#222222] flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2.5">
                        ${window.svgIcon('file-earmark-excel', 'w-3.5 h-3.5 text-[#616161]')}
                        <h5 class="text-xs font-semibold text-[#9e9e9e] mb-0">采购对象供应商导入</h5>
                    </div>
                    <button type="button"
                            id="poSupplierUploadTemplateBtn"
                            class="inline-flex items-center gap-1.5 bg-transparent text-[#888888] border border-[#2c2c2c] px-3 py-1.5 text-[11px] font-medium rounded-sm hover:border-[#d32f2f] hover:text-[#d32f2f] transition-all duration-150">
                        ${window.svgIcon('download', 'w-3.5 h-3.5')}
                        下载模板
                    </button>
                </div>
                <div class="p-5">
                    <form id="poSupplierUploadForm">
                        <div class="bg-[#161616] border border-[#252525] p-4">
                            <div class="mb-5">
                                <div class="flex items-center gap-2 mb-2.5">
                                    <span class="w-4 h-4 rounded-full bg-[#2a2a2a] flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-[#d32f2f]">1</span>
                                    </span>
                                    <span class="text-[13px] text-[#6b6b6b] font-medium tracking-wide uppercase">选择基地、项目与版本</span>
                                </div>
                                <div class="ml-6 grid grid-cols-1 sm:grid-cols-3 gap-3">
                                    <div>
                                        <label for="poSupplierUploadLocation" class="${UPLOAD_LABEL}">
                                            采购基地 <span class="text-[#d32f2f]">*</span>
                                        </label>
                                        <select id="poSupplierUploadLocation" required class="${UPLOAD_INPUT} w-full">
                                            <option value="">请选择采购基地</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label for="poSupplierUploadModel" class="${UPLOAD_LABEL}">
                                            项目 <span class="text-[#d32f2f]">*</span>
                                        </label>
                                        <select id="poSupplierUploadModel" required class="${UPLOAD_INPUT} w-full">
                                            <option value="">请先选择采购基地</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label for="poSupplierUploadVersion" class="${UPLOAD_LABEL}">
                                            版本 <span class="text-[#d32f2f]">*</span>
                                        </label>
                                        <select id="poSupplierUploadVersion" required class="${UPLOAD_INPUT} w-full">
                                            <option value="">请先选择项目</option>
                                        </select>
                                    </div>
                                </div>
                                <p class="ml-6 mt-1.5 text-[11px] text-[#616161]">须已生成该范围采购对象清单。模板按零件号去重；内部号给人看，方便到 ERP 联查。第二页目录只对照，导入不读。</p>
                            </div>
                            <div class="h-px bg-[#1e1e1e] mx-6 mb-4"></div>
                            <div>
                                <div class="flex items-center gap-2 mb-3">
                                    <span class="w-4 h-4 rounded-full bg-[#2a2a2a] flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-[#d32f2f]">2</span>
                                    </span>
                                    <span class="text-[13px] text-[#6b6b6b] font-medium tracking-wide uppercase">上传改供应商</span>
                                </div>
                                <div class="ml-6">
                                    <div id="poSupplierUploadZone" class="${UPLOAD_DROPZONE} mb-4" data-dropzone-state="idle">
                                        <div id="poSupplierUploadDropIdle" class="flex flex-col items-center gap-0">
                                            ${window.svgIcon('upload', 'w-10 h-10 text-[#616161] mx-auto mb-4')}
                                            <h5 id="poSupplierUploadTitle" class="text-xs font-medium text-[#9e9e9e] mb-1.5">拖拽文件到此处上传</h5>
                                            <p id="poSupplierUploadHint" class="text-[11px] text-[#616161] mb-5">或点击下方按钮选择文件</p>
                                            <input type="file" id="poSupplierUploadFileInput" class="hidden" accept=".xlsx">
                                            <button type="button" id="poSupplierUploadSelectFileBtn" class="${BTN_FILE_SELECT}">
                                                ${window.svgIcon('folder', 'w-3.5 h-3.5')}
                                                选择文件
                                            </button>
                                            <p class="text-[10px] text-[#616161] mt-5 mb-0">仅 .xlsx · 同步导入 · 只改第一页供应商列</p>
                                        </div>
                                        <div id="poSupplierUploadProgressPanel" class="hidden text-left w-full">
                                            <div class="flex items-center gap-2 min-w-0 mb-3">
                                                ${window.svgIcon('spinner', 'w-4 h-4 text-[#d32f2f]')}
                                                <h5 class="text-xs font-medium text-[#ffffff] truncate mb-0">正在导入供应商指定...</h5>
                                            </div>
                                            <div class="h-1.5 w-full bg-[#0a0a0a] border border-[#2c2c2c] overflow-hidden mb-3">
                                                <div class="h-full bg-[#d32f2f] shadow-[0_0_8px_rgba(211,47,47,0.5)] transition-all duration-300 animate-pulse"
                                                     style="width: 60%"></div>
                                            </div>
                                            <p id="poSupplierUploadProgressMsg" class="text-[11px] text-[#9e9e9e] leading-relaxed mb-0">解析并写入数据库，请稍候</p>
                                        </div>
                                    </div>
                                    <div id="poSupplierUploadFilePreview" class="hidden mb-4"></div>
                                    <div class="flex items-center justify-end gap-3">
                                        <button type="button" id="poSupplierUploadResetBtn" class="${BTN_GHOST}">重置</button>
                                        <button type="submit" id="poSupplierUploadSubmitBtn" disabled class="${BTN_UPLOAD_SUBMIT}">上传</button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </form>
                </div>
            </div>
            <div class="space-y-3">
                <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
                    <div class="px-4 py-3 border-b border-[#222222] flex items-center gap-2">
                        <span class="w-0.5 h-3 bg-[#d32f2f] shadow-[0_0_8px_rgba(211,47,47,0.5)]"></span>
                        <h5 class="text-[11px] font-bold text-[#9e9e9e] mb-0 tracking-widest uppercase">格式说明</h5>
                    </div>
                    <div class="p-4 space-y-3 text-xs text-[#616161]">
                        <p>只改第一页「供应商」。「内部号」给人看，方便到 ERP 联查，导入不读。相同零件号只出一行。空=清空。缩写 / 别名 / ERP 可解析为规范全称。</p>
                        <p>找不到的厂到 <span class="text-[#9e9e9e]">#/supplier-list</span> 补档，本页不建档。</p>
                        <p>已审要改须先在清单页反审核。自制禁止填非空供应商。</p>
                    </div>
                </div>
            </div>
        </div>
    `;
}
