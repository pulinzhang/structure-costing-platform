/**
 * 总成分类 — HUD 密表 + 抽屉增改
 */

import {
    HUD_SHELL,
    DRAWER_BACKDROP,
    DRAWER_SHELL,
    HUD_BAND,
    OPS_TH,
    BTN_HUD_CREATE,
    BTN_GHOST,
    BTN_SOLID,
} from '../../../ui/classes.js?v=15';
import { hudTableHtml, hudRowHtml, opsIconButtonHtml } from '../../../ui/hud-table.js?v=3';

function canOp(code) {
    return typeof window.can === 'function' ? window.can(code) : true;
}

export function assemblyCategoryTemplate() {
    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="${HUD_SHELL}">
                <div class="${HUD_BAND}">
                    <div class="flex flex-col items-stretch gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
                        <div>
                            <h2 class="text-[13px] font-semibold text-ink tracking-wide">总成分类</h2>
                            <p class="mt-1 text-[11px] text-ink-faint">冲压件、凸焊件、总成件、黑漆件。编码创建后不改</p>
                        </div>
                        <button type="button" id="acAddBtn" class="${BTN_HUD_CREATE}">
                            ${window.svgIcon('plus', 'w-3.5 h-3.5')}
                            新增
                        </button>
                    </div>
                    <div class="mt-3 flex flex-wrap items-center gap-2" id="acStatusBar">
                        <button type="button" class="ac-status" data-enabled="">全部</button>
                        <button type="button" class="ac-status" data-enabled="true">启用</button>
                        <button type="button" class="ac-status" data-enabled="false">已禁用</button>
                    </div>
                    <div class="mt-3 relative max-w-xs">
                        <span class="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none text-ink-faint">
                            ${window.svgIcon('search', 'w-3.5 h-3.5')}
                        </span>
                        <input type="text" id="acKeyword" placeholder="搜索编码或名称…"
                               class="w-full h-8 pl-8 pr-3 text-[11px] font-mono bg-app-hud border border-line-hud text-ink placeholder:text-ink-faint focus:outline-none focus:border-brand-hud rounded-sm">
                    </div>
                </div>
                ${hudTableHtml({
                    prefix: 'ac',
                    minWidth: '760px',
                    colgroupHtml: `
                            <col style="width: 8px;">
                            <col style="width: 10%;">
                            <col style="width: 22%;">
                            <col style="width: 22%;">
                            <col style="width: 12%;">
                            <col style="width: 18%;">
                            <col style="width: 88px;">`,
                    headHtml: `
                                <th class="p-0" aria-hidden="true"></th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-ink-faint">顺序</th>
                                <th class="record-key px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">名称</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-ink-faint">编码</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-ink-faint">状态</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-ink-faint">备注</th>
                                <th class="${OPS_TH}" aria-label="操作"></th>`,
                    empty: {
                        title: '暂无总成分类',
                        hint: '在本页手工新增',
                        showIcon: false,
                        className: 'py-16 text-center bg-app-hud',
                    },
                    loading: { label: '加载中..', className: 'flex-col gap-2 bg-app-hud' },
                })}
            </div>
        </div>

        <div class="${DRAWER_BACKDROP} transition-opacity" id="acFormBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[420px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="acFormDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-line bg-app-surface shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-brand-hud"></span>
                    <h5 class="text-xs font-semibold text-ink tracking-wider" id="acFormTitle">新增总成分类</h5>
                </div>
                <button type="button" id="acCloseForm" class="text-ink-dim hover:text-ink w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-5">
                <form id="acForm" class="space-y-4">
                    <div id="acCodeWrap">
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">编码 <span class="text-brand-hud">*</span></label>
                        <input type="text" id="acCode" maxlength="50" autocomplete="off"
                               class="w-full h-8 px-3 text-xs font-mono bg-app-hud border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active"
                               placeholder="如 stamping">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">名称 <span class="text-brand-hud">*</span></label>
                        <input type="text" id="acName" maxlength="50" autocomplete="off"
                               class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active"
                               placeholder="如 冲压件">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">顺序 <span class="text-brand-hud">*</span></label>
                        <input type="number" id="acSort" min="0" max="9999" step="1"
                               class="w-full h-8 px-3 text-xs font-mono bg-app-hud border border-line text-ink focus:outline-none focus:border-brand-active">
                    </div>
                    <div id="acEnabledWrap" class="hidden">
                        <label class="flex items-center gap-2 text-[11px] text-ink">
                            <input type="checkbox" id="acEnabled" class="brabus-switch" role="switch">
                            启用。停用之后不能再被新计费选用。
                        </label>
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">备注</label>
                        <input type="text" id="acRemark" maxlength="200" autocomplete="off"
                               class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active"
                               placeholder="可选">
                    </div>
                </form>
            </div>
            <div class="px-5 py-3 border-t border-line flex items-center justify-end gap-2 bg-app-surface shrink-0">
                <button type="button" id="acCancelForm" class="${BTN_GHOST}">取消</button>
                <button type="button" id="acSubmitForm" class="${BTN_SOLID}">保存</button>
            </div>
        </div>
    `;
}

export function renderAssemblyCategoryRows(records) {
    if (!records || !records.length) return '';
    const canUpdate = canOp('op:assembly-category:update');
    const canDelete = canOp('op:assembly-category:delete');
    return records.map((record) => hudRowHtml({
        cellsHtml: `
            <td class="px-2 py-2 text-[11px] text-ink-muted font-mono">${esc(record.sort_order)}</td>
            <td class="px-2 py-2 overflow-hidden">
                <div class="text-[14px] font-bold text-ink truncate" title="${esc(record.name)}">${esc(record.name)}</div>
            </td>
            <td class="px-2 py-2 text-[11px] font-mono text-ink-muted truncate">${esc(record.code)}</td>
            <td class="px-2 py-2 text-[11px] ${record.is_enabled ? 'text-ink' : 'text-ink-faint'}">${record.is_enabled ? '启用' : '已禁用'}</td>
            <td class="px-2 py-2 text-[10px] text-ink-faint truncate" title="${esc(record.remark || '')}">${esc(record.remark || '—')}</td>`,
        opsHtml: `<div class="inline-flex items-center justify-center gap-0.5">${canUpdate ? opsIconButtonHtml({
            action: 'edit',
            title: '编辑',
            icon: window.svgIcon('pencil', 'w-3.5 h-3.5'),
            attrs: `data-id="${esc(record.id)}"`,
        }) : ''}${canDelete ? opsIconButtonHtml({
            action: 'delete',
            danger: true,
            title: '删除',
            icon: window.svgIcon('trash', 'w-3.5 h-3.5'),
            attrs: `data-id="${esc(record.id)}" data-name="${esc(record.name)}"`,
        }) : ''}</div>`,
    })).join('');
}

export function syncAssemblyCategoryStatus(active) {
    document.querySelectorAll('.ac-status').forEach((btn) => {
        const selected = (btn.getAttribute('data-enabled') ?? '') === active;
        btn.className = selected
            ? 'ac-status px-2 py-0.5 text-[10px] font-mono rounded-md border border-brand-hud/50 bg-brand-hud/10 text-ink'
            : 'ac-status px-2 py-0.5 text-[10px] font-mono rounded-md border border-line-hud text-ink-muted hover:text-ink';
    });
}
