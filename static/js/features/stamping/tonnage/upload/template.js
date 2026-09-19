/**
 * 冲次单价上传 — 模板
 * 基地 + 年度必选；三列 Excel（名称 / 单位 / 单价）；同步导入
 */

import {
    BTN_FILE_SELECT,
    BTN_GHOST,
    BTN_UPLOAD_SUBMIT,
    UPLOAD_DROPZONE,
    UPLOAD_INPUT,
    UPLOAD_LABEL,
} from '../../../../ui-classes.js?v=1';

export function tonnageUploadTemplate() {
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
            <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
                <div class="px-5 py-3 border-b border-[#222222] flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2.5">
                        ${window.svgIcon('file-earmark-excel', 'w-3.5 h-3.5 text-[#616161]')}
                        <h5 class="text-xs font-semibold text-[#9e9e9e] mb-0">冲次单价导入</h5>
                    </div>
                    <button type="button"
                            id="tonnageUploadTemplateBtn"
                            class="inline-flex items-center gap-1.5 bg-transparent text-[#888888] border border-[#2c2c2c] px-3 py-1.5 text-[11px] font-medium rounded-sm hover:border-[#d32f2f] hover:text-[#d32f2f] transition-all duration-150">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                        下载模板
                    </button>
                </div>
                <div class="p-5">
                    <form id="tonnageUploadForm">
                        <div class="bg-[#161616] border border-[#252525] p-4">
                            <div class="mb-5">
                                <div class="flex items-center gap-2 mb-2.5">
                                    <span class="w-4 h-4 rounded-full bg-[#2a2a2a] flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-[#d32f2f]">1</span>
                                    </span>
                                    <span class="text-[13px] text-[#6b6b6b] font-medium tracking-wide uppercase">选择基地与年度</span>
                                </div>
                                <div class="ml-6 grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <div>
                                        <label for="tonnageUploadLocation" class="${UPLOAD_LABEL}">
                                            采购基地 <span class="text-[#d32f2f]">*</span>
                                        </label>
                                        <select id="tonnageUploadLocation"
                                                name="location"
                                                required
                                                class="${UPLOAD_INPUT} w-full">
                                            <option value="">请选择采购基地</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label for="tonnageUploadYear" class="${UPLOAD_LABEL}">
                                            年度 <span class="text-[#d32f2f]">*</span>
                                        </label>
                                        <input type="text"
                                               id="tonnageUploadYear"
                                               name="year"
                                               placeholder="例如：2026"
                                               required
                                               pattern="[0-9]{4}"
                                               maxlength="4"
                                               class="${UPLOAD_INPUT} w-full">
                                    </div>
                                </div>
                                <p class="ml-6 mt-1.5 text-[11px] text-[#616161]">导入时必须指定基地与年度，写入该基地该年的冲次单价</p>
                            </div>

                            <div class="h-px bg-[#1e1e1e] mx-6 mb-4"></div>

                            <div>
                                <div class="flex items-center gap-2 mb-3">
                                    <span class="w-4 h-4 rounded-full bg-[#2a2a2a] flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-[#d32f2f]">2</span>
                                    </span>
                                    <span class="text-[13px] text-[#6b6b6b] font-medium tracking-wide uppercase">上传冲次单价表</span>
                                </div>
                                <div class="ml-6">
                                    <div id="tonnageUploadZone" class="${UPLOAD_DROPZONE} mb-4" data-dropzone-state="idle">
                                        <div id="tonnageUploadDropIdle" class="flex flex-col items-center gap-0">
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
                                            <h5 id="tonnageUploadTitle" class="text-[11px] text-[#606060] font-semibold tracking-widest uppercase mb-1">拖拽文件到此处</h5>
                                            <p id="tonnageUploadHint" class="text-[10px] text-[#3a3a3a] mb-6">或点击下方按钮选择文件</p>
                                            <div class="flex items-center gap-3 mt-1 w-full px-3">
                                                <div class="h-px flex-1 bg-[#2a2a2a]"></div>
                                                <div class="w-1.5 h-1.5 border border-[#363636] rotate-45"></div>
                                                <div class="h-px flex-1 bg-[#2a2a2a]"></div>
                                            </div>
                                            <input type="file" id="tonnageUploadFileInput" class="hidden" accept=".xlsx">
                                            <button type="button"
                                                    id="tonnageUploadSelectFileBtn"
                                                    class="${BTN_FILE_SELECT}">
                                                ${window.svgIcon('folder', 'w-3.5 h-3.5')}
                                                浏览文件
                                            </button>
                                            <p class="text-[10px] text-[#3a3a3a] mt-4 mb-0">
                                                仅 .xlsx
                                                <span class="mx-2 text-[#2a2a2a]">|</span>
                                                同步导入
                                            </p>
                                        </div>

                                        <div id="tonnageUploadProgressPanel" class="hidden text-left w-full">
                                            <div class="flex items-center justify-between gap-3 mb-3">
                                                <div class="flex items-center gap-2 min-w-0">
                                                    ${window.svgIcon('spinner', 'w-4 h-4 text-[#d32f2f]')}
                                                    <h5 class="text-xs font-medium text-[#ffffff] truncate mb-0">正在导入冲次单价...</h5>
                                                </div>
                                            </div>
                                            <div class="h-1.5 w-full bg-[#0a0a0a] border border-[#2c2c2c] overflow-hidden mb-3">
                                                <div class="h-full bg-[#d32f2f] shadow-[0_0_8px_rgba(211,47,47,0.5)] transition-all duration-300 animate-pulse"
                                                     style="width: 60%"></div>
                                            </div>
                                            <p id="tonnageUploadProgressMsg" class="text-[11px] text-[#9e9e9e] leading-relaxed mb-0 whitespace-pre-wrap break-words max-h-48 overflow-y-auto">解析并写入数据库，请稍候</p>
                                        </div>
                                    </div>

                                    <div id="tonnageUploadFilePreview" class="hidden mb-4"></div>

                                    <div class="flex items-center justify-end gap-3">
                                        <button type="button"
                                                id="tonnageUploadResetBtn"
                                                class="${BTN_GHOST}">
                                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
                                            重置
                                        </button>
                                        <button type="submit"
                                                id="tonnageUploadSubmitBtn"
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
                            <h5 class="text-[11px] font-bold text-[#9e9e9e] mb-0 tracking-widest uppercase">格式说明</h5>
                        </div>
                        <span class="text-[10px] text-[#4d4d4d] tracking-wider">SPEC</span>
                    </div>
                    <div class="p-4 space-y-4">
                        <div>
                            <h6 class="text-[10px] uppercase tracking-wider text-[#616161] mb-2">固定三列</h6>
                            <ul class="list-disc list-inside text-xs text-[#616161] space-y-1.5">
                                <li><span class="text-[#9e9e9e]">名称</span>：吨位，如 400T</li>
                                <li><span class="text-[#9e9e9e]">单位</span>：固定为「次」</li>
                                <li><span class="text-[#9e9e9e]">单价</span>：元/次，固定保留三位小数</li>
                            </ul>
                        </div>
                        <div>
                            <h6 class="text-[10px] uppercase tracking-wider text-[#616161] mb-2">示例</h6>
                            <div class="overflow-hidden border border-[#2c2c2c]">
                                <table class="w-full">
                                    <thead>
                                        <tr class="bg-[#0a0a0a] border-b border-[#2c2c2c]">
                                            <th class="px-2 py-1.5 text-left text-[10px] font-semibold text-[#616161]">名称</th>
                                            <th class="px-2 py-1.5 text-left text-[10px] font-semibold text-[#616161]">单位</th>
                                            <th class="px-2 py-1.5 text-right text-[10px] font-semibold text-[#616161]">单价</th>
                                        </tr>
                                    </thead>
                                    <tbody class="divide-y divide-[#222222]">
                                        <tr><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">400T</td><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">次</td><td class="px-2 py-1.5 text-[11px] text-right font-mono tabular-nums text-[#9e9e9e]">0.564</td></tr>
                                        <tr><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">500T</td><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">次</td><td class="px-2 py-1.5 text-[11px] text-right font-mono tabular-nums text-[#9e9e9e]">0.622</td></tr>
                                        <tr><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">630T</td><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">次</td><td class="px-2 py-1.5 text-[11px] text-right font-mono tabular-nums text-[#9e9e9e]">0.713</td></tr>
                                        <tr><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">800T</td><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">次</td><td class="px-2 py-1.5 text-[11px] text-right font-mono tabular-nums text-[#9e9e9e]">1.026</td></tr>
                                        <tr><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">1000T</td><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">次</td><td class="px-2 py-1.5 text-[11px] text-right font-mono tabular-nums text-[#9e9e9e]">1.283</td></tr>
                                        <tr><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">1200T</td><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">次</td><td class="px-2 py-1.5 text-[11px] text-right font-mono tabular-nums text-[#9e9e9e]">1.539</td></tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        <div>
                            <h6 class="text-[10px] uppercase tracking-wider text-[#616161] mb-2">写入规则</h6>
                            <ul class="list-disc list-inside text-xs text-[#616161] space-y-1.5">
                                <li>唯一键：基地 + 年度 + 吨位</li>
                                <li>已存在则更新单价，不存在则新增</li>
                                <li>列表导出含基地/年份/审核列；导入只读名称/单位/单价（基地/年度以本页选择为准）</li>
                                <li>仅支持 .xlsx，同步导入无需等待队列</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}
