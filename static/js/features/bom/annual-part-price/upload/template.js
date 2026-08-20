/**
 * 年度零件价上传 — 模板
 * 基地 + 年度必选；Excel 列：零件号/名称/单位/单价/原供货类型/供应商/备注；同步导入
 */

export function annualPartPriceUploadTemplate() {
    return `
        <div class="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
            <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
                <div class="px-5 py-3 border-b border-[#222222] flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2.5">
                        ${window.svgIcon('file-earmark-excel', 'w-3.5 h-3.5 text-[#616161]')}
                        <h5 class="text-xs font-semibold text-[#9e9e9e] mb-0">年度零件价导入</h5>
                    </div>
                    <button type="button"
                            id="annualPartPriceUploadTemplateBtn"
                            class="inline-flex items-center gap-1.5 bg-transparent text-[#888888] border border-[#2c2c2c] px-3 py-1.5 text-[11px] font-medium rounded-sm hover:border-[#d32f2f] hover:text-[#d32f2f] transition-all duration-150">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                        下载模板
                    </button>
                </div>
                <div class="p-5">
                    <form id="annualPartPriceUploadForm">
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
                                        <label for="annualPartPriceUploadLocation" class="upload-label">
                                            采购基地 <span class="text-[#d32f2f]">*</span>
                                        </label>
                                        <select id="annualPartPriceUploadLocation"
                                                name="location"
                                                required
                                                class="upload-input w-full text-[11px]">
                                            <option value="">请选择采购基地</option>
                                            <option value="大连">大连</option>
                                            <option value="芜湖">芜湖</option>
                                            <option value="鄂尔多斯">鄂尔多斯</option>
                                            <option value="青岛">青岛</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label for="annualPartPriceUploadYear" class="upload-label">
                                            年度 <span class="text-[#d32f2f]">*</span>
                                        </label>
                                        <input type="text"
                                               id="annualPartPriceUploadYear"
                                               name="year"
                                               placeholder="例如：2026"
                                               required
                                               pattern="[0-9]{4}"
                                               maxlength="4"
                                               class="upload-input w-full">
                                    </div>
                                </div>
                                <p class="ml-6 mt-1.5 text-[11px] text-[#616161]">导入时必须指定基地与年度，写入该基地该年的年度零件价</p>
                            </div>

                            <div class="h-px bg-[#1e1e1e] mx-6 mb-4"></div>

                            <div>
                                <div class="flex items-center gap-2 mb-3">
                                    <span class="w-4 h-4 rounded-full bg-[#2a2a2a] flex items-center justify-center shrink-0">
                                        <span class="text-[10px] font-semibold text-[#d32f2f]">2</span>
                                    </span>
                                    <span class="text-[13px] text-[#6b6b6b] font-medium tracking-wide uppercase">上传年度零件价表</span>
                                </div>
                                <div class="ml-6">
                                    <div id="annualPartPriceUploadZone" class="upload-dropzone mb-4">
                                        <div id="annualPartPriceUploadDropIdle" class="flex flex-col items-center gap-0">
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
                                            <h5 id="annualPartPriceUploadTitle" class="text-[11px] text-[#606060] font-semibold tracking-widest uppercase mb-1">拖拽文件到此处</h5>
                                            <p id="annualPartPriceUploadHint" class="text-[10px] text-[#3a3a3a] mb-6">或点击下方按钮选择文件</p>
                                            <div class="flex items-center gap-3 mt-1 w-full px-3">
                                                <div class="h-px flex-1 bg-[#2a2a2a]"></div>
                                                <div class="w-1.5 h-1.5 border border-[#363636] rotate-45"></div>
                                                <div class="h-px flex-1 bg-[#2a2a2a]"></div>
                                            </div>
                                            <input type="file" id="annualPartPriceUploadFileInput" class="hidden" accept=".xlsx">
                                            <button type="button"
                                                    id="annualPartPriceUploadSelectFileBtn"
                                                    class="btn-file-select">
                                                ${window.svgIcon('folder', 'w-3.5 h-3.5')}
                                                浏览文件
                                            </button>
                                            <p class="text-[10px] text-[#3a3a3a] mt-4 mb-0">
                                                仅 .xlsx
                                                <span class="mx-2 text-[#2a2a2a]">|</span>
                                                同步导入
                                            </p>
                                        </div>

                                        <div id="annualPartPriceUploadProgressPanel" class="hidden text-left w-full">
                                            <div class="flex items-center justify-between gap-3 mb-3">
                                                <div class="flex items-center gap-2 min-w-0">
                                                    ${window.svgIcon('spinner', 'w-4 h-4 text-[#d32f2f]')}
                                                    <h5 class="text-xs font-medium text-[#ffffff] truncate mb-0">正在导入年度零件价...</h5>
                                                </div>
                                            </div>
                                            <div class="h-1.5 w-full bg-[#0a0a0a] border border-[#2c2c2c] overflow-hidden mb-3">
                                                <div class="h-full bg-[#d32f2f] shadow-[0_0_8px_rgba(211,47,47,0.5)] transition-all duration-300 animate-pulse"
                                                     style="width: 60%"></div>
                                            </div>
                                            <p id="annualPartPriceUploadProgressMsg" class="text-[11px] text-[#9e9e9e] leading-relaxed mb-0">解析并写入数据库，请稍候</p>
                                        </div>
                                    </div>

                                    <div id="annualPartPriceUploadFilePreview" class="hidden mb-4"></div>

                                    <div class="flex items-center justify-end gap-3">
                                        <button type="button"
                                                id="annualPartPriceUploadResetBtn"
                                                class="btn-ghost">
                                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
                                            重置
                                        </button>
                                        <button type="submit"
                                                id="annualPartPriceUploadSubmitBtn"
                                                disabled
                                                class="btn-upload-submit disabled:opacity-30 disabled:pointer-events-none">
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
                            <h6 class="text-[10px] uppercase tracking-wider text-[#616161] mb-2">Excel 列</h6>
                            <ul class="list-disc list-inside text-xs text-[#616161] space-y-1.5">
                                <li><span class="text-[#9e9e9e]">零件号</span>：取价主键，如 QR36410</li>
                                <li><span class="text-[#9e9e9e]">零件名称</span>：可选，如 焊接方螺母</li>
                                <li><span class="text-[#9e9e9e]">单位</span>：默认 pcs</li>
                                <li><span class="text-[#9e9e9e]">单价</span>：元/单位，固定四位小数，允许 0</li>
                                <li><span class="text-[#9e9e9e]">原供货类型</span>：如 标准件 / 沿用 / 胶块</li>
                                <li><span class="text-[#9e9e9e]">供应商</span>：可选</li>
                                <li><span class="text-[#9e9e9e]">备注</span>：可选</li>
                            </ul>
                        </div>
                        <div>
                            <h6 class="text-[10px] uppercase tracking-wider text-[#616161] mb-2">示例</h6>
                            <div class="overflow-hidden border border-[#2c2c2c] max-h-[280px] overflow-y-auto">
                                <table class="w-full">
                                    <thead class="sticky top-0">
                                        <tr class="bg-[#0a0a0a] border-b border-[#2c2c2c]">
                                            <th class="px-2 py-1.5 text-left text-[10px] font-semibold text-[#616161]">零件号</th>
                                            <th class="px-2 py-1.5 text-left text-[10px] font-semibold text-[#616161]">零件名称</th>
                                            <th class="px-2 py-1.5 text-left text-[10px] font-semibold text-[#616161]">单位</th>
                                            <th class="px-2 py-1.5 text-right text-[10px] font-semibold text-[#616161]">单价</th>
                                            <th class="px-2 py-1.5 text-left text-[10px] font-semibold text-[#616161]">原供货类型</th>
                                        </tr>
                                    </thead>
                                    <tbody class="divide-y divide-[#222222]">
                                        <tr><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">501004437AA</td><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">中通道后纵梁本体II</td><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">pcs</td><td class="px-2 py-1.5 text-[11px] text-right font-mono tabular-nums text-[#9e9e9e]">2.1300</td><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">沿用</td></tr>
                                        <tr><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">QR36410</td><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">焊接方螺母</td><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">pcs</td><td class="px-2 py-1.5 text-[11px] text-right font-mono tabular-nums text-[#9e9e9e]">0.1750</td><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">标准件</td></tr>
                                        <tr><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">504000341AA</td><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">左D柱下结构增强胶块</td><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">pcs</td><td class="px-2 py-1.5 text-[11px] text-right font-mono tabular-nums text-[#9e9e9e]">31.4900</td><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">胶块</td></tr>
                                        <tr><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">Q1980620</td><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">承面凸焊螺栓 M6X20</td><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">pcs</td><td class="px-2 py-1.5 text-[11px] text-right font-mono tabular-nums text-[#9e9e9e]">0.0620</td><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">标准件</td></tr>
                                        <tr><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">TBD</td><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">右D柱上结构增强胶块（需替换正式号）</td><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">pcs</td><td class="px-2 py-1.5 text-[11px] text-right font-mono tabular-nums text-[#9e9e9e]">19.3600</td><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">胶块</td></tr>
                                        <tr><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">T15-5400791</td><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">左前卷收器安装板</td><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">pcs</td><td class="px-2 py-1.5 text-[11px] text-right font-mono tabular-nums text-[#9e9e9e]">0.0000</td><td class="px-2 py-1.5 text-[11px] text-[#9e9e9e]">沿用</td></tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        <div>
                            <h6 class="text-[10px] uppercase tracking-wider text-[#616161] mb-2">写入规则</h6>
                            <ul class="list-disc list-inside text-xs text-[#616161] space-y-1.5">
                                <li>基地、年度在页面选择，不写进 Excel</li>
                                <li>唯一键：基地 + 年度 + 零件号</li>
                                <li>已存在则更新单价/名称等，不存在则新增</li>
                                <li>仅支持 .xlsx，同步导入；可点「下载模板」拿生产样例</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}
