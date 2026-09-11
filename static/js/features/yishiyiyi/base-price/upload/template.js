/**
 * Steel Base Price Upload Template
 * 基准价格上传 — 异步进度在拖拽区原位展示
 */

import {
    UPLOAD_DROPZONE,
    UPLOAD_INPUT,
    UPLOAD_LABEL,
} from '../../../../ui-classes.js?v=1';

export function basePriceUploadTemplate() {
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
            <!-- 左栏：表单卡片 -->
            <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
                <div class="px-5 py-3 border-b border-[#222222] flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2.5">
                        ${window.svgIcon('file-earmark-excel', 'w-3.5 h-3.5 text-[#616161]')}
                        <h5 class="text-xs font-semibold text-[#9e9e9e] mb-0">基准价格导入</h5>
                    </div>
                    <button type="button"
                            id="basePriceUploadTemplateBtn"
                            class="inline-flex items-center gap-1.5 bg-transparent text-[#888888] border border-[#2c2c2c] px-3 py-1.5 text-[11px] font-medium rounded-sm hover:border-[#d32f2f] hover:text-[#d32f2f] transition-all duration-150">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                        下载模板
                    </button>
                </div>
                <div class="p-5">
                    <form id="basePriceUploadForm">
                        <!-- 生效期间：年度 + 月份（手工录入） -->
                        <div class="grid grid-cols-2 gap-3 mb-5">
                            <div class="space-y-1">
                                <label for="basePriceYear" class="${UPLOAD_LABEL}">
                                    生效年度 <span class="text-[#d32f2f]">*</span>
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
                                    生效月份 <span class="text-[#d32f2f]">*</span>
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
                                ${window.svgIcon('upload', 'w-10 h-10 text-[#616161] mx-auto mb-4')}
                                <h5 id="basePriceUploadTitle" class="text-xs font-medium text-[#9e9e9e] mb-1.5">拖拽文件到此处上传</h5>
                                <p class="text-[11px] text-[#616161] mb-5">或点击下方按钮选择文件</p>
                                <input type="file" id="basePriceFileInput" class="hidden" accept=".xlsx,.xls">
                                <button type="button"
                                        id="basePriceSelectFileBtn"
                                        class="inline-flex items-center gap-1.5 bg-transparent text-[#505050] border border-[#252525] px-3 py-1.5 text-[11px] font-medium rounded-sm hover:bg-[#d32f2f]/10 hover:border-[#d32f2f]/60 hover:text-[#d32f2f] hover:shadow-[0_0_8px_rgba(211,47,47,0.15)] transition-all duration-200"
                                        style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);">
                                    ${window.svgIcon('folder', 'w-3.5 h-3.5')}
                                    选择文件
                                </button>
                                <p class="text-[10px] text-[#616161] mt-5 mb-0">支持 .xlsx, .xls（最大 50MB）</p>
                            </div>

                            <div id="basePriceProgressPanel" class="hidden text-left">
                                <div class="flex items-center justify-between gap-3 mb-3">
                                    <div class="flex items-center gap-2 min-w-0">
                                        ${window.svgIcon('spinner', 'w-4 h-4 text-[#d32f2f]')}
                                        <h5 id="basePriceProgressTitle" class="text-xs font-medium text-[#ffffff] truncate mb-0">正在解析基准价格...</h5>
                                    </div>
                                    <span id="basePriceProgressPercent" class="text-xs font-mono tabular-nums text-[#d32f2f] shrink-0">0%</span>
                                </div>
                                <div class="h-1.5 w-full bg-[#0a0a0a] border border-[#2c2c2c] overflow-hidden mb-3">
                                    <div id="basePriceProgressBar"
                                         class="h-full bg-[#d32f2f] shadow-[0_0_8px_rgba(211,47,47,0.5)] transition-all duration-300"
                                         style="width: 0%"></div>
                                </div>
                                <p id="basePriceProgressMsg" class="text-[11px] text-[#9e9e9e] leading-relaxed mb-0 whitespace-pre-wrap break-words max-h-48 overflow-y-auto">已提交解析队列</p>
                                <a id="basePriceGradeAction" href="#/steel-grade-category"
                                   class="hidden mt-3 inline-flex items-center gap-1 text-[11px] text-[#FF1E27] hover:text-[#ff5252]">打开牌号分类</a>
                            </div>
                        </div>

                        <!-- 文件预览 -->
                        <div id="basePriceFilePreview" class="hidden mb-5"></div>

                        <!-- 操作按钮行 -->
                        <div class="flex items-center justify-end gap-3">
                            <button type="button"
                                    id="basePriceResetButton"
                                    onclick="window.resetBasePriceUploadForm()"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#505050] border border-[#252525] px-3 py-1.5 text-[11px] font-medium rounded-sm hover:bg-[#d32f2f]/10 hover:border-[#d32f2f]/60 hover:text-[#d32f2f] hover:shadow-[0_0_8px_rgba(211,47,47,0.15)] transition-all duration-200"
                                    style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);">
                                ${window.svgIcon('refresh', 'w-3.5 h-3.5')}
                                重置
                            </button>
                            <button type="submit"
                                    id="basePriceSubmitButton"
                                    disabled
                                    class="inline-flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-semibold rounded-sm text-[#c8c8c8] border border-[#8a2020] transition-all duration-200 hover:text-white disabled:opacity-30 disabled:pointer-events-none"
                                    style="background: linear-gradient(180deg, #3d1515 0%, #2d0f0f 100%); border-color: #6b1a1a; box-shadow: 0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(211,47,47,0.1), 0 0 12px rgba(198,40,40,0.08);">
                                ${window.svgIcon('upload', 'w-3.5 h-3.5')}
                                导入基准价格
                            </button>
                        </div>
                    </form>
                </div>
            </div>

            <!-- 右栏：信息面板 -->
            <div class="space-y-3">
                <!-- 上传说明 -->
                <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
                    <div class="px-5 py-3 border-b border-[#222222] flex items-center gap-2.5">
                        <svg class="w-3.5 h-3.5 text-[#616161]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                        <h5 class="text-xs font-semibold text-[#616161] mb-0">导入说明</h5>
                    </div>
                    <div class="p-5">
                        <h6 class="${UPLOAD_LABEL} mb-2.5">文件来源</h6>
                        <ul class="list-disc list-inside text-xs text-[#616161] space-y-1.5 mb-4">
                            <li>发布价格及中标钢厂 Excel 文件（如：外协钢板2025年7月订单(2025年8月冲焊件原料)发布价格及中标.xlsx）</li>
                            <li>由奇瑞发布的中标钢厂及到厂原卷承兑价格</li>
                        </ul>
                        <h6 class="${UPLOAD_LABEL} mb-2.5">数据位置</h6>
                        <ul class="list-disc list-inside text-xs text-[#616161] space-y-1.5 mb-4">
                            <li>表头位于第4-5行，数据从第6行开始</li>
                            <li>包含钢种、牌号、参考规格及各基地的中标钢厂和到厂价格</li>
                            <li>具体列位置由后端解析器自动识别</li>
                        </ul>
                        <h6 class="${UPLOAD_LABEL} mb-2.5">Upsert 规则</h6>
                        <ul class="list-disc list-inside text-xs text-[#616161] space-y-1.5 mb-4">
                            <li>按 (年度, 月份, 基地, 钢厂, 牌号, 厚度, 宽度) 匹配</li>
                            <li>已存在的记录会被覆盖替换</li>
                            <li>支持新增和更新</li>
                        </ul>
                        <h6 class="${UPLOAD_LABEL} mb-2.5">支持的数据</h6>
                        <ul class="list-disc list-inside text-xs text-[#616161] space-y-1.5">
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
