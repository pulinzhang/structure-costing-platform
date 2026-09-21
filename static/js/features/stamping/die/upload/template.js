import { BTN_FILE_SELECT, BTN_GHOST, BTN_UPLOAD_SUBMIT, UPLOAD_DROPZONE, UPLOAD_INPUT, HUD_LED } from '../../../../ui/classes.js?v=12';

export function dieUploadTemplate() {
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
            <div class="bg-app-surface border border-line">
                <div class="px-5 py-3 border-b border-line-subtle flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2.5">
                        ${window.svgIcon('clipboard-list', 'w-3.5 h-3.5 text-ink-dim')}
                        <h5 class="text-xs font-semibold text-ink-muted mb-0">上传冲压模具布点清单</h5>
                    </div>
                    <button type="button"
                            id="dieUploadTemplateBtn"
                            class="inline-flex items-center gap-1.5 bg-transparent text-ink-muted border border-line px-3 py-1.5 text-[11px] font-medium rounded-sm hover:border-brand hover:text-brand transition-all duration-150">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                        下载模板
                    </button>
                </div>
                <div id="sopBannerSlot"></div>
                <div class="p-5">
                    <form id="dieUploadForm" enctype="multipart/form-data">
                        <div class="bg-app-surface border border-line p-4">
                            <div class="mb-5">
                                <div class="flex items-center gap-2 mb-2.5">
                                    <span class="w-4 h-4 rounded-full bg-app-elevated flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-brand">1</span>
                                    </span>
                                    <span class="text-[13px] text-ink-dim font-medium tracking-wide uppercase">选择采购基地</span>
                                </div>
                                <div class="ml-6">
                                    <select id="dieLocation" name="location" required class="${UPLOAD_INPUT} hud-filter w-[280px]">
                                        <option value="">请选择采购基地</option>
                                    </select>
                                    <p class="mt-2 text-[10px] text-ink-faint">必选。</p>
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
                                    <select id="dieVehicleModel" name="vehicle_model" required
                                            class="${UPLOAD_INPUT} hud-filter w-[280px]">
                                        <option value="">请先选择采购基地</option>
                                    </select>
                                    <p class="mt-2 text-[10px] text-ink-faint">必选该月可引入项目。须与文件名或标题里的项目一致。</p>
                                </div>
                            </div>
                            <div class="h-px bg-app-surface mx-6 mb-4"></div>
                            <div>
                                <div class="flex items-center gap-2 mb-3">
                                    <span class="w-4 h-4 rounded-full bg-app-elevated flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-brand">3</span>
                                    </span>
                                    <span class="text-[13px] text-ink-dim font-medium tracking-wide uppercase">上传布点文件</span>
                                </div>
                                <div class="ml-6">
                                    <div id="dieUploadZone" class="${UPLOAD_DROPZONE} mb-4" data-dropzone-state="idle">
                                        <div id="dieDropIdle" class="flex flex-col items-center gap-0">
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
                                            <h5 id="dieUploadTitle" class="text-[11px] text-ink-dim font-semibold tracking-widest uppercase mb-1">拖拽文件到此处</h5>
                                            <p id="dieUploadHint" class="text-[10px] text-ink-faint mb-6">或点击下方按钮选择文件</p>
                                            <div class="flex items-center gap-3 mt-1 w-full px-3">
                                                <div class="h-px flex-1 bg-app-elevated"></div>
                                                <div class="w-1.5 h-1.5 border border-line rotate-45"></div>
                                                <div class="h-px flex-1 bg-app-elevated"></div>
                                            </div>
                                            <input type="file" id="dieFileInput" class="hidden" accept=".xlsx,.xls">
                                            <button type="button" id="dieSelectFileBtn" class="${BTN_FILE_SELECT}">
                                                ${window.svgIcon('folder', 'w-3.5 h-3.5')}
                                                浏览文件
                                            </button>
                                            <p class="text-[10px] text-ink-faint mt-4 mb-0">.xlsx / .xls<span class="mx-2 text-ink-faint">|</span>最大 50MB · 项目须与上方填写一致</p>
                                        </div>
                                        <div id="dieProgressPanel" class="hidden text-left w-full">
                                            <div class="flex items-center justify-between gap-3 mb-3">
                                                <div class="flex items-center gap-2 min-w-0">
                                                    ${window.svgIcon('spinner', 'w-4 h-4 text-brand')}
                                                    <h5 id="dieProgressTitle" class="text-xs font-medium text-ink truncate mb-0">正在解析模具布点...</h5>
                                                </div>
                                                <span id="dieProgressPercent" class="text-xs font-mono tabular-nums text-brand shrink-0">0%</span>
                                            </div>
                                            <div class="h-1.5 w-full bg-app-deep border border-line overflow-hidden mb-3">
                                                <div id="dieProgressBar" class="h-full bg-brand hud-brand-glow transition-all duration-300" style="width: 0%"></div>
                                            </div>
                                            <p id="dieProgressMsg" class="text-[11px] text-ink-muted leading-relaxed mb-0 whitespace-pre-wrap break-words max-h-48 overflow-y-auto">已提交解析队列</p>
                                        </div>
                                    </div>
                                    <div id="dieFilePreview" class="hidden mb-4"></div>
                                    <div class="flex items-center justify-end gap-3">
                                        <button type="button" id="dieResetButton" class="${BTN_GHOST}">
                                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
                                            重置
                                        </button>
                                        <button type="submit" id="dieSubmitBtn" disabled class="${BTN_UPLOAD_SUBMIT}">
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
                            <span class="${HUD_LED}"></span>
                            <h5 class="text-[11px] font-bold text-ink-muted mb-0 tracking-widest uppercase">说明</h5>
                        </div>
                    </div>
                    <div class="p-4 space-y-3 text-[11px] text-ink-muted leading-relaxed">
                        <p>请先选择采购基地，再选择该月可引入项目。</p>
                        <p>文件名或标题里的项目必须和所选一致，不一致将退回、不会入库。</p>
                        <p>本页不选冲压厂：开模时尚无定点供应商。</p>
                        <p>模具编号可空，系统按规则自动编号；已填写的编号保持不变。</p>
                        <p>废料副产品：长/卷料宽、宽/卷料步距、可制件数、板料形状都空，且有零件净重 → 家模带出的小件，分摊比例记 0，不算模具费。不要只空长宽、其它列还填着。</p>
                        <p class="font-mono text-[10px] text-ink-dim leading-relaxed">
                            示意：<span class="text-ink-muted">T13J项目冲压模具布点工艺清单.xlsx</span>
                        </p>
                        <p>本表是模具费用计算依据：本页只入库几何与分摊比例，不算金额。金额在「冲压模具费计算」或自动核价引擎（有布点且当年无结果时补算）。第一次 SOP 抄项目起止；已有 SOP 后再导只更新文件里已有零件，不删未出现的号。文件含新号将整单拒绝。已改的分摊比例会按零件号保留（废料副产品除外，一律 0）。</p>
                        <p>同一零件的工序号不能重复。不导入简图与费用列。</p>
                    </div>
                </div>
                <div class="bg-app-surface border border-line">
                    <div class="px-4 py-3 border-b border-line-subtle">
                        <h5 class="text-[11px] font-bold text-ink-muted mb-0 tracking-widest uppercase">最近上传</h5>
                    </div>
                    <div class="p-4" id="dieRecentUploads">
                        <p class="text-[10px] text-ink-faint text-center py-5">暂无上传记录</p>
                    </div>
                </div>
            </div>
        </div>
    `;
}
