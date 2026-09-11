/**
 * 牌号分类档案 — HUD 密表 + 抽屉增改
 */

import { pageSizeSelectHtml } from '../../../page-size.js?v=2';

export const CATEGORY_TABS = Object.freeze([
    { id: 'all', label: '全部' },
    { id: '冷轧', label: '1 冷轧' },
    { id: '镀锌', label: '2 镀锌' },
    { id: '酸洗', label: '3 酸洗' },
]);

function canOp(code) {
    return typeof window.can === 'function' ? window.can(code) : true;
}

export function steelGradeCategoryTemplate() {
    const tabHtml = CATEGORY_TABS.map(
        (tab) => `
            <button type="button" data-action="tab" data-tab="${tab.id}"
                    class="sgc-tab px-2.5 py-1 text-[11px] font-mono rounded-md border transition-colors
                           bg-[#1A1A22] border-[#2A2A35] text-[#8E8E93] hover:text-white">
                ${tab.label}
            </button>`
    ).join('');

    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="bg-[#0A0A0C] border border-[#1A1A22] overflow-hidden w-full max-w-full"
                 style="box-shadow: 0 4px 24px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.02);">

                <div class="px-5 pt-4 pb-3.5 border-b border-[#14141A]"
                     style="background: linear-gradient(135deg, #0E0E12 0%, #121218 45%, #0C0C10 100%);">
                    <div class="flex items-start justify-between gap-4">
                        <div>
                            <h2 class="text-[13px] font-semibold text-[#F0F0F2] tracking-wide">牌号分类</h2>
                            <p class="mt-1 text-[11px] text-[#555555]">一个牌号一行，挂冷轧 / 镀锌 / 酸洗</p>
                        </div>
                        <div class="flex items-center gap-2 shrink-0">
                            <button type="button" id="sgcExportBtn"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#8E8E93] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded hover:border-[#FF1E27]/50 hover:text-[#FF1E27] transition-all">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                导出 Excel
                            </button>
                            <button type="button" id="sgcAddBtn"
                                    class="inline-flex items-center gap-1.5 bg-[#FF1E27] text-white px-3 py-1.5 text-[11px] font-semibold rounded hover:bg-[#d32f2f] transition-all">
                                ${window.svgIcon('plus', 'w-3 h-3')}
                                新增
                            </button>
                        </div>
                    </div>
                    <div class="mt-3 flex flex-wrap items-center gap-2" id="sgcTabBar">
                        ${tabHtml}
                    </div>
                    <div class="mt-3 relative max-w-xs">
                        <span class="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none text-[#555555]">
                            ${window.svgIcon('search', 'w-3.5 h-3.5')}
                        </span>
                        <input type="text" id="sgcGradeFilter" placeholder="搜索牌号…"
                               class="w-full h-8 pl-8 pr-3 text-[11px] font-mono bg-[#0A0A0E] border border-[#2A2A35] text-[#F0F0F2] placeholder:text-[#555555] focus:outline-none focus:border-[#FF1E27] rounded-sm">
                    </div>
                </div>

                <div class="overflow-x-auto bg-[#0A0A0E] brabus-bg-grid">
                    <table class="w-full table-fixed bg-transparent border-collapse" style="min-width: 760px;">
                        <colgroup>
                            <col style="width: 8px;">
                            <col style="width: 26%;">
                            <col style="width: 16%;">
                            <col style="width: 28%;">
                            <col style="width: 16%;">
                            <col style="width: 88px;">
                        </colgroup>
                        <thead>
                            <tr class="border-b border-[#17171C] bg-[#0B0B0D]/95">
                                <th class="p-0" aria-hidden="true"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">牌号</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-[#555555]">大类</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-[#555555]">备注</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-[#555555]">更新</th>
                                <th class="px-1 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">操作</th>
                            </tr>
                        </thead>
                        <tbody id="sgcTableBody"></tbody>
                    </table>
                </div>

                <div id="sgcEmptyState" class="hidden flex flex-col items-center justify-center py-16 text-center bg-[#0A0A0E]">
                    <div class="text-[#555555] mb-2">${window.svgIcon('inbox')}</div>
                    <p class="text-[12px] text-[#8E8E93] mb-1">暂无牌号</p>
                    <p class="text-[11px] text-[#555555]">请在本页手工新增；工艺或基价导入不会自动补档</p>
                </div>
                <div id="sgcLoadingState" class="hidden flex flex-col items-center justify-center py-16 gap-2 bg-[#0A0A0E]">
                    <div class="w-5 h-5 border-2 border-[#2c2c2c] border-t-[#FF1E27] rounded-full animate-spin"></div>
                    <span class="text-[11px] text-[#555555]">加载中</span>
                </div>

                <div class="flex items-center justify-between px-5 py-2.5 border-t border-[#14141A] bg-[#0A0A0E]">
                    <div class="flex items-center gap-3">
                        <span id="sgcTotalCount" class="text-[10px] font-mono text-[#555555]"></span>
                        ${pageSizeSelectHtml('sgcPageSize')}
                    </div>
                    <div class="flex items-center gap-0.5" id="sgcPaginationBtns"></div>
                </div>
            </div>
        </div>

        <div class="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm transition-opacity" id="sgcEditBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[420px] bg-[#121215] border-l border-[#2c2c2c]
                    transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="sgcEditDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-[#2c2c2c] bg-[#16161a] shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-[#FF1E27]"></span>
                    <h5 class="text-xs font-semibold text-white tracking-wider" id="sgcEditTitle">新增牌号</h5>
                </div>
                <button type="button" id="sgcCloseEdit" class="text-[#616161] hover:text-white w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-5">
                <form id="sgcEditForm" class="space-y-4">
                    <input type="hidden" id="sgcEditId" value="">
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">牌号 <span class="text-[#FF1E27]">*</span></label>
                        <input type="text" id="sgcEditGrade" required maxlength="50"
                               class="w-full h-8 px-3 text-xs font-mono bg-[#0a0a0c] border border-[#2c2c2c] text-white placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252]"
                               placeholder="如 DC01、DC51D+Z" autocomplete="off">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">大类 <span class="text-[#FF1E27]">*</span></label>
                        <select id="sgcEditCategory" required
                                class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-[#9e9e9e] appearance-none cursor-pointer focus:outline-none focus:border-[#ff5252]">
                            <option value="">请选择</option>
                            <option value="冷轧">冷轧</option>
                            <option value="镀锌">镀锌</option>
                            <option value="酸洗">酸洗</option>
                        </select>
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">备注</label>
                        <input type="text" id="sgcEditRemark" maxlength="200"
                               class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252]"
                               placeholder="可选" autocomplete="off">
                    </div>
                </form>
            </div>
            <div class="px-5 py-3 border-t border-[#2c2c2c] flex items-center justify-end gap-2 bg-[#16161a] shrink-0">
                <button type="button" id="sgcCancelEdit"
                        class="px-4 py-1.5 text-xs text-[#9e9e9e] hover:text-white border border-[#2c2c2c] hover:bg-[#262626] transition-all">取消</button>
                <button type="button" id="sgcSubmitEdit"
                        class="bg-[#FF1E27] hover:bg-[#d32f2f] text-white px-5 py-1.5 text-xs font-semibold transition-all">保存</button>
            </div>
        </div>

        <div class="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm" id="sgcDeleteBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[380px] bg-[#1a1a1a] border-l border-[#2a2a2a]
                    transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="sgcDeleteDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between shrink-0 border-b border-[#333333]">
                <h5 class="text-[11px] font-semibold tracking-wider text-[#b0b0b0] flex items-center gap-2.5">
                    <span class="w-[3px] h-3.5 bg-[#c62828] inline-block"></span>
                    确认删除
                </h5>
                <button type="button" id="sgcCloseDelete" class="w-8 h-8 text-[#707070] hover:text-white">✕</button>
            </div>
            <div class="flex-1 p-6">
                <input type="hidden" id="sgcDeleteId" value="">
                <p class="text-[12px] text-[#9e9e9e] mb-2">确定删除牌号 <span id="sgcDeleteGrade" class="font-mono text-white"></span>？</p>
                <p class="text-[11px] text-[#616161]">只删档案行，不改零件和基价。</p>
            </div>
            <div class="px-6 py-4 border-t border-[#262626] flex items-center justify-end gap-2 shrink-0">
                <button type="button" id="sgcCancelDelete"
                        class="inline-flex items-center bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-4 py-2 text-[11px] font-medium rounded hover:text-white">取消</button>
                <button type="button" id="sgcConfirmDelete"
                        class="inline-flex items-center bg-[#c62828] text-white px-4 py-2 text-[11px] font-semibold rounded hover:bg-[#b71c1c]">删除</button>
            </div>
        </div>
    `;
}

export function renderTableRows(records) {
    if (!records || !records.length) return '';
    const canUpdate = canOp('op:steel-grade-category:update');
    const canDelete = canOp('op:steel-grade-category:delete');

    return records
        .map((record) => {
            const updated = formatDateTime(record.updated_at);
            return `
        <tr class="group relative font-mono text-[11px] border-b border-[#141418] hover:bg-[#161620] transition-colors duration-100">
            <td class="p-0 relative">
                <div class="absolute left-0 top-0 bottom-0 w-[2px] bg-[#FF1E27] opacity-0 group-hover:opacity-70 transition-opacity"></div>
            </td>
            <td class="px-2 py-2 overflow-hidden">
                <div class="text-[14px] font-bold text-[#F0F0F2] truncate" title="${esc(record.grade)}">${esc(record.grade)}</div>
            </td>
            <td class="px-2 py-2 overflow-hidden">
                <span class="text-[#C8C8D0]">${esc(record.category_name)}</span>
            </td>
            <td class="px-2 py-2 text-[10px] text-[#555555] overflow-hidden truncate" title="${esc(record.remark || '')}">${esc(record.remark || '—')}</td>
            <td class="px-2 py-2 text-[9px] text-[#3A3A42] whitespace-nowrap overflow-hidden">
                <div>${esc(record.updated_by || '—')}</div>
                <div>${esc(updated)}</div>
            </td>
            <td class="px-1 py-2 text-center">
                <div class="inline-flex items-center justify-center gap-0.5 opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto focus-within:opacity-100 focus-within:pointer-events-auto transition-opacity duration-100">
                    ${canUpdate ? `
                    <button type="button" data-action="edit" data-id="${esc(record.id)}"
                            class="inline-flex items-center justify-center w-7 h-7 rounded-sm text-[#555555] hover:text-[#C8C8D0] hover:bg-[#161620] transition-all"
                            title="编辑" aria-label="编辑">
                        ${window.svgIcon('pencil', 'w-3.5 h-3.5')}
                    </button>` : ''}
                    ${canDelete ? `
                    <button type="button" data-action="delete" data-id="${esc(record.id)}" data-grade="${esc(record.grade)}"
                            class="inline-flex items-center justify-center w-7 h-7 rounded-sm text-[#555555] hover:text-[#ef5350] hover:bg-[#161620] transition-all"
                            title="删除" aria-label="删除">
                        ${window.svgIcon('trash', 'w-3.5 h-3.5')}
                    </button>` : ''}
                </div>
            </td>
        </tr>`;
        })
        .join('');
}

export function renderPagination(currentPage, totalPages) {
    if (totalPages <= 1) return '';
    let buttons = `
        <button type="button" class="page-btn flex items-center justify-center w-6 h-6 text-[10px] ${currentPage === 1 ? 'text-[#333333] cursor-not-allowed' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'} transition-all"
                data-page="${currentPage - 1}" ${currentPage === 1 ? 'disabled' : ''}>
            ${window.svgIcon('chevron-left', 'w-3 h-3')}
        </button>`;
    const maxVisible = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);
    if (endPage - startPage < maxVisible - 1) startPage = Math.max(1, endPage - maxVisible + 1);
    if (startPage > 1) {
        buttons += `<button type="button" class="page-btn flex items-center justify-center w-6 h-6 text-[10px] text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]" data-page="1">1</button>`;
        if (startPage > 2) buttons += `<span class="px-0.5 text-[#333333] text-[9px]">…</span>`;
    }
    for (let i = startPage; i <= endPage; i += 1) {
        const isActive = i === currentPage;
        buttons += `<button type="button" class="page-btn flex items-center justify-center w-6 h-6 text-[10px] ${isActive ? 'bg-[#FF1E27] text-white' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'}" data-page="${i}">${i}</button>`;
    }
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) buttons += `<span class="px-0.5 text-[#333333] text-[9px]">…</span>`;
        buttons += `<button type="button" class="page-btn flex items-center justify-center w-6 h-6 text-[10px] text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]" data-page="${totalPages}">${totalPages}</button>`;
    }
    buttons += `
        <button type="button" class="page-btn flex items-center justify-center w-6 h-6 text-[10px] ${currentPage === totalPages ? 'text-[#333333] cursor-not-allowed' : 'text-[#585858] hover:text-[#c0c0c0] hover:bg-[#232323]'}"
                data-page="${currentPage + 1}" ${currentPage === totalPages ? 'disabled' : ''}>
            ${window.svgIcon('chevron-right', 'w-3 h-3')}
        </button>`;
    return buttons;
}

export function syncTabStyles(activeTab) {
    document.querySelectorAll('.sgc-tab').forEach((btn) => {
        const isActive = btn.getAttribute('data-tab') === activeTab;
        btn.className = isActive
            ? 'sgc-tab px-2.5 py-1 text-[11px] font-mono rounded-md border transition-colors bg-[#1A080A] border-[#FF1E27]/50 text-white'
            : 'sgc-tab px-2.5 py-1 text-[11px] font-mono rounded-md border transition-colors bg-[#1A1A22] border-[#2A2A35] text-[#8E8E93] hover:text-white';
    });
}

function formatDateTime(value) {
    if (!value) return '—';
    const text = String(value);
    if (text.length >= 16) return text.slice(0, 16).replace('T', ' ');
    return text;
}
