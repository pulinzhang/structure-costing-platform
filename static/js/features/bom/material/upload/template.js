/**
 * BOM 材料清单上传 — 模板
 * 仅上传：基地必选 + Excel 拖拽，无列表/删除/树
 */

import {
    BTN_FILE_SELECT,
    BTN_GHOST,
    BTN_UPLOAD_SUBMIT,
    UPLOAD_DROPZONE,
    UPLOAD_INPUT,
} from '../../../../ui-classes.js?v=1';

export function bomUploadTemplate() {
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
            <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
                <div class="px-5 py-3 border-b border-[#222222] flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2.5">
                        ${window.svgIcon('file-earmark-excel', 'w-3.5 h-3.5 text-[#616161]')}
                        <h5 class="text-xs font-semibold text-[#9e9e9e] mb-0">上传车身件材料清单</h5>
                    </div>
                    <button type="button"
                            id="bomUploadTemplateBtn"
                            class="inline-flex items-center gap-1.5 bg-transparent text-[#888888] border border-[#2c2c2c] px-3 py-1.5 text-[11px] font-medium rounded-sm hover:border-[#d32f2f] hover:text-[#d32f2f] transition-all duration-150">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                        下载模板
                    </button>
                </div>
                <div class="p-5">
                    <form id="bomUploadForm">
                        <div class="bg-[#161616] border border-[#252525] p-4">
                            <div class="mb-5">
                                <div class="flex items-center gap-2 mb-2.5">
                                    <span class="w-4 h-4 rounded-full bg-[#2a2a2a] flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-[#d32f2f]">1</span>
                                    </span>
                                    <span class="text-[13px] text-[#6b6b6b] font-medium tracking-wide uppercase">选择采购基地</span>
                                </div>
                                <div class="ml-6">
                                    <select id="bomUploadLocation"
                                            name="location"
                                            required
                                            class="${UPLOAD_INPUT} w-[280px]">
                                        <option value="">请选择采购基地</option>
                                    </select>
                                    <p class="mt-1.5 text-[11px] text-[#616161]">核价按基地匹配钢价，导入时必须指定基地</p>
                                </div>
                            </div>

                            <div class="h-px bg-[#1e1e1e] mx-6 mb-4"></div>

                            <div class="mb-5">
                                <div class="flex items-center gap-2 mb-2.5">
                                    <span class="w-4 h-4 rounded-full bg-[#2a2a2a] flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-[#d32f2f]">2</span>
                                    </span>
                                    <span class="text-[13px] text-[#6b6b6b] font-medium tracking-wide uppercase">选择项目</span>
                                </div>
                                <div class="ml-6">
                                    <select id="bomUploadVehicleModel"
                                            name="vehicle_model"
                                            required
                                            class="${UPLOAD_INPUT} w-[280px]">
                                        <option value="">请先选择采购基地</option>
                                    </select>
                                    <p class="mt-1.5 text-[11px] text-[#616161]">必选该月可引入项目。文件代号须与所选一致。</p>
                                </div>
                            </div>

                            <div class="h-px bg-[#1e1e1e] mx-6 mb-4"></div>

                            <div>
                                <div class="flex items-center gap-2 mb-3">
                                    <span class="w-4 h-4 rounded-full bg-[#2a2a2a] flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-[#d32f2f]">3</span>
                                    </span>
                                    <span class="text-[13px] text-[#6b6b6b] font-medium tracking-wide uppercase">上传材料清单</span>
                                </div>
                                <div class="ml-6">
                                    <div id="bomUploadZone" class="${UPLOAD_DROPZONE} mb-4" data-dropzone-state="idle">
                                        <div id="bomUploadDropIdle" class="flex flex-col items-center gap-0">
                                            <div class="flex items-center gap-3 mb-5 w-full px-3">
                                                <div class="h-px flex-1 bg-[#2a2a2a]"></div>
                                                <div class="w-1.5 h-1.5 border border-[#363636] rotate-45"></div>
                                                <div class="h-px flex-1 bg-[#2a2a2a]"></div>
                                            </div>
                                            <div class="mb-3 relative">
                                                <div class="absolute inset-0 bg-[#d32f2f]/8 blur-xl rounded-full"></div>
                                                <svg class="w-9 h-9 text-[#4a4a4a] relative z-10" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.2">
                                                    <path stroke-linecap="round" stroke-linejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
                                                </svg>
                                            </div>
                                            <h5 id="bomUploadTitle" class="text-[11px] text-[#606060] font-semibold tracking-widest uppercase mb-1">拖拽文件到此处</h5>
                                            <p id="bomUploadHint" class="text-[10px] text-[#3a3a3a] mb-6">或点击下方按钮选择文件</p>
                                            <div class="flex items-center gap-3 mt-1 w-full px-3">
                                                <div class="h-px flex-1 bg-[#2a2a2a]"></div>
                                                <div class="w-1.5 h-1.5 border border-[#363636] rotate-45"></div>
                                                <div class="h-px flex-1 bg-[#2a2a2a]"></div>
                                            </div>
                                            <input type="file" id="bomUploadFileInput" class="hidden" accept=".xlsx,.xls">
                                            <button type="button"
                                                    id="bomUploadSelectFileBtn"
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

                                        <div id="bomUploadProgressPanel" class="hidden text-left w-full">
                                            <div class="flex items-center justify-between gap-3 mb-3">
                                                <div class="flex items-center gap-2 min-w-0">
                                                    ${window.svgIcon('spinner', 'w-4 h-4 text-[#d32f2f]')}
                                                    <h5 id="bomUploadProgressTitle" class="text-xs font-medium text-[#ffffff] truncate mb-0">正在导入材料清单...</h5>
                                                </div>
                                                <span id="bomUploadProgressPercent" class="text-xs font-mono tabular-nums text-[#d32f2f] shrink-0">…</span>
                                            </div>
                                            <div class="h-1.5 w-full bg-[#0a0a0a] border border-[#2c2c2c] overflow-hidden mb-3">
                                                <div id="bomUploadProgressBar"
                                                     class="h-full bg-[#d32f2f] shadow-[0_0_8px_rgba(211,47,47,0.5)] transition-all duration-300 animate-pulse"
                                                     style="width: 60%"></div>
                                            </div>
                                            <p id="bomUploadProgressMsg" class="text-[11px] text-[#9e9e9e] leading-relaxed mb-0">解析三级树并落盘简图，请稍候</p>
                                        </div>
                                    </div>

                                    <div id="bomUploadFilePreview" class="hidden mb-4"></div>

                                    <div id="bomUploadErrorPanel"
                                         class="hidden mb-4 border border-[#5c1a1a] bg-[#1a0808]"
                                         role="alert">
                                        <div class="flex items-start justify-between gap-3 px-3 py-2.5 border-b border-[#3a1515]">
                                            <div class="min-w-0">
                                                <h6 id="bomUploadErrorTitle"
                                                    class="text-[11px] font-semibold text-[#ef5350] mb-0.5 tracking-wide">导入失败</h6>
                                                <p class="text-[10px] text-[#8E8E93] mb-0">请对照 Excel 行号修改原始表后重新上传，可复制全文</p>
                                            </div>
                                            <div class="flex items-center gap-1 shrink-0">
                                                <button type="button"
                                                        id="bomUploadErrorCopyBtn"
                                                        class="px-2 py-1 text-[10px] text-[#9e9e9e] border border-[#2c2c2c] rounded-sm hover:border-[#9e9e9e] hover:text-white transition-all">
                                                    复制
                                                </button>
                                                <button type="button"
                                                        id="bomUploadErrorCloseBtn"
                                                        class="text-[#616161] hover:text-[#ffffff] transition-colors p-1"
                                                        aria-label="关闭错误提示">
                                                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                                                </button>
                                            </div>
                                        </div>
                                        <pre id="bomUploadErrorBody"
                                             class="m-0 px-3 py-3 text-[12px] font-mono leading-relaxed text-[#ffcdd2] whitespace-pre-wrap break-words max-h-[360px] overflow-y-auto select-text"></pre>
                                    </div>

                                    <div class="flex items-center justify-end gap-3">
                                        <button type="button"
                                                id="bomUploadResetBtn"
                                                class="${BTN_GHOST}">
                                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
                                            重置
                                        </button>
                                        <button type="submit"
                                                id="bomUploadSubmitBtn"
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

            <div class="space-y-3">
                <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
                    <div class="px-4 py-3 border-b border-[#222222] flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <span style="width:2px;height:12px;background:#d32f2f;border-radius:1px;display:inline-block;box-shadow:0 0 6px rgba(211,47,47,0.4);"></span>
                            <h5 class="text-[11px] font-bold text-[#9e9e9e] mb-0 tracking-widest uppercase">导入说明</h5>
                        </div>
                        <span class="text-[10px] text-[#4d4d4d] tracking-wider">SPEC</span>
                    </div>
                    <div class="p-4 space-y-4">
                        <div>
                            <h6 class="text-[10px] uppercase tracking-wider text-[#616161] mb-2">文件要求</h6>
                            <ul class="list-disc list-inside text-xs text-[#616161] space-y-1.5">
                                <li>车身件产品材料清单 Excel（.xlsx / .xls）</li>
                                <li>含三级稀疏树：总成 / 一级 / 二级</li>
                                <li>项目、版本从文件头自动解析</li>
                            </ul>
                        </div>
                        <div>
                            <h6 class="text-[10px] uppercase tracking-wider text-[#616161] mb-2">覆盖规则</h6>
                            <ul class="list-disc list-inside text-xs text-[#616161] space-y-1.5">
                                <li>唯一键：基地 + 项目 + 版本</li>
                                <li>同键再次导入将替换整棵树</li>
                                <li>有内部号的物料必须一物一码（同一零件号对应唯一内部号，反之亦然）</li>
                                <li>同一分总成挂在不同总成下时，焊信与二级子件单车用量必须相同</li>
                                <li>源 Excel 与简图落盘保留</li>
                            </ul>
                        </div>
                        <div>
                            <h6 class="text-[10px] uppercase tracking-wider text-[#616161] mb-2">节点角色</h6>
                            <ul class="list-disc list-inside text-xs text-[#616161] space-y-1.5">
                                <li>板料（料厚 T=…）→ 自制件</li>
                                <li>标准件（M6 等）→ 外购件</li>
                                <li>胶类用量 mm → 耗材</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}
