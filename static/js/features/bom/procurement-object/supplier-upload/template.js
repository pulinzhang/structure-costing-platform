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
                                <p class="ml-6 mt-1.5 text-[11px] text-ink-dim">先在这个基地、项目和版本下生成采购对象。只改第一页黄色的「供应商」列。填法看右边说明。</p>
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
                                            <p class="text-[10px] text-ink-dim mt-5 mb-0">只收 .xlsx。只改第一页供应商列。</p>
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
                                            <p id="poSupplierUploadProgressMsg" class="text-[11px] text-ink-muted leading-relaxed mb-0 whitespace-pre-wrap break-words max-h-48 overflow-y-auto">正在导入，请稍候</p>
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
                        <p>只改第一页「供应商」这一列。内部号是给您对照 ERP 用的，上传时不看。同一个零件号只占一行。供应商留空，就是清掉原来的供应商。填简称、别名或 ERP 编号都可以，保存时会换成工商全称。</p>
                        <p>名单里没有的供应商，请先到 <a href="#/supplier-list" class="text-brand-hud hover:text-brand-active">供应商列表</a> 补上。这一页不能新建供应商。</p>
                        <p>材料检查没通过的零件也可以上传，上传后仍是待审核。已经审核过的行不会改。自制件不要填供应商。</p>
                    </div>
                </div>
            </div>
        </div>
    `;
}
