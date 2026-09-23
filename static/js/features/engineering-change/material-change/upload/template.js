/**
 * 材料变更上传
 */

import { UPLOAD_DROPZONE, UPLOAD_INPUT, HUD_LED } from '../../../../ui/classes.js?v=13';
import {
    uploadBrowseButtonHtml,
    uploadFileHintHtml,
    uploadResetButtonHtml,
    uploadSubmitButtonHtml,
    uploadTemplateButtonHtml,
} from '../../../../ui/upload-actions.js?v=2';

export function materialChangeUploadTemplate() {
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
            <div class="bg-app-surface border border-line">
                <div class="px-5 py-3 border-b border-line-subtle flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2.5">
                        ${window.svgIcon('file-earmark-excel', 'w-3.5 h-3.5 text-ink-dim')}
                        <h5 class="text-xs font-semibold text-ink-muted mb-0">上传材料变更</h5>
                    </div>
                    ${uploadTemplateButtonHtml('ecmUploadTemplateBtn')}
                </div>
                <div class="p-5">
                    <form id="ecmUploadForm" enctype="multipart/form-data">
                        <div class="bg-app-surface border border-line p-4">
                            <div class="mb-5">
                                <div class="flex items-center gap-2 mb-2.5">
                                    <span class="w-4 h-4 rounded-full bg-app-elevated flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-brand">1</span>
                                    </span>
                                    <span class="text-[13px] text-ink-dim font-medium tracking-wide uppercase">选择采购基地 / 项目</span>
                                </div>
                                <div class="ml-6">
                                    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                                        <select id="ecmUploadLocation" name="location" required class="${UPLOAD_INPUT} hud-filter">
                                            <option value="">请选择采购基地</option>
                                        </select>
                                        <select id="ecmUploadVehicleModel" name="vehicle_model" required class="${UPLOAD_INPUT} hud-filter">
                                            <option value="">请先选择采购基地</option>
                                        </select>
                                    </div>
                                    <p class="mt-2 text-[10px] text-ink-faint">必选。项目须该生效月可引入，且与工程变更单（材质）完全一致。</p>
                                </div>
                            </div>
                            <div class="h-px bg-app-surface mx-6 mb-4"></div>
                            <div class="mb-5">
                                <div class="flex items-center gap-2 mb-2.5">
                                    <span class="w-4 h-4 rounded-full bg-app-elevated flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-brand">2</span>
                                    </span>
                                    <span class="text-[13px] text-ink-dim font-medium tracking-wide uppercase">选择生效年月</span>
                                </div>
                                <div class="ml-6">
                                    <div class="flex items-center gap-3">
                                        <select id="ecmUploadYear" name="effective_year" required class="${UPLOAD_INPUT} hud-filter w-[140px]"></select>
                                        <select id="ecmUploadMonth" name="effective_month" required class="${UPLOAD_INPUT} hud-filter w-[120px]"></select>
                                    </div>
                                    <p class="mt-2 text-[10px] text-ink-faint">表里写成「2026年6月」或「2026年06月」都可以，也可以是日期。须和这里选的年月一致。</p>
                                </div>
                            </div>
                            <div class="h-px bg-app-surface mx-6 mb-4"></div>
                            <div>
                                <div class="flex items-center gap-2 mb-3">
                                    <span class="w-4 h-4 rounded-full bg-app-elevated flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-brand">3</span>
                                    </span>
                                    <span class="text-[13px] text-ink-dim font-medium tracking-wide uppercase">上传材料变更</span>
                                </div>
                                <div class="ml-6">
                                    <div id="ecmUploadZone" class="${UPLOAD_DROPZONE} mb-4" data-dropzone-state="idle">
                                        <div id="ecmDropIdle" class="flex flex-col items-center gap-0">
                                            <h5 id="ecmUploadTitle" class="text-[11px] text-ink-dim font-semibold tracking-widest uppercase mb-1">拖拽文件到此处</h5>
                                            ${uploadFileHintHtml('ecmUploadHint')}
                                            <input type="file" id="ecmUploadFileInput" class="hidden" accept=".xlsx">
                                            ${uploadBrowseButtonHtml('ecmUploadSelectFileBtn')}
                                            <p class="text-[10px] text-ink-faint mt-4 mb-0">只收 .xlsx · 最大 50MB · 必须恰好两张表 · 料厚填数字，最多两位小数</p>
                                        </div>
                                        <div id="ecmProgressPanel" class="hidden text-left w-full">
                                            <div class="flex items-center justify-between gap-3 mb-3">
                                                <h5 id="ecmProgressTitle" class="text-xs font-medium text-ink truncate mb-0">正在解析材料变更...</h5>
                                                <span id="ecmProgressPercent" class="text-xs font-mono tabular-nums text-brand shrink-0">0%</span>
                                            </div>
                                            <div class="h-1.5 w-full bg-app-deep border border-line overflow-hidden mb-3">
                                                <div id="ecmProgressBar" class="h-full bg-brand hud-brand-glow transition-all duration-300" style="width: 0%"></div>
                                            </div>
                                            <p id="ecmProgressMsg" class="text-[11px] text-ink-muted leading-relaxed mb-0 whitespace-pre-wrap break-words max-h-48 overflow-y-auto">已提交解析队列</p>
                                        </div>
                                    </div>
                                    <div id="ecmFilePreview" class="hidden mb-4"></div>
                                    <div id="ecmUploadErrorPanel" class="hidden mb-4 border border-danger/50 bg-app-deep" role="alert">
                                        <div class="flex items-start justify-between gap-3 px-3 py-2.5 border-b border-danger/30">
                                            <h6 class="text-[11px] font-semibold text-danger mb-0 tracking-wide">导入失败</h6>
                                            <div class="flex items-center gap-1 shrink-0">
                                                <button type="button" id="ecmUploadErrorCopyBtn" class="px-2 py-1 text-[10px] text-ink-muted border border-line rounded-sm">复制</button>
                                                <button type="button" id="ecmUploadErrorCloseBtn" class="text-ink-dim p-1" aria-label="关闭">
                                                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"/></svg>
                                                </button>
                                            </div>
                                        </div>
                                        <pre id="ecmUploadErrorBody" class="m-0 px-3 py-3 text-[12px] font-mono leading-relaxed text-danger whitespace-pre-wrap break-words max-h-[360px] overflow-y-auto select-text"></pre>
                                    </div>
                                    <div class="flex items-center justify-end gap-3">
                                        ${uploadResetButtonHtml('ecmUploadResetBtn')}
                                        ${uploadSubmitButtonHtml('ecmUploadSubmitBtn')}
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
                    <div class="p-4 space-y-3 text-[11px] text-ink-muted leading-relaxed">
                        <p>只收「工程变更单（材质）」。一条不过整本拒，禁止修空格。</p>
                        <p>变更前必须等于库里最新材料。再变请另起一本更晚月。</p>
                        <p>不改工艺行材料。回滚在列表整本删除。</p>
                    </div>
                </div>
                <div class="bg-app-surface border border-line">
                    <div class="px-4 py-3 border-b border-line-subtle">
                        <h5 class="text-[11px] font-bold text-ink-muted mb-0 tracking-widest uppercase">最近上传</h5>
                    </div>
                    <div class="p-4" id="ecmRecentUploads"></div>
                </div>
            </div>
        </div>
    `;
}
