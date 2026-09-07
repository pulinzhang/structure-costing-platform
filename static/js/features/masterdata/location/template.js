/**
 * 基地主数据 — 用户管理风格面板 + 表 + 抽屉（无 KPI / 搜索 / 分页）
 */

export function locationTemplate() {
    return `
        <div class="space-y-3 w-full max-w-full text-[#9e9e9e]">
            <div class="bg-[#121215] border border-[#2c2c2c]">
                <div class="p-3 border-b border-[#222222] flex flex-wrap items-center justify-between gap-3 bg-[#16161a]">
                    <div class="min-w-0">
                        <div class="text-xs font-semibold text-white tracking-wider">基地</div>
                        <p class="text-[11px] text-[#616161] mt-0.5">规范名与别名一次录入；创建后规范名不改；已启用才能当采购基地写入</p>
                    </div>
                    <button id="btnAddLocation" class="h-8 inline-flex items-center gap-1.5 bg-[#d32f2f] hover:bg-[#b71c1c] text-white px-4 text-xs font-semibold transition-all">
                        ${window.svgIcon('plus', 'w-3.5 h-3.5')}
                        <span>新增基地</span>
                    </button>
                </div>

                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs border-collapse">
                        <thead>
                            <tr class="bg-[#0e0e11] border-b border-[#2c2c2c] text-[#9e9e9e]">
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider">规范名</th>
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider">别名</th>
                                <th class="px-4 py-3 text-[10px] font-semibold tracking-wider text-center">状态</th>
                                <th class="p-0 w-9" aria-label="操作"></th>
                            </tr>
                        </thead>
                        <tbody id="locationTableBody" class="divide-y divide-[#222222]"></tbody>
                    </table>
                </div>

                <div id="locationEmptyState" class="hidden flex flex-col items-center justify-center py-16 text-center">
                    <div class="p-3 bg-[#1e1e1e] border border-[#2c2c2c] text-[#616161] mb-2">
                        ${window.svgIcon('inbox', 'w-6 h-6')}
                    </div>
                    <p class="text-xs text-[#9e9e9e] mb-1">暂无基地</p>
                    <p class="text-[11px] text-[#616161]">点击右上角新增基地</p>
                </div>

                <div id="locationLoadingState" class="hidden flex flex-col items-center justify-center py-16 gap-2">
                    <div class="w-5 h-5 border-2 border-[#2c2c2c] border-t-[#d32f2f] rounded-full animate-spin"></div>
                    <span class="text-[11px] text-[#616161]">加载中..</span>
                </div>
            </div>
        </div>

        <div class="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm transition-opacity" id="locationCreateBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[420px] bg-[#121215] border-l border-[#2c2c2c] shadow-2xl transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="locationCreateDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-[#2c2c2c] bg-[#16161a] shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-[#d32f2f]"></span>
                    <h5 class="text-xs font-semibold text-white tracking-wider">新增基地</h5>
                </div>
                <button type="button" id="closeLocationCreateDrawer" class="text-[#616161] hover:text-white w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-5">
                <form id="locationCreateForm" class="space-y-4">
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">规范名 <span class="text-[#d32f2f]">*</span></label>
                        <input type="text" id="locationCreateName" required maxlength="50"
                               placeholder="例如：青岛"
                               class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-colors">
                        <p class="text-[10px] text-[#616161] mt-1">创建后不可修改；默认已启用</p>
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">别名 <span class="text-[#d32f2f]">*</span></label>
                        <textarea id="locationCreateAliases" required rows="3"
                                  placeholder="每行一个，例如：&#10;青岛基地&#10;青岛厂"
                                  class="w-full px-3 py-2 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-colors resize-y"></textarea>
                        <p class="text-[10px] text-[#616161] mt-1">至少一条；历史叫法未登记则对不上</p>
                    </div>
                </form>
            </div>
            <div class="px-5 py-3 border-t border-[#2c2c2c] flex items-center justify-end gap-2 bg-[#16161a] shrink-0">
                <button type="button" id="cancelLocationCreateBtn" class="px-4 py-1.5 text-xs text-[#9e9e9e] hover:text-white border border-[#2c2c2c] hover:bg-[#262626] transition-all">取消</button>
                <button type="button" id="submitLocationCreateBtn" class="bg-[#d32f2f] hover:bg-[#b71c1c] text-white px-5 py-1.5 text-xs font-semibold transition-all">保存</button>
            </div>
        </div>

        <div class="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm transition-opacity" id="locationEditBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[420px] bg-[#121215] border-l border-[#2c2c2c] shadow-2xl transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="locationEditDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-[#2c2c2c] bg-[#16161a] shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-[#d32f2f]"></span>
                    <h5 class="text-xs font-semibold text-white tracking-wider">编辑基地</h5>
                </div>
                <button type="button" id="closeLocationEditDrawer" class="text-[#616161] hover:text-white w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-5 space-y-4">
                <div>
                    <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">规范名</label>
                    <input type="text" id="locationEditName" readonly
                           class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-[#9e9e9e] cursor-not-allowed">
                    <p class="text-[10px] text-[#616161] mt-1">规范名创建后不可修改</p>
                </div>
                <div>
                    <div class="flex items-center justify-between mb-2">
                        <span class="text-[10px] font-semibold text-[#616161] tracking-wider">别名</span>
                        <span id="locationEditAliasCount" class="font-mono text-[10px] text-[#616161]"></span>
                    </div>
                    <div class="border border-[#2c2c2c] bg-[#0a0a0c]">
                        <ul id="locationEditAliasList" class="divide-y divide-[#222222]"></ul>
                    </div>
                </div>
            </div>
            <div class="px-5 py-3 border-t border-[#2c2c2c] bg-[#16161a] shrink-0">
                <form id="locationEditAliasForm" class="flex items-center gap-2">
                    <input type="text" id="locationEditAliasInput" maxlength="50" placeholder="新别名，例如：青岛厂"
                           class="flex-1 min-w-0 h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] transition-colors">
                    <button type="submit" id="submitLocationEditAliasBtn" class="h-8 px-4 bg-[#d32f2f] hover:bg-[#b71c1c] text-white text-xs font-semibold shrink-0">添加</button>
                </form>
            </div>
        </div>

        <div class="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm transition-opacity" id="locationDeleteBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[360px] bg-[#121215] border-l border-[#2c2c2c] shadow-2xl transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="locationDeleteDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-[#2c2c2c] bg-[#16161a]">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-[#c62828]"></span>
                    <h5 class="text-xs font-semibold text-white tracking-wider">确认删除</h5>
                </div>
                <button type="button" id="closeLocationDeleteDrawer" class="text-[#616161] hover:text-white">✕</button>
            </div>
            <div class="flex-1 p-5">
                <div class="p-3 bg-[#c62828]/15 border border-[#c62828]/40 mb-3">
                    <p class="text-xs text-[#9e9e9e]">
                        确认删除基地 <span id="locationDeleteName" class="text-[#d32f2f] font-mono font-bold"></span>
                    </p>
                </div>
                <p class="text-[11px] text-[#616161]">仍被引用时无法删除。此操作不可恢复。</p>
            </div>
            <div class="px-5 py-3 border-t border-[#2c2c2c] flex items-center justify-end gap-2 bg-[#16161a]">
                <button type="button" id="cancelLocationDeleteBtn" class="px-4 py-1.5 text-xs text-[#9e9e9e] hover:text-white border border-[#2c2c2c]">取消</button>
                <button type="button" id="confirmLocationDeleteBtn" class="bg-[#c62828] hover:bg-[#b71c1c] text-white font-semibold px-4 py-1.5 text-xs">确认删除</button>
            </div>
        </div>

        <div class="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm transition-opacity" id="locationToggleBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[360px] bg-[#121215] border-l border-[#2c2c2c] shadow-2xl transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="locationToggleDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-[#2c2c2c] bg-[#16161a]">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-[#d32f2f]"></span>
                    <h5 class="text-xs font-semibold text-white tracking-wider" id="locationToggleTitle">确认禁用</h5>
                </div>
                <button type="button" id="closeLocationToggleDrawer" class="text-[#616161] hover:text-white">✕</button>
            </div>
            <div class="flex-1 p-5">
                <div class="p-3 bg-[#1a080a] border border-[#d32f2f]/30 mb-3">
                    <p class="text-xs text-[#9e9e9e]">
                        <span id="locationToggleLead">确认禁用基地</span>
                        <span id="locationToggleName" class="text-[#d32f2f] font-mono font-bold ml-1"></span>
                    </p>
                </div>
                <p class="text-[11px] text-[#616161]" id="locationToggleHint">禁用后不能再按此基地写入或开引擎；列表筛选仍可见。</p>
            </div>
            <div class="px-5 py-3 border-t border-[#2c2c2c] flex items-center justify-end gap-2 bg-[#16161a]">
                <button type="button" id="cancelLocationToggleBtn" class="px-4 py-1.5 text-xs text-[#9e9e9e] hover:text-white border border-[#2c2c2c]">取消</button>
                <button type="button" id="confirmLocationToggleBtn" class="bg-[#d32f2f] hover:bg-[#b71c1c] text-white font-semibold px-4 py-1.5 text-xs">确认禁用</button>
            </div>
        </div>
    `;
}

export function renderLocationRows(records) {
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
            ? `<span class="text-[#9e9e9e]">${esc(aliases.join('，'))}</span>`
            : `<span class="text-[#616161]">—</span>`;
        const canUpdate = hasPermission('op:location:update');
        const canDelete = hasPermission('op:location:delete');
        const toggleLabel = isEnabled ? '禁用' : '启用';
        const name = esc(record.location);
        return `
        <tr class="hover:bg-[#ffffff]/[0.02] transition-colors border-b border-[#222222] group" data-location="${name}">
            <td class="px-4 py-2.5 whitespace-nowrap">
                <span class="font-mono font-semibold text-xs text-[#ffffff]">${name}</span>
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
                    ${canDelete ? `<button type="button" data-action="delete" class="p-1.5 text-[#9e9e9e] hover:text-[#ef5350] hover:bg-[#262626] transition-all" title="删除">
                        ${window.svgIcon('trash', 'w-3.5 h-3.5')}
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
