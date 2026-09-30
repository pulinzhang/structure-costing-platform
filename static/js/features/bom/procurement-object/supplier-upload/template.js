/**
 * 采购对象批量上传供应商
 */

import { UPLOAD_DROPZONE, UPLOAD_INPUT, UPLOAD_LABEL, HUD_LED } from '../../../../ui/classes.js?v=14';
import {
    uploadBrowseButtonHtml,
    uploadFileHintHtml,
    uploadResetButtonHtml,
    uploadSubmitButtonHtml,
    uploadTemplateButtonHtml,
} from '../../../../ui/upload-actions.js?v=2';

export function procurementObjectSupplierUploadTemplate() {
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
            <div class="bg-app-surface border border-line">
                <div class="px-5 py-3 border-b border-line-subtle flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2.5">
                        ${window.svgIcon('file-earmark-excel', 'w-3.5 h-3.5 text-ink-dim')}
                        <h5 class="text-xs font-semibold text-ink-muted mb-0">采购对象供应商导入</h5>
                    </div>
                    ${uploadTemplateButtonHtml('poSupplierUploadTemplateBtn')}
                </div>
                <div class="p-5">
                    <form id="poSupplierUploadForm">
                        <div class="bg-app-surface border border-line p-4">
                            <div class="mb-5">
                                <div class="flex items-center gap-2 mb-2.5">
                                    <span class="w-4 h-4 rounded-full bg-app-elevated flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-brand">1</span>
                                    </span>
                                    <span class="text-[13px] text-ink-dim font-medium tracking-wide uppercase">选择基地、项目与版本</span>
                                </div>
                                <div class="ml-6 grid grid-cols-1 sm:grid-cols-3 gap-3">
                                    <div>
                                        <label for="poSupplierUploadLocation" class="${UPLOAD_LABEL}">
                                            采购基地 <span class="text-brand">*</span>
                                        </label>
                                        <select id="poSupplierUploadLocation" required class="${UPLOAD_INPUT} hud-filter w-full">
                                            <option value="">请选择采购基地</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label for="poSupplierUploadModel" class="${UPLOAD_LABEL}">
                                            项目 <span class="text-brand">*</span>
                                        </label>
                                        <select id="poSupplierUploadModel" required class="${UPLOAD_INPUT} hud-filter w-full">
                                            <option value="">请先选择采购基地</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label for="poSupplierUploadVersion" class="${UPLOAD_LABEL}">
                                            版本 <span class="text-brand">*</span>
                                        </label>
                                        <select id="poSupplierUploadVersion" required class="${UPLOAD_INPUT} hud-filter w-full">
                                            <option value="">请先选择项目</option>
                                        </select>
                                    </div>
                                </div>
                                <p class="ml-6 mt-1.5 text-[11px] text-ink-dim">这个范围要先生成采购对象。相同零件号只出一行。内部号只给人看，导入不读，方便到 ERP 查。第二页目录只对照，导入不读。检查没过的仍可上传，状态是待审；已经审核的不动。</p>
                                <div id="poSupplierUploadQaBanner"
                                     class="ml-6 mt-2 hidden text-[11px] text-brand-hud bg-brand-hud/10 border border-brand/30 px-3 py-2 leading-relaxed"></div>
                            </div>
                            <div class="h-px bg-app-surface mx-6 mb-4"></div>
                            <div>
                                <div class="flex items-center gap-2 mb-3">
                                    <span class="w-4 h-4 rounded-full bg-app-elevated flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-brand">2</span>
                                    </span>
                                    <span class="text-[13px] text-ink-dim font-medium tracking-wide uppercase">上传改供应商</span>
                                </div>
                                <div class="ml-6">
                                    <div id="poSupplierUploadZone" class="${UPLOAD_DROPZONE} mb-4" data-dropzone-state="idle">
                                        <div id="poSupplierUploadDropIdle" class="flex flex-col items-center gap-0">
                                            ${window.svgIcon('upload', 'w-10 h-10 text-ink-dim mx-auto mb-4')}
                                            <h5 id="poSupplierUploadTitle" class="text-xs font-medium text-ink-muted mb-1.5">拖拽文件到此处上传</h5>
                                            ${uploadFileHintHtml('poSupplierUploadHint')}
                                            <input type="file" id="poSupplierUploadFileInput" class="hidden" accept=".xlsx">
                                            ${uploadBrowseButtonHtml('poSupplierUploadSelectFileBtn')}
                                            <p class="text-[10px] text-ink-dim mt-5 mb-0">仅 .xlsx · 同步导入 · 只改第一页供应商列</p>
                                        </div>
                                        <div id="poSupplierUploadProgressPanel" class="hidden text-left w-full">
                                            <div class="flex items-center gap-2 min-w-0 mb-3">
                                                <span id="poSupplierUploadProgressIcon">${window.svgIcon('spinner', 'w-4 h-4 text-brand')}</span>
                                                <h5 id="poSupplierUploadProgressTitle" class="text-xs font-medium text-ink truncate mb-0">正在导入供应商指定...</h5>
                                            </div>
                                            <div class="h-1.5 w-full bg-app-deep border border-line overflow-hidden mb-3">
                                                <div id="poSupplierUploadProgressBar"
                                                     class="h-full bg-brand hud-brand-glow transition-all duration-300 animate-pulse"
                                                     style="width: 60%"></div>
                                            </div>
                                            <p id="poSupplierUploadProgressMsg" class="text-[11px] text-ink-muted leading-relaxed mb-0 whitespace-pre-wrap break-words max-h-48 overflow-y-auto">解析并写入数据库，请稍候</p>
                                        </div>
                                    </div>
                                    <div id="poSupplierUploadFilePreview" class="hidden mb-4"></div>
                                    <div class="flex items-center justify-end gap-3">
                                        ${uploadResetButtonHtml('poSupplierUploadResetBtn')}
                                        ${uploadSubmitButtonHtml('poSupplierUploadSubmitBtn')}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </form>
                </div>
            </div>
            <div class="space-y-3">
                <div class="bg-app-surface border border-line">
                    <div class="px-4 py-3 border-b border-line-subtle flex items-center gap-2">
                        <span class="${HUD_LED}"></span>
                        <h5 class="text-[11px] font-bold text-ink-muted mb-0 tracking-widest uppercase">格式说明</h5>
                    </div>
                    <div class="p-4 space-y-3 text-xs text-ink-dim">
                        <p>只改第一页的「供应商」。内部号只给人看，导入不读。相同零件号只出一行。供应商空着就是清空。填缩写、别名或 ERP 编号，都会换成工商名称。</p>
                        <p>找不到的厂到 <span class="text-ink-muted">#/supplier-list</span> 补档，本页不新建供应商。</p>
                        <p>检查没过的仍可上传，状态是待审。已经审核的行不动。自制件不能填供应商。</p>
                    </div>
                </div>
            </div>
        </div>
    `;
}
