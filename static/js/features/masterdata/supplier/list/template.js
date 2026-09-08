/**
 * 供应商一览 — 基地风格面板 + 表 + 抽屉；有搜索 / 分页 / 导出，无删除
 */

import { pageSizeSelectHtml } from '../../../../page-size.js?v=2';

export function supplierListTemplate() {
    return `
        <div class="space-y-3 w-full max-w-full text-[#9e9e9e]">
            <div class="bg-[#121215] border border-[#2c2c2c]">
                <div class="p-3 border-b border-[#222222] flex flex-wrap items-center justify-between gap-3 bg-[#16161a]">
                    <div class="min-w-0">
                        <div class="text-xs font-semibold text-white tracking-wider">供应商</div>
                        <p class="text-[11px] text-[#616161] mt-0.5">全称是规范名，与现网工艺确认一致、给下游存；缩写只给人看；别名吸收表头乱写。创建后三者不改。已启用才能新引入</p>
                    </div>
                    <div class="flex items-center gap-2 shrink-0">
                        <button id="supplierBtnExport" type="button"
                                class="h-8 inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-4 text-xs font-medium hover:border-[#9e9e9e] hover:text-white transition-all">
                            ${window.svgIcon('download', 'w-3.5 h-3.5')}
                            <span>导出 Excel</span>
                        </button>
                        <button id="supplierBtnCreate" type="button"
                                class="h-8 inline-flex items-center gap-1.5 bg-[#d32f2f] hover:bg-[#b71c1c] text-white px-4 text-xs font-semibold transition-all">
                            ${window.svgIcon('plus', 'w-3.5 h-3.5')}
                            <span>新增供应商</span>
                        </button>
                    </div>
                </div>

                <div class="px-3 py-2.5 border-b border-[#222222] flex flex-wrap items-center gap-2 bg-[#121215]">
                    <div class="relative flex-1 min-w-[220px] max-w-sm">
                        <span class="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none text-[#616161]">
                            ${window.svgIcon('search', 'w-3.5 h-3.5')}
                        </span>
                        <input type="text" id="supplierFilterKeyword" placeholder="缩写 / 全称 / ERP / 别名"
                               class="w-full h-8 pl-8 pr-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-[#ffffff] placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-colors">
                    </div>
                    <button id="supplierBtnSearch" type="button"
                            class="h-8 inline-flex items-center gap-1.5 px-3 text-[11px] font-semibold text-[#c8c8c8] border border-[#2c2c2c] hover:text-white hover:border-[#9e9e9e] transition-all">
                        ${window.svgIcon('search', 'w-3 h-3')}
                        查询
                    </button>
                    <div class="flex items-center gap-1.5 ml-1">
                        <button type="button" data-enabled-filter="" class="supplier-status-capsule px-2 py-0.5 text-[10px] font-mono rounded-md border border-[#d32f2f]/50 bg-[#1a080a] text-[#d32f2f]">全部</button>
                        <button type="button" data-enabled-filter="true" class="supplier-status-capsule px-2 py-0.5 text-[10px] font-mono rounded-md border border-[#2c2c2c] text-[#616161] hover:text-[#9e9e9e]">已启用</button>
                        <button type="button" data-enabled-filter="false" class="supplier-status-capsule px-2 py-0.5 text-[10px] font-mono rounded-md border border-[#2c2c2c] text-[#616161] hover:text-[#9e9e9e]">已禁用</button>
                    </div>
                </div>

                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs border-collapse">
                        <thead>
                            <tr class="bg-[#0e0e11] border-b border-[#2c2c2c] text-[#9e9e9e]">
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider">缩写</th>
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider">全称</th>
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider">ERP 代码</th>
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider">别名</th>
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider text-center">状态</th>
                                <th class="p-0 w-9" aria-label="操作"></th>
                            </tr>
                        </thead>
                        <tbody id="supplierTableBody" class="divide-y divide-[#222222]"></tbody>
                    </table>
                </div>

                <div class="flex items-center justify-between px-4 py-2.5 border-t border-[#222222] bg-[#0e0e11]" id="supplierPagination">
                    <div class="flex items-center gap-3 min-w-0">
                        <span id="supplierTotalCount" class="text-xs text-[#616161] font-mono"></span>
                        ${pageSizeSelectHtml('supplierPageSize')}
                    </div>
                    <div class="flex items-center gap-1" id="supplierPaginationBtns"></div>
                </div>

                <div id="supplierEmptyState" class="hidden flex flex-col items-center justify-center py-16 text-center">
                    <div class="p-3 bg-[#1e1e1e] border border-[#2c2c2c] text-[#616161] mb-2">
                        ${window.svgIcon('inbox', 'w-6 h-6')}
                    </div>
                    <p class="text-xs text-[#9e9e9e] mb-1">暂无供应商</p>
                    <p id="supplierEmptyHint" class="text-[11px] text-[#616161]">点右上角新增，或到上传页导入 Excel</p>
                </div>

                <div id="supplierLoadingState" class="hidden flex flex-col items-center justify-center py-16 gap-2">
                    <div class="w-5 h-5 border-2 border-[#2c2c2c] border-t-[#d32f2f] rounded-full animate-spin"></div>
                    <span class="text-[11px] text-[#616161]">加载中..</span>
                </div>
            </div>
        </div>

        <div class="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm transition-opacity" id="supplierCreateBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[420px] bg-[#121215] border-l border-[#2c2c2c] shadow-2xl transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="supplierCreateDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-[#2c2c2c] bg-[#16161a] shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-[#d32f2f]"></span>
                    <h5 class="text-xs font-semibold text-white tracking-wider">新增供应商</h5>
                </div>
                <button type="button" id="closeSupplierCreateDrawer" class="text-[#616161] hover:text-white w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-5">
                <form id="supplierCreateForm" class="space-y-4">
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">缩写 <span class="text-[#d32f2f]">*</span></label>
                        <input type="text" id="supplierCreateAbbreviation" required maxlength="50"
                               placeholder="例如：常庆"
                               class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-colors">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">全称 <span class="text-[#d32f2f]">*</span></label>
                        <input type="text" id="supplierCreateFullName" required maxlength="100"
                               placeholder="例如：安庆常庆汽车部件有限公司"
                               class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-colors">
                        <p class="text-[10px] text-[#616161] mt-1">规范名，创建后不可修改；默认已启用</p>
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">ERP 代码 <span class="text-[#d32f2f]">*</span></label>
                        <input type="text" id="supplierCreateErpCode" required maxlength="50"
                               placeholder="对外身份"
                               class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-colors">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">别名</label>
                        <textarea id="supplierCreateAliases" rows="3"
                                  placeholder="每行一个，可空。工艺常见乱写建议一并录入"
                                  class="w-full px-3 py-2 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-colors resize-y"></textarea>
                    </div>
                </form>
            </div>
            <div class="px-5 py-3 border-t border-[#2c2c2c] flex items-center justify-end gap-2 bg-[#16161a] shrink-0">
                <button type="button" id="cancelSupplierCreateBtn" class="px-4 py-1.5 text-xs text-[#9e9e9e] hover:text-white border border-[#2c2c2c] hover:bg-[#262626] transition-all">取消</button>
                <button type="button" id="submitSupplierCreateBtn" class="bg-[#d32f2f] hover:bg-[#b71c1c] text-white px-5 py-1.5 text-xs font-semibold transition-all">保存</button>
            </div>
        </div>

        <div class="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm transition-opacity" id="supplierEditBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[420px] bg-[#121215] border-l border-[#2c2c2c] shadow-2xl transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="supplierEditDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-[#2c2c2c] bg-[#16161a] shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-[#d32f2f]"></span>
                    <h5 class="text-xs font-semibold text-white tracking-wider">编辑供应商</h5>
                </div>
                <button type="button" id="closeSupplierEditDrawer" class="text-[#616161] hover:text-white w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-5 space-y-4">
                <div>
                    <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">缩写</label>
                    <input type="text" id="supplierEditAbbreviation" readonly
                           class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-[#9e9e9e] cursor-not-allowed">
                </div>
                <div>
                    <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">全称</label>
                    <input type="text" id="supplierEditFullName" readonly
                           class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-[#9e9e9e] cursor-not-allowed">
                </div>
                <div>
                    <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">ERP 代码</label>
                    <input type="text" id="supplierEditErpCode" readonly
                           class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-[#9e9e9e] cursor-not-allowed">
                    <p class="text-[10px] text-[#616161] mt-1">缩写 / 全称 / ERP 代码创建后不可修改</p>
                </div>
                <div>
                    <div class="flex items-center justify-between mb-2">
                        <span class="text-[10px] font-semibold text-[#616161] tracking-wider">别名</span>
                        <span id="supplierEditAliasCount" class="font-mono text-[10px] text-[#616161]"></span>
                    </div>
                    <div class="border border-[#2c2c2c] bg-[#0a0a0c]">
                        <ul id="supplierEditAliasList" class="divide-y divide-[#222222]"></ul>
                    </div>
                </div>
            </div>
            <div class="px-5 py-3 border-t border-[#2c2c2c] bg-[#16161a] shrink-0">
                <form id="supplierEditAliasForm" class="flex items-center gap-2">
                    <input type="text" id="supplierEditAliasInput" maxlength="100" placeholder="新别名，例如：常庆汽配"
                           class="flex-1 min-w-0 h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-colors">
                    <button type="submit" id="submitSupplierEditAliasBtn" class="h-8 px-4 bg-[#d32f2f] hover:bg-[#b71c1c] text-white text-xs font-semibold shrink-0">添加</button>
                </form>
            </div>
        </div>

        <div class="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm transition-opacity" id="supplierToggleBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[360px] bg-[#121215] border-l border-[#2c2c2c] shadow-2xl transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="supplierToggleDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-[#2c2c2c] bg-[#16161a]">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-[#d32f2f]"></span>
                    <h5 class="text-xs font-semibold text-white tracking-wider" id="supplierToggleTitle">确认禁用</h5>
                </div>
                <button type="button" id="closeSupplierToggleDrawer" class="text-[#616161] hover:text-white">✕</button>
            </div>
            <div class="flex-1 p-5">
                <div class="p-3 bg-[#1a080a] border border-[#d32f2f]/30 mb-3">
                    <p class="text-xs text-[#9e9e9e]">
                        <span id="supplierToggleLead">确认禁用供应商</span>
                        <span id="supplierToggleName" class="text-[#d32f2f] font-mono font-bold ml-1"></span>
                    </p>
                </div>
                <p class="text-[11px] text-[#616161]" id="supplierToggleHint">禁用后不能再按此供应商新引入；列表筛选仍可见。</p>
            </div>
            <div class="px-5 py-3 border-t border-[#2c2c2c] flex items-center justify-end gap-2 bg-[#16161a]">
                <button type="button" id="cancelSupplierToggleBtn" class="px-4 py-1.5 text-xs text-[#9e9e9e] hover:text-white border border-[#2c2c2c]">取消</button>
                <button type="button" id="confirmSupplierToggleBtn" class="bg-[#d32f2f] hover:bg-[#b71c1c] text-white font-semibold px-4 py-1.5 text-xs">确认禁用</button>
            </div>
        </div>
    `;
}

