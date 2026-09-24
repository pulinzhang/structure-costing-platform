/**
 * 供应商一览 — HUD 密表 + 抽屉；有搜索 / 分页 / 导出
 */

import { HUD_SHELL, DRAWER_SHELL, DRAWER_BACKDROP, HUD_BAND, OPS_TH, BTN_HUD_CREATE, BTN_HUD_SAVE, BTN_HUD_CHIP, BTN_GHOST, BTN_SOLID, BTN_SOLID_DANGER } from '../../../../ui/classes.js?v=13';
import { hudTableHtml, hudRowHtml, opsIconButtonHtml } from '../../../../ui/hud-table.js?v=2';

import { moreMenuItemHtml, moreMenuShellHtml } from '../../../../ui/more-menu.js?v=6';

export function supplierListTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="${HUD_SHELL}">
                <div class="${HUD_BAND}">
                    <div class="flex items-start justify-between gap-4 mb-3">
                        <div class="min-w-0">
                            <h2 class="text-[13px] font-semibold text-ink tracking-wide">供应商</h2>
                            <p class="mt-1 text-[11px] text-ink-faint">缩写显示在页面上，全称用来对表头。停用之后不能再选用。</p>
                        </div>
                        <div class="flex items-center gap-1.5 shrink-0">
                            ${moreMenuShellHtml({
                                wrapId: 'supplierMoreWrap',
                                btnId: 'supplierMoreBtn',
                                menuId: 'supplierMoreMenu',
                                itemsHtml: moreMenuItemHtml({ id: 'supplierBtnExport', label: '导出' }),
                            })}
                            <button id="supplierBtnCreate" type="button"
                                    class="${BTN_HUD_CREATE}">
                                ${window.svgIcon('plus', 'w-3.5 h-3.5')}
                                新增
                            </button>
                        </div>
                    </div>
                    <div class="flex flex-wrap items-center gap-2">
                        <div class="relative flex-1 min-w-[220px] max-w-sm">
                            <span class="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none text-ink-faint">
                                ${window.svgIcon('search', 'w-3.5 h-3.5')}
                            </span>
                            <input type="text" id="supplierFilterKeyword" placeholder="缩写 / 全称 / 对外代码 / 别名"
                                   class="w-full h-8 pl-8 pr-3 text-[11px] font-mono bg-app-hud border border-line-hud text-ink placeholder:text-ink-faint focus:outline-none focus:border-brand-hud rounded-sm">
                        </div>
                        <div class="flex items-center gap-1.5">
                            <button type="button" data-enabled-filter="" class="supplier-status-capsule px-2 py-0.5 text-[10px] font-mono rounded-md border border-brand-hud/50 bg-brand-hud/10 text-ink">全部</button>
                            <button type="button" data-enabled-filter="true" class="supplier-status-capsule px-2 py-0.5 text-[10px] font-mono rounded-md border border-line-hud text-ink-muted hover:text-ink">已启用</button>
                            <button type="button" data-enabled-filter="false" class="supplier-status-capsule px-2 py-0.5 text-[10px] font-mono rounded-md border border-line-hud text-ink-muted hover:text-ink">已禁用</button>
                        </div>
                    </div>
                </div>

                ${hudTableHtml({
                    prefix: 'supplier',
                    minWidth: '860px',
                    colgroupHtml: `
                            <col style="width: 8px;">
                            <col style="width: 12%;">
                            <col style="width: 28%;">
                            <col style="width: 12%;">
                            <col>
                            <col style="width: 72px;">
                            <col style="width: 120px;">`,
                    headHtml: `
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">缩写</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-ink-faint">全称</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-ink-faint">对外代码</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-ink-faint">别名</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-ink-faint">状态</th>
                                <th class="${OPS_TH}" aria-label="操作"></th>`,
                    empty: {
                        title: '暂无供应商',
                        hint: '点右上角新增，或从上传页补档',
                        showIcon: false,
                        className: 'py-16 text-center bg-app-hud',
                    },
                    loading: { label: '加载中..', className: 'flex-col gap-2 bg-app-hud' },
                })}
            </div>
        </div>

        <div class="${DRAWER_BACKDROP}" id="supplierCreateBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[420px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="supplierCreateDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-line bg-app-surface shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-brand-hud"></span>
                    <h5 class="text-xs font-semibold text-ink tracking-wider">新增供应商</h5>
                </div>
                <button type="button" id="closeSupplierCreateDrawer" class="text-ink-dim hover:text-ink w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-5">
                <form id="supplierCreateForm" class="space-y-4">
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">缩写 <span class="text-brand-hud">*</span></label>
                        <input type="text" id="supplierCreateAbbreviation" required maxlength="50"
                               placeholder="例如：常庆"
                               class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">全称 <span class="text-brand-hud">*</span></label>
                        <input type="text" id="supplierCreateFullName" required maxlength="100"
                               placeholder="与营业执照一致"
                               class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">对外代码 <span class="text-brand-hud">*</span></label>
                        <input type="text" id="supplierCreateErpCode" required maxlength="50"
                               placeholder="给外部系统用的代码"
                               class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">别名</label>
                        <textarea id="supplierCreateAliases" rows="3"
                                  placeholder="每行一个，可空；吸收工艺表头乱写"
                                  class="w-full px-3 py-2 text-xs bg-app-hud border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active resize-y"></textarea>
                    </div>
                </form>
            </div>
            <div class="px-5 py-3 border-t border-line flex items-center justify-end gap-2 bg-app-surface shrink-0">
                <button type="button" id="cancelSupplierCreateBtn" class="${BTN_GHOST}">取消</button>
                <button type="button" id="submitSupplierCreateBtn" class="${BTN_SOLID}">保存</button>
            </div>
        </div>

        <div class="${DRAWER_BACKDROP}" id="supplierEditBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[420px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="supplierEditDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-line bg-app-surface shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-brand-hud"></span>
                    <h5 class="text-xs font-semibold text-ink tracking-wider">编辑供应商</h5>
                </div>
                <button type="button" id="closeSupplierEditDrawer" class="text-ink-dim hover:text-ink w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-5 space-y-4">
                <div>
                    <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">缩写</label>
                    <input type="text" id="supplierEditAbbreviation" maxlength="50"
                           class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-ink focus:outline-none focus:border-brand-active">
                </div>
                <div>
                    <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">全称</label>
                    <input type="text" id="supplierEditFullName" maxlength="100"
                           class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-ink focus:outline-none focus:border-brand-active">
                </div>
                <div>
                    <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">对外代码</label>
                    <input type="text" id="supplierEditErpCode" maxlength="50"
                           class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-ink focus:outline-none focus:border-brand-active">
                    <p class="text-[10px] text-ink-faint mt-1">改全称成功后旧名收成别名；仍被引用则不能改</p>
                </div>
                <div>
                    <div class="flex items-center justify-between mb-2">
                        <span class="text-[10px] font-semibold text-ink-dim tracking-wider">别名</span>
                        <span id="supplierEditAliasCount" class="font-mono text-[10px] text-ink-faint"></span>
                    </div>
                    <div class="border border-line bg-app-hud">
                        <ul id="supplierEditAliasList" class="divide-y divide-line-subtle"></ul>
                    </div>
                </div>
            </div>
            <div class="px-5 py-3 border-t border-line bg-app-surface shrink-0 space-y-2">
                <form id="supplierEditAliasForm" class="flex items-center gap-2">
                    <input type="text" id="supplierEditAliasInput" maxlength="100" placeholder="新别名，例如：常庆汽配"
                           class="flex-1 min-w-0 h-8 px-3 text-xs bg-app-hud border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active">
                    <button type="submit" id="submitSupplierEditAliasBtn" class="${BTN_HUD_CHIP} shrink-0">添加</button>
                </form>
                <div class="flex justify-end">
                    <button type="button" id="submitSupplierEditBtn" class="${BTN_SOLID}">保存资料</button>
                </div>
            </div>
        </div>

        <div class="${DRAWER_BACKDROP}" id="supplierToggleBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[360px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="supplierToggleDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-line bg-app-surface shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-brand-hud"></span>
                    <h5 class="text-xs font-semibold text-ink tracking-wider" id="supplierToggleTitle">确认禁用</h5>
                </div>
                <button type="button" id="closeSupplierToggleDrawer" class="text-ink-dim hover:text-ink w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 p-5">
                <p class="text-xs text-ink-muted mb-2" id="supplierToggleLead">确认禁用供应商</p>
                <p id="supplierToggleName" class="text-sm font-semibold text-ink font-mono"></p>
                <p class="text-[11px] text-ink-faint mt-3" id="supplierToggleHint">禁用后不能再按此供应商新引入；列表筛选仍可见。</p>
            </div>
            <div class="px-5 py-3 border-t border-line flex items-center justify-end gap-2 bg-app-surface shrink-0">
                <button type="button" id="cancelSupplierToggleBtn" class="${BTN_GHOST}">取消</button>
                <button type="button" id="confirmSupplierToggleBtn" class="${BTN_HUD_SAVE}">确认禁用</button>
            </div>
        </div>

        <div class="${DRAWER_BACKDROP}" id="supplierDeleteBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[360px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="supplierDeleteDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-line bg-app-surface shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-brand-hud"></span>
                    <h5 class="text-xs font-semibold text-ink tracking-wider">删除供应商</h5>
                </div>
                <button type="button" id="closeSupplierDeleteDrawer" class="text-ink-dim hover:text-ink w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 p-5">
                <p class="text-xs text-ink-muted mb-2">确认删除供应商</p>
                <p id="supplierDeleteName" class="text-sm font-semibold text-ink font-mono"></p>
                <p class="text-[11px] text-ink-faint mt-3">仍被引用则不能删除。别名会一并删除。</p>
            </div>
            <div class="px-5 py-3 border-t border-line flex items-center justify-end gap-2 bg-app-surface shrink-0">
                <button type="button" id="cancelSupplierDeleteBtn" class="${BTN_GHOST}">取消</button>
                <button type="button" id="confirmSupplierDeleteBtn" class="${BTN_SOLID_DANGER}">删除</button>
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
            ? `<span class="text-[9px] font-medium tracking-[0.08em] text-ink-faint">启用</span>`
            : `<span class="text-[9px] font-medium tracking-[0.08em] text-ink-faint">禁用</span>`;
        const aliases = Array.isArray(record.aliases) ? record.aliases.filter(Boolean) : [];
        const aliasText = aliases.length
            ? `<span class="text-[11px] text-ink-muted">${esc(aliases.join(', '))}</span>`
            : `<span class="text-[11px] text-ink-faint">—</span>`;
        const canUpdate = hasPermission('op:supplier-list:update');
        const canDelete = hasPermission('op:supplier-list:delete');
        const toggleLabel = isEnabled ? '禁用' : '启用';
        const fullName = esc(record.full_name);
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
            attrs: `data-full-name="${fullName}"`,
            cellsHtml: `
            <td class="px-2 py-2 overflow-hidden">
                <div class="text-[14px] font-bold text-ink truncate">${esc(record.abbreviation)}</div>
            </td>
            <td class="px-2 py-2 overflow-hidden">
                <div class="text-[11px] text-ink-muted truncate" title="${fullName}">${fullName}</div>
            </td>
            <td class="px-2 py-2 overflow-hidden">
                <span class="text-[10px] text-ink-muted tabular-nums">${esc(record.erp_code)}</span>
            </td>
            <td class="px-2 py-2 overflow-hidden truncate">${aliasText}</td>
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
