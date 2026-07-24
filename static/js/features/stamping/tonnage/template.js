/**
 * Tonnage Price Template
 * 吨位价格维护页面 — Brabus Carbon & Precision Dark
 */

export function tonnagePriceTemplate() {
    return `
        <div class="space-y-4">
            <!-- 页面标题区 -->
            <div class="flex items-center justify-between mb-6">
                <div class="flex items-center gap-3">
                    <div class="w-[2px] h-5 bg-[#d32f2f] rounded-[1px] shadow-[0_0_6px_rgba(211,47,47,0.25)]"></div>
                    <h2 class="text-[13px] font-semibold text-[#ffffff] tracking-wide">压机吨位单冲次价格</h2>
                </div>
                <div class="flex items-center gap-2">
                    <button id="btnCopyTemplate" class="inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-3 py-1.5 text-[11px] font-medium rounded hover:border-[#d32f2f] hover:text-[#d32f2f] transition-all">
                        ${window.svgIcon('copy', 'w-3.5 h-3.5')}
                        复制模板
                    </button>
                    <button id="btnAddTonnagePrice" class="inline-flex items-center gap-1.5 bg-[#d32f2f] text-white px-3 py-1.5 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all">
                        ${window.svgIcon('plus', 'w-3.5 h-3.5')}
                        新增价格
                    </button>
                </div>
            </div>

            <!-- 筛选区 -->
            <div class="bg-[#1e1e1e] border border-[#2c2c2c] p-4">
                <div class="flex items-end gap-4">
                    <div class="flex-1">
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">选择年份</label>
                        <select id="yearFilter" class="h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] transition-all rounded w-full min-w-[140px]">
                            <option value="">全部年份</option>
                        </select>
                    </div>
                    <button id="btnFilter" class="inline-flex items-center gap-1.5 bg-[#262626] text-[#9e9e9e] border border-[#2c2c2c] px-4 py-2 text-[11px] font-medium rounded hover:border-[#d32f2f] hover:text-[#d32f2f] transition-all">
                        ${window.svgIcon('search', 'w-3.5 h-3.5')}
                        查询
                    </button>
                </div>
            </div>

            <!-- 数据表格 -->
            <div class="bg-[#1e1e1e] border border-[#2c2c2c]">
                <div class="overflow-x-auto">
                    <table class="w-full">
                        <thead>
                            <tr class="bg-[#0a0a0a] border-b border-[#2c2c2c]">
                                <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161] whitespace-nowrap">年份</th>
                                <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161] whitespace-nowrap">压机吨位 (T)</th>
                                <th class="px-4 py-3 text-right text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161] whitespace-nowrap">单冲次价格 (元)</th>
                                <th class="px-4 py-3 text-center text-[10px] font-semibold uppercase tracking-[0.12em] text-[#616161] whitespace-nowrap w-24">操作</th>
                            </tr>
                        </thead>
                        <tbody id="tonnagePriceTableBody" class="divide-y divide-[#222222]">
                            <!-- 动态渲染 -->
                        </tbody>
                    </table>
                </div>

                <!-- 空状态 -->
                <div id="emptyState" class="hidden flex flex-col items-center justify-center py-14">
                    <div class="w-10 h-10 bg-[#262626] flex items-center justify-center mb-3">
                        ${window.svgIcon('clipboard-list', 'w-5 h-5 text-[#616161]')}
                    </div>
                    <h5 class="text-xs font-medium text-[#9e9e9e] mb-1">暂无数据</h5>
                    <p class="text-[11px] text-[#616161]">点击"新增价格"按钮添加记录</p>
                </div>

                <!-- 加载中 -->
                <div id="loadingState" class="hidden flex items-center justify-center py-14">
                    <div class="w-6 h-6 border-2 border-[#2c2c2c] border-t-[#d32f2f] rounded-full animate-spin"></div>
                </div>
            </div>

            <!-- 分页 -->
            <div id="paginationContainer" class="flex items-center justify-between text-[11px] text-[#616161]">
                <span id="totalCount">共 0 条</span>
                <div class="flex items-center gap-1" id="paginationBtns">
                    <!-- 动态渲染 -->
                </div>
            </div>
        </div>

        <!-- 编辑/新增弹窗 -->
        <div id="editModal" class="hidden fixed inset-0 z-50 flex items-center justify-center">
            <div class="fixed inset-0 bg-black/70 backdrop-blur-sm" id="editModalBackdrop"></div>
            <div class="relative z-10 w-[400px] bg-[#1a1a1a] border border-[#2a2a2a] rounded p-6 shadow-[0_0_40px_rgba(0,0,0,0.6)]">
                <div class="flex items-center justify-between mb-5">
                    <h3 id="editModalTitle" class="text-[11px] font-semibold text-[#b0b0b0] uppercase tracking-wider flex items-center gap-2">
                        <span class="w-[2px] h-4 bg-[#d32f2f] rounded-[1px] shadow-[0_0_6px_rgba(211,47,47,0.3)]"></span>
                        编辑价格
                    </h3>
                    <button id="closeEditModal" class="w-7 h-7 flex items-center justify-center rounded text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all">
                        ${window.svgIcon('x-lg', 'w-4 h-4')}
                    </button>
                </div>

                <form id="editForm" class="space-y-4">
                    <input type="hidden" id="editRecordId" value="">

                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">年份 <span class="text-[#d32f2f]">*</span></label>
                        <input type="number" id="editYear" min="2000" max="2100" required
                               class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded"
                               placeholder="如: 2026">
                    </div>

                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">压机吨位 (T) <span class="text-[#d32f2f]">*</span></label>
                        <input type="number" id="editTonnage" min="1" required
                               class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded"
                               placeholder="如: 800">
                    </div>

                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">单冲次价格 (元) <span class="text-[#d32f2f]">*</span></label>
                        <input type="number" id="editPrice" min="0" step="0.0001" required
                               class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded"
                               placeholder="如: 0.8500">
                    </div>

                    <div class="flex items-center justify-end gap-2 pt-2">
                        <button type="button" id="cancelEditBtn" class="inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-4 py-2 text-[11px] font-medium rounded hover:border-[#9e9e9e] hover:text-white transition-all">
                            取消
                        </button>
                        <button type="submit" class="inline-flex items-center gap-1.5 bg-[#d32f2f] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all">
                            ${window.svgIcon('check', 'w-3.5 h-3.5')}
                            保存
                        </button>
                    </div>
                </form>
            </div>
        </div>

        <!-- 复制模板弹窗 -->
        <div id="copyModal" class="hidden fixed inset-0 z-50 flex items-center justify-center">
            <div class="fixed inset-0 bg-black/70 backdrop-blur-sm" id="copyModalBackdrop"></div>
            <div class="relative z-10 w-[400px] bg-[#1a1a1a] border border-[#2a2a2a] rounded p-6 shadow-[0_0_40px_rgba(0,0,0,0.6)]">
                <div class="flex items-center justify-between mb-5">
                    <h3 class="text-[11px] font-semibold text-[#b0b0b0] uppercase tracking-wider flex items-center gap-2">
                        <span class="w-[2px] h-4 bg-[#d32f2f] rounded-[1px] shadow-[0_0_6px_rgba(211,47,47,0.3)]"></span>
                        复制价格模板
                    </h3>
                    <button id="closeCopyModal" class="w-7 h-7 flex items-center justify-center rounded text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all">
                        ${window.svgIcon('x-lg', 'w-4 h-4')}
                    </button>
                </div>

                <form id="copyForm" class="space-y-4">
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">源年份 <span class="text-[#d32f2f]">*</span></label>
                        <select id="sourceYear" required
                                class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#9e9e9e] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] transition-all rounded">
                            <option value="">请选择源年份</option>
                        </select>
                    </div>

                    <div class="flex items-center justify-center">
                        ${window.svgIcon('chevron-right', 'w-4 h-4 text-[#616161]')}
                    </div>

                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] uppercase tracking-[0.1em] mb-1.5 block">目标年份 <span class="text-[#d32f2f]">*</span></label>
                        <input type="number" id="targetYear" min="2000" max="2100" required
                               class="w-full h-9 px-3 text-xs bg-[#0a0a0a] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-all rounded"
                               placeholder="如: 2027">
                    </div>

                    <div class="bg-[#0c0c0c] border border-[#1a1a1a] rounded p-3">
                        <p class="text-[11px] text-[#616161]">
                            <span class="text-[#f57f17]">提示：</span>
                            复制操作将<strong class="text-[#9e9e9e]">覆盖</strong>目标年份的现有数据，请谨慎操作。
                        </p>
                    </div>

                    <div class="flex items-center justify-end gap-2 pt-2">
                        <button type="button" id="cancelCopyBtn" class="inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-4 py-2 text-[11px] font-medium rounded hover:border-[#9e9e9e] hover:text-white transition-all">
                            取消
                        </button>
                        <button type="submit" class="inline-flex items-center gap-1.5 bg-[#d32f2f] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all">
                            ${window.svgIcon('copy', 'w-3.5 h-3.5')}
                            复制
                        </button>
                    </div>
                </form>
            </div>
        </div>

        <!-- 删除确认弹窗 -->
        <div id="deleteModal" class="hidden fixed inset-0 z-50 flex items-center justify-center">
            <div class="fixed inset-0 bg-black/70 backdrop-blur-sm" id="deleteModalBackdrop"></div>
            <div class="relative z-10 w-[360px] bg-[#1a1a1a] border border-[#2a2a2a] rounded p-6 shadow-[0_0_40px_rgba(0,0,0,0.6)]">
                <div class="flex items-center justify-between mb-5">
                    <h3 class="text-[11px] font-semibold text-[#b0b0b0] uppercase tracking-wider flex items-center gap-2">
                        <span class="w-[2px] h-4 bg-[#c62828] rounded-[1px] shadow-[0_0_6px_rgba(198,40,40,0.3)]"></span>
                        确认删除
                    </h3>
                    <button id="closeDeleteModal" class="w-7 h-7 flex items-center justify-center rounded text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all">
                        ${window.svgIcon('x-lg', 'w-4 h-4')}
                    </button>
                </div>

                <input type="hidden" id="deleteRecordId" value="">

                <p class="text-[12px] text-[#9e9e9e] mb-5">
                    确定要删除这条价格记录吗？<br>
                    <span class="text-[#616161]">此操作不可撤销。</span>
                </p>

                <div class="flex items-center justify-end gap-2">
                    <button id="cancelDeleteBtn" class="inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-4 py-2 text-[11px] font-medium rounded hover:border-[#9e9e9e] hover:text-white transition-all">
                        取消
                    </button>
                    <button id="confirmDeleteBtn" class="inline-flex items-center gap-1.5 bg-[#c62828] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c] transition-all">
                        ${window.svgIcon('trash', 'w-3.5 h-3.5')}
                        删除
                    </button>
                </div>
            </div>
        </div>
    `;
}

