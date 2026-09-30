import { HUD_SHELL, DRAWER_SHELL, DRAWER_BACKDROP, HUD_BAND, OPS_TH, BTN_HUD_CREATE, BTN_HUD_SAVE, BTN_HUD_CHIP, BTN_GHOST, BTN_SOLID, BTN_SOLID_DANGER } from '../../../ui/classes.js?v=13';
import { hudTableHtml, hudRowHtml, opsIconButtonHtml } from '../../../ui/hud-table.js?v=3';
/**
 * 基地主数据 — HUD 密表 + 抽屉（无 KPI / 搜索 / 分页）
 */

export function locationTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="${HUD_SHELL}">
                <div class="${HUD_BAND}">
                    <div class="flex flex-col items-stretch gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
                        <div class="min-w-0">
                            <h2 class="text-[13px] font-semibold text-ink tracking-wide">基地</h2>
                            <p class="mt-1 text-[11px] text-ink-faint">核价作用域锚点；别名吸收表头乱写；启用后才能写入</p>
                        </div>
                        <button id="btnAddLocation" type="button"
                                class="${BTN_HUD_CREATE} shrink-0">
                            ${window.svgIcon('plus', 'w-3.5 h-3.5')}
                            新增
                        </button>
                    </div>
                </div>

                ${hudTableHtml({
                    prefix: 'location',
                    pagination: false,
                    minWidth: '640px',
                    colgroupHtml: `
                            <col style="width: 8px;">
                            <col style="width: 22%;">
                            <col>
                            <col style="width: 88px;">
                            <col style="width: 120px;">`,
                    headHtml: `
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">基地</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-ink-faint">别名</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-ink-faint">状态</th>
                                <th class="${OPS_TH}" aria-label="操作"></th>`,
                    empty: {
                        title: '暂无基地',
                        hint: '点右上角新增基地',
                        showIcon: false,
                        className: 'py-16 text-center bg-app-hud',
                    },
                    loading: { label: '加载中..', className: 'flex-col gap-2 bg-app-hud' },
                })}
            </div>
        </div>

        <div class="${DRAWER_BACKDROP}" id="locationCreateBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[420px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="locationCreateDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-line bg-app-surface shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-brand-hud"></span>
                    <h5 class="text-xs font-semibold text-ink tracking-wider">新增基地</h5>
                </div>
                <button type="button" id="closeLocationCreateDrawer" class="text-ink-dim hover:text-ink w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-5">
                <form id="locationCreateForm" class="space-y-4">
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">基地 <span class="text-brand-hud">*</span></label>
                        <input type="text" id="locationCreateName" required maxlength="50"
                               placeholder="例如：青岛"
                               class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active">
                        <p class="text-[10px] text-ink-faint mt-1">创建后不可改；默认启用</p>
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">别名 <span class="text-brand-hud">*</span></label>
                        <textarea id="locationCreateAliases" required rows="3"
                                  placeholder="每行一个，例如：&#10;青岛基地&#10;青岛厂"
                                  class="w-full px-3 py-2 text-xs bg-app-hud border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active resize-y"></textarea>
                        <p class="text-[10px] text-ink-faint mt-1">至少一条</p>
                    </div>
                </form>
            </div>
            <div class="px-5 py-3 border-t border-line flex items-center justify-end gap-2 bg-app-surface shrink-0">
                <button type="button" id="cancelLocationCreateBtn" class="${BTN_GHOST}">取消</button>
                <button type="button" id="submitLocationCreateBtn" class="${BTN_SOLID}">保存</button>
            </div>
        </div>

        <div class="${DRAWER_BACKDROP}" id="locationEditBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[420px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="locationEditDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-line bg-app-surface shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-brand-hud"></span>
                    <h5 class="text-xs font-semibold text-ink tracking-wider">编辑基地</h5>
                </div>
                <button type="button" id="closeLocationEditDrawer" class="text-ink-dim hover:text-ink w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-5 space-y-4">
                <div>
                    <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">基地</label>
                    <input type="text" id="locationEditName" readonly
                           class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-ink-muted cursor-not-allowed">
                    <p class="text-[10px] text-ink-faint mt-1">创建后不可改</p>
                </div>
                <div>
                    <div class="flex items-center justify-between mb-2">
                        <span class="text-[10px] font-semibold text-ink-dim tracking-wider">别名</span>
                        <span id="locationEditAliasCount" class="font-mono text-[10px] text-ink-faint"></span>
                    </div>
                    <div class="border border-line bg-app-hud">
                        <ul id="locationEditAliasList" class="divide-y divide-line-subtle"></ul>
                    </div>
                </div>
            </div>
            <div class="px-5 py-3 border-t border-line bg-app-surface shrink-0">
                <form id="locationEditAliasForm" class="flex items-center gap-2">
                    <input type="text" id="locationEditAliasInput" maxlength="50" placeholder="新别名，例如：青岛厂"
                           class="flex-1 min-w-0 h-8 px-3 text-xs bg-app-hud border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active">
                    <button type="submit" id="submitLocationEditAliasBtn" class="${BTN_HUD_CHIP} shrink-0">添加</button>
                </form>
            </div>
        </div>

        <div class="${DRAWER_BACKDROP}" id="locationDeleteBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[360px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="locationDeleteDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-line bg-app-surface shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-brand-hud"></span>
                    <h5 class="text-xs font-semibold text-ink tracking-wider">删除基地</h5>
                </div>
                <button type="button" id="closeLocationDeleteDrawer" class="text-ink-dim hover:text-ink w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 p-5">
                <p class="text-xs text-ink-muted mb-2">确认删除基地</p>
                <p id="locationDeleteName" class="text-sm font-semibold text-ink font-mono"></p>
                <p class="text-[11px] text-ink-faint mt-3">仍被引用时无法删除。此操作不可恢复。</p>
            </div>
            <div class="px-5 py-3 border-t border-line flex items-center justify-end gap-2 bg-app-surface shrink-0">
                <button type="button" id="cancelLocationDeleteBtn" class="${BTN_GHOST}">取消</button>
                <button type="button" id="confirmLocationDeleteBtn" class="${BTN_SOLID_DANGER}">删除</button>
            </div>
        </div>

        <div class="${DRAWER_BACKDROP}" id="locationToggleBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[360px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="locationToggleDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-line bg-app-surface shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-brand-hud"></span>
                    <h5 class="text-xs font-semibold text-ink tracking-wider" id="locationToggleTitle">确认禁用</h5>
                </div>
                <button type="button" id="closeLocationToggleDrawer" class="text-ink-dim hover:text-ink w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 p-5">
                <p class="text-xs text-ink-muted mb-2" id="locationToggleLead">确认禁用基地</p>
                <p id="locationToggleName" class="text-sm font-semibold text-ink font-mono"></p>
                <p class="text-[11px] text-ink-faint mt-3" id="locationToggleHint">禁用后不能再按此基地写入或开引擎；列表筛选仍可见。</p>
            </div>
            <div class="px-5 py-3 border-t border-line flex items-center justify-end gap-2 bg-app-surface shrink-0">
                <button type="button" id="cancelLocationToggleBtn" class="${BTN_GHOST}">取消</button>
                <button type="button" id="confirmLocationToggleBtn" class="${BTN_HUD_SAVE}">确认禁用</button>
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
            ? `<span class="text-[9px] font-medium tracking-[0.08em] text-ink-faint">启用</span>`
            : `<span class="text-[9px] font-medium tracking-[0.08em] text-ink-faint">禁用</span>`;
        const aliases = Array.isArray(record.aliases) ? record.aliases.filter(Boolean) : [];
        const aliasText = aliases.length
            ? `<span class="text-[11px] text-ink-muted">${esc(aliases.join('，'))}</span>`
            : `<span class="text-[11px] text-ink-faint">—</span>`;
        const canUpdate = hasPermission('op:location:update');
        const canDelete = hasPermission('op:location:delete');
        const toggleLabel = isEnabled ? '禁用' : '启用';
        const name = esc(record.location);
        const editBtn = canUpdate
            ? opsIconButtonHtml({
                action: 'edit',
                title: '编辑',
                icon: window.svgIcon('pencil', 'w-3.5 h-3.5'),
            })
            : '';
        const toggleBtn = canUpdate
            ? opsIconButtonHtml({
                action: 'toggle',
                title: toggleLabel,
                icon: window.svgIcon(isEnabled ? 'ban' : 'check-circle', 'w-3.5 h-3.5'),
                attrs: `data-enabled="${isEnabled ? '1' : '0'}"`,
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
        return hudRowHtml({
            attrs: `data-location="${name}"`,
            cellsHtml: `
            <td class="px-2 py-2 overflow-hidden">
                <div class="text-[14px] font-bold text-ink truncate">${name}</div>
            </td>
            <td class="px-2 py-2 overflow-hidden">${aliasText}</td>
            <td class="px-2 py-2 text-center whitespace-nowrap">${statusBadge}</td>`,
            opsHtml: `<div class="inline-flex items-center justify-center gap-0.5 whitespace-nowrap">${editBtn}${toggleBtn}${deleteBtn}</div>`,
        });
    }).join('');
}

export function renderAliasItems(aliases, canUpdate) {
    const items = Array.isArray(aliases) ? aliases.filter(Boolean) : [];
    if (!items.length) {
        return `<li class="px-3 py-8 text-center text-[11px] text-ink-faint">暂无别名</li>`;
    }
    return items.map((alias) => {
        const deleteBtn = canUpdate
            ? `<button type="button" data-action="delete-alias" data-alias="${esc(alias)}" class="w-7 h-7 inline-flex items-center justify-center text-ink-faint hover:text-danger transition-all" title="删除别名">${window.svgIcon('trash', 'w-3.5 h-3.5')}</button>`
            : '';
        return `<li class="flex items-center gap-2 px-3 h-9 hover:bg-app-rowhover transition-colors">
            <span class="flex-1 min-w-0 font-mono text-[11px] text-ink truncate" title="${esc(alias)}">${esc(alias)}</span>
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
