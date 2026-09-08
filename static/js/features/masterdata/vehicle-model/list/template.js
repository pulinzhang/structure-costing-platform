/**
 * 项目一览 — HUD 密表，按基地分卡 / 分段
 */

function monthOptionsHtml(selected) {
    const items = [];
    for (let month = 1; month <= 12; month += 1) {
        const label = typeof fmtMonth === 'function' ? fmtMonth(month) : `${String(month).padStart(2, '0')}月`;
        const isSelected = Number(selected) === month ? ' selected' : '';
        items.push(`<option value="${month}"${isSelected}>${label}</option>`);
    }
    return items.join('');
}

function yearOptionsHtml(selected, extraYears) {
    const years = new Set(extraYears || []);
    const current = selected || new Date().getFullYear();
    years.add(current);
    for (let year = current - 3; year <= current + 8; year += 1) {
        years.add(year);
    }
    return [...years].sort((a, b) => a - b).map((year) => {
        const label = typeof fmtYear === 'function' ? fmtYear(year) : `${year}年`;
        const isSelected = Number(selected) === year ? ' selected' : '';
        return `<option value="${year}"${isSelected}>${label}</option>`;
    }).join('');
}

export function vehicleModelListTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="bg-[#0A0A0C] border border-[#1A1A22] overflow-hidden w-full max-w-full"
                 style="box-shadow: 0 4px 24px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.02);">
                <div class="px-5 pt-4 pb-3.5 border-b border-[#14141A]"
                     style="background: linear-gradient(135deg, #0E0E12 0%, #121218 45%, #0C0C10 100%);">
                    <div class="flex items-start justify-between gap-4 mb-3">
                        <div id="vmHudCards" class="flex flex-wrap gap-2 flex-1 min-w-0"></div>
                        <div class="flex items-center gap-2 shrink-0">
                            <button id="vmBtnExport" type="button"
                                    class="inline-flex items-center gap-1.5 bg-transparent text-[#8E8E93] border border-[#2A2A35] px-3 py-1.5 text-[11px] font-medium rounded-md hover:border-[#FF1E27]/50 hover:text-[#FF1E27] transition-all">
                                ${window.svgIcon('download', 'w-3 h-3')}
                                导出 Excel
                            </button>
                            <button id="vmBtnCreate" type="button"
                                    class="inline-flex items-center gap-1.5 bg-[#FF1E27] hover:bg-[#d32f2f] text-white px-3 py-1.5 text-[11px] font-semibold rounded-md transition-all">
                                ${window.svgIcon('plus', 'w-3.5 h-3.5')}
                                新增项目
                            </button>
                        </div>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="text-[10px] text-[#555555] tracking-wider">筛选</span>
                        <span id="vmFilterCapsule" class="px-2 py-0.5 text-[10px] font-mono rounded-md border border-[#2A2A35] text-[#8E8E93]">全部基地</span>
                    </div>
                </div>

                <div class="overflow-x-auto bg-[#0A0A0E] brabus-bg-grid">
                    <table class="w-full table-fixed bg-transparent border-collapse" style="min-width: 820px;">
                        <colgroup>
                            <col style="width: 8px;">
                            <col>
                            <col style="width: 140px;">
                            <col style="width: 140px;">
                            <col style="width: 120px;">
                            <col style="width: 88px;">
                            <col style="width: 88px;">
                        </colgroup>
                        <thead>
                            <tr class="border-b border-[#17171C] bg-[#0B0B0D]/95">
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-[#555555]">项目代号</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">生效年月</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">失效年月</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-[#555555]">当前供货台数</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">该月状态</th>
                                <th class="px-1 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-[#555555]">操作</th>
                            </tr>
                        </thead>
                        <tbody id="vmTableBody"></tbody>
                    </table>
                </div>
                <div id="vmEmptyState" class="hidden flex flex-col items-center justify-center py-16 text-center">
                    <p class="text-xs text-[#8E8E93] mb-1">暂无项目</p>
                    <p class="text-[11px] text-[#555555]">点右上角新增，或到上传页导入 Excel</p>
                </div>
                <div id="vmLoadingState" class="hidden flex flex-col items-center justify-center py-16 gap-2">
                    <div class="w-5 h-5 border-2 border-[#2c2c2c] border-t-[#FF1E27] rounded-full animate-spin"></div>
                    <span class="text-[11px] text-[#555555]">加载中..</span>
                </div>
            </div>
        </div>

        <div class="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm" id="vmCreateBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[420px] bg-[#121215] border-l border-[#2c2c2c] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="vmCreateDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-[#2c2c2c] bg-[#16161a] shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-[#FF1E27]"></span>
                    <h5 class="text-xs font-semibold text-white tracking-wider">新增项目</h5>
                </div>
                <button type="button" id="vmCloseCreate" class="text-[#616161] hover:text-white w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-5">
                <form id="vmCreateForm" class="space-y-4">
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">基地 <span class="text-[#FF1E27]">*</span></label>
                        <select id="vmCreateLocation" required
                                class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#ff5252]"></select>
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">项目代号 <span class="text-[#FF1E27]">*</span></label>
                        <input type="text" id="vmCreateCode" required maxlength="50" placeholder="例如：T13J"
                               class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252]">
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">生效年 <span class="text-[#FF1E27]">*</span></label>
                            <select id="vmCreateEffectiveYear" class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#ff5252]"></select>
                        </div>
                        <div>
                            <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">生效月 <span class="text-[#FF1E27]">*</span></label>
                            <select id="vmCreateEffectiveMonth" class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#ff5252]"></select>
                        </div>
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">失效年</label>
                            <select id="vmCreateExpiryYear" class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#ff5252]">
                                <option value="">尚未失效</option>
                            </select>
                        </div>
                        <div>
                            <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">失效月</label>
                            <select id="vmCreateExpiryMonth" class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#ff5252]">
                                <option value="">—</option>
                            </select>
                        </div>
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">当前供货台数 <span class="text-[#FF1E27]">*</span></label>
                        <input type="number" id="vmCreateSuppliedUnits" min="0" step="1" value="0"
                               class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white placeholder:text-[#616161] focus:outline-none focus:border-[#ff5252]">
                        <p class="text-[10px] text-[#555555] mt-1">单位：台。日后模具费等分摊到达上限后不再摊。</p>
                    </div>
                </form>
            </div>
            <div class="px-5 py-3 border-t border-[#2c2c2c] flex items-center justify-end gap-2 bg-[#16161a] shrink-0">
                <button type="button" id="vmCancelCreate" class="px-4 py-1.5 text-xs text-[#9e9e9e] border border-[#2c2c2c] hover:text-white">取消</button>
                <button type="button" id="vmSubmitCreate" class="bg-[#FF1E27] hover:bg-[#d32f2f] text-white px-5 py-1.5 text-xs font-semibold">保存</button>
            </div>
        </div>

        <div class="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm" id="vmEditBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[420px] bg-[#121215] border-l border-[#2c2c2c] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="vmEditDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-[#2c2c2c] bg-[#16161a] shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-[#FF1E27]"></span>
                    <h5 class="text-xs font-semibold text-white tracking-wider">编辑项目</h5>
                </div>
                <button type="button" id="vmCloseEdit" class="text-[#616161] hover:text-white w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-5 space-y-4">
                <div>
                    <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">基地</label>
                    <input type="text" id="vmEditLocation" readonly
                           class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-[#9e9e9e] cursor-not-allowed">
                </div>
                <div>
                    <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">项目代号</label>
                    <input type="text" id="vmEditCode" readonly
                           class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-[#9e9e9e] cursor-not-allowed">
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">生效年</label>
                        <select id="vmEditEffectiveYear" class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#ff5252]"></select>
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">生效月</label>
                        <select id="vmEditEffectiveMonth" class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#ff5252]"></select>
                    </div>
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">失效年</label>
                        <select id="vmEditExpiryYear" class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#ff5252]"></select>
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">失效月</label>
                        <select id="vmEditExpiryMonth" class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#ff5252]"></select>
                    </div>
                </div>
                <div>
                    <label class="text-[10px] font-semibold text-[#616161] tracking-wider mb-1 block">当前供货台数</label>
                    <input type="number" id="vmEditSuppliedUnits" min="0" step="1"
                           class="w-full h-8 px-3 text-xs bg-[#0a0a0c] border border-[#2c2c2c] text-white focus:outline-none focus:border-[#ff5252]">
                    <p class="text-[10px] text-[#555555] mt-1">单位：台。日后模具费等分摊到达上限后不再摊。</p>
                </div>
            </div>
            <div class="px-5 py-3 border-t border-[#2c2c2c] flex items-center justify-end gap-2 bg-[#16161a] shrink-0">
                <button type="button" id="vmCancelEdit" class="px-4 py-1.5 text-xs text-[#9e9e9e] border border-[#2c2c2c] hover:text-white">取消</button>
                <button type="button" id="vmSubmitEdit" class="bg-[#FF1E27] hover:bg-[#d32f2f] text-white px-5 py-1.5 text-xs font-semibold">保存</button>
            </div>
        </div>

        <div class="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm" id="vmDeleteBackdrop" style="display:none"></div>
        <div class="fixed inset-y-0 right-0 z-[85] w-[360px] bg-[#121215] border-l border-[#2c2c2c] transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col"
             id="vmDeleteDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-[#2c2c2c] bg-[#16161a] shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-[#FF1E27]"></span>
                    <h5 class="text-xs font-semibold text-white tracking-wider">删除项目</h5>
                </div>
                <button type="button" id="vmCloseDelete" class="text-[#616161] hover:text-white w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 p-5">
                <p class="text-xs text-[#9e9e9e] mb-2">确认删除项目</p>
                <p id="vmDeleteLead" class="text-sm font-semibold text-white"></p>
                <p class="text-[11px] text-[#555555] mt-3">仍被引用时无法删除。</p>
            </div>
            <div class="px-5 py-3 border-t border-[#2c2c2c] flex items-center justify-end gap-2 bg-[#16161a] shrink-0">
                <button type="button" id="vmCancelDelete" class="px-4 py-1.5 text-xs text-[#9e9e9e] border border-[#2c2c2c]">取消</button>
                <button type="button" id="vmConfirmDelete" class="bg-[#c62828] hover:bg-[#b71c1c] text-white px-5 py-1.5 text-xs font-semibold">删除</button>
            </div>
        </div>
    `;
}

export function renderHudCards(locations, filterLocation, asOfYear, asOfMonth) {
    const totalProjects = locations.reduce((sum, card) => sum + (card.project_count || 0), 0);
    const totalIntroducible = locations.reduce((sum, card) => sum + (card.introducible_count || 0), 0);
    const period = (typeof fmtPeriod === 'function')
        ? fmtPeriod(asOfYear, asOfMonth)
        : `${asOfYear}-${String(asOfMonth).padStart(2, '0')}`;
    const allActive = !filterLocation
        ? 'border-[#FF1E27]/50 bg-[#1A080A]'
        : 'border-[#1E1E26] bg-[#0D0D11]/80';
    const cards = [`
        <button type="button" data-action="filter-all"
                class="text-left min-w-[140px] p-3 border ${allActive} transition-colors">
            <div class="text-[10px] tracking-wider text-[#555555]">全部 · ${esc(period)}</div>
            <div class="mt-1 text-[18px] font-bold tabular-nums text-[#F0F0F2]">${totalProjects}
                <span class="text-[10px] text-[#555555] font-medium ml-1">项目</span>
            </div>
            <div class="text-[10px] text-[#8E8E93] mt-1">该月可引入 ${totalIntroducible}</div>
        </button>
    `];
    locations.forEach((card) => {
        const selected = filterLocation === card.location
            ? 'border-[#FF1E27]/50 bg-[#1A080A]'
            : 'border-[#1E1E26] bg-[#0D0D11]/80';
        const disabled = card.is_enabled ? '' : 'opacity-60';
        const intro = card.is_enabled ? String(card.introducible_count ?? 0) : '—';
        const disabledLabel = card.is_enabled
            ? ''
            : '<span class="text-[9px] text-[#ef5350] ml-1">已禁用</span>';
        cards.push(`
            <button type="button" data-action="filter-location" data-location="${esc(card.location)}"
                    class="text-left min-w-[140px] p-3 border ${selected} ${disabled} transition-colors">
                <div class="text-[10px] tracking-wider text-[#555555]">${esc(card.location)}${disabledLabel}</div>
                <div class="mt-1 text-[18px] font-bold tabular-nums text-[#F0F0F2]">${card.project_count || 0}
                    <span class="text-[10px] text-[#555555] font-medium ml-1">项目</span>
                </div>
                <div class="text-[10px] text-[#8E8E93] mt-1">该月可引入 ${intro}</div>
                <div class="text-[9px] text-[#3A3A42] mt-0.5">未生效 ${card.pending_count || 0} · 已失效 ${card.expired_count || 0}</div>
            </button>
        `);
    });
    return cards.join('');
}

export function renderTableBody(locations, items, filterLocation, canUpdate, canDelete) {
    const byLocation = new Map();
    items.forEach((row) => {
        const list = byLocation.get(row.location) || [];
        list.push(row);
        byLocation.set(row.location, list);
    });
    const sections = locations.filter((card) => {
        if (filterLocation && card.location !== filterLocation) return false;
        return (card.project_count || 0) > 0;
    });
    if (!sections.length) return '';

    const numCell = 'px-2 py-2 font-mono text-[10px] text-right tabular-nums text-[#8E8E93]';
    const rows = [];
    sections.forEach((card) => {
        const disabledHint = card.is_enabled ? '' : '<span class="ml-2 text-[9px] text-[#ef5350]">已禁用</span>';
        rows.push(`
            <tr class="bg-[#0B0B0D] border-b border-[#17171C]">
                <td class="p-0"></td>
                <td colspan="6" class="px-2 py-1.5 text-[10px] tracking-[0.08em] text-[#6E6E73]">
                    ${esc(card.location)}
                    <span class="text-[#3A3A42] ml-2">${card.project_count} 项</span>
                    ${disabledHint}
                </td>
            </tr>
        `);
        (byLocation.get(card.location) || []).forEach((row) => {
            const expiry = (row.expiry_year && row.expiry_month)
                ? (typeof fmtPeriod === 'function' ? fmtPeriod(row.expiry_year, row.expiry_month) : `${row.expiry_year}-${row.expiry_month}`)
                : '—';
            const effective = typeof fmtPeriod === 'function'
                ? fmtPeriod(row.effective_year, row.effective_month)
                : `${row.effective_year}-${row.effective_month}`;
            const supplied = (typeof fmtNum === 'function')
                ? fmtNum(row.current_supplied_units ?? 0, 0)
                : String(row.current_supplied_units ?? 0);
            const editBtn = canUpdate
                ? `<button type="button" data-action="edit" class="w-7 h-7 inline-flex items-center justify-center text-[#6E6E73] hover:text-[#FF1E27] opacity-0 group-hover:opacity-100 focus:opacity-100" title="编辑">${window.svgIcon('pencil', 'w-3.5 h-3.5')}</button>`
                : '';
            const deleteBtn = canDelete
                ? `<button type="button" data-action="delete" class="w-7 h-7 inline-flex items-center justify-center text-[#6E6E73] hover:text-[#ef5350] opacity-0 group-hover:opacity-100 focus:opacity-100" title="删除">${window.svgIcon('trash', 'w-3.5 h-3.5')}</button>`
                : '';
            rows.push(`
                <tr class="group relative font-mono text-[11px] border-b border-[#141418] hover:bg-[#161620] transition-colors duration-100"
                    data-location="${esc(row.location)}" data-vehicle-model="${esc(row.vehicle_model)}">
                    <td class="p-0 relative">
                        <div class="absolute left-0 top-0 bottom-0 w-[2px] bg-[#FF1E27] opacity-0 group-hover:opacity-70 transition-opacity"></div>
                    </td>
                    <td class="px-2 py-2 overflow-hidden">
                        <div class="text-[14px] font-bold text-[#F0F0F2]">${esc(row.vehicle_model)}</div>
                    </td>
                    <td class="${numCell}">${esc(effective)}</td>
                    <td class="${numCell}">${esc(expiry)}</td>
                    <td class="${numCell}">${esc(supplied)}<span class="text-[9px] text-[#3A3A42] ml-1">台</span></td>
                    <td class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.08em] text-[#555555]">${esc(row.period_status)}</td>
                    <td class="px-1 py-2 text-center whitespace-nowrap">${editBtn}${deleteBtn}</td>
                </tr>
            `);
        });
    });
    return rows.join('');
}

export function fillYearMonthSelects(prefix, effectiveYear, effectiveMonth, expiryYear, expiryMonth) {
    const extra = [effectiveYear, expiryYear].filter(Boolean);
    const effYear = document.getElementById(`${prefix}EffectiveYear`);
    const effMonth = document.getElementById(`${prefix}EffectiveMonth`);
    const expYear = document.getElementById(`${prefix}ExpiryYear`);
    const expMonth = document.getElementById(`${prefix}ExpiryMonth`);
    if (effYear) effYear.innerHTML = yearOptionsHtml(effectiveYear, extra);
    if (effMonth) effMonth.innerHTML = monthOptionsHtml(effectiveMonth);
    if (expYear) {
        expYear.innerHTML = `<option value="">尚未失效</option>${yearOptionsHtml(expiryYear, extra)}`;
        expYear.value = expiryYear ? String(expiryYear) : '';
    }
    if (expMonth) {
        expMonth.innerHTML = `<option value="">—</option>${monthOptionsHtml(expiryMonth)}`;
        expMonth.value = expiryMonth ? String(expiryMonth) : '';
    }
    if (effYear && effectiveYear) effYear.value = String(effectiveYear);
    if (effMonth && effectiveMonth) effMonth.value = String(effectiveMonth);
}
