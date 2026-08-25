/**
 * Operation Logs Template
 * 操作日志 — Brabus Carbon & Precision Dark
 */

export function logsTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">

            <div class="bg-[#1e1e1e] border border-[#2c2c2c] overflow-hidden w-full max-w-full"
                 style="box-shadow: 0 2px 12px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.03);">

                <div class="flex items-center justify-between px-5 py-3.5 border-b border-[#222222]"
                     style="background: linear-gradient(90deg, #1c1c1c 0%, #1e1e1e 60%);">
                    <div class="flex items-center gap-3">
                        <div class="w-[2px] h-4 bg-[#d32f2f] rounded-[1px] shadow-[0_0_6px_rgba(211,47,47,0.3)]"></div>
                        <h2 class="text-[12px] font-semibold text-[#c8c8c8] tracking-wide">操作日志</h2>
                    </div>
                    <div class="flex items-center gap-2">
                        <button id="btnExportLogs"
                                class="inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-3 py-1.5 text-[11px] font-medium rounded-sm hover:border-[#d32f2f] hover:text-[#d32f2f] transition-all duration-150">
                            ${window.svgIcon('download', 'w-3 h-3')}
                            导出
                        </button>
                    </div>
                </div>

                <div class="flex items-center justify-between px-5 py-2.5 border-b border-[#1e1e1e]"
                     style="background: linear-gradient(180deg, #181818 0%, #161616 100%);">
                    <div class="flex items-center gap-3 flex-wrap">
                        <div class="flex items-center gap-1.5">
                            <label class="text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em] whitespace-nowrap">账号</label>
                            <input type="text" id="filterUsername" placeholder="模糊搜索"
                                   class="w-28 h-7 px-2.5 text-[11px] bg-[#0d0d0d] border border-[#272727] text-[#909090] placeholder:text-[#484848] focus:outline-none focus:border-[#ff5252] transition-all rounded-sm">
                        </div>
                        <div class="flex items-center gap-1.5">
                            <label class="text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em] whitespace-nowrap">模块</label>
                            <select id="filterModule"
                                    class="w-32 h-7 pl-2.5 pr-7 text-[11px] bg-[#0d0d0d] border border-[#272727] text-[#909090] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] transition-all rounded-sm">
                                <option value="">全部</option>
                            </select>
                        </div>
                        <div class="flex items-center gap-1.5">
                            <label class="text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em] whitespace-nowrap">动作</label>
                            <select id="filterAction"
                                    class="w-28 h-7 pl-2.5 pr-7 text-[11px] bg-[#0d0d0d] border border-[#272727] text-[#909090] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] transition-all rounded-sm">
                                <option value="">全部</option>
                            </select>
                        </div>
                        <div class="flex items-center gap-1.5">
                            <label class="text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em] whitespace-nowrap">方法</label>
                            <select id="filterMethod"
                                    class="w-24 h-7 pl-2.5 pr-7 text-[11px] bg-[#0d0d0d] border border-[#272727] text-[#909090] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] transition-all rounded-sm">
                                <option value="">全部</option>
                            </select>
                        </div>
                        <div class="flex items-center gap-1.5">
                            <label class="text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em] whitespace-nowrap">结果</label>
                            <select id="filterSuccess"
                                    class="w-24 h-7 pl-2.5 pr-7 text-[11px] bg-[#0d0d0d] border border-[#272727] text-[#909090] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252] transition-all rounded-sm">
                                <option value="">全部</option>
                                <option value="true">成功</option>
                                <option value="false">失败</option>
                            </select>
                        </div>
                        <div class="flex items-center gap-1.5">
                            <label class="text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em] whitespace-nowrap">起</label>
                            <input type="datetime-local" id="filterCreatedFrom"
                                   class="h-7 px-2 text-[11px] bg-[#0d0d0d] border border-[#272727] text-[#909090] focus:outline-none focus:border-[#ff5252] transition-all rounded-sm">
                        </div>
                        <div class="flex items-center gap-1.5">
                            <label class="text-[9px] font-semibold text-[#484848] uppercase tracking-[0.12em] whitespace-nowrap">止</label>
                            <input type="datetime-local" id="filterCreatedTo"
                                   class="h-7 px-2 text-[11px] bg-[#0d0d0d] border border-[#272727] text-[#909090] focus:outline-none focus:border-[#ff5252] transition-all rounded-sm">
                        </div>
                        <button id="btnFilter"
                                class="inline-flex items-center gap-1 h-7 px-3 text-[11px] font-medium bg-[#242424] text-[#787878] border border-[#272727] rounded-sm hover:border-[#d32f2f] hover:text-[#d32f2f] transition-all duration-150">
                            ${window.svgIcon('search', 'w-3 h-3')}
                            查询
                        </button>
                        <button id="btnResetFilter"
                                class="inline-flex items-center h-7 px-3 text-[11px] font-medium text-[#616161] hover:text-[#9e9e9e] transition-all duration-150">
                            重置
                        </button>
                    </div>
                </div>

                <div class="overflow-x-auto">
                    <table class="w-full">
                        <thead>
                            <tr style="background: linear-gradient(180deg, #111111 0%, #0e0e0e 100%); border-bottom: 1px solid #222222;">
                                <th class="px-4 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">时间</th>
                                <th class="px-4 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">操作人</th>
                                <th class="px-4 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">模块</th>
                                <th class="px-4 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">动作</th>
                                <th class="px-4 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">摘要</th>
                                <th class="px-4 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">方法</th>
                                <th class="px-4 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">路径</th>
                                <th class="px-4 py-2.5 text-center text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">状态</th>
                                <th class="px-4 py-2.5 text-left text-[9px] font-semibold uppercase tracking-[0.15em] text-[#484848] whitespace-nowrap">IP</th>
                            </tr>
                        </thead>
                        <tbody id="logsTableBody" class="divide-y divide-[#1d1d1d]">
                        </tbody>
                    </table>
                </div>

                <div class="flex items-center justify-between px-5 py-2 border-t border-[#1e1e1e] bg-[#141414]" id="paginationContainer">
                    <span id="totalCountPagination" class="text-[10px] text-[#484848]"></span>
                    <div class="flex items-center gap-0.5" id="paginationBtns"></div>
                </div>

                <div id="emptyState" class="hidden flex flex-col items-center justify-center py-10">
                    <div class="w-8 h-8 flex items-center justify-center mb-3 rounded-sm" style="background:#141414; border: 1px solid #222222;">
                        ${window.svgIcon('clipboard-list', 'w-4 h-4 text-[#3a3a3a]')}
                    </div>
                    <h5 class="text-[11px] font-medium text-[#555555] mb-1">暂无操作日志</h5>
                    <p class="text-[10px] text-[#3a3a3a]">写操作与导出成功后将出现在此</p>
                </div>

                <div id="loadingState" class="hidden flex items-center justify-center py-10">
                    <div class="w-4 h-4 border border-[#252525] border-t-[#d32f2f] rounded-full animate-spin"></div>
                </div>
            </div>
        </div>
    `;
}

function formatDateTime(value) {
    if (!value) return '-';
    return String(value).replace('T', ' ').slice(0, 19);
}

/**
 * @param {Array} records
 * @returns {string}
 */
export function renderTableRows(records) {
    if (!records || !Array.isArray(records) || records.length === 0) {
        return '';
    }
    return records.map((record, idx) => {
        const isEven = idx % 2 === 1;
        const successBadge = record.success
            ? `<span class="inline-flex items-center px-2 py-0.5 text-[10px] font-semibold bg-[#2e7d32]/20 text-[#4caf50] rounded">${esc(record.status_code)}</span>`
            : `<span class="inline-flex items-center px-2 py-0.5 text-[10px] font-semibold bg-[#c62828]/20 text-[#ef5350] rounded">${esc(record.status_code)}</span>`;
        const operator = record.operator_name || record.username || '-';
        const operatorSub = record.username && record.operator_name && record.username !== record.operator_name
            ? `<div class="text-[10px] text-[#616161] font-mono">${esc(record.username)}</div>`
            : '';

        return `
            <tr class="${isEven ? 'bg-[#1a1a1a]/40' : ''} hover:bg-[#ffffff]/[0.02] transition-colors">
                <td class="px-4 py-2.5 text-[11px] text-[#9e9e9e] font-mono whitespace-nowrap">${esc(formatDateTime(record.created_at))}</td>
                <td class="px-4 py-2.5 text-[11px] text-[#c8c8c8]">
                    <div>${esc(operator)}</div>
                    ${operatorSub}
                </td>
                <td class="px-4 py-2.5 text-[11px] text-[#9e9e9e] whitespace-nowrap">${esc(record.module)}</td>
                <td class="px-4 py-2.5 text-[11px] text-[#9e9e9e] whitespace-nowrap">${esc(record.action)}</td>
                <td class="px-4 py-2.5 text-[11px] text-[#c8c8c8] max-w-[220px] truncate" title="${esc(record.summary)}">${esc(record.summary)}</td>
                <td class="px-4 py-2.5 text-[11px] text-[#9e9e9e] font-mono whitespace-nowrap">${esc(record.method)}</td>
                <td class="px-4 py-2.5 text-[11px] text-[#787878] font-mono max-w-[260px] truncate" title="${esc(record.path)}">${esc(record.path)}</td>
                <td class="px-4 py-2.5 text-center">${successBadge}</td>
                <td class="px-4 py-2.5 text-[11px] text-[#616161] font-mono whitespace-nowrap">${esc(record.client_ip)}</td>
            </tr>
        `;
    }).join('');
}

/**
 * @param {number} currentPage
 * @param {number} totalPages
 * @returns {string}
 */
export function renderPagination(currentPage, totalPages) {
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
        if (startPage > 2) buttons += `<span class="px-0.5 text-[#333333] leading-6 text-[9px]">…</span>`;
    }

    for (let i = startPage; i <= endPage; i++) {
        const isActive = i === currentPage;
        buttons += `
            <button class="page-btn flex items-center justify-center min-w-[24px] h-6 px-1.5 rounded-sm text-[10px] ${isActive ? 'bg-[#d32f2f] text-white' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'} transition-all duration-150"
                    data-page="${i}">${i}</button>
        `;
    }

    if (endPage < totalPages) {
        if (endPage < totalPages - 1) buttons += `<span class="px-0.5 text-[#333333] leading-6 text-[9px]">…</span>`;
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
