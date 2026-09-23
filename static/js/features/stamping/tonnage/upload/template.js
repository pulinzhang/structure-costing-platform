/**
 * 冲次单价上传 — 模板
 * 基地 + 年度必选；三列 Excel（名称 / 单位 / 单价）；同步导入
 */

import { UPLOAD_DROPZONE, UPLOAD_INPUT, UPLOAD_LABEL, HUD_LED } from '../../../../ui/classes.js?v=13';
import {
    uploadBrowseButtonHtml,
    uploadFileHintHtml,
    uploadResetButtonHtml,
    uploadSubmitButtonHtml,
    uploadTemplateButtonHtml,
} from '../../../../ui/upload-actions.js?v=2';

export function tonnageUploadTemplate() {
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
            <div class="bg-app-surface border border-line">
                <div class="px-5 py-3 border-b border-line-subtle flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2.5">
                        ${window.svgIcon('file-earmark-excel', 'w-3.5 h-3.5 text-ink-dim')}
                        <h5 class="text-xs font-semibold text-ink-muted mb-0">冲次单价导入</h5>
                    </div>
                    ${uploadTemplateButtonHtml('tonnageUploadTemplateBtn')}
                </div>
                <div class="p-5">
                    <form id="tonnageUploadForm">
                        <div class="bg-app-surface border border-line p-4">
                            <div class="mb-5">
                                <div class="flex items-center gap-2 mb-2.5">
                                    <span class="w-4 h-4 rounded-full bg-app-elevated flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-brand">1</span>
                                    </span>
                                    <span class="text-[13px] text-ink-dim font-medium tracking-wide uppercase">选择基地与年度</span>
                                </div>
                                <div class="ml-6 grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <div>
                                        <label for="tonnageUploadLocation" class="${UPLOAD_LABEL}">
                                            采购基地 <span class="text-brand">*</span>
                                        </label>
                                        <select id="tonnageUploadLocation"
                                                name="location"
                                                required
                                                class="${UPLOAD_INPUT} hud-filter w-full">
                                            <option value="">请选择采购基地</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label for="tonnageUploadYear" class="${UPLOAD_LABEL}">
                                            年度 <span class="text-brand">*</span>
                                        </label>
                                        <input type="text"
                                               id="tonnageUploadYear"
                                               name="year"
                                               placeholder="例如：2026"
                                               required
                                               pattern="[0-9]{4}"
                                               maxlength="4"
                                               class="${UPLOAD_INPUT} w-full">
                                    </div>
                                </div>
                                <p class="ml-6 mt-1.5 text-[11px] text-ink-dim">导入时必须指定基地与年度，写入该基地该年的冲次单价</p>
                            </div>

                            <div class="h-px bg-app-surface mx-6 mb-4"></div>

                            <div>
                                <div class="flex items-center gap-2 mb-3">
                                    <span class="w-4 h-4 rounded-full bg-app-elevated flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-brand">2</span>
                                    </span>
                                    <span class="text-[13px] text-ink-dim font-medium tracking-wide uppercase">上传冲次单价表</span>
                                </div>
                                <div class="ml-6">
                                    <div id="tonnageUploadZone" class="${UPLOAD_DROPZONE} mb-4" data-dropzone-state="idle">
                                        <div id="tonnageUploadDropIdle" class="flex flex-col items-center gap-0">
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
                                            <h5 id="tonnageUploadTitle" class="text-[11px] text-ink-dim font-semibold tracking-widest uppercase mb-1">拖拽文件到此处</h5>
                                            ${uploadFileHintHtml('tonnageUploadHint')}
                                            <div class="flex items-center gap-3 mt-1 w-full px-3">
                                                <div class="h-px flex-1 bg-app-elevated"></div>
                                                <div class="w-1.5 h-1.5 border border-line rotate-45"></div>
                                                <div class="h-px flex-1 bg-app-elevated"></div>
                                            </div>
                                            <input type="file" id="tonnageUploadFileInput" class="hidden" accept=".xlsx">
                                            ${uploadBrowseButtonHtml('tonnageUploadSelectFileBtn')}
                                            <p class="text-[10px] text-ink-faint mt-4 mb-0">
                                                仅 .xlsx
                                                <span class="mx-2 text-ink-faint">|</span>
                                                同步导入
                                            </p>
                                        </div>

                                        <div id="tonnageUploadProgressPanel" class="hidden text-left w-full">
                                            <div class="flex items-center gap-2 min-w-0 mb-3">
                                                <span id="tonnageUploadProgressIcon">${window.svgIcon('spinner', 'w-4 h-4 text-brand')}</span>
                                                <h5 id="tonnageUploadProgressTitle" class="text-xs font-medium text-ink truncate mb-0">正在导入冲次单价...</h5>
                                            </div>
                                            <div class="h-1.5 w-full bg-app-deep border border-line overflow-hidden mb-3">
                                                <div id="tonnageUploadProgressBar"
                                                     class="h-full bg-brand hud-brand-glow transition-all duration-300 animate-pulse"
                                                     style="width: 60%"></div>
                                            </div>
                                            <p id="tonnageUploadProgressMsg" class="text-[11px] text-ink-muted leading-relaxed mb-0 whitespace-pre-wrap break-words max-h-48 overflow-y-auto">解析并写入数据库，请稍候</p>
                                        </div>
                                    </div>

                                    <div id="tonnageUploadFilePreview" class="hidden mb-4"></div>

                                    <div class="flex items-center justify-end gap-3">
                                        ${uploadResetButtonHtml('tonnageUploadResetBtn')}
                                        ${uploadSubmitButtonHtml('tonnageUploadSubmitBtn')}
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
                        <span class="text-[10px] text-ink-dim tracking-wider">SPEC</span>
                    </div>
                    <div class="p-4 space-y-4">
                        <div>
                            <h6 class="text-[10px] uppercase tracking-wider text-ink-dim mb-2">固定三列</h6>
                            <ul class="list-disc list-inside text-xs text-ink-dim space-y-1.5">
                                <li><span class="text-ink-muted">名称</span>：吨位，如 400T</li>
                                <li><span class="text-ink-muted">单位</span>：固定为「次」</li>
                                <li><span class="text-ink-muted">单价</span>：元/次，固定保留三位小数</li>
                            </ul>
                        </div>
                        <div>
                            <h6 class="text-[10px] uppercase tracking-wider text-ink-dim mb-2">示例</h6>
                            <div class="overflow-hidden border border-line">
                                <table class="w-full">
                                    <thead>
                                        <tr class="bg-app-deep border-b border-line">
                                            <th class="px-2 py-1.5 text-left text-[10px] font-semibold text-ink-dim">名称</th>
                                            <th class="px-2 py-1.5 text-left text-[10px] font-semibold text-ink-dim">单位</th>
                                            <th class="px-2 py-1.5 text-right text-[10px] font-semibold text-ink-dim">单价</th>
                                        </tr>
                                    </thead>
                                    <tbody class="divide-y divide-line-subtle">
                                        <tr><td class="px-2 py-1.5 text-[11px] text-ink-muted">400T</td><td class="px-2 py-1.5 text-[11px] text-ink-muted">次</td><td class="px-2 py-1.5 text-[11px] text-right font-mono tabular-nums text-ink-muted">0.564</td></tr>
                                        <tr><td class="px-2 py-1.5 text-[11px] text-ink-muted">500T</td><td class="px-2 py-1.5 text-[11px] text-ink-muted">次</td><td class="px-2 py-1.5 text-[11px] text-right font-mono tabular-nums text-ink-muted">0.622</td></tr>
                                        <tr><td class="px-2 py-1.5 text-[11px] text-ink-muted">630T</td><td class="px-2 py-1.5 text-[11px] text-ink-muted">次</td><td class="px-2 py-1.5 text-[11px] text-right font-mono tabular-nums text-ink-muted">0.713</td></tr>
                                        <tr><td class="px-2 py-1.5 text-[11px] text-ink-muted">800T</td><td class="px-2 py-1.5 text-[11px] text-ink-muted">次</td><td class="px-2 py-1.5 text-[11px] text-right font-mono tabular-nums text-ink-muted">1.026</td></tr>
                                        <tr><td class="px-2 py-1.5 text-[11px] text-ink-muted">1000T</td><td class="px-2 py-1.5 text-[11px] text-ink-muted">次</td><td class="px-2 py-1.5 text-[11px] text-right font-mono tabular-nums text-ink-muted">1.283</td></tr>
                                        <tr><td class="px-2 py-1.5 text-[11px] text-ink-muted">1200T</td><td class="px-2 py-1.5 text-[11px] text-ink-muted">次</td><td class="px-2 py-1.5 text-[11px] text-right font-mono tabular-nums text-ink-muted">1.539</td></tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        <div>
                            <h6 class="text-[10px] uppercase tracking-wider text-ink-dim mb-2">写入规则</h6>
                            <ul class="list-disc list-inside text-xs text-ink-dim space-y-1.5">
                                <li>唯一键：基地 + 年度 + 吨位</li>
                                <li>已存在则更新单价，不存在则新增</li>
                                <li>列表导出含基地/年份/审核列；导入只读名称/单位/单价（基地/年度以本页选择为准）</li>
                                <li>仅支持 .xlsx，同步导入无需等待队列</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}
