/**
 * 冲压检具费上传 — 基地+项目必选，模板从模具布点带出零件
 */

import { UPLOAD_DROPZONE, UPLOAD_INPUT, HUD_LED } from '../../../../ui/classes.js?v=14';
import { recentUploadsCardHtml } from '../../../../ui/recent-uploads.js?v=3';
import {
    uploadBrowseButtonHtml,
    uploadFileHintHtml,
    uploadResetButtonHtml,
    uploadSubmitButtonHtml,
    uploadTemplateButtonHtml,
} from '../../../../ui/upload-actions.js?v=2';

export function gaugeFeeUploadTemplate() {
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
            <div class="bg-app-surface border border-line">
                <div class="px-5 py-3 border-b border-line-subtle flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2.5">
                        ${window.svgIcon('file-earmark-excel', 'w-3.5 h-3.5 text-ink-dim')}
                        <h5 class="text-xs font-semibold text-ink-muted mb-0">上传冲压检具费</h5>
                    </div>
                    ${uploadTemplateButtonHtml('gfuTemplateBtn')}
                </div>
                <div class="p-5">
                    <form id="gfuForm">
                        <div class="bg-app-surface border border-line p-4">
                            <div class="mb-5">
                                <div class="flex items-center gap-2 mb-2.5">
                                    <span class="w-4 h-4 rounded-full bg-app-elevated flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-brand">1</span>
                                    </span>
                                    <span class="text-[13px] text-ink-dim font-medium tracking-wide uppercase">选择采购基地</span>
                                </div>
                                <div class="ml-6">
                                    <select id="gfuLocation" name="location" required class="${UPLOAD_INPUT} hud-filter w-full max-w-[280px]">
                                        <option value="">请选择采购基地</option>
                                    </select>
                                </div>
                            </div>
                            <div class="h-px bg-app-surface mx-6 mb-4"></div>
                            <div class="mb-5">
                                <div class="flex items-center gap-2 mb-2.5">
                                    <span class="w-4 h-4 rounded-full bg-app-elevated flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-brand">2</span>
                                    </span>
                                    <span class="text-[13px] text-ink-dim font-medium tracking-wide uppercase">选择项目</span>
                                </div>
                                <div class="ml-6">
                                    <select id="gfuVehicle" name="vehicle_model" required class="${UPLOAD_INPUT} hud-filter w-full max-w-[280px]">
                                        <option value="">请先选择基地</option>
                                    </select>
                                    <p class="mt-2 text-[10px] text-ink-faint">模板零件来自模具布点。</p>
                                </div>
                            </div>
                            <div class="h-px bg-app-surface mx-6 mb-4"></div>
                            <div>
                                <div class="flex items-center gap-2 mb-3">
                                    <span class="w-4 h-4 rounded-full bg-app-elevated flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-brand">3</span>
                                    </span>
                                    <span class="text-[13px] text-ink-dim font-medium tracking-wide uppercase">上传检具费</span>
                                </div>
                                <div class="ml-6">
                                    <div id="gfuZone" class="${UPLOAD_DROPZONE} mb-4" data-dropzone-state="idle">
                                        <div id="gfuDropIdle" class="flex flex-col items-center gap-0">
                                            <div class="mb-3 relative">
                                                <svg class="w-9 h-9 text-ink-faint" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.2">
                                                    <path stroke-linecap="round" stroke-linejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
                                                </svg>
                                            </div>
                                            <h5 id="gfuTitle" class="text-[11px] text-ink-dim font-semibold tracking-widest uppercase mb-1">拖拽文件到此处</h5>
                                            ${uploadFileHintHtml('gfuHint')}
                                            <input type="file" id="gfuFileInput" class="hidden" accept=".xlsx">
                                            ${uploadBrowseButtonHtml('gfuSelectFileBtn')}
                                            <p class="text-[10px] text-ink-faint mt-4 mb-0">只收 .xlsx</p>
                                        </div>
                                        <div id="gfuProgressPanel" class="hidden text-left w-full">
                                            <div class="flex items-center gap-2 min-w-0 mb-3">
                                                <span id="gfuProgressIcon">${window.svgIcon('spinner', 'w-4 h-4 text-brand')}</span>
                                                <h5 id="gfuProgressTitle" class="text-xs font-medium text-ink truncate mb-0">正在导入检具费...</h5>
                                            </div>
                                            <div class="h-1.5 w-full bg-app-deep border border-line overflow-hidden mb-3">
                                                <div id="gfuProgressBar"
                                                     class="h-full bg-brand hud-brand-glow transition-all duration-300 animate-pulse"
                                                     style="width: 60%"></div>
                                            </div>
                                            <p id="gfuProgressMsg" class="text-[11px] text-ink-muted leading-relaxed mb-0 whitespace-pre-wrap break-words max-h-48 overflow-y-auto">正在导入。</p>
                                        </div>
                                    </div>
                                    <div id="gfuFilePreview" class="hidden mb-4"></div>
                                    <div class="flex items-center justify-end gap-3">
                                        ${uploadResetButtonHtml('gfuResetBtn')}
                                        ${uploadSubmitButtonHtml('gfuSubmitBtn')}
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
                        <h5 class="text-[11px] font-bold text-ink-muted mb-0 tracking-widest uppercase">说明</h5>
                    </div>
                    <div class="p-4 text-[11px] text-ink-muted leading-relaxed">
                        <p class="mb-0">零件来自模具布点。再传会整份换成新表。零件号必须已在布点里。</p>
                    </div>
                </div>
                ${recentUploadsCardHtml('gfuRecentUploads')}
            </div>
        </div>
    `;
}
