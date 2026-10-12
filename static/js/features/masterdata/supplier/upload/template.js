/**
 * 供应商上传 — 核价厂档补录；列：缩写 / 全称 / 对外代码 / 别名
 */

import { UPLOAD_DROPZONE } from '../../../../ui/classes.js?v=14';
import {
    uploadBrowseButtonHtml,
    uploadFileHintHtml,
    uploadResetButtonHtml,
    uploadSubmitButtonHtml,
    uploadTemplateButtonHtml,
} from '../../../../ui/upload-actions.js?v=2';
import { recentUploadsCardHtml } from '../../../../ui/recent-uploads.js?v=3';

export function supplierUploadTemplate() {
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
            <div class="bg-app-hud border border-line-hud">
                <div class="px-5 py-3 border-b border-line-subtle flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2.5">
                        <span class="w-1 h-3.5 bg-brand-hud"></span>
                        <h5 class="text-xs font-semibold text-ink mb-0 tracking-wider">供应商补档</h5>
                    </div>
                    ${uploadTemplateButtonHtml('supplierUploadTemplateBtn')}
                </div>
                <div class="p-5">
                    <form id="supplierUploadForm">
                        <div id="supplierUploadZone" class="${UPLOAD_DROPZONE} mb-4" data-dropzone-state="idle">
                            <div id="supplierUploadDropIdle" class="flex flex-col items-center gap-0">
                                ${window.svgIcon('upload', 'w-10 h-10 text-ink-dim mx-auto mb-4')}
                                <h5 id="supplierUploadTitle" class="text-xs font-medium text-ink-muted mb-1.5">拖入 Excel</h5>
                                ${uploadFileHintHtml('supplierUploadHint')}
                                <input type="file" id="supplierUploadFileInput" class="hidden" accept=".xlsx,.xls">
                                ${uploadBrowseButtonHtml('supplierUploadSelectFileBtn')}
                                <p class="text-[10px] text-ink-faint mt-5 mb-0">.xlsx / .xls · 同步写入</p>
                            </div>
                            <div id="supplierUploadProgressPanel" class="hidden text-left w-full">
                                <div class="flex items-center gap-2 min-w-0 mb-3">
                                    <span id="supplierUploadProgressIcon">${window.svgIcon('spinner', 'w-4 h-4 text-brand-hud')}</span>
                                    <h5 id="supplierUploadProgressTitle" class="text-xs font-medium text-ink truncate mb-0">正在写入…</h5>
                                </div>
                                <div class="h-1.5 w-full bg-app-deep border border-line overflow-hidden mb-3">
                                    <div id="supplierUploadProgressBar"
                                         class="h-full bg-brand-hud transition-all duration-300 animate-pulse"
                                         style="width: 60%"></div>
                                </div>
                                <p id="supplierUploadProgressMsg" class="text-[11px] text-ink-muted leading-relaxed mb-0 whitespace-pre-wrap break-words max-h-48 overflow-y-auto">解析中</p>
                            </div>
                        </div>
                        <div id="supplierUploadFilePreview" class="hidden mb-4"></div>
                        <div class="flex items-center justify-end gap-3">
                            ${uploadResetButtonHtml('supplierUploadResetBtn')}
                            ${uploadSubmitButtonHtml('supplierUploadSubmitBtn')}
                        </div>
                    </form>
                </div>
            </div>
            <div class="space-y-3">
                <div class="bg-app-hud border border-line-hud">
                    <div class="px-4 py-3 border-b border-line-subtle flex items-center gap-2">
                        <span class="w-1 h-3 bg-brand-hud"></span>
                        <h5 class="text-[11px] font-semibold text-ink-muted mb-0 tracking-wider">要点</h5>
                    </div>
                    <div class="p-4 space-y-3">
                        <p class="text-xs text-ink-dim leading-relaxed mb-0">按全称认出供应商。已有全称则跳过。有一行不对，整份不写入。</p>
                        <a href="#/supplier-list" class="block text-[11px] text-brand-hud hover:text-brand-active">打开供应商列表 →</a>
                    </div>
                </div>
                ${recentUploadsCardHtml('supplierRecentUploads', 'bg-app-hud border border-line-hud')}
            </div>
        </div>
    `;
}
