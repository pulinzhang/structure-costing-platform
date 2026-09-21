/**
 * 项目一览 — HUD 密表，按基地分卡 / 分段
 */

import { moreMenuItemHtml, moreMenuShellHtml } from '../../../../ui/more-menu.js?v=3';
import { HUD_SHELL, DRAWER_SHELL, DRAWER_BACKDROP, HUD_BAND, OPS_TH } from '../../../../ui/classes.js?v=8';
import { hudTableHtml, hudRowHtml, opsIconButtonHtml } from '../../../../ui/hud-table.js?v=1';


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
            <div class="${HUD_SHELL}">
                <div class="${HUD_BAND}">
                    <div class="flex items-start justify-between gap-4 mb-3">
                        <div id="vmHudCards" class="flex flex-wrap gap-2 flex-1 min-w-0"></div>
                        <div class="flex items-center gap-1.5 shrink-0">
                            ${moreMenuShellHtml({
                                wrapId: 'vmMoreWrap',
                                btnId: 'vmMoreBtn',
                                menuId: 'vmMoreMenu',
                                itemsHtml: moreMenuItemHtml({ id: 'vmBtnExport', label: '导出' }),
                            })}
                            <button id="vmBtnCreate" type="button"
                                    class="inline-flex items-center gap-1.5 bg-brand-hud hover:bg-brand text-white px-3 py-1.5 text-[11px] font-semibold rounded-md transition-all">
                                ${window.svgIcon('plus', 'w-3.5 h-3.5')}
                                新增
                            </button>
                        </div>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="text-[10px] text-ink-faint tracking-wider">筛选</span>
                        <span id="vmFilterCapsule" class="px-2 py-0.5 text-[10px] font-mono rounded-md border border-line-hud text-ink-muted">全部基地</span>
                    </div>
                </div>

                ${hudTableHtml({
                    prefix: 'vm',
                    pagination: false,
                    minWidth: '820px',
                    colgroupHtml: `
                            <col style="width: 8px;">
                            <col>
                            <col style="width: 140px;">
                            <col style="width: 140px;">
                            <col style="width: 120px;">
                            <col style="width: 88px;">
                            <col style="width: 88px;">`,
                    headHtml: `
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">项目代号</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-faint">生效年月</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-faint">失效年月</th>
                                <th class="px-2 py-2 text-right text-[9px] font-medium tracking-[0.06em] text-ink-faint">当前供货台数</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-ink-faint">该月状态</th>
                                <th class="${OPS_TH}" aria-label="操作"></th>`,
                    empty: {
                        title: '暂无项目',
                        hint: '点右上角新增，或从上传页补档',
                        showIcon: false,
                        className: 'py-16 text-center',
                    },
                    loading: { label: '加载中..', className: 'flex-col gap-2' },
                })}
            </div>
        </div>

        <div class="${DRAWER_BACKDROP}" id="vmCreateBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[420px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="vmCreateDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-line bg-app-surface shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-brand-hud"></span>
                    <h5 class="text-xs font-semibold text-white tracking-wider">新增项目</h5>
                </div>
                <button type="button" id="vmCloseCreate" class="text-ink-dim hover:text-ink w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-5">
                <form id="vmCreateForm" class="space-y-4">
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">基地 <span class="text-brand-hud">*</span></label>
                        <select id="vmCreateLocation" required
                                class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-white focus:outline-none focus:border-brand-active"></select>
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">项目代号 <span class="text-brand-hud">*</span></label>
                        <input type="text" id="vmCreateCode" required maxlength="50" placeholder="例如：T13J"
                               class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-white placeholder:text-ink-dim focus:outline-none focus:border-brand-active">
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">生效年 <span class="text-brand-hud">*</span></label>
                            <select id="vmCreateEffectiveYear" class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-white focus:outline-none focus:border-brand-active"></select>
                        </div>
                        <div>
                            <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">生效月 <span class="text-brand-hud">*</span></label>
                            <select id="vmCreateEffectiveMonth" class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-white focus:outline-none focus:border-brand-active"></select>
                        </div>
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">失效年</label>
                            <select id="vmCreateExpiryYear" class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-white focus:outline-none focus:border-brand-active">
                                <option value="">尚未失效</option>
                            </select>
                        </div>
                        <div>
                            <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">失效月</label>
                            <select id="vmCreateExpiryMonth" class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-white focus:outline-none focus:border-brand-active">
                                <option value="">—</option>
                            </select>
                        </div>
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">当前供货台数 <span class="text-brand-hud">*</span></label>
                        <input type="number" id="vmCreateSuppliedUnits" min="0" step="1" value="0"
                               class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-white placeholder:text-ink-dim focus:outline-none focus:border-brand-active">
                        <p class="text-[10px] text-ink-faint mt-1">单位：台。日后模具费等分摊到达上限后不再摊。</p>
                    </div>
                </form>
            </div>
            <div class="px-5 py-3 border-t border-line flex items-center justify-end gap-2 bg-app-surface shrink-0">
                <button type="button" id="vmCancelCreate" class="px-4 py-1.5 text-xs text-ink-muted border border-line hover:text-ink">取消</button>
                <button type="button" id="vmSubmitCreate" class="bg-brand-hud hover:bg-brand text-white px-5 py-1.5 text-xs font-semibold">保存</button>
            </div>
        </div>

        <div class="${DRAWER_BACKDROP}" id="vmEditBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[420px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="vmEditDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-line bg-app-surface shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-brand-hud"></span>
                    <h5 class="text-xs font-semibold text-white tracking-wider">编辑项目</h5>
                </div>
                <button type="button" id="vmCloseEdit" class="text-ink-dim hover:text-ink w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-5 space-y-4">
                <div>
                    <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">基地</label>
                    <input type="text" id="vmEditLocation" readonly
                           class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-ink-muted cursor-not-allowed">
                </div>
                <div>
                    <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">项目代号</label>
                    <input type="text" id="vmEditCode" readonly
                           class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-ink-muted cursor-not-allowed">
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">生效年</label>
                        <select id="vmEditEffectiveYear" class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-white focus:outline-none focus:border-brand-active"></select>
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">生效月</label>
                        <select id="vmEditEffectiveMonth" class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-white focus:outline-none focus:border-brand-active"></select>
                    </div>
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">失效年</label>
                        <select id="vmEditExpiryYear" class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-white focus:outline-none focus:border-brand-active"></select>
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">失效月</label>
                        <select id="vmEditExpiryMonth" class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-white focus:outline-none focus:border-brand-active"></select>
                    </div>
                </div>
                <div>
                    <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">当前供货台数</label>
                    <input type="number" id="vmEditSuppliedUnits" min="0" step="1"
                           class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-white focus:outline-none focus:border-brand-active">
                    <p class="text-[10px] text-ink-faint mt-1">单位：台。日后模具费等分摊到达上限后不再摊。</p>
                </div>
            </div>
            <div class="px-5 py-3 border-t border-line flex items-center justify-end gap-2 bg-app-surface shrink-0">
                <button type="button" id="vmCancelEdit" class="px-4 py-1.5 text-xs text-ink-muted border border-line hover:text-ink">取消</button>
                <button type="button" id="vmSubmitEdit" class="bg-brand-hud hover:bg-brand text-white px-5 py-1.5 text-xs font-semibold">保存</button>
            </div>
        </div>

        <div class="${DRAWER_BACKDROP}" id="vmDeleteBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[360px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="vmDeleteDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-line bg-app-surface shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-brand-hud"></span>
                    <h5 class="text-xs font-semibold text-white tracking-wider">删除项目</h5>
                </div>
                <button type="button" id="vmCloseDelete" class="text-ink-dim hover:text-ink w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 p-5">
                <p class="text-xs text-ink-muted mb-2">确认删除项目</p>
                <p id="vmDeleteLead" class="text-sm font-semibold text-white"></p>
                <p class="text-[11px] text-ink-faint mt-3">仍被引用时无法删除。</p>
            </div>
            <div class="px-5 py-3 border-t border-line flex items-center justify-end gap-2 bg-app-surface shrink-0">
                <button type="button" id="vmCancelDelete" class="px-4 py-1.5 text-xs text-ink-muted border border-line">取消</button>
                <button type="button" id="vmConfirmDelete" class="bg-danger hover:bg-brand-hover text-white px-5 py-1.5 text-xs font-semibold">删除</button>
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
        ? 'border-brand-hud/50 bg-brand-hud/10'
        : 'border-line-hud bg-app-main/80';
    const cards = [`
        <button type="button" data-action="filter-all"
                class="text-left min-w-[140px] p-3 border ${allActive} transition-colors">
            <div class="text-[10px] tracking-wider text-ink-faint">全部 · ${esc(period)}</div>
            <div class="mt-1 text-[18px] font-bold tabular-nums text-ink">${totalProjects}
                <span class="text-[10px] text-ink-faint font-medium ml-1">项目</span>
            </div>
            <div class="text-[10px] text-ink-muted mt-1">该月可引入 ${totalIntroducible}</div>
        </button>
    `];
    locations.forEach((card) => {
        const selected = filterLocation === card.location
            ? 'border-brand-hud/50 bg-brand-hud/10'
            : 'border-line-hud bg-app-main/80';
        const disabled = card.is_enabled ? '' : 'opacity-60';
        const intro = card.is_enabled ? String(card.introducible_count ?? 0) : '—';
        const disabledLabel = card.is_enabled
            ? ''
            : '<span class="text-[9px] text-danger ml-1">已禁用</span>';
        cards.push(`
            <button type="button" data-action="filter-location" data-location="${esc(card.location)}"
                    class="text-left min-w-[140px] p-3 border ${selected} ${disabled} transition-colors">
                <div class="text-[10px] tracking-wider text-ink-faint">${esc(card.location)}${disabledLabel}</div>
                <div class="mt-1 text-[18px] font-bold tabular-nums text-ink">${card.project_count || 0}
                    <span class="text-[10px] text-ink-faint font-medium ml-1">项目</span>
                </div>
                <div class="text-[10px] text-ink-muted mt-1">该月可引入 ${intro}</div>
                <div class="text-[9px] text-ink-faint mt-0.5">未生效 ${card.pending_count || 0} · 已失效 ${card.expired_count || 0}</div>
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

    const numCell = 'px-2 py-2 font-mono text-[10px] text-right tabular-nums text-ink-muted';
    const rows = [];
    sections.forEach((card) => {
        const disabledHint = card.is_enabled ? '' : '<span class="ml-2 text-[9px] text-danger">已禁用</span>';
        rows.push(`
            <tr class="bg-app-hud border-b border-line-subtle">
                <td class="p-0"></td>
                <td colspan="6" class="px-2 py-1.5 text-[10px] tracking-[0.08em] text-ink-dim">
                    ${esc(card.location)}
                    <span class="text-ink-faint ml-2">${card.project_count} 项</span>
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
                ? opsIconButtonHtml({
                    action: 'edit',
                    title: '编辑',
                    icon: window.svgIcon('pencil', 'w-3.5 h-3.5'),
                })
                : '';
            const deleteBtn = canDelete
                ? opsIconButtonHtml({
                    action: 'delete',
                    danger: true,
                    title: '删除',
                    icon: window.svgIcon('trash', 'w-3.5 h-3.5'),
                })
                : '';
            rows.push(hudRowHtml({
                attrs: `data-location="${esc(row.location)}" data-vehicle-model="${esc(row.vehicle_model)}"`,
                cellsHtml: `
                    <td class="px-2 py-2 overflow-hidden">
                        <div class="text-[14px] font-bold text-ink">${esc(row.vehicle_model)}</div>
                    </td>
                    <td class="${numCell}">${esc(effective)}</td>
                    <td class="${numCell}">${esc(expiry)}</td>
                    <td class="${numCell}">${esc(supplied)}<span class="text-[9px] text-ink-faint ml-1">台</span></td>
                    <td class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.08em] text-ink-faint">${esc(row.period_status)}</td>`,
                opsHtml: `<div class="inline-flex items-center justify-center gap-0.5 whitespace-nowrap">${editBtn}${deleteBtn}</div>`,
            }));
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