/**
 * 渲染表格行
 */
export function renderTableRows(records) {
    if (!records || records.length === 0) {
        return '';
    }
    return records.map(record => `
        <tr class="hover:bg-[#ffffff]/[0.02] transition-colors" data-id="${esc(record.id)}">
            <td class="px-4 py-3 text-xs text-[#9e9e9e] whitespace-nowrap">${esc(record.year)}</td>
            <td class="px-4 py-3 text-xs text-[#ffffff] whitespace-nowrap font-medium">${esc(record.tonnage)} T</td>
            <td class="px-4 py-3 text-xs text-right font-mono tabular-nums text-[#d32f2f] whitespace-nowrap">
                <span class="shadow-[0_0_8px_rgba(211,47,47,0.2)]">${fmtNum(record.price_per_stroke, 4)}</span>
            </td>
            <td class="px-4 py-3 text-center whitespace-nowrap">
                <div class="flex items-center justify-center gap-1">
                    <button class="edit-btn p-1.5 rounded text-[#616161] hover:text-[#d32f2f] hover:bg-[#d32f2f]/10 transition-all" title="编辑">
                        ${window.svgIcon('ruler', 'w-3.5 h-3.5')}
                    </button>
                    <button class="delete-btn p-1.5 rounded text-[#616161] hover:text-[#c62828] hover:bg-[#c62828]/10 transition-all" title="删除">
                        ${window.svgIcon('trash', 'w-3.5 h-3.5')}
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

/**
 * 渲染分页按钮
 */
export function renderPagination(currentPage, totalPages, total) {
    if (totalPages <= 1) {
        return '';
    }

    let buttons = '';

    // 上一页
    buttons += `
        <button class="page-btn px-2.5 py-1.5 rounded text-[11px] ${currentPage === 1 ? 'text-[#616161] cursor-not-allowed' : 'text-[#9e9e9e] hover:text-[#ffffff] hover:bg-[#262626]'} transition-all"
                data-page="${currentPage - 1}" ${currentPage === 1 ? 'disabled' : ''}>
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
            </svg>
        </button>
    `;

    // 页码
    const maxVisible = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);

    if (endPage - startPage < maxVisible - 1) {
        startPage = Math.max(1, endPage - maxVisible + 1);
    }

    if (startPage > 1) {
        buttons += `<button class="page-btn px-2.5 py-1.5 rounded text-[11px] text-[#9e9e9e] hover:text-[#ffffff] hover:bg-[#262626] transition-all" data-page="1">1</button>`;
        if (startPage > 2) {
            buttons += `<span class="px-1 text-[#616161]">...</span>`;
        }
    }

    for (let i = startPage; i <= endPage; i++) {
        const isActive = i === currentPage;
        buttons += `
            <button class="page-btn px-2.5 py-1.5 rounded text-[11px] ${isActive ? 'bg-[#d32f2f] text-white' : 'text-[#9e9e9e] hover:text-[#ffffff] hover:bg-[#262626]'} transition-all"
                    data-page="${i}">${i}</button>
        `;
    }

    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            buttons += `<span class="px-1 text-[#616161]">...</span>`;
        }
        buttons += `<button class="page-btn px-2.5 py-1.5 rounded text-[11px] text-[#9e9e9e] hover:text-[#ffffff] hover:bg-[#262626] transition-all" data-page="${totalPages}">${totalPages}</button>`;
    }

    // 下一页
    buttons += `
        <button class="page-btn px-2.5 py-1.5 rounded text-[11px] ${currentPage === totalPages ? 'text-[#616161] cursor-not-allowed' : 'text-[#9e9e9e] hover:text-[#ffffff] hover:bg-[#262626]'} transition-all"
                data-page="${currentPage + 1}" ${currentPage === totalPages ? 'disabled' : ''}>
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
            </svg>
        </button>
    `;

    return buttons;
}
