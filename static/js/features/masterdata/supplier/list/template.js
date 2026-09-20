/**
 * 供应商一览 — HUD 密表 + 抽屉；有搜索 / 分页 / 导出
 */

import { paginationBarHtml } from '../../../../page-size.js?v=3';
import { moreMenuItemHtml, moreMenuShellHtml } from '../../../../more-menu.js?v=1';

export function supplierListTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="bg-[#0A0A0C] border border-[#1A1A22] overflow-hidden w-full max-w-full"
                 style="box-shadow: 0 4px 24px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.02);">
                <div class="px-5 pt-4 pb-3.5 border-b border-[#14141A]"
                     style="background: linear-gradient(135deg, #0E0E12 0%, #121218 45%, #0C0C10 100%);">
                    <div class="flex items-start justify-between gap-4 mb-3">
                        <div class="min-w-0">
                            <h2 class="text-[13px] font-semibold text-[#F0F0F2] tracking-wide">供应商</h2>
                            <p class="mt-1 text-[11px] text-[#555555]">核价树上游厂档：缩写上屏，全称对表头，启用后才能引入</p>
                        </div>
                        <div class="flex items-center gap-1.5 shrink-0">
                            ${moreMenuShellHtml({
                                wrapId: 'supplierMoreWrap',
                                btnId: 'supplierMoreBtn',
                                menuId: 'supplierMoreMenu',
                                itemsHtml: moreMenuItemHtml({ id: 'supplierBtnExport', label: '导出' }),
                            })}
                            <button id="supplierBtnCreate" type="button"
                                    class="inline-flex items-center gap-1.5 bg-[#FF1E27] hover:bg-[#d32f2f] text-white px-3 py-1.5 text-[11px] font-semibold rounded-md transition-all">
                                ${window.svgIcon('plus', 'w-3.5 h-3.5')}
                                新增
                            </button>
                        </div>
                    </div>
                    <div class="flex flex-wrap items-center gap-2">
                        <div class="relative flex-1 min-w-[220px] max-w-sm">
                            <span class="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none text-[#555555]">
                                ${window.svgIcon('search', 'w-3.5 h-3.5')}
                            </span>
                            <input type="text" id="supplierFilterKeyword" placeholder="缩写 / 全称 / 对外代码 / 别名"
                                   class="w-full h-8 pl-8 pr-3 text-[11px] font-mono bg-[#0A0A0E] border border-[#2A2A35] text-[#F0F0F2] placeholder:text-[#555555] focus:outline-none focus:border-[#FF1E27] rounded-sm">
                        </div>
                        <div class="flex items-center gap-1.5">
                            <button type="button" data-enabled-filter="" class="supplier-status-capsule px-2 py-0.5 text-[10px] font-mono rounded-md border border-[#FF1E27]/50 bg-[#1A080A] text-white">全部</button>
                            <button type="button" data-enabled-filter="true" class="supplier-status-capsule px-2 py-0.5 text-[10px] font-mono rounded-md border border-[#2A2A35] text-[#8E8E93] hover:text-white">已启用</button>
                            <button type="button" data-enabled-filter="false" class="supplier-status-capsule px-2 py-0.5 text-[10px] font-mono rounded-md border border-[#2A2A35] text-[#8E8E93] hover:text-white">已禁用</button>
                        </div>
                    </div>
                </div>

                <div class="overflow-x-auto brabus-bg-grid">
                    <table class="w-full table-fixed bg-transparent border-separate border-spacing-0" style="min-width: 860px;">
                        <colgroup>
                            <col style="width: 8px;">
                            <col style="width: 12%;">
                            <col style="width: 28%;">
                            <col style="width: 12%;">
                            <col>
                            <col style="width: 72px;">
                            <col style="width: 120px;">
                        </colgroup>
                        <thead>
                            <tr class="border-b border-[#17171C] bg-[#0B0B0D]/95">
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">缩写</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-[#555555]">全称</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-[#555555]">对外代码</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-[#555555]">别名</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">状态</th>
                                <th class="p-0 w-9 sticky right-0 z-[3] bg-[#0B0B0D]" aria-label="操作"></th>
                            </tr>
                        </thead>
                        <tbody id="supplierTableBody"></tbody>
                    </table>
                </div>

                ${paginationBarHtml({ infoId: 'supplierTotalCount', selectId: 'supplierPageSize', buttonsId: 'supplierPaginationBtns', wrapperId: 'supplierPagination' })}

                <div id="supplierEmptyState" class="hidden flex flex-col items-center justify-center py-16 text-center bg-[#0A0A0E]">
                    <p class="text-xs text-[#8E8E93] mb-1">暂无供应商</p>
                    <p id="supplierEmptyHint" class="text-[11px] text-[#555555]">点右上角新增，或从上传页补档</p>
                </div>
                <div id="supplierLoadingState" class="hidden flex flex-col items-center justify-center py-16 gap-2 bg-[#0A0A0E]">
                    <div class="w-5 h-5 border-2 border-[#2c2c2c] border-t-[#FF1E27] rounded-full animate-spin"></div>
                    <span class="text-[11px] text-[#555555]">加载中..</span>
                </div>
            </div>
        </div>

        <div class="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm" id="supplierCreateBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[420px] bg-[#121215] border-l border-[#2c2c2c] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="supplierCreateDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-[#2c2c2c] bg-[#16161a] shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-[#FF1E27]"></span>
                    <h5 class="text-xs font-semibold text-white tracking-wider">新增供应商</h5>
                </div>
                <button type="button" id="closeSupplierCreateDrawer" class="text-[#616161] hover:text-white w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-5">
                <form id="supplierCreateForm" class="space-y-4">
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">缩写 <span class="text-[#FF1E27]">*</span></label>
                        <input type="text" id="supplierCreateAbbreviation" required maxlength="50"
                               placeholder="例如：常庆"
                               class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252]">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">全称 <span class="text-[#FF1E27]">*</span></label>
                        <input type="text" id="supplierCreateFullName" required maxlength="100"
                               placeholder="与营业执照一致"
                               class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252]">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">对外代码 <span class="text-[#FF1E27]">*</span></label>
                        <input type="text" id="supplierCreateErpCode" required maxlength="50"
                               placeholder="对外对接码"
                               class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252]">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">别名</label>
                        <textarea id="supplierCreateAliases" rows="3"
                                  placeholder="每行一个，可空；吸收工艺表头乱写"
                                  class="w-full px-3 py-2 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] resize-y"></textarea>
                    </div>
                </form>
            </div>
            <div class="px-5 py-3 border-t border-[#2c2c2c] flex items-center justify-end gap-2 bg-[#16161a] shrink-0">
                <button type="button" id="cancelSupplierCreateBtn" class="px-4 py-1.5 text-xs text-[#9e9e9e] border border-[#2c2c2c] hover:text-white">取消</button>
                <button type="button" id="submitSupplierCreateBtn" class="bg-[#FF1E27] hover:bg-[#d32f2f] text-white px-5 py-1.5 text-xs font-semibold">保存</button>
            </div>
        </div>

        <div class="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm" id="supplierEditBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[420px] bg-[#121215] border-l border-[#2c2c2c] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="supplierEditDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-[#2c2c2c] bg-[#16161a] shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-[#FF1E27]"></span>
                    <h5 class="text-xs font-semibold text-white tracking-wider">编辑供应商</h5>
                </div>
                <button type="button" id="closeSupplierEditDrawer" class="text-[#616161] hover:text-white w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-5 space-y-4">
                <div>
                    <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">缩写</label>
                    <input type="text" id="supplierEditAbbreviation" maxlength="50"
                           class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#ff5252]">
                </div>
                <div>
                    <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">全称</label>
                    <input type="text" id="supplierEditFullName" maxlength="100"
                           class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#ff5252]">
                </div>
                <div>
                    <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">对外代码</label>
                    <input type="text" id="supplierEditErpCode" maxlength="50"
                           class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#ff5252]">
                    <p class="text-[10px] text-[#555555] mt-1">改全称成功后旧名收成别名；仍被引用则不能改</p>
                </div>
                <div>
                    <div class="flex items-center justify-between mb-2">
                        <span class="text-[10px] font-semibold text-[#616161] tracking-wider">别名</span>
                        <span id="supplierEditAliasCount" class="font-mono text-[10px] text-[#555555]"></span>
                    </div>
                    <div class="border border-[#2c2c2c] bg-[#0a0a0c]">
                        <ul id="supplierEditAliasList" class="divide-y divide-[#222222]"></ul>
                    </div>
                </div>
            </div>
            <div class="px-5 py-3 border-t border-[#2c2c2c] bg-[#16161a] shrink-0 space-y-2">
                <form id="supplierEditAliasForm" class="flex items-center gap-2">
                    <input type="text" id="supplierEditAliasInput" maxlength="100" placeholder="新别名，例如：常庆汽配"
                           class="flex-1 min-w-0 h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252]">
                    <button type="submit" id="submitSupplierEditAliasBtn" class="h-8 px-4 bg-[#FF1E27] hover:bg-[#d32f2f] text-white text-xs font-semibold shrink-0">添加</button>
                </form>
                <div class="flex justify-end">
                    <button type="button" id="submitSupplierEditBtn" class="h-8 px-4 bg-[#FF1E27] hover:bg-[#d32f2f] text-white text-xs font-semibold">保存资料</button>
                </div>
            </div>
        </div>

        <div class="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm" id="supplierToggleBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[360px] bg-[#121215] border-l border-[#2c2c2c] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="supplierToggleDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-[#2c2c2c] bg-[#16161a] shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-[#FF1E27]"></span>
                    <h5 class="text-xs font-semibold text-white tracking-wider" id="supplierToggleTitle">确认禁用</h5>
                </div>
                <button type="button" id="closeSupplierToggleDrawer" class="text-[#616161] hover:text-white w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 p-5">
                <p class="text-xs text-[#9e9e9e] mb-2" id="supplierToggleLead">确认禁用供应商</p>
                <p id="supplierToggleName" class="text-sm font-semibold text-white font-mono"></p>
                <p class="text-[11px] text-[#555555] mt-3" id="supplierToggleHint">禁用后不能再按此供应商新引入；列表筛选仍可见。</p>
            </div>
            <div class="px-5 py-3 border-t border-[#2c2c2c] flex items-center justify-end gap-2 bg-[#16161a] shrink-0">
                <button type="button" id="cancelSupplierToggleBtn" class="px-4 py-1.5 text-xs text-[#9e9e9e] border border-[#2c2c2c]">取消</button>
                <button type="button" id="confirmSupplierToggleBtn" class="bg-[#FF1E27] hover:bg-[#d32f2f] text-white px-5 py-1.5 text-xs font-semibold">确认禁用</button>
            </div>
        </div>

        <div class="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm" id="supplierDeleteBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[360px] bg-[#121215] border-l border-[#2c2c2c] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="supplierDeleteDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-[#2c2c2c] bg-[#16161a] shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-[#FF1E27]"></span>
                    <h5 class="text-xs font-semibold text-white tracking-wider">删除供应商</h5>
                </div>
                <button type="button" id="closeSupplierDeleteDrawer" class="text-[#616161] hover:text-white w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 p-5">
                <p class="text-xs text-[#9e9e9e] mb-2">确认删除供应商</p>
                <p id="supplierDeleteName" class="text-sm font-semibold text-white font-mono"></p>
                <p class="text-[11px] text-[#555555] mt-3">仍被引用则不能删除。别名会一并删除。</p>
            </div>
            <div class="px-5 py-3 border-t border-[#2c2c2c] flex items-center justify-end gap-2 bg-[#16161a] shrink-0">
                <button type="button" id="cancelSupplierDeleteBtn" class="px-4 py-1.5 text-xs text-[#9e9e9e] border border-[#2c2c2c]">取消</button>
                <button type="button" id="confirmSupplierDeleteBtn" class="bg-[#c62828] hover:bg-[#b71c1c] text-white px-5 py-1.5 text-xs font-semibold">删除</button>
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
            ? `<span class="text-[9px] font-medium tracking-[0.08em] text-[#555555]">启用</span>`
            : `<span class="text-[9px] font-medium tracking-[0.08em] text-[#3A3A42]">禁用</span>`;
        const aliases = Array.isArray(record.aliases) ? record.aliases.filter(Boolean) : [];
        const aliasText = aliases.length
            ? `<span class="text-[11px] text-[#8E8E93]">${esc(aliases.join(', '))}</span>`
            : `<span class="text-[11px] text-[#3A3A42]">—</span>`;
        const canUpdate = hasPermission('op:supplier-list:update');
        const canDelete = hasPermission('op:supplier-list:delete');
        const toggleLabel = isEnabled ? '禁用' : '启用';
        const fullName = esc(record.full_name);
        const editBtn = canUpdate
            ? `<button type="button" data-action="edit" class="w-7 h-7 inline-flex items-center justify-center text-[#6E6E73] hover:text-[#FF1E27] opacity-0 group-hover:opacity-100 focus:opacity-100" title="编辑">${window.svgIcon('pencil', 'w-3.5 h-3.5')}</button>`
            : '';
        const toggleBtn = canUpdate
            ? `<button type="button" data-action="toggle" data-enabled="${isEnabled ? '1' : '0'}" class="px-1.5 h-7 text-[10px] text-[#6E6E73] hover:text-[#FF1E27] opacity-0 group-hover:opacity-100 focus:opacity-100" title="${toggleLabel}">${toggleLabel}</button>`
            : '';
        const deleteBtn = canDelete
            ? `<button type="button" data-action="delete" class="w-7 h-7 inline-flex items-center justify-center text-[#6E6E73] hover:text-[#ef5350] opacity-0 group-hover:opacity-100 focus:opacity-100" title="删除">${window.svgIcon('trash', 'w-3.5 h-3.5')}</button>`
            : '';
        return `
        <tr class="group relative font-mono text-[11px] border-b border-[#141418] hover:bg-[#161620] transition-colors duration-100" data-full-name="${fullName}">
            <td class="p-0 relative">
                <div class="absolute left-0 top-0 bottom-0 w-[2px] bg-[#FF1E27] opacity-0 group-hover:opacity-70 transition-opacity"></div>
            </td>
            <td class="px-2 py-2 overflow-hidden">
                <div class="text-[14px] font-bold text-[#F0F0F2] truncate">${esc(record.abbreviation)}</div>
            </td>
            <td class="px-2 py-2 overflow-hidden">
                <div class="text-[11px] text-[#C8C8D0] truncate" title="${fullName}">${fullName}</div>
            </td>
            <td class="px-2 py-2 overflow-hidden">
                <span class="text-[10px] text-[#8E8E93] tabular-nums">${esc(record.erp_code)}</span>
            </td>
            <td class="px-2 py-2 overflow-hidden truncate">${aliasText}</td>
            <td class="px-2 py-2 text-center whitespace-nowrap">${statusBadge}</td>
            <td class="px-1 py-2 text-center whitespace-nowrap sticky right-0 z-[2] brabus-bg-grid group-hover:bg-[#161620]">${editBtn}${toggleBtn}${deleteBtn}</td>
        </tr>`;
    }).join('');
}

export function renderAliasItems(aliases, canUpdate) {
    const items = Array.isArray(aliases) ? aliases.filter(Boolean) : [];
    if (!items.length) {
        return `<li class="px-3 py-8 text-center text-[11px] text-[#555555]">暂无别名</li>`;
    }
    return items.map((alias) => {
        const deleteBtn = canUpdate
            ? `<button type="button" data-action="delete-alias" data-alias="${esc(alias)}" class="w-7 h-7 inline-flex items-center justify-center text-[#555555] hover:text-[#ef5350] transition-all" title="删除别名">${window.svgIcon('trash', 'w-3.5 h-3.5')}</button>`
            : '';
        return `<li class="flex items-center gap-2 px-3 h-9 hover:bg-[#161620] transition-colors">
            <span class="flex-1 min-w-0 font-mono text-[11px] text-[#F0F0F2] truncate" title="${esc(alias)}">${esc(alias)}</span>
            ${deleteBtn}
        </li>`;
    }).join('');
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
