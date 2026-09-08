/**
 * Upload Template
 * 上传页面 — Brabus Carbon & Precision Dark
 * - 双栏布局：左侧表单 + 右侧信息面板
 * - 主按钮 Brabus 红 / 次按钮 Ghost 文字型
 * - 拖拽区加大垂直留白
 */

import {
    BTN_FILE_SELECT,
    BTN_GHOST,
    BTN_UPLOAD_SUBMIT,
    UPLOAD_DROPZONE,
} from '../../../../ui-classes.js?v=1';

export function uploadTemplate() {
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
            <!-- ===== 左栏：表单卡片 ===== -->
            <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
                <div class="px-5 py-3 border-b border-[#222222] flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2.5">
                        ${window.svgIcon('clipboard-list', 'w-3.5 h-3.5 text-[#616161]')}
                        <h5 class="text-xs font-semibold text-[#9e9e9e] mb-0">上传项目冲压工艺文件</h5>
                    </div>
                    <button type="button"
                            id="stampingUploadTemplateBtn"
                            class="inline-flex items-center gap-1.5 bg-transparent text-[#888888] border border-[#2c2c2c] px-3 py-1.5 text-[11px] font-medium rounded-sm hover:border-[#d32f2f] hover:text-[#d32f2f] transition-all duration-150">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                        下载模板
                    </button>
                </div>
                <div class="p-5">
                    <form id="uploadForm" enctype="multipart/form-data">

                        <!-- Brabus 机械舱：上传文件 -->
                        <div class="bg-[#161616] border border-[#252525] p-4">
                            <div>
                                <div class="flex items-center gap-2 mb-3">
                                    <span class="w-4 h-4 rounded-full bg-[#2a2a2a] flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-[#d32f2f]">1</span>
                                    </span>
                                    <span class="text-[13px] text-[#6b6b6b] font-medium tracking-wide uppercase">上传工艺文件</span>
                                </div>
                                <div class="ml-6">
                                    <div id="uploadZone" class="${UPLOAD_DROPZONE} mb-4" data-dropzone-state="idle">
                                        <div id="stampingDropIdle" class="flex flex-col items-center gap-0">
                                            <!-- 顶部角标线 -->
                                            <div class="flex items-center gap-3 mb-5 w-full px-3">
                                                <div class="h-px flex-1 bg-[#2a2a2a]"></div>
                                                <div class="w-1.5 h-1.5 border border-[#363636] rotate-45"></div>
                                                <div class="h-px flex-1 bg-[#2a2a2a]"></div>
                                            </div>
                                            <!-- 上传图标 -->
                                            <div class="mb-3 relative">
                                                <div class="absolute inset-0 bg-[#d32f2f]/8 blur-xl rounded-full"></div>
                                                <svg class="w-9 h-9 text-[#4a4a4a] relative z-10" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.2">
                                                    <path stroke-linecap="round" stroke-linejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
                                                </svg>
                                            </div>
                                            <!-- 主文字 -->
                                            <h5 id="uploadTitle" class="text-[11px] text-[#606060] font-semibold tracking-widest uppercase mb-1">拖拽文件到此处</h5>
                                            <p id="uploadHint" class="text-[10px] text-[#3a3a3a] mb-6">或点击下方按钮选择文件</p>
                                            <!-- 底部角标线 -->
                                            <div class="flex items-center gap-3 mt-1 w-full px-3">
                                                <div class="h-px flex-1 bg-[#2a2a2a]"></div>
                                                <div class="w-1.5 h-1.5 border border-[#363636] rotate-45"></div>
                                                <div class="h-px flex-1 bg-[#2a2a2a]"></div>
                                            </div>
                                            <input type="file" id="fileInput" class="hidden" accept=".xlsx,.xls">
                                            <button type="button"
                                                    id="stampingSelectFileBtn"
                                                    class="${BTN_FILE_SELECT}">
                                                ${window.svgIcon('folder', 'w-3.5 h-3.5')}
                                                浏览文件
                                            </button>
                                            <p class="text-[10px] text-[#3a3a3a] mt-4 mb-0">
                                                .xlsx / .xls
                                                <span class="mx-2 text-[#2a2a2a]">|</span>
                                                最大 50MB
                                            </p>
                                        </div>

                                        <div id="stampingProgressPanel" class="hidden text-left w-full">
                                            <div class="flex items-center justify-between gap-3 mb-3">
                                                <div class="flex items-center gap-2 min-w-0">
                                                    ${window.svgIcon('spinner', 'w-4 h-4 text-[#d32f2f]')}
                                                    <h5 id="stampingProgressTitle" class="text-xs font-medium text-[#ffffff] truncate mb-0">正在解析工艺文件...</h5>
                                                </div>
                                                <span id="stampingProgressPercent" class="text-xs font-mono tabular-nums text-[#d32f2f] shrink-0">0%</span>
                                            </div>
                                            <div class="h-1.5 w-full bg-[#0a0a0a] border border-[#2c2c2c] overflow-hidden mb-3">
                                                <div id="stampingProgressBar"
                                                     class="h-full bg-[#d32f2f] shadow-[0_0_8px_rgba(211,47,47,0.5)] transition-all duration-300"
                                                     style="width: 0%"></div>
                                            </div>
                                            <p id="stampingProgressMsg" class="text-[11px] text-[#9e9e9e] leading-relaxed mb-0 whitespace-pre-wrap break-words max-h-48 overflow-y-auto">已提交解析队列</p>
                                        </div>
                                    </div>

                                    <!-- 文件预览 -->
                                    <div id="filePreview" class="hidden mb-4"></div>

                                    <!-- 操作按钮行 -->
                                    <div class="flex items-center justify-end gap-3">
                                        <button type="button"
                                                id="stampingResetButton"
                                                onclick="window.resetUploadForm()"
                                                class="${BTN_GHOST}">
                                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
                                            重置
                                        </button>
                                        <button type="submit"
                                                id="submitBtn"
                                                disabled
                                                class="${BTN_UPLOAD_SUBMIT}">
                                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                                            上传
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </form>
                </div>
            </div>

            <!-- ===== 右栏：信息面板 ===== -->
            <div class="space-y-3">
                <!-- 填写说明 -->
                <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
                    <div class="px-4 py-3 border-b border-[#222222] flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <span style="width:2px;height:12px;background:#d32f2f;border-radius:1px;display:inline-block;box-shadow:0 0 6px rgba(211,47,47,0.4);"></span>
                            <h5 class="text-[11px] font-bold text-[#9e9e9e] mb-0 tracking-widest">填写说明</h5>
                        </div>
                    </div>
                    <div class="p-4 space-y-3 text-[11px] text-[#888888] leading-relaxed">
                        <p class="text-[#ffb74d]">本文件为双方签字的工艺确认表。只需选择文件。项目与冲压工厂从表头解析；采购基地由项目主数据带出。未登记、已禁用、该月不可引入，或同一代号挂在多个可引入基地，将退回。落库写规范项目代号与供应商全称。同基地 + 冲压厂 + 项目 + 版本再次上传将覆盖。不必先有模具布点。</p>
                        <p>模具编号可空。冲压厂若要算模具费，再另传模具布点。</p>
                        <p><span class="text-[#c8c8c8]">是否利废</span>只看本表「料片式样」。写「利用××废料」（如利用侧围废料）或格里写「利废」（含错写成「利费」）即记为利用件，材料按成品净重 × 废料月度价（从废料里捡出的成品），不按一事一议新板价。写「要利废」表示这件会产出废料给别人用，不是利用件。方料 / 卷料 / 条料仍表示料片形状，与利废是两件事。</p>
                        <p><span class="text-[#c8c8c8]">废料副产品</span>：长/卷料宽、宽/卷料步距、可制件数、料片式样都空，且有零件净重 → 家模带出的小件，材料同样按废料净重，不算冲压费。不要只空长宽、其它列还填着。</p>
                        <p>模具布点是计划，不作为利废或废料副产品依据；与本表不一致时以本表为准。</p>
                        <p>同一零件的工序号（如 OP30）不可重复，否则整单失败并标出 Excel 行号。</p>
                        <p>拼焊件：零件号整段合并，料片长/宽可按子片切块。下载模板含普通件与拼焊样例。</p>
                    </div>
                </div>

                <!-- 最近上传记录 -->
                <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
                    <div class="px-4 py-3 border-b border-[#222222] flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <span style="width:2px;height:12px;background:#d32f2f;border-radius:1px;display:inline-block;box-shadow:0 0 6px rgba(211,47,47,0.4);"></span>
                            <h5 class="text-[11px] font-bold text-[#9e9e9e] mb-0 tracking-widest uppercase">最近上传</h5>
                        </div>
                    </div>
                    <div class="p-4" id="recentUploads">
                        <div class="text-center py-5">
                            <div class="w-8 h-8 bg-[#1a1a1a] border border-[#2a2a2a] flex items-center justify-center mx-auto mb-2.5">
                                <svg class="w-4 h-4 text-[#4a4a4a]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
                            </div>
                            <p class="text-[10px] text-[#4a4a4a]">暂无上传记录</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}
