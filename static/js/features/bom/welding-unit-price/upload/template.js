/**
 * 焊接单价上传 — 模板
 * 基地 + 年度必选；四列 Excel（名称 / 单位 / 费用 / 备注）；同步导入
 */

import { BTN_FILE_SELECT, BTN_GHOST, BTN_UPLOAD_SUBMIT, UPLOAD_DROPZONE, UPLOAD_INPUT, UPLOAD_LABEL, HUD_LED } from '../../../../ui/classes.js?v=8';

export function weldingUnitPriceUploadTemplate() {
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
            <div class="bg-app-surface border border-line">
                <div class="px-5 py-3 border-b border-line-subtle flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2.5">
                        ${window.svgIcon('file-earmark-excel', 'w-3.5 h-3.5 text-ink-dim')}
                        <h5 class="text-xs font-semibold text-ink-muted mb-0">焊接单价导入</h5>
                    </div>
                    <button type="button"
                            id="weldingUnitPriceUploadTemplateBtn"
                            class="inline-flex items-center gap-1.5 bg-transparent text-ink-muted border border-line px-3 py-1.5 text-[11px] font-medium rounded-sm hover:border-brand hover:text-brand transition-all duration-150">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                        下载模板
                    </button>
                </div>
                <div class="p-5">
                    <form id="weldingUnitPriceUploadForm">
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
                                        <label for="weldingUnitPriceUploadLocation" class="${UPLOAD_LABEL}">
                                            采购基地 <span class="text-brand">*</span>
                                        </label>
                                        <select id="weldingUnitPriceUploadLocation"
                                                name="location"
                                                required
                                                class="${UPLOAD_INPUT} w-full">
                                            <option value="">请选择采购基地</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label for="weldingUnitPriceUploadYear" class="${UPLOAD_LABEL}">
                                            年度 <span class="text-brand">*</span>
                                        </label>
                                        <input type="text"
                                               id="weldingUnitPriceUploadYear"
                                               name="year"
                                               placeholder="例如：2026"
                                               required
                                               pattern="[0-9]{4}"
                                               maxlength="4"
                                               class="${UPLOAD_INPUT} w-full">
                                    </div>
                                </div>
                                <p class="ml-6 mt-1.5 text-[11px] text-ink-dim">导入时必须指定基地与年度，写入该基地该年的焊接单价</p>
                            </div>

                            <div class="h-px bg-app-surface mx-6 mb-4"></div>

                            <div>
                                <div class="flex items-center gap-2 mb-3">
                                    <span class="w-4 h-4 rounded-full bg-app-elevated flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-brand">2</span>
                                    </span>
                                    <span class="text-[13px] text-ink-dim font-medium tracking-wide uppercase">上传焊接单价表</span>
                                </div>
                                <div class="ml-6">
                                    <div id="weldingUnitPriceUploadZone" class="${UPLOAD_DROPZONE} mb-4" data-dropzone-state="idle">
                                        <div id="weldingUnitPriceUploadDropIdle" class="flex flex-col items-center gap-0">
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
                                            <h5 id="weldingUnitPriceUploadTitle" class="text-[11px] text-ink-dim font-semibold tracking-widest uppercase mb-1">拖拽文件到此处</h5>
                                            <p id="weldingUnitPriceUploadHint" class="text-[10px] text-ink-faint mb-6">或点击下方按钮选择文件</p>
                                            <div class="flex items-center gap-3 mt-1 w-full px-3">
                                                <div class="h-px flex-1 bg-app-elevated"></div>
                                                <div class="w-1.5 h-1.5 border border-line rotate-45"></div>
                                                <div class="h-px flex-1 bg-app-elevated"></div>
                                            </div>
                                            <input type="file" id="weldingUnitPriceUploadFileInput" class="hidden" accept=".xlsx">
                                            <button type="button"
                                                    id="weldingUnitPriceUploadSelectFileBtn"
                                                    class="${BTN_FILE_SELECT}">
                                                ${window.svgIcon('folder', 'w-3.5 h-3.5')}
                                                浏览文件
                                            </button>
                                            <p class="text-[10px] text-ink-faint mt-4 mb-0">
                                                仅 .xlsx
                                                <span class="mx-2 text-ink-faint">|</span>
                                                同步导入
                                            </p>
                                        </div>

                                        <div id="weldingUnitPriceUploadProgressPanel" class="hidden text-left w-full">
                                            <div class="flex items-center gap-2 min-w-0 mb-3">
                                                <span id="weldingUnitPriceUploadProgressIcon">${window.svgIcon('spinner', 'w-4 h-4 text-brand')}</span>
                                                <h5 id="weldingUnitPriceUploadProgressTitle" class="text-xs font-medium text-ink truncate mb-0">正在导入焊接单价...</h5>
                                            </div>
                                            <div class="h-1.5 w-full bg-app-deep border border-line overflow-hidden mb-3">
                                                <div id="weldingUnitPriceUploadProgressBar"
                                                     class="h-full bg-brand shadow-[0_0_8px_rgb(var(--brabus-red)/0.5)] transition-all duration-300 animate-pulse"
                                                     style="width: 60%"></div>
                                            </div>
                                            <p id="weldingUnitPriceUploadProgressMsg" class="text-[11px] text-ink-muted leading-relaxed mb-0 whitespace-pre-wrap break-words max-h-48 overflow-y-auto">解析并写入数据库，请稍候</p>
                                        </div>
                                    </div>

                                    <div id="weldingUnitPriceUploadFilePreview" class="hidden mb-4"></div>

                                    <div id="weldingUnitPriceUploadResult"
                                         class="hidden mb-4 border border-line bg-app-main"
                                         role="status"
                                         aria-live="polite">
                                        <div class="flex items-start justify-between gap-3 px-3 py-2.5 border-b border-line-subtle">
                                            <div class="flex items-center gap-2 min-w-0">
                                                <span id="weldingUnitPriceUploadResultAccent"
                                                      class="${HUD_LED}"></span>
                                                <h6 id="weldingUnitPriceUploadResultTitle"
                                                    class="text-[11px] font-semibold text-ink-muted mb-0 tracking-wide">导入结果</h6>
                                            </div>
                                            <button type="button"
                                                    id="weldingUnitPriceUploadResultCloseBtn"
                                                    class="text-ink-dim hover:text-ink transition-colors shrink-0"
                                                    aria-label="关闭结果">
                                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"/></svg>
                                            </button>
                                        </div>
                                        <div id="weldingUnitPriceUploadResultBody"
                                             class="px-3 py-3 text-[12px] text-ink-muted leading-relaxed whitespace-pre-wrap break-words max-h-[240px] overflow-y-auto"></div>
                                    </div>

                                    <div class="flex items-center justify-end gap-3">
                                        <button type="button"
                                                id="weldingUnitPriceUploadResetBtn"
                                                class="${BTN_GHOST}">
                                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
                                            重置
                                        </button>
                                        <button type="submit"
                                                id="weldingUnitPriceUploadSubmitBtn"
                                                disabled
                                                class="${BTN_UPLOAD_SUBMIT}">
                                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                                            上传
                                        </button>
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
                            <span class="hud-led"></span>
                            <h5 class="text-[11px] font-bold text-ink-muted mb-0 tracking-widest uppercase">格式说明</h5>
                        </div>
                        <span class="text-[10px] text-ink-dim tracking-wider">SPEC</span>
                    </div>
                    <div class="p-4 space-y-4">
                        <div>
                            <h6 class="text-[10px] uppercase tracking-wider text-ink-dim mb-2">固定四列</h6>
                            <ul class="list-disc list-inside text-xs text-ink-dim space-y-1.5">
                                <li><span class="text-ink-muted">名称</span>：须与下方标准工艺目录<span class="font-semibold text-ink-muted">完全一致</span></li>
                                <li><span class="text-ink-muted">单位</span>：须与目录单位一致（个 / CM / MM / 平方）</li>
                                <li><span class="text-ink-muted">费用</span>：工费单价（元），固定保留四位小数</li>
                                <li><span class="text-ink-muted">备注</span>：可选</li>
                            </ul>
                        </div>
                        <div>
                            <div class="flex items-center justify-between gap-2 mb-2">
                                <h6 class="text-[10px] uppercase tracking-wider text-ink-dim mb-0">标准工艺目录</h6>
                                <span id="weldingUnitPriceCatalogCount" class="text-[10px] font-mono text-ink-faint">—</span>
                            </div>
                            <p class="text-[10px] text-ink-dim mb-2 leading-relaxed">
                                名称写错一字（如「拆边」）导入会整批中止；模板另含同名工作表。
                            </p>
                            <div class="overflow-hidden border border-line max-h-[320px] overflow-y-auto">
                                <table class="w-full">
                                    <thead class="sticky top-0">
                                        <tr class="bg-app-deep border-b border-line">
                                            <th class="px-2 py-1.5 text-left text-[10px] font-semibold text-ink-dim">名称</th>
                                            <th class="px-2 py-1.5 text-left text-[10px] font-semibold text-ink-dim">单位</th>
                                        </tr>
                                    </thead>
                                    <tbody id="weldingUnitPriceCatalogBody" class="divide-y divide-line-subtle">
                                        <tr>
                                            <td colspan="2" class="px-2 py-3 text-[11px] text-ink-faint text-center">加载标准目录…</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        <div>
                            <h6 class="text-[10px] uppercase tracking-wider text-ink-dim mb-2">写入规则</h6>
                            <ul class="list-disc list-inside text-xs text-ink-dim space-y-1.5">
                                <li>唯一键：基地 + 年度 + 名称</li>
                                <li>已存在则更新费用/单位/备注，不存在则新增</li>
                                <li>列表导出含基地/年份/审核列；导入只读名称/单位/费用/备注（基地/年度以本页选择为准）</li>
                                <li>非目录名称 / 单位不匹配 → 整批中止</li>
                                <li>仅支持 .xlsx，同步导入无需等待队列</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}
