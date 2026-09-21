/**
 * 冲压检具费上传 — 基地+项目必选，模板从模具布点带出零件
 */

import { BTN_FILE_SELECT, BTN_GHOST, BTN_UPLOAD_SUBMIT, UPLOAD_DROPZONE, UPLOAD_INPUT, HUD_LED } from '../../../../ui/classes.js?v=12';

export function gaugeFeeUploadTemplate() {
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
            <div class="bg-app-surface border border-line">
                <div class="px-5 py-3 border-b border-line-subtle flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2.5">
                        ${window.svgIcon('file-earmark-excel', 'w-3.5 h-3.5 text-ink-dim')}
                        <h5 class="text-xs font-semibold text-ink-muted mb-0">上传冲压检具费</h5>
                    </div>
                    <button type="button" id="gfuTemplateBtn"
                            class="inline-flex items-center gap-1.5 bg-transparent text-ink-muted border border-line px-3 py-1.5 text-[11px] font-medium rounded-sm hover:border-brand hover:text-brand transition-all duration-150">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                        下载模板
                    </button>
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
                                    <select id="gfuLocation" name="location" required class="${UPLOAD_INPUT} hud-filter w-[280px]">
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
                                    <select id="gfuVehicle" name="vehicle_model" required class="${UPLOAD_INPUT} hud-filter w-[280px]">
                                        <option value="">请先选择基地</option>
                                    </select>
                                    <p class="mt-2 text-[10px] text-ink-faint">选项与模具布点相同。须先选基地和项目才能下载模板；模板零件来自已入库模具布点。</p>
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
                                            <p id="gfuHint" class="text-[10px] text-ink-faint mb-6">或点击下方按钮选择文件</p>
                                            <input type="file" id="gfuFileInput" class="hidden" accept=".xlsx">
                                            <button type="button" id="gfuSelectFileBtn" class="${BTN_FILE_SELECT}">
                                                ${window.svgIcon('folder', 'w-3.5 h-3.5')}
                                                浏览文件
                                            </button>
                                            <p class="text-[10px] text-ink-faint mt-4 mb-0">仅 .xlsx · 同步导入</p>
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
                                            <p id="gfuProgressMsg" class="text-[11px] text-ink-muted leading-relaxed mb-0 whitespace-pre-wrap break-words max-h-48 overflow-y-auto">解析并写入数据库，请稍候</p>
                                        </div>
                                    </div>
                                    <div id="gfuFilePreview" class="hidden mb-4"></div>
                                    <div class="flex items-center justify-end gap-3">
                                        <button type="button" id="gfuResetBtn" class="${BTN_GHOST}">重置</button>
                                        <button type="submit" id="gfuSubmitBtn" disabled class="${BTN_UPLOAD_SUBMIT}">上传</button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </form>
                </div>
            </div>
            <div class="bg-app-surface border border-line">
                <div class="px-4 py-3 border-b border-line-subtle flex items-center gap-2">
                    <span class="${HUD_LED}"></span>
                    <h5 class="text-[11px] font-bold text-ink-muted mb-0 tracking-widest uppercase">说明</h5>
                </div>
                <div class="p-4 space-y-3 text-[11px] text-ink-muted leading-relaxed">
                    <p class="text-warn">模板零件来自该基地+项目的模具布点。没有模具布点则无需维护检具费，请先上传模具布点。</p>
                    <p>检具费（万元）、项目分摊数量（万台）必填，不能为空或负数。模板预填 0.8 万 / 10 万台 / 生效。</p>
                    <p>上传按基地+项目整包覆盖，不算年度分摊，不进成品 I7。</p>
                    <p>Excel 中的零件号必须属于该范围模具布点，否则整单拒绝。</p>
                </div>
            </div>
        </div>
    `;
}
