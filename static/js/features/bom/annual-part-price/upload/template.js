/**
 * 年度零件价上传 — 模板
 * 下载模板：基地 + 项目 + 年度；导入仍按基地 + 年度写入价表
 */

import { UPLOAD_DROPZONE, UPLOAD_INPUT, UPLOAD_LABEL, HUD_LED } from '../../../../ui/classes.js?v=14';
import { recentUploadsCardHtml } from '../../../../ui/recent-uploads.js?v=3';
import {
    uploadBrowseButtonHtml,
    uploadFileHintHtml,
    uploadResetButtonHtml,
    uploadSubmitButtonHtml,
    uploadTemplateButtonHtml,
} from '../../../../ui/upload-actions.js?v=2';

export function annualPartPriceUploadTemplate() {
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
            <div class="bg-app-surface border border-line">
                <div class="px-5 py-3 border-b border-line-subtle flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2.5">
                        ${window.svgIcon('file-earmark-excel', 'w-3.5 h-3.5 text-ink-dim')}
                        <h5 class="text-xs font-semibold text-ink-muted mb-0">年度零件价导入</h5>
                    </div>
                    ${uploadTemplateButtonHtml('annualPartPriceUploadTemplateBtn')}
                </div>
                <div class="p-5">
                    <form id="annualPartPriceUploadForm">
                        <div class="bg-app-surface border border-line p-4">
                            <div class="mb-5">
                                <div class="flex items-center gap-2 mb-2.5">
                                    <span class="w-4 h-4 rounded-full bg-app-elevated flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-brand">1</span>
                                    </span>
                                    <span class="text-[13px] text-ink-dim font-medium tracking-wide uppercase">选择基地、项目与年度</span>
                                </div>
                                <div class="ml-6 grid grid-cols-1 sm:grid-cols-3 gap-3">
                                    <div>
                                        <label for="annualPartPriceUploadLocation" class="${UPLOAD_LABEL}">
                                            采购基地 <span class="text-brand">*</span>
                                        </label>
                                        <select id="annualPartPriceUploadLocation"
                                                name="location"
                                                required
                                                class="${UPLOAD_INPUT} hud-filter w-full">
                                            <option value="">请选择采购基地</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label for="annualPartPriceUploadVehicleModel" class="${UPLOAD_LABEL}">
                                            项目 <span class="text-brand">*</span>
                                        </label>
                                        <select id="annualPartPriceUploadVehicleModel"
                                                name="vehicle_model"
                                                required
                                                class="${UPLOAD_INPUT} hud-filter w-full">
                                            <option value="">请先选择采购基地</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label for="annualPartPriceUploadYear" class="${UPLOAD_LABEL}">
                                            年度 <span class="text-brand">*</span>
                                        </label>
                                        <input type="text"
                                               id="annualPartPriceUploadYear"
                                               name="year"
                                               placeholder="例如：2026"
                                               required
                                               pattern="[0-9]{4}"
                                               maxlength="4"
                                               class="${UPLOAD_INPUT} w-full">
                                    </div>
                                </div>
                                <p class="ml-6 mt-1.5 text-[11px] text-ink-dim">先选基地、项目和年度再下载。</p>
                            </div>

                            <div class="h-px bg-app-surface mx-6 mb-4"></div>

                            <div>
                                <div class="flex items-center gap-2 mb-3">
                                    <span class="w-4 h-4 rounded-full bg-app-elevated flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-brand">2</span>
                                    </span>
                                    <span class="text-[13px] text-ink-dim font-medium tracking-wide uppercase">上传年度零件价表</span>
                                </div>
                                <div class="ml-6">
                                    <div id="annualPartPriceUploadZone" class="${UPLOAD_DROPZONE} mb-4" data-dropzone-state="idle">
                                        <div id="annualPartPriceUploadDropIdle" class="flex flex-col items-center gap-0">
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
                                            <h5 id="annualPartPriceUploadTitle" class="text-[11px] text-ink-dim font-semibold tracking-widest uppercase mb-1">拖拽文件到此处</h5>
                                            ${uploadFileHintHtml('annualPartPriceUploadHint')}
                                            <div class="flex items-center gap-3 mt-1 w-full px-3">
                                                <div class="h-px flex-1 bg-app-elevated"></div>
                                                <div class="w-1.5 h-1.5 border border-line rotate-45"></div>
                                                <div class="h-px flex-1 bg-app-elevated"></div>
                                            </div>
                                            <input type="file" id="annualPartPriceUploadFileInput" class="hidden" accept=".xlsx">
                                            ${uploadBrowseButtonHtml('annualPartPriceUploadSelectFileBtn')}
                                            <p class="text-[10px] text-ink-faint mt-4 mb-0">
                                                只收 .xlsx
                                            </p>
                                        </div>

                                        <div id="annualPartPriceUploadProgressPanel" class="hidden text-left w-full">
                                            <div class="flex items-center gap-2 min-w-0 mb-3">
                                                <span id="annualPartPriceUploadProgressIcon">${window.svgIcon('spinner', 'w-4 h-4 text-brand')}</span>
                                                <h5 id="annualPartPriceUploadProgressTitle" class="text-xs font-medium text-ink truncate mb-0">正在导入年度零件价...</h5>
                                            </div>
                                            <div class="h-1.5 w-full bg-app-deep border border-line overflow-hidden mb-3">
                                                <div id="annualPartPriceUploadProgressBar"
                                                     class="h-full bg-brand hud-brand-glow transition-all duration-300 animate-pulse"
                                                     style="width: 60%"></div>
                                            </div>
                                            <p id="annualPartPriceUploadProgressMsg" class="text-[11px] text-ink-muted leading-relaxed mb-0 whitespace-pre-wrap break-words max-h-48 overflow-y-auto">正在导入。</p>
                                        </div>
                                    </div>

                                    <div id="annualPartPriceUploadFilePreview" class="hidden mb-4"></div>

                                    <div class="flex items-center justify-end gap-3">
                                        ${uploadResetButtonHtml('annualPartPriceUploadResetBtn')}
                                        ${uploadSubmitButtonHtml('annualPartPriceUploadSubmitBtn')}
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
                            <h5 class="text-[11px] font-bold text-ink-muted mb-0 tracking-widest uppercase">格式说明</h5>
                        </div>
                    </div>
                    <div class="p-4">
                        <p class="text-[11px] text-ink-muted leading-relaxed mb-0">同一基地、同一年、同一零件号，再传会更新。已审核的不会被盖掉。</p>
                    </div>
                </div>
                ${recentUploadsCardHtml('annualPartPriceRecentUploads')}
            </div>
        </div>
    `;
}
