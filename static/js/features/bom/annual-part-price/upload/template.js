/**
 * 年度零件价上传 — 模板
 * 下载模板：基地 + 项目 + 年度；导入仍按基地 + 年度写入价表
 */

import { UPLOAD_DROPZONE, UPLOAD_INPUT, UPLOAD_LABEL, HUD_LED } from '../../../../ui/classes.js?v=14';
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
                                <p class="ml-6 mt-1.5 text-[11px] text-ink-dim">下载模板须选基地、项目、年度。第二页「填写说明」：1 采购单位 = N 核价单位，N 可小数（如 25.4），核价单价=采购单价÷N。导入仍写入该基地该年，不必删说明页。</p>
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
                                                仅 .xlsx
                                                <span class="mx-2 text-ink-faint">|</span>
                                                同步导入
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
                                            <p id="annualPartPriceUploadProgressMsg" class="text-[11px] text-ink-muted leading-relaxed mb-0 whitespace-pre-wrap break-words max-h-48 overflow-y-auto">解析并写入数据库，请稍候</p>
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
                        <span class="text-[10px] text-ink-dim tracking-wider">SPEC</span>
                    </div>
                    <div class="p-4 space-y-4">
                        <div>
                            <h6 class="text-[10px] uppercase tracking-wider text-ink-dim mb-2">Excel 列</h6>
                            <ul class="list-disc list-inside text-xs text-ink-dim space-y-1.5">
                                <li><span class="text-ink-muted">零件号</span>：必填；模板按所选项目带出外购叶子（含未进工艺库的板料、L2 标准件）</li>
                                <li><span class="text-ink-muted">零件名称</span> / <span class="text-ink-muted">规格</span> / <span class="text-ink-muted">供应商</span> / <span class="text-ink-muted">备注</span>：可选；规格不参与取价</li>
                                <li><span class="text-ink-muted">单位 / 单价</span>：核价口径；单位抄 BOM；单价模板预填 0</li>
                                <li><span class="text-ink-muted">采购单位</span>：模板与单位相同；<span class="text-ink-muted">采购单价</span>留空；<span class="text-ink-muted">转换系数</span>默认 1</li>
                                <li><span class="text-ink-muted">换算</span>：1 采购单位 = N 核价单位。N 默认 1，可小数（1 英寸=25.4 mm 填 25.4；1 打=12 填 12）。核价单价 = 采购单价 ÷ N。不要填 1/12</li>
                                <li><span class="text-ink-muted">原供货类型</span>：模板按行预填「标准件」/「胶块」/「沿用」；导入可改</li>
                            </ul>
                        </div>
                        <div>
                            <h6 class="text-[10px] uppercase tracking-wider text-ink-dim mb-2">写入规则</h6>
                            <ul class="list-disc list-inside text-xs text-ink-dim space-y-1.5">
                                <li>下载模板须先选基地、项目、年度，且该基地该项目已有材料清单</li>
                                <li>同一条按基地、年度、零件号区分。一样的就更新，没有的就新增。只接受 .xlsx</li>
                                <li>列表导出含基地/年份/审核列；导入只读模板同列（基地/年度以本页选择为准）</li>
                                <li>已审核记录导入不会覆盖，所以会出现「更新 0 条」；改价须先在列表反审核</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}
