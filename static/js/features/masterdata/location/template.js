/**
 * 基地主数据 — HUD 密表 + 抽屉（无 KPI / 搜索 / 分页）
 */

export function locationTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="bg-[#0A0A0C] border border-[#1A1A22] overflow-hidden w-full max-w-full"
                 style="box-shadow: 0 4px 24px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.02);">
                <div class="px-5 pt-4 pb-3.5 border-b border-[#14141A]"
                     style="background: linear-gradient(135deg, #0E0E12 0%, #121218 45%, #0C0C10 100%);">
                    <div class="flex items-start justify-between gap-4">
                        <div class="min-w-0">
                            <h2 class="text-[13px] font-semibold text-[#F0F0F2] tracking-wide">基地</h2>
                            <p class="mt-1 text-[11px] text-[#555555]">核价作用域锚点；别名吸收表头乱写；启用后才能写入</p>
                        </div>
                        <button id="btnAddLocation" type="button"
                                class="inline-flex items-center gap-1.5 bg-[#FF1E27] hover:bg-[#d32f2f] text-white px-3 py-1.5 text-[11px] font-semibold rounded-md transition-all shrink-0">
                            ${window.svgIcon('plus', 'w-3.5 h-3.5')}
                            新增
                        </button>
                    </div>
                </div>

                <div class="overflow-x-auto brabus-bg-grid">
                    <table class="w-full table-fixed bg-transparent border-separate border-spacing-0" style="min-width: 640px;">
                        <colgroup>
                            <col style="width: 8px;">
                            <col style="width: 22%;">
                            <col>
                            <col style="width: 88px;">
                            <col style="width: 120px;">
                        </colgroup>
                        <thead>
                            <tr class="border-b border-[#17171C] bg-[#0B0B0D]/95">
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">基地</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-[#555555]">别名</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">状态</th>
                                <th class="p-0 w-9 sticky right-0 z-[3] bg-[#0B0B0D]" aria-label="操作"></th>
                            </tr>
                        </thead>
                        <tbody id="locationTableBody"></tbody>
                    </table>
                </div>

                <div id="locationEmptyState" class="hidden flex flex-col items-center justify-center py-16 text-center bg-[#0A0A0E]">
                    <p class="text-xs text-[#8E8E93] mb-1">暂无基地</p>
                    <p class="text-[11px] text-[#555555]">点右上角新增基地</p>
                </div>
                <div id="locationLoadingState" class="hidden flex flex-col items-center justify-center py-16 gap-2 bg-[#0A0A0E]">
                    <div class="w-5 h-5 border-2 border-[#2c2c2c] border-t-[#FF1E27] rounded-full animate-spin"></div>
                    <span class="text-[11px] text-[#555555]">加载中..</span>
                </div>
            </div>
        </div>

        <div class="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm" id="locationCreateBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[420px] bg-[#121215] border-l border-[#2c2c2c] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="locationCreateDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-[#2c2c2c] bg-[#16161a] shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-[#FF1E27]"></span>
                    <h5 class="text-xs font-semibold text-white tracking-wider">新增基地</h5>
                </div>
                <button type="button" id="closeLocationCreateDrawer" class="text-[#616161] hover:text-white w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-5">
                <form id="locationCreateForm" class="space-y-4">
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">基地 <span class="text-[#FF1E27]">*</span></label>
                        <input type="text" id="locationCreateName" required maxlength="50"
                               placeholder="例如：青岛"
                               class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252]">
                        <p class="text-[10px] text-[#555555] mt-1">创建后不可改；默认启用</p>
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">别名 <span class="text-[#FF1E27]">*</span></label>
                        <textarea id="locationCreateAliases" required rows="3"
                                  placeholder="每行一个，例如：&#10;青岛基地&#10;青岛厂"
                                  class="w-full px-3 py-2 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252] resize-y"></textarea>
                        <p class="text-[10px] text-[#555555] mt-1">至少一条</p>
                    </div>
                </form>
            </div>
            <div class="px-5 py-3 border-t border-[#2c2c2c] flex items-center justify-end gap-2 bg-[#16161a] shrink-0">
                <button type="button" id="cancelLocationCreateBtn" class="px-4 py-1.5 text-xs text-[#9e9e9e] border border-[#2c2c2c] hover:text-white">取消</button>
                <button type="button" id="submitLocationCreateBtn" class="bg-[#FF1E27] hover:bg-[#d32f2f] text-white px-5 py-1.5 text-xs font-semibold">保存</button>
            </div>
        </div>

        <div class="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm" id="locationEditBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[420px] bg-[#121215] border-l border-[#2c2c2c] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="locationEditDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-[#2c2c2c] bg-[#16161a] shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-[#FF1E27]"></span>
                    <h5 class="text-xs font-semibold text-white tracking-wider">编辑基地</h5>
                </div>
                <button type="button" id="closeLocationEditDrawer" class="text-[#616161] hover:text-white w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-5 space-y-4">
                <div>
                    <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">基地</label>
                    <input type="text" id="locationEditName" readonly
                           class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-[#9e9e9e] cursor-not-allowed">
                    <p class="text-[10px] text-[#555555] mt-1">创建后不可改</p>
                </div>
                <div>
                    <div class="flex items-center justify-between mb-2">
                        <span class="text-[10px] font-semibold text-[#616161] tracking-wider">别名</span>
                        <span id="locationEditAliasCount" class="font-mono text-[10px] text-[#555555]"></span>
                    </div>
                    <div class="border border-[#2c2c2c] bg-[#0a0a0c]">
                        <ul id="locationEditAliasList" class="divide-y divide-[#222222]"></ul>
                    </div>
                </div>
            </div>
            <div class="px-5 py-3 border-t border-[#2c2c2c] bg-[#16161a] shrink-0">
                <form id="locationEditAliasForm" class="flex items-center gap-2">
                    <input type="text" id="locationEditAliasInput" maxlength="50" placeholder="新别名，例如：青岛厂"
                           class="flex-1 min-w-0 h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252]">
                    <button type="submit" id="submitLocationEditAliasBtn" class="h-8 px-4 bg-[#FF1E27] hover:bg-[#d32f2f] text-white text-xs font-semibold shrink-0">添加</button>
                </form>
            </div>
        </div>

        <div class="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm" id="locationDeleteBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[360px] bg-[#121215] border-l border-[#2c2c2c] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="locationDeleteDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-[#2c2c2c] bg-[#16161a] shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-[#FF1E27]"></span>
                    <h5 class="text-xs font-semibold text-white tracking-wider">删除基地</h5>
                </div>
                <button type="button" id="closeLocationDeleteDrawer" class="text-[#616161] hover:text-white w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 p-5">
                <p class="text-xs text-[#9e9e9e] mb-2">确认删除基地</p>
                <p id="locationDeleteName" class="text-sm font-semibold text-white font-mono"></p>
                <p class="text-[11px] text-[#555555] mt-3">仍被引用时无法删除。此操作不可恢复。</p>
            </div>
            <div class="px-5 py-3 border-t border-[#2c2c2c] flex items-center justify-end gap-2 bg-[#16161a] shrink-0">
                <button type="button" id="cancelLocationDeleteBtn" class="px-4 py-1.5 text-xs text-[#9e9e9e] border border-[#2c2c2c]">取消</button>
                <button type="button" id="confirmLocationDeleteBtn" class="bg-[#c62828] hover:bg-[#b71c1c] text-white px-5 py-1.5 text-xs font-semibold">删除</button>
            </div>
        </div>

        <div class="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm" id="locationToggleBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[360px] bg-[#121215] border-l border-[#2c2c2c] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="locationToggleDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-[#2c2c2c] bg-[#16161a] shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-[#FF1E27]"></span>
                    <h5 class="text-xs font-semibold text-white tracking-wider" id="locationToggleTitle">确认禁用</h5>
                </div>
                <button type="button" id="closeLocationToggleDrawer" class="text-[#616161] hover:text-white w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 p-5">
                <p class="text-xs text-[#9e9e9e] mb-2" id="locationToggleLead">确认禁用基地</p>
                <p id="locationToggleName" class="text-sm font-semibold text-white font-mono"></p>
                <p class="text-[11px] text-[#555555] mt-3" id="locationToggleHint">禁用后不能再按此基地写入或开引擎；列表筛选仍可见。</p>
            </div>
            <div class="px-5 py-3 border-t border-[#2c2c2c] flex items-center justify-end gap-2 bg-[#16161a] shrink-0">
                <button type="button" id="cancelLocationToggleBtn" class="px-4 py-1.5 text-xs text-[#9e9e9e] border border-[#2c2c2c]">取消</button>
                <button type="button" id="confirmLocationToggleBtn" class="bg-[#FF1E27] hover:bg-[#d32f2f] text-white px-5 py-1.5 text-xs font-semibold">确认禁用</button>
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
            ? `<span class="text-[9px] font-medium tracking-[0.08em] text-[#555555]">启用</span>`
            : `<span class="text-[9px] font-medium tracking-[0.08em] text-[#3A3A42]">禁用</span>`;
        const aliases = Array.isArray(record.aliases) ? record.aliases.filter(Boolean) : [];
        const aliasText = aliases.length
            ? `<span class="text-[11px] text-[#8E8E93]">${esc(aliases.join('，'))}</span>`
            : `<span class="text-[11px] text-[#3A3A42]">—</span>`;
        const canUpdate = hasPermission('op:location:update');
        const canDelete = hasPermission('op:location:delete');
        const toggleLabel = isEnabled ? '禁用' : '启用';
        const name = esc(record.location);
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
        <tr class="group relative font-mono text-[11px] border-b border-[#141418] hover:bg-[#161620] transition-colors duration-100" data-location="${name}">
            <td class="p-0 relative">
                <div class="absolute left-0 top-0 bottom-0 w-[2px] bg-[#FF1E27] opacity-0 group-hover:opacity-70 transition-opacity"></div>
            </td>
            <td class="px-2 py-2 overflow-hidden">
                <div class="text-[14px] font-bold text-[#F0F0F2] truncate">${name}</div>
            </td>
            <td class="px-2 py-2 overflow-hidden">${aliasText}</td>
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
