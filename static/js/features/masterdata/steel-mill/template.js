/**
 * 钢厂档案 — HUD 密表 + 抽屉。无导入、无导出。
 */

import { HUD_SHELL, DRAWER_SHELL, DRAWER_BACKDROP, HUD_BAND, OPS_TH, BTN_HUD_CREATE, BTN_GHOST, BTN_SOLID, BTN_SOLID_DANGER } from '../../../ui/classes.js?v=13';
import { hudTableHtml, hudRowHtml, opsIconButtonHtml } from '../../../ui/hud-table.js?v=2';

export function steelMillTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="${HUD_SHELL}">
                <div class="${HUD_BAND}">
                    <div class="flex items-start justify-between gap-4 mb-3">
                        <div class="min-w-0">
                            <h2 class="text-[13px] font-semibold text-ink tracking-wide">钢厂</h2>
                            <p class="mt-1 text-[11px] text-ink-faint">缩写显示在页面上，全称用来对表头。停用之后不能再选用。</p>
                        </div>
                        <button id="steelMillBtnCreate" type="button" class="${BTN_HUD_CREATE} shrink-0">
                            ${window.svgIcon('plus', 'w-3.5 h-3.5')}
                            新增
                        </button>
                    </div>
                    <div class="flex flex-wrap items-center gap-2">
                        <div class="relative flex-1 min-w-[220px] max-w-sm">
                            <span class="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none text-ink-faint">
                                ${window.svgIcon('search', 'w-3.5 h-3.5')}
                            </span>
                            <input type="text" id="steelMillFilterKeyword" placeholder="缩写 / 全称 / 别名"
                                   class="w-full h-8 pl-8 pr-3 text-[11px] font-mono bg-app-hud border border-line-hud text-ink placeholder:text-ink-faint focus:outline-none focus:border-brand-hud rounded-sm">
                        </div>
                        <div class="flex items-center gap-1.5">
                            <button type="button" data-enabled-filter="" class="steel-mill-status-capsule px-2 py-0.5 text-[10px] font-mono rounded-md border border-brand-hud/50 bg-brand-hud/10 text-ink">全部</button>
                            <button type="button" data-enabled-filter="true" class="steel-mill-status-capsule px-2 py-0.5 text-[10px] font-mono rounded-md border border-line-hud text-ink-muted hover:text-ink">已启用</button>
                            <button type="button" data-enabled-filter="false" class="steel-mill-status-capsule px-2 py-0.5 text-[10px] font-mono rounded-md border border-line-hud text-ink-muted hover:text-ink">已禁用</button>
                        </div>
                    </div>
                </div>

                ${hudTableHtml({
                    prefix: 'steelMill',
                    minWidth: '760px',
                    colgroupHtml: `
                            <col style="width: 8px;">
                            <col style="width: 16%;">
                            <col style="width: 22%;">
                            <col>
                            <col style="width: 72px;">
                            <col style="width: 120px;">`,
                    headHtml: `
                                <th class="p-0"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">缩写</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-ink-faint">全称</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-ink-faint">别名</th>
                                <th class="px-2 py-2 text-center text-[9px] font-medium tracking-[0.06em] text-ink-faint">状态</th>
                                <th class="${OPS_TH}" aria-label="操作"></th>`,
                    empty: {
                        title: '暂无钢厂',
                        hint: '点右上角新增',
                        showIcon: false,
                        className: 'py-16 text-center bg-app-hud',
                    },
                    loading: { label: '加载中..', className: 'flex-col gap-2 bg-app-hud' },
                })}
            </div>
        </div>

        <div class="${DRAWER_BACKDROP}" id="steelMillFormBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[420px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="steelMillFormDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-line bg-app-surface shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-brand-hud"></span>
                    <h5 id="steelMillFormTitle" class="text-xs font-semibold text-ink tracking-wider">新增钢厂</h5>
                </div>
                <button type="button" id="closeSteelMillFormDrawer" class="text-ink-dim hover:text-ink w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-5">
                <form id="steelMillForm" class="space-y-4">
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">缩写 <span class="text-brand-hud">*</span></label>
                        <input type="text" id="steelMillAbbreviation" required maxlength="50"
                               placeholder="页面上显示的字，例如：山钢"
                               class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">全称 <span class="text-brand-hud">*</span></label>
                        <input type="text" id="steelMillFullName" required maxlength="50"
                               placeholder="用来对表头，可与缩写相同"
                               class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">别名</label>
                        <textarea id="steelMillAliases" rows="4"
                                  placeholder="每行一个，例如：&#10;山钢(新)"
                                  class="w-full px-3 py-2 text-xs bg-app-hud border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active resize-y"></textarea>
                        <p class="text-[10px] text-ink-faint mt-1">别名不能与任何缩写或全称相同</p>
                    </div>
                    <label id="steelMillEnabledWrap" class="hidden flex items-center gap-2 text-[11px] text-ink-muted">
                        <input type="checkbox" id="steelMillEnabled" class="accent-brand-hud">
                        启用。停用之后不能再选用。
                    </label>
                </form>
            </div>
            <div class="px-5 py-3 border-t border-line flex items-center justify-end gap-2 bg-app-surface shrink-0">
                <button type="button" id="cancelSteelMillFormBtn" class="${BTN_GHOST}">取消</button>
                <button type="button" id="submitSteelMillFormBtn" class="${BTN_SOLID}">保存</button>
            </div>
        </div>

        <div class="${DRAWER_BACKDROP}" id="steelMillDeleteBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[420px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="steelMillDeleteDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-line bg-app-surface shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-brand-hud"></span>
                    <h5 class="text-xs font-semibold text-ink tracking-wider">删除钢厂</h5>
                </div>
                <button type="button" id="closeSteelMillDeleteDrawer" class="text-ink-dim hover:text-ink w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 p-5">
                <p class="text-xs text-ink-muted mb-2">确认删除钢厂</p>
                <p id="steelMillDeleteName" class="text-sm font-semibold text-ink font-mono"></p>
                <p class="text-[11px] text-ink-faint mt-3">仍被引用则不能删除。别名会一并删除。</p>
            </div>
            <div class="px-5 py-3 border-t border-line flex items-center justify-end gap-2 bg-app-surface shrink-0">
                <button type="button" id="cancelSteelMillDeleteBtn" class="${BTN_GHOST}">取消</button>
                <button type="button" id="confirmSteelMillDeleteBtn" class="${BTN_SOLID_DANGER}">删除</button>
            </div>
        </div>
    `;
}

export function renderSteelMillRows(records) {
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
            ? `<span class="text-[11px] text-ink-muted">${esc(aliases.join('、'))}</span>`
            : `<span class="text-[11px] text-ink-faint">—</span>`;
        const canUpdate = hasPermission('op:steel-mill:update');
        const canDelete = hasPermission('op:steel-mill:delete');
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
                title: isEnabled ? '禁用' : '启用',
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
            attrs: `data-id="${record.id}"`,
            cellsHtml: `
            <td class="px-2 py-2 overflow-hidden">
                <div class="text-[14px] font-bold text-ink truncate">${esc(record.abbreviation)}</div>
            </td>
            <td class="px-2 py-2 overflow-hidden">
                <div class="text-[11px] text-ink-muted truncate">${esc(record.full_name)}</div>
            </td>
            <td class="px-2 py-2 overflow-hidden truncate">${aliasText}</td>
            <td class="px-2 py-2 text-center whitespace-nowrap">${statusBadge}</td>`,
            opsHtml: `<div class="inline-flex items-center justify-center gap-0.5 whitespace-nowrap">${editBtn}${toggleBtn}${deleteBtn}</div>`,
        });
    }).join('');
}

function hasPermission(code) {
    if (typeof window.can === 'function') {
        return window.can(code);
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
