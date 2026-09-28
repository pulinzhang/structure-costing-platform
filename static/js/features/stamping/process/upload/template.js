/**
 * Upload Template
 * 上传页面 — Brabus Carbon & Precision Dark
 * - 双栏布局：左侧表单 + 右侧信息面板
 * - 主按钮 Brabus 红 / 次按钮 Ghost 文字型
 * - 拖拽区加大垂直留白
 */

import { UPLOAD_DROPZONE, HUD_LED } from '../../../../ui/classes.js?v=13';
import {
    uploadBrowseButtonHtml,
    uploadFileHintHtml,
    uploadResetButtonHtml,
    uploadSubmitButtonHtml,
    uploadTemplateButtonHtml,
} from '../../../../ui/upload-actions.js?v=2';

export function uploadTemplate() {
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
            <!-- ===== 左栏：表单卡片 ===== -->
            <div class="bg-app-surface border border-line">
                <div class="px-5 py-3 border-b border-line-subtle flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2.5">
                        ${window.svgIcon('clipboard-list', 'w-3.5 h-3.5 text-ink-dim')}
                        <h5 class="text-xs font-semibold text-ink-muted mb-0">上传项目冲压工艺文件</h5>
                    </div>
                    ${uploadTemplateButtonHtml('stampingUploadTemplateBtn')}
                </div>
                <div id="sopBannerSlot"></div>
                <div class="p-5">
                    <form id="uploadForm" enctype="multipart/form-data">

                        <!-- Brabus 机械舱：上传文件 -->
                        <div class="bg-app-surface border border-line p-4">
                            <div>
                                <div class="flex items-center gap-2 mb-3">
                                    <span class="w-4 h-4 rounded-full bg-app-elevated flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-brand">1</span>
                                    </span>
                                    <span class="text-[13px] text-ink-dim font-medium tracking-wide uppercase">上传工艺文件</span>
                                </div>
                                <div class="ml-6">
                                    <div id="uploadZone" class="${UPLOAD_DROPZONE} mb-4" data-dropzone-state="idle">
                                        <div id="stampingDropIdle" class="flex flex-col items-center gap-0">
                                            <!-- 顶部角标线 -->
                                            <div class="flex items-center gap-3 mb-5 w-full px-3">
                                                <div class="h-px flex-1 bg-app-elevated"></div>
                                                <div class="w-1.5 h-1.5 border border-line rotate-45"></div>
                                                <div class="h-px flex-1 bg-app-elevated"></div>
                                            </div>
                                            <!-- 上传图标 -->
                                            <div class="mb-3 relative">
                                                <div class="absolute inset-0 bg-brand/8 blur-xl rounded-full"></div>
                                                <svg class="w-9 h-9 text-ink-faint relative z-10" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.2">
                                                    <path stroke-linecap="round" stroke-linejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
                                                </svg>
                                            </div>
                                            <!-- 主文字 -->
                                            <h5 id="uploadTitle" class="text-[11px] text-ink-dim font-semibold tracking-widest uppercase mb-1">拖拽文件到此处</h5>
                                            ${uploadFileHintHtml('uploadHint')}
                                            <!-- 底部角标线 -->
                                            <div class="flex items-center gap-3 mt-1 w-full px-3">
                                                <div class="h-px flex-1 bg-app-elevated"></div>
                                                <div class="w-1.5 h-1.5 border border-line rotate-45"></div>
                                                <div class="h-px flex-1 bg-app-elevated"></div>
                                            </div>
                                            <input type="file" id="fileInput" class="hidden" accept=".xlsx,.xls">
                                            ${uploadBrowseButtonHtml('stampingSelectFileBtn')}
                                            <p class="text-[10px] text-ink-faint mt-4 mb-0">
                                                .xlsx / .xls
                                                <span class="mx-2 text-ink-faint">|</span>
                                                最大 50MB
                                            </p>
                                        </div>

                                        <div id="stampingProgressPanel" class="hidden text-left w-full">
                                            <div class="flex items-center justify-between gap-3 mb-3">
                                                <div class="flex items-center gap-2 min-w-0">
                                                    ${window.svgIcon('spinner', 'w-4 h-4 text-brand')}
                                                    <h5 id="stampingProgressTitle" class="text-xs font-medium text-ink truncate mb-0">正在解析工艺文件...</h5>
                                                </div>
                                                <span id="stampingProgressPercent" class="text-xs font-mono tabular-nums text-brand shrink-0">0%</span>
                                            </div>
                                            <div class="h-1.5 w-full bg-app-deep border border-line overflow-hidden mb-3">
                                                <div id="stampingProgressBar"
                                                     class="h-full bg-brand hud-brand-glow transition-all duration-300"
                                                     style="width: 0%"></div>
                                            </div>
                                            <p id="stampingProgressMsg" class="text-[11px] text-ink-muted leading-relaxed mb-0 whitespace-pre-wrap break-words max-h-48 overflow-y-auto">已提交解析队列</p>
                                            <a id="stampingGradeAction" href="#/steel-grade-category"
                                               class="hidden mt-3 inline-flex items-center gap-1 text-[11px] text-brand-hud hover:text-brand-active">打开牌号分类</a>
                                        </div>
                                    </div>

                                    <!-- 文件预览 -->
                                    <div id="filePreview" class="hidden mb-4"></div>

                                    <!-- 操作按钮行 -->
                                    <div class="flex items-center justify-end gap-3">
                                        ${uploadResetButtonHtml('stampingResetButton')}
                                        ${uploadSubmitButtonHtml('submitBtn')}
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
                <div class="bg-app-surface border border-line">
                    <div class="px-4 py-3 border-b border-line-subtle flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <span class="${HUD_LED}"></span>
                            <h5 class="text-[11px] font-bold text-ink-muted mb-0 tracking-widest">填写说明</h5>
                        </div>
                    </div>
                    <div class="p-4 space-y-3 text-[11px] text-ink-muted leading-relaxed">
                        <p class="text-warn">本页只导入第一次投产，选文件即可。项目和冲压工厂从表格抬头读取，基地按项目档案带出。项目没登记、已停用、这个月不能做，或同一个项目代号挂在多个基地上，整份退回。按档案里的项目代号和供应商全称保存。已经投产后再传：文件里已有的零件会更新，没写到的不会删；出现新零件号整份退回，换零件号走工程变更。这个范围已经算过冲压加工费的零件，不能删。不必先有模具布点。</p>
                        <p>模具编号可空。冲压厂若要算模具费，再另传模具布点。</p>
                        <p><span class="text-ink-muted">是否利废</span>只看本表「料片式样」。写成「利用××废料」（例如利用侧围废料），或格子里写「利废」（写成「利费」也算），就是利用件：材料按成品净重 × 废料月度价，不按新板价。写「要利废」是这件会产出废料给别人用，不是利用件。方料、卷料、条料只表示料片形状，和利废无关。</p>
                        <p><span class="text-ink-muted">废料副产品</span>：长、宽、可制件数、料片式样都空，但有零件净重。这是家模带出的小件，材料按废料净重算，不算冲压费。不要只空长和宽、其它格还填着。</p>
                        <p>模具布点是计划，不作为利废或废料副产品依据；与本表不一致时以本表为准。</p>
                        <p>同一零件的工序号（如 OP30）不可重复，否则整单失败并标出 Excel 行号。</p>
                        <p>拼焊件：零件号整段合并，料片的长和宽可以按每一小片分开填。下载的模板里有普通件和拼焊的例子。</p>
                    </div>
                </div>

                <!-- 最近上传记录 -->
                <div class="bg-app-surface border border-line">
                    <div class="px-4 py-3 border-b border-line-subtle flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <span class="${HUD_LED}"></span>
                            <h5 class="text-[11px] font-bold text-ink-muted mb-0 tracking-widest uppercase">最近上传</h5>
                        </div>
                    </div>
                    <div class="p-4" id="recentUploads">
                        <div class="text-center py-5">
                            <div class="w-8 h-8 bg-app-surface border border-line flex items-center justify-center mx-auto mb-2.5">
                                <svg class="w-4 h-4 text-ink-faint" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
                            </div>
                            <p class="text-[10px] text-ink-faint">暂无上传记录</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}
