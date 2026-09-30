/**
 * 项目上传 — 基地写在 Excel 列里；同步写入
 */

import { UPLOAD_DROPZONE } from '../../../../ui/classes.js?v=14';
import {
    uploadBrowseButtonHtml,
    uploadFileHintHtml,
    uploadResetButtonHtml,
    uploadSubmitButtonHtml,
    uploadTemplateButtonHtml,
} from '../../../../ui/upload-actions.js?v=2';

export function vehicleModelUploadTemplate() {
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
            <div class="bg-app-hud border border-line-hud">
                <div class="px-5 py-3 border-b border-line-subtle flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2.5">
                        <span class="w-1 h-3.5 bg-brand-hud"></span>
                        <h5 class="text-xs font-semibold text-ink mb-0 tracking-wider">项目补档</h5>
                    </div>
                    ${uploadTemplateButtonHtml('vmUploadTemplateBtn')}
                </div>
                <div class="p-5">
                    <form id="vmUploadForm">
                        <div id="vmUploadZone" class="${UPLOAD_DROPZONE} mb-4" data-dropzone-state="idle">
                            <div id="vmUploadDropIdle" class="flex flex-col items-center gap-0">
                                ${window.svgIcon('upload', 'w-10 h-10 text-ink-dim mx-auto mb-4')}
                                <h5 id="vmUploadTitle" class="text-xs font-medium text-ink-muted mb-1.5">拖入 Excel</h5>
                                ${uploadFileHintHtml('vmUploadHint')}
                                <input type="file" id="vmUploadFileInput" class="hidden" accept=".xlsx,.xls">
                                ${uploadBrowseButtonHtml('vmUploadSelectFileBtn')}
                                <p class="text-[10px] text-ink-faint mt-5 mb-0">.xlsx / .xls · 基地写在模板列</p>
                            </div>
                            <div id="vmUploadProgressPanel" class="hidden text-left w-full">
                                <div class="flex items-center gap-2 min-w-0 mb-3">
                                    <span id="vmUploadProgressIcon">${window.svgIcon('spinner', 'w-4 h-4 text-brand-hud')}</span>
                                    <h5 id="vmUploadProgressTitle" class="text-xs font-medium text-ink truncate mb-0">正在写入…</h5>
                                </div>
                                <div class="h-1.5 w-full bg-app-deep border border-line overflow-hidden mb-3">
                                    <div id="vmUploadProgressBar"
                                         class="h-full bg-brand-hud transition-all duration-300 animate-pulse"
                                         style="width: 60%"></div>
                                </div>
                                <p id="vmUploadProgressMsg" class="text-[11px] text-ink-muted leading-relaxed mb-0 whitespace-pre-wrap break-words max-h-48 overflow-y-auto">解析中</p>
                            </div>
                        </div>
                        <div id="vmUploadFilePreview" class="hidden mb-4"></div>
                        <div class="flex items-center justify-end gap-3">
                            ${uploadResetButtonHtml('vmUploadResetBtn')}
                            ${uploadSubmitButtonHtml('vmUploadSubmitBtn')}
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
                    <div class="p-4 space-y-4">
                        <div>
                            <h6 class="text-[10px] tracking-wider text-ink-faint mb-2">列</h6>
                            <ul class="list-disc list-inside text-xs text-ink-dim space-y-1.5">
                                <li><span class="text-ink-muted">基地</span>：已启用基地名或别名</li>
                                <li><span class="text-ink-muted">项目代号</span>：入库大写</li>
                                <li><span class="text-ink-muted">生效年 / 月</span>：必填</li>
                                <li><span class="text-ink-muted">失效年 / 月</span>：同空或同有</li>
                                <li><span class="text-ink-muted">当前供货台数</span>：空视为 0</li>
                            </ul>
                        </div>
                        <div>
                            <h6 class="text-[10px] tracking-wider text-ink-faint mb-2">规则</h6>
                            <ul class="list-disc list-inside text-xs text-ink-dim space-y-1.5">
                                <li>已有基地+代号则跳过</li>
                                <li>任一行失败整单不写</li>
                                <li>改期 / 台数到项目列表抽屉</li>
                            </ul>
                        </div>
                        <a href="#/vehicle-model-list" class="block text-[11px] text-brand-hud hover:text-brand-active">打开项目列表 →</a>
                    </div>
                </div>
            </div>
        </div>
    `;
}
