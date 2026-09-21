/**
 * Policy Upload Template
 * 政策导入页面 — 异步上传 + 任务进度轮询
 * - 双栏布局：左侧表单 + 右侧信息面板
 * - 拖拽区原位显示解析进度条与日志
 */

import {
    BTN_FILE_SELECT,
    BTN_GHOST,
    BTN_UPLOAD_SUBMIT,
    UPLOAD_DROPZONE,
    UPLOAD_INPUT,
    UPLOAD_LABEL,
} from '../../../../ui/classes.js?v=11';

export function policyUploadTemplate() {
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
            <!-- ===== 左栏：表单卡片 ===== -->
            <div class="bg-app-surface border border-line">
                <div class="px-5 py-3 border-b border-line-subtle flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2.5">
                        ${window.svgIcon('file-earmark-excel', 'w-3.5 h-3.5 text-ink-dim')}
                        <h5 class="text-xs font-semibold text-ink-muted mb-0">厚度、宽度、锌层加减价导入</h5>
                    </div>
                    <button type="button"
                            id="policyUploadTemplateBtn"
                            class="inline-flex items-center gap-1.5 bg-transparent text-ink-muted border border-line px-3 py-1.5 text-[11px] font-medium rounded-sm hover:border-brand hover:text-brand transition-all duration-150">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                        下载模板
                    </button>
                </div>
                <div class="p-5">
                    <form id="policyUploadForm">
                        <!-- 生效期间：年度 + 月份（手工录入） -->
                        <div class="grid grid-cols-2 gap-3 mb-5">
                            <div class="space-y-1">
                                <label for="policyYear" class="${UPLOAD_LABEL}">
                                    生效年度 <span class="text-brand">*</span>
                                </label>
                                <input type="text"
                                       id="policyYear"
                                       name="year"
                                       placeholder="例如：2026"
                                       required
                                       pattern="[0-9]{4}"
                                       class="${UPLOAD_INPUT}">
                            </div>
                            <div class="space-y-1">
                                <label for="policyMonth" class="${UPLOAD_LABEL}">
                                    生效月份 <span class="text-brand">*</span>
                                </label>
                                <input type="text"
                                       id="policyMonth"
                                       name="month"
                                       placeholder="例如：7"
                                       required
                                       pattern="[0-9]{1,2}"
                                       class="${UPLOAD_INPUT}">
                            </div>
                        </div>

                        <!-- 拖拽上传区（解析中切换为进度面板） -->
                        <div id="policyUploadZone" class="${UPLOAD_DROPZONE} mb-5" data-dropzone-state="idle">
                            <div id="policyDropIdle">
                                ${window.svgIcon('upload', 'w-10 h-10 text-ink-dim mx-auto mb-4')}
                                <h5 id="policyUploadTitle" class="text-xs font-medium text-ink-muted mb-1.5">拖拽文件到此处上传</h5>
                                <p class="text-[11px] text-ink-dim mb-5">或点击下方按钮选择文件</p>
                                <input type="file" id="policyFileInput" class="hidden" accept=".xlsx,.xls,.xlsm">
                                <button type="button"
                                        id="policySelectFileBtn"
                                        class="${BTN_FILE_SELECT}">
                                    ${window.svgIcon('folder', 'w-3.5 h-3.5')}
                                    选择文件
                                </button>
                                <p class="text-[10px] text-ink-dim mt-5 mb-0">支持 .xlsx, .xls, .xlsm（最大 50MB）</p>
                            </div>

                            <!-- 解析进度（运行中显示在拖拽区原位置） -->
                            <div id="policyProgressPanel" class="hidden text-left">
                                <div class="flex items-center justify-between gap-3 mb-3">
                                    <div class="flex items-center gap-2 min-w-0">
                                        ${window.svgIcon('spinner', 'w-4 h-4 text-brand')}
                                        <h5 id="policyProgressTitle" class="text-xs font-medium text-ink truncate mb-0">正在解析政策文件...</h5>
                                    </div>
                                    <span id="policyProgressPercent" class="text-xs font-mono tabular-nums text-brand shrink-0">0%</span>
                                </div>
                                <div class="h-1.5 w-full bg-app-deep border border-line overflow-hidden mb-3">
                                    <div id="policyProgressBar"
                                         class="h-full bg-brand hud-brand-glow transition-all duration-300"
                                         style="width: 0%"></div>
                                </div>
                                <p id="policyProgressMsg" class="text-[11px] text-ink-muted leading-relaxed mb-0 whitespace-pre-wrap break-words max-h-48 overflow-y-auto">已提交解析队列</p>
                            </div>
                        </div>

                        <!-- 文件预览 -->
                        <div id="policyFilePreview" class="hidden mb-5"></div>

                        <!-- 操作按钮行 -->
                        <div class="flex items-center justify-end gap-3">
                            <button type="button"
                                    id="policyResetButton"
                                    class="${BTN_GHOST}">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
                                重置
                            </button>
                            <button type="submit"
                                    id="policySubmitButton"
                                    disabled
                                    class="${BTN_UPLOAD_SUBMIT}">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                                导入政策
                            </button>
                        </div>
                    </form>
                </div>
            </div>

            <!-- ===== 右栏：信息面板 ===== -->
            <div class="space-y-3">
                <!-- 上传说明 -->
                <div class="bg-app-surface border border-line">
                    <div class="px-5 py-3 border-b border-line-subtle flex items-center gap-2.5">
                        <svg class="w-3.5 h-3.5 text-ink-dim" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                        <h5 class="text-xs font-semibold text-ink-dim mb-0">导入说明</h5>
                    </div>
                    <div class="p-5">
                        <h6 class="${UPLOAD_LABEL} mb-2.5">Excel 文件格式要求</h6>
                        <ul class="list-disc list-inside text-xs text-ink-dim space-y-1.5 mb-4">
                            <li>文件应包含钢价政策相关信息</li>
                            <li>支持马钢、宝钢、首钢、鞍钢等钢厂</li>
                            <li>数据从第一行开始，不要有空行</li>
                        </ul>
                        <h6 class="${UPLOAD_LABEL} mb-2.5">upsert 规则</h6>
                        <ul class="list-disc list-inside text-xs text-ink-dim space-y-1.5 mb-4">
                            <li>按 (年度, 月份, 钢厂, 钢种, 类型, 牌号, 基准厚度) 匹配</li>
                            <li>已存在的政策会被覆盖替换</li>
                            <li>支持新增和更新</li>
                        </ul>
                        <h6 class="${UPLOAD_LABEL} mb-2.5">支持的政策文件</h6>
                        <ul class="list-disc list-inside text-xs text-ink-dim space-y-1.5">
                            <li>马钢政策</li>
                            <li>宝钢政策</li>
                            <li>首钢政策</li>
                            <li>鞍钢政策</li>
                            <li>唐钢、邯钢、VAMA、山钢、涟钢等</li>
                        </ul>
                    </div>
                </div>

                <!-- 最近导入记录 -->
                <div class="bg-app-surface border border-line">
                    <div class="px-5 py-3 border-b border-line-subtle flex items-center gap-2.5">
                        <svg class="w-3.5 h-3.5 text-ink-dim" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                        <h5 class="text-xs font-semibold text-ink-dim mb-0">最近导入</h5>
                    </div>
                    <div class="p-5" id="recentPolicyUploads">
                        <div class="text-center py-6">
                            <div class="w-8 h-8 bg-app-elevated flex items-center justify-center mx-auto mb-2.5">
                                <svg class="w-4 h-4 text-ink-dim" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
                            </div>
                            <p class="text-[11px] text-ink-dim">暂无导入记录</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}
