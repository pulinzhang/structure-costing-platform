import { UPLOAD_DROPZONE, UPLOAD_INPUT, HUD_LED } from '../../../../ui/classes.js?v=14';
import { recentUploadsCardHtml } from '../../../../ui/recent-uploads.js?v=3';
import {
    uploadBrowseButtonHtml,
    uploadFileHintHtml,
    uploadResetButtonHtml,
    uploadSubmitButtonHtml,
    uploadTemplateButtonHtml,
} from '../../../../ui/upload-actions.js?v=2';

export function dieUploadTemplate() {
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
            <div class="bg-app-surface border border-line">
                <div class="px-5 py-3 border-b border-line-subtle flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2.5">
                        ${window.svgIcon('clipboard-list', 'w-3.5 h-3.5 text-ink-dim')}
                        <h5 class="text-xs font-semibold text-ink-muted mb-0">上传冲压模具布点清单</h5>
                    </div>
                    ${uploadTemplateButtonHtml('dieUploadTemplateBtn')}
                </div>
                <div id="sopBannerSlot"></div>
                <div class="p-5">
                    <form id="dieUploadForm" enctype="multipart/form-data">
                        <div class="bg-app-surface border border-line p-4">
                            <div class="mb-5">
                                <div class="flex items-center gap-2 mb-2.5">
                                    <span class="w-4 h-4 rounded-full bg-app-elevated flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-brand">1</span>
                                    </span>
                                    <span class="text-[13px] text-ink-dim font-medium tracking-wide uppercase">选择采购基地</span>
                                </div>
                                <div class="ml-6">
                                    <select id="dieLocation" name="location" required class="${UPLOAD_INPUT} hud-filter w-full max-w-[280px]">
                                        <option value="">请选择采购基地</option>
                                    </select>
                                    <p class="mt-2 text-[10px] text-ink-faint">必选。</p>
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
                                    <select id="dieVehicleModel" name="vehicle_model" required
                                            class="${UPLOAD_INPUT} hud-filter w-full max-w-[280px]">
                                        <option value="">请先选择采购基地</option>
                                    </select>
                                    <p class="mt-2 text-[10px] text-ink-faint">须和文件里的项目一致。</p>
                                </div>
                            </div>
                            <div class="h-px bg-app-surface mx-6 mb-4"></div>
                            <div>
                                <div class="flex items-center gap-2 mb-3">
                                    <span class="w-4 h-4 rounded-full bg-app-elevated flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-brand">3</span>
                                    </span>
                                    <span class="text-[13px] text-ink-dim font-medium tracking-wide uppercase">上传布点文件</span>
                                </div>
                                <div class="ml-6">
                                    <div id="dieUploadZone" class="${UPLOAD_DROPZONE} mb-4" data-dropzone-state="idle">
                                        <div id="dieDropIdle" class="flex flex-col items-center gap-0">
                                            <div class="flex items-center gap-3 mb-5 w-full px-3">
                                                <div class="h-px flex-1 bg-app-elevated"></div>
                                                <div class="w-1.5 h-1.5 border border-line rotate-45"></div>
                                                <div class="h-px flex-1 bg-app-elevated"></div>
                                            </div>
                                            <div class="mb-3 relative">
                                                <div class="absolute inset-0 bg-brand/8 blur-xl rounded-full"></div>
                                                <svg class="w-9 h-9 text-ink-faint relative z-10" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.2">
                                                    <path stroke-linecap="round" stroke-linejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
                                                </svg>
                                            </div>
                                            <h5 id="dieUploadTitle" class="text-[11px] text-ink-dim font-semibold tracking-widest uppercase mb-1">拖拽文件到此处</h5>
                                            ${uploadFileHintHtml('dieUploadHint')}
                                            <div class="flex items-center gap-3 mt-1 w-full px-3">
                                                <div class="h-px flex-1 bg-app-elevated"></div>
                                                <div class="w-1.5 h-1.5 border border-line rotate-45"></div>
                                                <div class="h-px flex-1 bg-app-elevated"></div>
                                            </div>
                                            <input type="file" id="dieFileInput" class="hidden" accept=".xlsx,.xls">
                                            ${uploadBrowseButtonHtml('dieSelectFileBtn')}
                                            <p class="text-[10px] text-ink-faint mt-4 mb-0">.xlsx / .xls<span class="mx-2 text-ink-faint">|</span>最大 50MB</p>
                                        </div>
                                        <div id="dieProgressPanel" class="hidden text-left w-full">
                                            <div class="flex items-center justify-between gap-3 mb-3">
                                                <div class="flex items-center gap-2 min-w-0">
                                                    <span id="dieProgressIcon">${window.svgIcon('spinner', 'w-4 h-4 text-brand')}</span>
                                                    <h5 id="dieProgressTitle" class="text-xs font-medium text-ink truncate mb-0">正在解析模具布点...</h5>
                                                </div>
                                                <span id="dieProgressPercent" class="text-xs font-mono tabular-nums text-brand shrink-0">0%</span>
                                            </div>
                                            <div class="h-1.5 w-full bg-app-deep border border-line overflow-hidden mb-3">
                                                <div id="dieProgressBar" class="h-full bg-brand hud-brand-glow transition-all duration-300" style="width: 0%"></div>
                                            </div>
                                            <p id="dieProgressMsg" class="text-[11px] text-ink-muted leading-relaxed mb-0 whitespace-pre-wrap break-words max-h-48 overflow-y-auto">正在导入。</p>
                                        </div>
                                    </div>
                                    <div id="dieFilePreview" class="hidden mb-4"></div>
                                    <div class="flex items-center justify-end gap-3">
                                        ${uploadResetButtonHtml('dieResetButton')}
                                        ${uploadSubmitButtonHtml('dieSubmitBtn')}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </form>
                </div>
            </div>
            <div class="space-y-3">
                <div class="bg-app-surface border border-line">
                    <div class="px-4 py-3 border-b border-line-subtle flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <span class="${HUD_LED}"></span>
                            <h5 class="text-[11px] font-bold text-ink-muted mb-0 tracking-widest uppercase">说明</h5>
                        </div>
                    </div>
                    <div class="p-4 space-y-2 text-[11px] text-ink-muted leading-relaxed">
                        <p>文件里的项目必须和本页所选一致。</p>
                        <p>已经投产后再传，只更新写到的零件。出现新零件号，整份退回。</p>
                    </div>
                </div>
                ${recentUploadsCardHtml('dieRecentUploads')}
            </div>
        </div>
    `;
}
