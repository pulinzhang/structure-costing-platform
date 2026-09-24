/**
 * 工程变更上传 — 与冲压布点 / 工艺上传同一套舱体。
 */

import { UPLOAD_DROPZONE, UPLOAD_INPUT, HUD_LED } from '../../../../ui/classes.js?v=13';
import {
    uploadBrowseButtonHtml,
    uploadFileHintHtml,
    uploadResetButtonHtml,
    uploadSubmitButtonHtml,
    uploadTemplateButtonHtml,
} from '../../../../ui/upload-actions.js?v=2';

export function engineeringChangeUploadTemplate() {
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
            <div class="bg-app-surface border border-line">
                <div class="px-5 py-3 border-b border-line-subtle flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2.5">
                        ${window.svgIcon('file-earmark-excel', 'w-3.5 h-3.5 text-ink-dim')}
                        <h5 class="text-xs font-semibold text-ink-muted mb-0">上传工程变更</h5>
                    </div>
                    ${uploadTemplateButtonHtml('ecUploadTemplateBtn')}
                </div>
                <div class="p-5">
                    <form id="ecUploadForm" enctype="multipart/form-data">
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
                                        <select id="ecUploadLocation" name="location" required class="${UPLOAD_INPUT} hud-filter">
                                            <option value="">请选择采购基地</option>
                                        </select>
                                        <select id="ecUploadVehicleModel" name="vehicle_model" required class="${UPLOAD_INPUT} hud-filter">
                                            <option value="">请先选择采购基地</option>
                                        </select>
                                    </div>
                                    <p class="mt-2 text-[10px] text-ink-faint">必选。用基地找到投产清单。这个月这个项目必须还在做，并且和工程变更单上的项目一致。</p>
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
                                        <select id="ecUploadYear" name="effective_year" required
                                                class="${UPLOAD_INPUT} hud-filter w-[140px]"></select>
                                        <select id="ecUploadMonth" name="effective_month" required
                                                class="${UPLOAD_INPUT} hud-filter w-[120px]"></select>
                                    </div>
                                    <p class="mt-2 text-[10px] text-ink-faint">须和工程变更单上的生效年月一致。从这个月起用新零件号，上个月仍按变更前的总成结账。</p>
                                </div>
                            </div>
                            <div class="h-px bg-app-surface mx-6 mb-4"></div>
                            <div>
                                <div class="flex items-center gap-2 mb-3">
                                    <span class="w-4 h-4 rounded-full bg-app-elevated flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-brand">3</span>
                                    </span>
                                    <span class="text-[13px] text-ink-dim font-medium tracking-wide uppercase">上传变更文件</span>
                                </div>
                                <div class="ml-6">
                                    <div id="ecUploadZone" class="${UPLOAD_DROPZONE} mb-4" data-dropzone-state="idle">
                                        <div id="ecDropIdle" class="flex flex-col items-center gap-0">
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
                                            <h5 id="ecUploadTitle" class="text-[11px] text-ink-dim font-semibold tracking-widest uppercase mb-1">拖拽文件到此处</h5>
                                            ${uploadFileHintHtml('ecUploadHint')}
                                            <div class="flex items-center gap-3 mt-1 w-full px-3">
                                                <div class="h-px flex-1 bg-app-elevated"></div>
                                                <div class="w-1.5 h-1.5 border border-line rotate-45"></div>
                                                <div class="h-px flex-1 bg-app-elevated"></div>
                                            </div>
                                            <input type="file" id="ecUploadFileInput" class="hidden" accept=".xlsx,.xls">
                                            ${uploadBrowseButtonHtml('ecUploadSelectFileBtn')}
                                            <p class="text-[10px] text-ink-faint mt-4 mb-0">.xlsx / .xls<span class="mx-2 text-ink-faint">|</span>最大 50MB · 须含工程变更单、材料清单、工艺确认表</p>
                                        </div>
                                        <div id="ecProgressPanel" class="hidden text-left w-full">
                                            <div class="flex items-center justify-between gap-3 mb-3">
                                                <div class="flex items-center gap-2 min-w-0">
                                                    ${window.svgIcon('spinner', 'w-4 h-4 text-brand')}
                                                    <h5 id="ecProgressTitle" class="text-xs font-medium text-ink truncate mb-0">正在解析工程变更...</h5>
                                                </div>
                                                <span id="ecProgressPercent" class="text-xs font-mono tabular-nums text-brand shrink-0">0%</span>
                                            </div>
                                            <div class="h-1.5 w-full bg-app-deep border border-line overflow-hidden mb-3">
                                                <div id="ecProgressBar" class="h-full bg-brand hud-brand-glow transition-all duration-300" style="width: 0%"></div>
                                            </div>
                                            <p id="ecProgressMsg" class="text-[11px] text-ink-muted leading-relaxed mb-0 whitespace-pre-wrap break-words max-h-48 overflow-y-auto">已提交解析队列</p>
                                        </div>
                                    </div>
                                    <div id="ecFilePreview" class="hidden mb-4"></div>
                                    <div id="ecUploadErrorPanel"
                                         class="hidden mb-4 border border-danger/50 bg-app-deep"
                                         role="alert">
                                        <div class="flex items-start justify-between gap-3 px-3 py-2.5 border-b border-danger/30">
                                            <div class="min-w-0">
                                                <h6 id="ecUploadErrorTitle"
                                                    class="text-[11px] font-semibold text-danger mb-0.5 tracking-wide">导入失败</h6>
                                                <p class="text-[10px] text-ink-muted mb-0">请对照提示修改 Excel 后重新上传，可复制全文</p>
                                            </div>
                                            <div class="flex items-center gap-1 shrink-0">
                                                <button type="button"
                                                        id="ecUploadErrorCopyBtn"
                                                        class="px-2 py-1 text-[10px] text-ink-muted border border-line rounded-sm hover:border-ink-muted hover:text-ink transition-all">
                                                    复制
                                                </button>
                                                <button type="button"
                                                        id="ecUploadErrorCloseBtn"
                                                        class="text-ink-dim hover:text-ink transition-colors p-1"
                                                        aria-label="关闭错误提示">
                                                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"/></svg>
                                                </button>
                                            </div>
                                        </div>
                                        <pre id="ecUploadErrorBody"
                                             class="m-0 px-3 py-3 text-[12px] font-mono leading-relaxed text-danger whitespace-pre-wrap break-words max-h-[360px] overflow-y-auto select-text"></pre>
                                    </div>
                                    <div class="flex items-center justify-end gap-3">
                                        ${uploadResetButtonHtml('ecUploadResetBtn')}
                                        ${uploadSubmitButtonHtml('ecUploadSubmitBtn')}
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
                    <div class="p-4 space-y-3 text-[11px] text-ink-muted leading-relaxed">
                        <p>下载模板即青岛 T28 五种填法样表。整本一次上传，后台解析，本页看进度。</p>
                        <p>工程变更单一行一种改法：完成停止 / 改图 / 增加零件 / 此件不装。同一本可以多行，也可以只有一行。</p>
                        <p>上方基地、项目、生效年月须与 Excel 互校。项目、生效年月必须和工程变更单一致。</p>
                        <p>必须有三张表：工程变更单、车身件材料清单、冲压工艺确认表。不要「零件汇总」。有旧模具布点的，系统按变更单建到新零件号上，简图从工艺确认表抄过去。</p>
                        <p>Excel 只写改了什么。系统会按整份材料清单启用新总成。要看采购件，请筛选这次变更后的版本。</p>
                        <p class="text-warn">改图之后，不要再在投产的材料清单、工艺、布点三页整份覆盖。换零件号只在本页上传。</p>
                    </div>
                </div>
                <div class="bg-app-surface border border-line">
                    <div class="px-4 py-3 border-b border-line-subtle flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <span class="${HUD_LED}"></span>
                            <h5 class="text-[11px] font-bold text-ink-muted mb-0 tracking-widest uppercase">最近上传</h5>
                        </div>
                    </div>
                    <div class="p-4" id="ecRecentUploads">
                        <div class="text-center py-5">
                            <div class="w-8 h-8 bg-app-surface border border-line flex items-center justify-center mx-auto mb-2.5">
                                <svg class="w-4 h-4 text-ink-faint" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
                            </div>
                            <p class="text-[10px] text-ink-faint">暂无上传记录</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}
