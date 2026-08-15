/**
 * Tonnage Price Template
 * 冲次单价维护页面 —Brabus Carbon & Precision Dark
 *
 * 抽屉式交互（与零件列表/partDrawer 对齐）：
 * - 编辑/新增  →editDrawer（40px 右侧滑入）
 * - 复制模板  →copyDrawer（80px 右侧滑入）
 * - 删除确认  →deleteDrawer（80px 右侧滑入）
 */

import { pageSizeSelectHtml } from '../../../../page-size.js?v=2';

export function tonnagePriceTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">

            <!-- 页面主面板：面板头部（标题按钮）+ 表格 -->
            <div class="bg-[#1e1e1e] border border-[#2c2c2c] overflow-hidden w-full max-w-full"
                 style="box-shadow: 0 2px 12px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.03);">

                <!-- 面板头部：标题+ 操作按钮 -->
                <div class="flex items-center justify-between px-5 py-3.5 border-b border-[#222222]"
                     style="background: linear-gradient(90deg, #1c1c1c 0%, #1e1e1e 60%);">
                    <div class="flex items-center gap-3">
                        <div class="w-[2px] h-4 bg-[#d32f2f] rounded-[1px] shadow-[0_0_6px_rgba(211,47,47,0.3)]"></div>
                        <h2 class="text-[12px] font-semibold text-[#c8c8c8] tracking-wide">冲次单价</h2>
                    </div>
                    <div class="flex items-center gap-2">
                        <button id="btnBatchDeleteTonnagePrice" class="inline-flex items-center gap-1.5 bg-transparent text-[#888888] border border-[#2c2c2c] px-3 py-1.5 text-[11px] font-medium rounded-sm hover:border-[#c62828] hover:text-[#ef5350] transition-all duration-150">
                            ${window.svgIcon('trash', 'w-3 h-3')}
                            批量删除
                        </button>
                        <button id="btnExportTonnagePrice" class="inline-flex items-center gap-1.5 bg-transparent text-[#888888] border border-[#2c2c2c] px-3 py-1.5 text-[11px] font-medium rounded-sm hover:border-[#d32f2f] hover:text-[#d32f2f] transition-all duration-150">
                            ${window.svgIcon('download', 'w-3 h-3')}
                            导出 Excel
                        </button>
                        <button id="btnCopyTemplate" class="inline-flex items-center gap-1.5 bg-transparent text-[#888888] border border-[#2c2c2c] px-3 py-1.5 text-[11px] font-medium rounded-sm hover:border-[#d32f2f] hover:text-[#d32f2f] transition-all duration-150">
                            ${window.svgIcon('copy', 'w-3 h-3')}
                            复制模板
                        </button>
                        <button id="btnAddTonnagePrice" class="inline-flex items-center gap-1.5 bg-[#d32f2f] text-white px-3 py-1.5 text-[11px] font-semibold rounded-sm hover:bg-[#b71c1c] transition-all duration-150">
                            ${window.svgIcon('plus', 'w-3 h-3')}
                            新增价格
                        </button>
                    </div>
                </div>

                <!-- 工具栏：筛选-->
                <div class="flex items-center justify-between px-5 py-2.5 border-b border-[#1e1e1e]"
                     style="background: linear-gradient(180deg, #181818 0%, #161616 100%);">
                    <!-- 左侧：筛选控价-->
                    <div class="flex items-center gap-3">
                        <div class="flex items-center gap-1.5">
                            <label class="text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em] whitespace-nowrap">基地</label>
                            <select id="locationFilter"
                                    class="w-36 h-7 pl-2.5 pr-7 text-[11px] bg-[#0d0d0d] border border-[#272727] text-[#909090] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] transition-all rounded-sm">
                                <option value="">请选择基地</option>
                            </select>
                        </div>

                        <div class="flex items-center gap-1.5">
                            <label class="text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em] whitespace-nowrap">年份</label>
                            <select id="yearFilter"
                                    class="w-36 h-7 pl-2.5 pr-7 text-[11px] bg-[#0d0d0d] border border-[#272727] text-[#909090] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] transition-all rounded-sm">
                                <option value="">请选择年份</option>
                            </select>
                        </div>

                        <button id="btnFilter"
                                class="inline-flex items-center gap-1.5 h-7 px-3 text-[11px] font-semibold rounded-sm text-[#c8c8c8] border border-[#8a2020] transition-all duration-200 hover:text-white"
                                style="background: linear-gradient(180deg, #3d1515 0%, #2d0f0f 100%); border-color: #6b1a1a; box-shadow: 0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(211,47,47,0.1), 0 0 12px rgba(198,40,40,0.08);">
                            ${window.svgIcon('search', 'w-3 h-3')}
                            查询
                        </button>
                        <span class="text-[10px] text-[#484848]">批量删除须同时选择基地和年度</span>
                    </div>
                </div>

                <!-- 表格匹-->
                <div class="overflow-x-auto">
                    <table class="w-full">
                        <thead>
                            <tr style="background: linear-gradient(180deg, #111111 0%, #0e0e0e 100%); border-bottom: 1px solid #222222;">
                                <th class="px-5 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">基地</th>
                                <th class="px-5 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">年份</th>
                                <th class="px-5 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">压机吨位 (T)</th>
                                <th class="px-5 py-2.5 text-right text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">单冲次价格(全</th>
                                <th class="p-0 w-9" aria-label="操作"></th>
                            </tr>
                        </thead>
                        <tbody id="tonnagePriceTableBody" class="divide-y divide-[#1d1d1d]">
                            <!-- 动态渲查-->
                        </tbody>
                    </table>
                </div>

                <!-- 分页：右下角 -->
                <div class="flex items-center justify-between px-5 py-2 border-t border-[#1e1e1e] bg-[#141414]" id="paginationContainer">
                    <div class="flex items-center gap-3 min-w-0">
                        <span id="totalCountPagination" class="text-[10px] text-[#484848]"></span>
                        ${pageSizeSelectHtml('tonnagePageSize')}
                    </div>
                    <div class="flex items-center gap-0.5" id="paginationBtns">
                        <!-- 动态渲查-->
                    </div>
                </div>

                <!-- 空状态-->
                <div id="emptyState" class="hidden flex flex-col items-center justify-center py-10">
                    <div class="w-8 h-8 flex items-center justify-center mb-3 rounded-sm" style="background:#141414; border: 1px solid #222222;">
                        ${window.svgIcon('clipboard-list', 'w-4 h-4 text-[#3a3a3a]')}
                    </div>
                    <h5 class="text-[11px] font-medium text-[#555555] mb-1">暂无数据</h5>
                    <p class="text-[10px] text-[#3a3a3a]">点击上方"新增价格"添加记录</p>
                </div>

                <!-- 加载中-->
                <div id="loadingState" class="hidden flex items-center justify-center py-10">
                    <div class="w-4 h-4 border border-[#252525] border-t-[#d32f2f] rounded-full animate-spin"></div>
                </div>
            </div>
        </div>

        <!-- 编辑/新增抽屉 -->
        <div class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm transition-opacity duration-300"
             id="editDrawerBackdrop" style="display:none"></div>

        <div class="fixed inset-y-0 right-0 z-[85] w-[640px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="editDrawer" style="display:none; max-height: 100vh; box-shadow: -20px 0 60px rgba(0,0,0,0.95), -8px 0 30px rgba(0,0,0,0.8), 0 0 1px rgba(255,255,255,0.05);">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0"
                 style="background: linear-gradient(180deg, #1f1f1f 0%, #1a1a1a 100%); border-bottom: 1px solid #333333;">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] flex items-center gap-2.5 uppercase" id="editDrawerTitle">
                    <span style="width:3px;height:14px;background:#d32f2f;border-radius:1px;display:inline-block;box-shadow: 0 0 8px rgba(211,47,47,0.5);"></span>
                    编辑价格
                </h5>
                <button type="button" id="closeEditDrawer"
                        class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all duration-200 group">
                    <svg class="w-4 h-4 transition-transform duration-200 group-hover:scale-110" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>

            <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain" id="editDrawerContent" style="scrollbar-width: thin; scrollbar-color: #3a3a3a #1a1a1a;">
                <form id="editForm" class="p-6 space-y-5">
                    <input type="hidden" id="editRecordId" value="">

                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">基地 <span class="text-[#d32f2f]">*</span></label>
                        <select id="editLocation" required
                                class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] transition-all rounded">
                            <option value="">请选择基地</option>
                            <option value="大连">大连</option>
                            <option value="芜湖">芜湖</option>
                            <option value="鄂尔多斯">鄂尔多斯</option>
                            <option value="青岛">青岛</option>
                        </select>
                    </div>

                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">年份 <span class="text-[#d32f2f]">*</span></label>
                        <input type="number" id="editYear" min="2000" max="2100" required
                               class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded"
                               placeholder="如 2026">
                    </div>

                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">压机吨位 (T) <span class="text-[#d32f2f]">*</span></label>
                        <input type="number" id="editTonnage" min="1" required
                               class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded"
                               placeholder="如 800">
                    </div>

                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">单冲次价格(全 <span class="text-[#d32f2f]">*</span></label>
                        <input type="number" id="editPrice" min="0" step="0.001" required
                               class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded"
                               placeholder="如 0.850">
                    </div>

                    <div class="bg-[#0c0c0c] border border-[#1a1a1a] rounded p-3">
                        <p class="text-[11px] text-[#616161]">
                            <span class="text-[#616161]">说明（</span>
                            单冲次价格为该吨位压机每一次冲程的加工费用，单位：全次。
                        </p>
                    </div>
                </form>
            </div>

            <div class="px-6 py-4 border-t border-[#262626] flex items-center justify-end gap-2 shrink-0" style="background: linear-gradient(0deg, #1a1a1a 0%, #161616 100%);">
                <button type="button" id="cancelEditBtn" class="inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-4 py-2 text-[11px] font-medium rounded hover:border-[#9e9e9e] hover:text-white transition-all">
                    取消
                </button>
                <button type="button" id="submitEditBtn" class="inline-flex items-center gap-1.5 bg-[#d32f2f] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all">
                    ${window.svgIcon('archive', 'w-3.5 h-3.5')}
                    保存
                </button>
            </div>
        </div>

        <!-- 复制模板抽屉 -->
        <div class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm transition-opacity duration-300"
             id="copyDrawerBackdrop" style="display:none"></div>

        <div class="fixed inset-y-0 right-0 z-[85] w-[480px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="copyDrawer" style="display:none; max-height: 100vh; box-shadow: -20px 0 60px rgba(0,0,0,0.95), -8px 0 30px rgba(0,0,0,0.8), 0 0 1px rgba(255,255,255,0.05);">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0"
                 style="background: linear-gradient(180deg, #1f1f1f 0%, #1a1a1a 100%); border-bottom: 1px solid #333333;">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] flex items-center gap-2.5 uppercase">
                    <span style="width:3px;height:14px;background:#d32f2f;border-radius:1px;display:inline-block;box-shadow: 0 0 8px rgba(211,47,47,0.5);"></span>
                    复制价格模板
                </h5>
                <button type="button" id="closeCopyDrawer"
                        class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all duration-200 group">
                    <svg class="w-4 h-4 transition-transform duration-200 group-hover:scale-110" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>

            <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain" id="copyDrawerContent" style="scrollbar-width: thin; scrollbar-color: #3a3a3a #1a1a1a;">
                <form id="copyForm" class="p-6 space-y-5">
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">基地 <span class="text-[#d32f2f]">*</span></label>
                        <select id="copyLocation" required
                                class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] transition-all rounded">
                            <option value="">请选择基地</option>
                            <option value="大连">大连</option>
                            <option value="芜湖">芜湖</option>
                            <option value="鄂尔多斯">鄂尔多斯</option>
                            <option value="青岛">青岛</option>
                        </select>
                    </div>

                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">源年份<span class="text-[#d32f2f]">*</span></label>
                        <select id="sourceYear" required
                                class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] transition-all rounded">
                            <option value="">请选择源年份</option>
                        </select>
                    </div>

                    <div class="flex items-center justify-center py-1">
                        ${window.svgIcon('chevron-right', 'w-4 h-4 text-[#616161]')}
                    </div>

                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">目标年份 <span class="text-[#d32f2f]">*</span></label>
                        <input type="number" id="targetYear" min="2000" max="2100" required
                               class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded"
                               placeholder="如 2027">
                    </div>

                    <div class="bg-[#0c0c0c] border border-[#1a1a1a] rounded p-3">
                        <p class="text-[11px] text-[#616161]">
                            <span class="text-[#f57f17]">提示（</span>
                            复制仅作用于所选基地，将strong class="text-[#9e9e9e]">覆盖</strong>该基地目标年份的现有数据，请谨慎操作。
                        </p>
                    </div>
                </form>
            </div>

            <div class="px-6 py-4 border-t border-[#262626] flex items-center justify-end gap-2 shrink-0" style="background: linear-gradient(0deg, #1a1a1a 0%, #161616 100%);">
                <button type="button" id="cancelCopyBtn" class="inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-4 py-2 text-[11px] font-medium rounded hover:border-[#9e9e9e] hover:text-white transition-all">
                    取消
                </button>
                <button type="button" id="submitCopyBtn" class="inline-flex items-center gap-1.5 bg-[#d32f2f] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all">
                    ${window.svgIcon('arrows-split', 'w-3.5 h-3.5')}
                    复制
                </button>
            </div>
        </div>

        <!-- 删除确认抽屉 -->
        <div class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm transition-opacity duration-300"
             id="deleteDrawerBackdrop" style="display:none"></div>

        <div class="fixed inset-y-0 right-0 z-[85] w-[380px] bg-[#1a1a1a] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="deleteDrawer" style="display:none; max-height: 100vh; box-shadow: -20px 0 60px rgba(0,0,0,0.95), -8px 0 30px rgba(0,0,0,0.8), 0 0 1px rgba(255,255,255,0.05);">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0"
                 style="background: linear-gradient(180deg, #1f1f1f 0%, #1a1a1a 100%); border-bottom: 1px solid #333333;">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] flex items-center gap-2.5 uppercase">
                    <span style="width:3px;height:14px;background:#c62828;border-radius:1px;display:inline-block;box-shadow: 0 0 8px rgba(198,40,40,0.5);"></span>
                    确认删除
                </h5>
                <button type="button" id="closeDeleteDrawer"
                        class="flex items-center justify-center w-8 h-8 rounded-md text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all duration-200 group">
                    <svg class="w-4 h-4 transition-transform duration-200 group-hover:scale-110" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>

            <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain" id="deleteDrawerContent" style="scrollbar-width: thin; scrollbar-color: #3a3a3a #1a1a1a;">
                <input type="hidden" id="deleteRecordId" value="">
                <div class="p-6">
                    <p class="text-[12px] text-[#9e9e9e] mb-3">
                        确定要删除这条价格记录吗）
                    </p>
                    <p class="text-[11px] text-[#616161]">此操作不可撤销。</p>
                </div>
            </div>

            <div class="px-6 py-4 border-t border-[#262626] flex items-center justify-end gap-2 shrink-0" style="background: linear-gradient(0deg, #1a1a1a 0%, #161616 100%);">
                <button type="button" id="cancelDeleteBtn" class="inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-4 py-2 text-[11px] font-medium rounded hover:border-[#9e9e9e] hover:text-white transition-all">
                    取消
                </button>
                <button type="button" id="confirmDeleteBtn" class="inline-flex items-center gap-1.5 bg-[#c62828] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all">
                    ${window.svgIcon('trash', 'w-3.5 h-3.5')}
                    删除
                </button>
            </div>
        </div>
    `;
}

/**
 * 渲染表格表
 * - 偶数行微调背景色，形成精致斑马纹
 * - 编辑图标：pencil
 */
export function renderTableRows(records) {
    if (!records || !Array.isArray(records) || records.length === 0) {
        return '';
    }
    return records.map((record, idx) => {
        const isEven = idx % 2 === 1; // 偶数行（idx 1,3,5...）略深
        return `
        <tr class="group transition-colors duration-150 cursor-default ${isEven ? '' : ''}"
            data-id="${esc(record.id)}"
            style="${isEven ? 'background: rgba(255,255,255,0.012);' : ''}">
            <td class="px-5 py-2.5 text-[11px] text-[#b0b0b0] whitespace-nowrap font-medium tracking-wide border-b border-[#1d1d1d]">${esc(record.location)}</td>
            <td class="px-5 py-2.5 text-[11px] text-[#686868] whitespace-nowrap font-mono tracking-wide border-b border-[#1d1d1d]">${esc(record.year)}</td>
            <td class="px-5 py-2.5 text-[11px] text-[#b0b0b0] whitespace-nowrap font-medium tracking-wide border-b border-[#1d1d1d]">${esc(record.tonnage)} T</td>
            <td class="px-5 py-2.5 text-[11px] text-right font-mono tabular-nums text-[#d32f2f] whitespace-nowrap tracking-wide border-b border-[#1d1d1d]">
                <span class="shadow-[0_0_8px_rgba(211,47,47,0.2)]">${fmtNum(record.price_per_stroke, 3)}</span>
            </td>
            <td class="px-5 py-2.5 text-center whitespace-nowrap border-b border-[#1d1d1d]">
                <div class="inline-flex items-center justify-center gap-0.5 opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto focus-within:opacity-100 focus-within:pointer-events-auto transition-opacity duration-100">
                    ${(typeof can === 'function' ? can('op:stamping-tonnage:update') : true) ? `
                    <button type="button" class="edit-btn inline-flex items-center justify-center w-7 h-7 rounded-sm text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620] transition-all" title="编辑" aria-label="编辑">
                        ${window.svgIcon('pencil', 'w-3.5 h-3.5')}
                    </button>` : ''}
                    ${(typeof can === 'function' ? can('op:stamping-tonnage:delete') : true) ? `
                    <button type="button" class="delete-btn inline-flex items-center justify-center w-7 h-7 rounded-sm text-[#555555] hover:text-[#ef5350] hover:bg-[#161620] transition-all" title="删除" aria-label="删除">
                        ${window.svgIcon('trash', 'w-3.5 h-3.5')}
                    </button>` : ''}
                </div>
            </td>
        </tr>`;
    }).join('');
}

/**
 * 渲染分页按钮
 */
export function renderPagination(currentPage, totalPages, total) {
    if (totalPages <= 1) {
        return '';
    }

    let buttons = '';

    buttons += `
        <button class="page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] ${currentPage === 1 ? 'text-[#333333] cursor-not-allowed' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'} transition-all duration-150"
                data-page="${currentPage - 1}" ${currentPage === 1 ? 'disabled' : ''}>
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
            </svg>
        </button>
    `;

    const maxVisible = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);
    if (endPage - startPage < maxVisible - 1) {
        startPage = Math.max(1, endPage - maxVisible + 1);
    }

    if (startPage > 1) {
        buttons += `<button class="page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323] transition-all duration-150" data-page="1">1</button>`;
        if (startPage > 2) buttons += `<span class="px-0.5 text-[#333333] leading-6 text-[9px]">—</span>`;
    }

    for (let i = startPage; i <= endPage; i++) {
        const isActive = i === currentPage;
        buttons += `
            <button class="page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] ${isActive ? 'bg-[#d32f2f] text-white shadow-[0_0_8px_rgba(211,47,47,0.25)]' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'} transition-all duration-150"
                    data-page="${i}">${i}</button>
        `;
    }

    if (endPage < totalPages) {
        if (endPage < totalPages - 1) buttons += `<span class="px-0.5 text-[#333333] leading-6 text-[9px]">—</span>`;
        buttons += `<button class="page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323] transition-all duration-150" data-page="${totalPages}">${totalPages}</button>`;
    }

    buttons += `
        <button class="page-btn flex items-center justify-center w-6 h-6 rounded-sm text-[10px] ${currentPage === totalPages ? 'text-[#333333] cursor-not-allowed' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'} transition-all duration-150"
                data-page="${currentPage + 1}" ${currentPage === totalPages ? 'disabled' : ''}>
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
            </svg>
        </button>
    `;

    return buttons;
}