export function renderSupplierRows(records) {
    if (!records || !Array.isArray(records) || records.length === 0) {
        return '';
    }
    return records.map((record) => {
        const isEnabled = record.is_enabled !== false;
        const statusBadge = isEnabled
            ? `<span class="text-[10px] tracking-[0.08em] text-[#555555]">启用</span>`
            : `<span class="text-[10px] tracking-[0.08em] text-[#3A3A42]">禁用</span>`;
        const aliases = Array.isArray(record.aliases) ? record.aliases.filter(Boolean) : [];
        const aliasText = aliases.length
            ? `<span class="text-[#9e9e9e]">${esc(aliases.join(', '))}</span>`
            : `<span class="text-[#616161]">—</span>`;
        const canUpdate = hasPermission('op:supplier-list:update');
        const toggleLabel = isEnabled ? '禁用' : '启用';
        const fullName = esc(record.full_name);
        return `
        <tr class="hover:bg-[#ffffff]/[0.02] transition-colors border-b border-[#222222] group" data-full-name="${fullName}">
            <td class="px-4 py-2.5 whitespace-nowrap">
                <span class="font-mono font-semibold text-xs text-[#ffffff]">${esc(record.abbreviation)}</span>
            </td>
            <td class="px-4 py-2.5">
                <span class="text-xs text-[#ffffff]" title="${fullName}">${fullName}</span>
            </td>
            <td class="px-4 py-2.5 whitespace-nowrap">
                <span class="font-mono text-[11px] text-[#9e9e9e]">${esc(record.erp_code)}</span>
            </td>
            <td class="px-4 py-2.5">${aliasText}</td>
            <td class="px-4 py-2.5 text-center whitespace-nowrap">${statusBadge}</td>
            <td class="px-4 py-2.5 text-right whitespace-nowrap pr-5">
                <div class="inline-flex items-center gap-0.5 bg-[#0a0a0c] border border-[#2c2c2c] p-0.5 opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto focus-within:opacity-100 focus-within:pointer-events-auto transition-opacity">
                    ${canUpdate ? `<button type="button" data-action="edit" class="p-1.5 text-[#9e9e9e] hover:text-white hover:bg-[#262626] transition-all" title="编辑">
                        ${window.svgIcon('pencil', 'w-3.5 h-3.5')}
                    </button>` : ''}
                    ${canUpdate ? `<button type="button" data-action="toggle" data-enabled="${isEnabled ? '1' : '0'}" class="px-2 h-7 text-[10px] text-[#616161] hover:text-white hover:bg-[#262626] transition-all" title="${toggleLabel}">
                        ${toggleLabel}
                    </button>` : ''}
                </div>
            </td>
        </tr>`;
    }).join('');
}

