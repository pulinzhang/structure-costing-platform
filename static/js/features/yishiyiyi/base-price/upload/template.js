/**
 * Steel Base Price Upload Template
 * 基准价格上传 — 异步进度在拖拽区原位展示
 */

import {
    UPLOAD_DROPZONE,
    UPLOAD_INPUT,
    UPLOAD_LABEL,
} from '../../../../ui/classes.js?v=14';
import {
    uploadBrowseButtonHtml,
    uploadFileHintHtml,
    uploadResetButtonHtml,
    uploadSubmitButtonHtml,
    uploadTemplateButtonHtml,
} from '../../../../ui/upload-actions.js?v=2';

export function basePriceUploadTemplate() {
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
            <!-- 左栏：表单卡片 -->
            <div class="bg-app-surface border border-line">
                <div class="px-5 py-3 border-b border-line-subtle flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2.5">
                        ${window.svgIcon('file-earmark-excel', 'w-3.5 h-3.5 text-ink-dim')}
                        <h5 class="text-xs font-semibold text-ink-muted mb-0">基准价格导入</h5>
                    </div>
                    ${uploadTemplateButtonHtml('basePriceUploadTemplateBtn')}
                </div>
                <div class="p-5">
                    <form id="basePriceUploadForm">
                        <!-- 生效期间：年度 + 月份（手工录入） -->
                        <div class="grid grid-cols-2 gap-3 mb-5">
                            <div class="space-y-1">
                                <label for="basePriceYear" class="${UPLOAD_LABEL}">
                                    生效年度 <span class="text-brand">*</span>
                                </label>
                                <input type="text"
                                       id="basePriceYear"
                                       name="year"
                                       placeholder="例如：2026"
                                       required
                                       pattern="[0-9]{4}"
                                       class="${UPLOAD_INPUT}">
                            </div>
                            <div class="space-y-1">
                                <label for="basePriceMonth" class="${UPLOAD_LABEL}">
                                    生效月份 <span class="text-brand">*</span>
                                </label>
                                <input type="text"
                                       id="basePriceMonth"
                                       name="month"
                                       placeholder="例如：7"
                                       required
                                       pattern="[0-9]{1,2}"
                                       class="${UPLOAD_INPUT}">
                            </div>
                        </div>

                        <!-- 拖拽上传区 -->
                        <div id="basePriceUploadZone" class="${UPLOAD_DROPZONE} mb-5" data-dropzone-state="idle">
                            <div id="basePriceDropIdle">
                                ${window.svgIcon('upload', 'w-10 h-10 text-ink-dim mx-auto mb-4')}
                                <h5 id="basePriceUploadTitle" class="text-xs font-medium text-ink-muted mb-1.5">拖拽文件到此处上传</h5>
                                ${uploadFileHintHtml('basePriceUploadHint')}
                                <input type="file" id="basePriceFileInput" class="hidden" accept=".xlsx,.xls">
                                ${uploadBrowseButtonHtml('basePriceSelectFileBtn')}
                                <p class="text-[10px] text-ink-dim mt-5 mb-0">支持 .xlsx, .xls（最大 50MB）</p>
                            </div>

                            <div id="basePriceProgressPanel" class="hidden text-left">
                                <div class="flex items-center justify-between gap-3 mb-3">
                                    <div class="flex items-center gap-2 min-w-0">
                                        <span id="basePriceProgressIcon">${window.svgIcon('spinner', 'w-4 h-4 text-brand')}</span>
                                        <h5 id="basePriceProgressTitle" class="text-xs font-medium text-ink truncate mb-0">正在解析基准价格...</h5>
                                    </div>
                                    <span id="basePriceProgressPercent" class="text-xs font-mono tabular-nums text-brand shrink-0">0%</span>
                                </div>
                                <div class="h-1.5 w-full bg-app-deep border border-line overflow-hidden mb-3">
                                    <div id="basePriceProgressBar"
                                         class="h-full bg-brand hud-brand-glow transition-all duration-300"
                                         style="width: 0%"></div>
                                </div>
                                <p id="basePriceProgressMsg" class="text-[11px] text-ink-muted leading-relaxed mb-0 whitespace-pre-wrap break-words max-h-48 overflow-y-auto">正在导入，请稍候</p>
                                <a id="basePriceGradeAction" href="#/steel-grade-category"
                                   class="hidden mt-3 inline-flex items-center gap-1 text-[11px] text-brand-hud hover:text-brand-active">打开牌号分类</a>
                            </div>
                        </div>

                        <!-- 文件预览 -->
                        <div id="basePriceFilePreview" class="hidden mb-5"></div>

                        <!-- 操作按钮行 -->
                        <div class="flex items-center justify-end gap-3">
                            ${uploadResetButtonHtml('basePriceResetButton')}
                            ${uploadSubmitButtonHtml('basePriceSubmitButton')}
                        </div>
                    </form>
                </div>
            </div>

            <!-- 右栏：信息面板 -->
            <div class="space-y-3">
                <!-- 上传说明 -->
                <div class="bg-app-surface border border-line">
                    <div class="px-5 py-3 border-b border-line-subtle flex items-center gap-2.5">
                        <svg class="w-3.5 h-3.5 text-ink-dim" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                        <h5 class="text-xs font-semibold text-ink-dim mb-0">导入说明</h5>
                    </div>
                    <div class="p-5">
                        <h6 class="${UPLOAD_LABEL} mb-2.5">传什么</h6>
                        <ul class="list-disc list-inside text-xs text-ink-dim space-y-1.5 mb-4">
                            <li>钢厂发布的价格表，里面有中标钢厂和到厂原卷价格。</li>
                            <li>价格是元/吨，不含税。</li>
                        </ul>
                        <h6 class="${UPLOAD_LABEL} mb-2.5">表长什么样</h6>
                        <ul class="list-disc list-inside text-xs text-ink-dim space-y-1.5 mb-4">
                            <li>表头在第 4 到第 5 行，数据从第 6 行开始。</li>
                            <li>要有钢种、牌号、参考规格，以及各基地的中标钢厂和到厂价格。</li>
                            <li>每个基地的价格后面，必须有一列标题里带「加工费」。每个牌号都要填数字，单位是元/吨。</li>
                            <li>没有加工费这一列，或者格子是空的、不是数字，这一整份都不收。不会改去读旁边的价格，也不会自动填一个加工费。</li>
                            <li>单价加上加工费，跟上个月同一基地、同一规格比，涨跌超过系统里设的范围（默认上下 300 元/吨），这一整份都不收。</li>
                            <li>加工费超过系统里设的上限，这一整份都不收。</li>
                        </ul>
                        <h6 class="${UPLOAD_LABEL} mb-2.5">再传一份时</h6>
                        <ul class="list-disc list-inside text-xs text-ink-dim space-y-1.5 mb-4">
                            <li>同一年、同一个月、同一个基地、同一家钢厂、同一个牌号、同一厚度和宽度，再传会盖掉原来的。没有的会新增。</li>
                            <li>只导入已经启用的采购基地。表里其它基地的列会跳过。</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    `;
}
