/**
 * BOM 材料清单上传 — 模板
 * 仅上传：基地必选 + Excel 拖拽，无列表/删除/树
 */

import { UPLOAD_DROPZONE, UPLOAD_INPUT, HUD_LED } from '../../../../ui/classes.js?v=15';
import { recentUploadsCardHtml } from '../../../../ui/recent-uploads.js?v=3';
import {
    uploadBrowseButtonHtml,
    uploadFileHintHtml,
    uploadResetButtonHtml,
    uploadSubmitButtonHtml,
    uploadTemplateButtonHtml,
} from '../../../../ui/upload-actions.js?v=2';

export function bomUploadTemplate() {
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
            <div class="bg-app-surface border border-line">
                <div class="px-5 py-3 border-b border-line-subtle flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2.5">
                        ${window.svgIcon('file-earmark-excel', 'w-3.5 h-3.5 text-ink-dim')}
                        <h5 class="text-xs font-semibold text-ink-muted mb-0">上传车身件材料清单</h5>
                    </div>
                    ${uploadTemplateButtonHtml('bomUploadTemplateBtn')}
                </div>
                <div id="sopBannerSlot"></div>
                <div class="p-5">
                    <form id="bomUploadForm">
                        <div class="bg-app-surface border border-line p-4">
                            <div class="mb-5">
                                <div class="flex items-center gap-2 mb-2.5">
                                    <span class="w-4 h-4 rounded-full bg-app-elevated flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-brand">1</span>
                                    </span>
                                    <span class="text-[13px] text-ink-dim font-medium tracking-wide uppercase">选择采购基地</span>
                                </div>
                                <div class="ml-6">
                                    <select id="bomUploadLocation"
                                            name="location"
                                            required
                                            class="${UPLOAD_INPUT} hud-filter w-full max-w-[280px]">
                                        <option value="">请选择采购基地</option>
                                    </select>
                                    <p class="mt-1.5 text-[11px] text-ink-dim">必选。钢价按这个基地匹配。</p>
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
                                    <select id="bomUploadVehicleModel"
                                            name="vehicle_model"
                                            required
                                            class="${UPLOAD_INPUT} hud-filter w-full max-w-[280px]">
                                        <option value="">请先选择采购基地</option>
                                    </select>
                                    <p class="mt-1.5 text-[11px] text-ink-dim">文件里的项目代号必须和所选一致。</p>
                                </div>
                            </div>

                            <div class="h-px bg-app-surface mx-6 mb-4"></div>

                            <div>
                                <div class="flex items-center gap-2 mb-3">
                                    <span class="w-4 h-4 rounded-full bg-app-elevated flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-brand">3</span>
                                    </span>
                                    <span class="text-[13px] text-ink-dim font-medium tracking-wide uppercase">上传材料清单</span>
                                </div>
                                <div class="ml-6">
                                    <div id="bomUploadZone" class="${UPLOAD_DROPZONE} mb-4" data-dropzone-state="idle">
                                        <div id="bomUploadDropIdle" class="flex flex-col items-center gap-0">
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
                                            <h5 id="bomUploadTitle" class="text-[11px] text-ink-dim font-semibold tracking-widest uppercase mb-1">拖拽文件到此处</h5>
                                            ${uploadFileHintHtml('bomUploadHint')}
                                            <div class="flex items-center gap-3 mt-1 w-full px-3">
                                                <div class="h-px flex-1 bg-app-elevated"></div>
                                                <div class="w-1.5 h-1.5 border border-line rotate-45"></div>
                                                <div class="h-px flex-1 bg-app-elevated"></div>
                                            </div>
                                            <input type="file" id="bomUploadFileInput" class="hidden" accept=".xlsx,.xls">
                                            ${uploadBrowseButtonHtml('bomUploadSelectFileBtn')}
                                            <p class="text-[10px] text-ink-faint mt-4 mb-0">
                                                .xlsx / .xls
                                                <span class="mx-2 text-ink-faint">|</span>
                                                最大 50MB
                                            </p>
                                        </div>

                                        <div id="bomUploadProgressPanel" class="hidden text-left w-full">
                                            <div class="flex items-center justify-between gap-3 mb-3">
                                                <div class="flex items-center gap-2 min-w-0">
                                                    <span id="bomUploadProgressIcon">${window.svgIcon('spinner', 'w-4 h-4 text-brand')}</span>
                                                    <h5 id="bomUploadProgressTitle" class="text-xs font-medium text-ink truncate mb-0">正在解析材料清单...</h5>
                                                </div>
                                                <span id="bomUploadProgressPercent" class="text-xs font-mono tabular-nums text-brand shrink-0">0%</span>
                                            </div>
                                            <div class="h-1.5 w-full bg-app-deep border border-line overflow-hidden mb-3">
                                                <div id="bomUploadProgressBar"
                                                     class="h-full bg-brand hud-brand-glow transition-all duration-300"
                                                     style="width: 0%"></div>
                                            </div>
                                            <p id="bomUploadProgressMsg" class="text-[11px] text-ink-muted leading-relaxed mb-0 whitespace-pre-wrap break-words max-h-48 overflow-y-auto">正在导入。</p>
                                        </div>
                                    </div>

                                    <div id="bomUploadFilePreview" class="hidden mb-4"></div>

                                    <div id="bomUploadErrorPanel"
                                         class="hidden mb-4 border border-danger/50 bg-app-deep"
                                         role="alert">
                                        <div class="flex items-start justify-between gap-3 px-3 py-2.5 border-b border-danger/30">
                                            <div class="min-w-0">
                                                <h6 id="bomUploadErrorTitle"
                                                    class="text-[11px] font-semibold text-danger mb-0.5 tracking-wide">导入失败</h6>
                                                <p class="text-[10px] text-ink-muted mb-0">请按提示里的行号改好原表后再上传。这段话可以复制。</p>
                                            </div>
                                            <div class="flex items-center gap-1 shrink-0">
                                                <button type="button"
                                                        id="bomUploadErrorCopyBtn"
                                                        class="px-2 py-1 text-[10px] text-ink-muted border border-line rounded-sm hover:border-ink-muted hover:text-ink transition-all">
                                                    复制
                                                </button>
                                                <button type="button"
                                                        id="bomUploadErrorCloseBtn"
                                                        class="text-ink-dim hover:text-ink transition-colors p-1"
                                                        aria-label="关闭错误提示">
                                                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"/></svg>
                                                </button>
                                            </div>
                                        </div>
                                        <pre id="bomUploadErrorBody"
                                             class="m-0 px-3 py-3 text-[12px] font-mono leading-relaxed text-danger whitespace-pre-wrap break-words max-h-[360px] overflow-y-auto select-text"></pre>
                                    </div>

                                    <div class="flex items-center justify-end gap-3">
                                        ${uploadResetButtonHtml('bomUploadResetBtn')}
                                        ${uploadSubmitButtonHtml('bomUploadSubmitBtn')}
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
                            <h5 class="text-[11px] font-bold text-ink-muted mb-0 tracking-widest uppercase">导入说明</h5>
                        </div>
                    </div>
                    <div class="p-4">
                        <p class="text-[11px] text-ink-muted leading-relaxed mb-0">项目和版本从表头读取。已经投产后再传，只更新写到的总成。出现新零件号，整份不收。</p>
                    </div>
                </div>
                ${recentUploadsCardHtml('bomRecentUploads')}
            </div>
        </div>
    `;
}