export function renderAliasItems(aliases, canUpdate) {
    const items = Array.isArray(aliases) ? aliases.filter(Boolean) : [];
    if (!items.length) {
        return `<li class="px-3 py-8 text-center text-[11px] text-[#616161]">暂无别名</li>`;
    }
    return items.map((alias) => {
        const deleteBtn = canUpdate
            ? `<button type="button" data-action="delete-alias" data-alias="${esc(alias)}" class="w-7 h-7 inline-flex items-center justify-center text-[#555555] hover:text-[#ef5350] hover:bg-[#1a080a] transition-all" title="删除别名">${window.svgIcon('trash', 'w-3.5 h-3.5')}</button>`
            : '';
        return `<li class="flex items-center gap-2 px-3 h-9 hover:bg-[#161620] transition-colors">
            <span class="flex-1 min-w-0 font-mono text-[11px] text-[#F0F0F2] truncate" title="${esc(alias)}">${esc(alias)}</span>
            ${deleteBtn}
        </li>`;
    }).join('');
}

export function renderPagination(currentPage, totalPages) {
    if (totalPages <= 1) {
        return '';
    }

    let buttons = '';
    buttons += `
        <button class="page-btn px-2 h-6 text-[11px] border ${currentPage === 1 ? 'border-[#2c2c2c]/50 text-[#333333] cursor-not-allowed' : 'border-[#2c2c2c] text-[#9e9e9e] hover:text-white hover:bg-[#262626]'} transition-all"
                data-page="${currentPage - 1}" ${currentPage === 1 ? 'disabled' : ''}>上一页</button>
    `;

    const maxVisible = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);
    if (endPage - startPage < maxVisible - 1) {
        startPage = Math.max(1, endPage - maxVisible + 1);
    }

    if (startPage > 1) {
        buttons += `<button class="page-btn w-6 h-6 text-[11px] border border-[#2c2c2c] text-[#9e9e9e] hover:text-white hover:bg-[#262626] transition-all" data-page="1">1</button>`;
        if (startPage > 2) buttons += `<span class="px-1 text-[#616161] text-xs">—</span>`;
    }

    for (let i = startPage; i <= endPage; i++) {
        const isActive = i === currentPage;
        buttons += `
            <button class="page-btn w-6 h-6 text-[11px] font-mono ${isActive ? 'bg-[#d32f2f] border border-[#d32f2f] text-white' : 'border border-[#2c2c2c] text-[#9e9e9e] hover:text-white hover:bg-[#262626]'} transition-all"
                    data-page="${i}">${i}</button>
        `;
    }

    if (endPage < totalPages) {
        if (endPage < totalPages - 1) buttons += `<span class="px-1 text-[#616161] text-xs">—</span>`;
        buttons += `<button class="page-btn w-6 h-6 text-[11px] border border-[#2c2c2c] text-[#9e9e9e] hover:text-white hover:bg-[#262626] transition-all" data-page="${totalPages}">${totalPages}</button>`;
    }

    buttons += `
        <button class="page-btn px-2 h-6 text-[11px] border ${currentPage === totalPages ? 'border-[#2c2c2c]/50 text-[#333333] cursor-not-allowed' : 'border-[#2c2c2c] text-[#9e9e9e] hover:text-white hover:bg-[#262626]'} transition-all"
                data-page="${currentPage + 1}" ${currentPage === totalPages ? 'disabled' : ''}>下一页</button>
    `;
    return buttons;
}

function hasPermission(code) {
    if (typeof window.can === 'function') {
        return window.can(code);
    }
    try {
        const raw = localStorage.getItem('brabus_user');
        const session = raw ? JSON.parse(raw) : null;
        if (session?.is_admin === true) return true;
        const permissions = Array.isArray(session?.permissions) ? session.permissions : [];
        if (permissions.includes('*') || permissions.includes(code)) return true;
    } catch {
        /* ignore */
    }
    return true;
}

function esc(str) {
    if (typeof window.esc === 'function') return window.esc(str);
    if (str === null || str === undefined) return '-';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
