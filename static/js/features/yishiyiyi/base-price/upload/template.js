/**
 * Steel Base Price Upload Template
 * 基准价格上传 — 异步进度在拖拽区原位展示
 */

import {
    UPLOAD_DROPZONE,
    UPLOAD_INPUT,
    UPLOAD_LABEL,
} from '../../../../ui/classes.js?v=13';
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
                                        ${window.svgIcon('spinner', 'w-4 h-4 text-brand')}
                                        <h5 id="basePriceProgressTitle" class="text-xs font-medium text-ink truncate mb-0">正在解析基准价格...</h5>
                                    </div>
                                    <span id="basePriceProgressPercent" class="text-xs font-mono tabular-nums text-brand shrink-0">0%</span>
                                </div>
                                <div class="h-1.5 w-full bg-app-deep border border-line overflow-hidden mb-3">
                                    <div id="basePriceProgressBar"
                                         class="h-full bg-brand hud-brand-glow transition-all duration-300"
                                         style="width: 0%"></div>
                                </div>
                                <p id="basePriceProgressMsg" class="text-[11px] text-ink-muted leading-relaxed mb-0 whitespace-pre-wrap break-words max-h-48 overflow-y-auto">已提交解析队列</p>
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
                        <h6 class="${UPLOAD_LABEL} mb-2.5">文件来源</h6>
                        <ul class="list-disc list-inside text-xs text-ink-dim space-y-1.5 mb-4">
                            <li>发布价格及中标钢厂 Excel 文件（如：外协钢板2025年7月订单(2025年8月冲焊件原料)发布价格及中标.xlsx）</li>
                            <li>由奇瑞发布的中标钢厂及到厂原卷承兑价格</li>
                        </ul>
                        <h6 class="${UPLOAD_LABEL} mb-2.5">数据位置</h6>
                        <ul class="list-disc list-inside text-xs text-ink-dim space-y-1.5 mb-4">
                            <li>表头位于第4-5行，数据从第6行开始</li>
                            <li>包含钢种、牌号、参考规格及各基地的中标钢厂和到厂价格</li>
                            <li>各基地价格列之后必须有表头含「加工费」的列，每个牌号填数字（元/吨）</li>
                            <li>没有加工费列，或单元格为空、不是数字时整批拒绝。不会改读旁边的价格，也不会填默认加工费</li>
                            <li>单价加加工费相对上月同一基地、同一规格的涨跌，超出系统设置里的基准价月度价格变动范围（默认 ±300 元/吨）则整批拒绝</li>
                            <li>加工费大于系统设置里的基准价加工费上限则整批拒绝</li>
                        </ul>
                        <h6 class="${UPLOAD_LABEL} mb-2.5">Upsert 规则</h6>
                        <ul class="list-disc list-inside text-xs text-ink-dim space-y-1.5 mb-4">
                            <li>按 (年度, 月份, 基地, 钢厂, 牌号, 厚度, 宽度) 匹配</li>
                            <li>已存在的记录会被覆盖替换</li>
                            <li>支持新增和更新</li>
                        </ul>
                        <h6 class="${UPLOAD_LABEL} mb-2.5">支持的数据</h6>
                        <ul class="list-disc list-inside text-xs text-ink-dim space-y-1.5">
                            <li>只导入基地页已启用的采购基地；宽表其它基地列会跳过</li>
                            <li>中标钢厂及到厂原卷承兑价格</li>
                            <li>价格单位：元/吨，不含税</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    `;
}
