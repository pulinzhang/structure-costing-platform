/**
 * 牌号分类档案 — HUD 密表 + 抽屉增改
 */

import { HUD_SHELL, DRAWER_BACKDROP, DRAWER_SHELL, HUD_BAND, OPS_TH, BTN_HUD_CREATE, HUD_FILTER, BTN_GHOST, BTN_SOLID, BTN_SOLID_DANGER } from '../../../ui/classes.js?v=15';
import { hudTableHtml, hudRowHtml, opsIconButtonHtml } from '../../../ui/hud-table.js?v=3';

import { moreMenuItemHtml, moreMenuShellHtml } from '../../../ui/more-menu.js?v=7';

export const CATEGORY_TABS = Object.freeze([
    { id: 'all', label: '全部' },
    { id: '冷轧', label: '1 冷轧' },
    { id: '镀锌', label: '2 镀锌' },
    { id: '酸洗', label: '3 酸洗' },
]);

function canOp(code) {
    return typeof window.can === 'function' ? window.can(code) : true;
}

export function steelGradeCategoryTemplate() {
    const tabHtml = CATEGORY_TABS.map(
        (tab) => `
            <button type="button" data-action="tab" data-tab="${tab.id}"
                    class="sgc-tab px-2.5 py-1 text-[11px] font-mono rounded-md border transition-colors
                           bg-app-elevated border-line-hud text-ink-muted hover:text-ink">
                ${tab.label}
            </button>`
    ).join('');

    return `
        <div class="space-y-2 w-full max-w-full">
            <div class="${HUD_SHELL}">

                <div class="${HUD_BAND}">
                    <div class="flex flex-col items-stretch gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
                        <div>
                            <h2 class="text-[13px] font-semibold text-ink tracking-wide">牌号分类</h2>
                            <p class="mt-1 text-[11px] text-ink-faint">核价材质分类；工艺与基价只读本档，不自动补行</p>
                        </div>
                        <div class="flex items-center justify-end gap-1.5 shrink-0 w-full sm:w-auto">
                            ${moreMenuShellHtml({
                                wrapId: 'sgcMoreWrap',
                                btnId: 'sgcMoreBtn',
                                menuId: 'sgcMoreMenu',
                                itemsHtml: [
                                    moreMenuItemHtml({ id: 'sgcTemplateBtn', label: '下载模板' }),
                                    moreMenuItemHtml({ id: 'sgcImportBtn', label: '导入' }),
                                    moreMenuItemHtml({ id: 'sgcExportBtn', label: '导出' }),
                                ].join(''),
                            })}
                            <input type="file" id="sgcImportFileInput" class="hidden" accept=".xlsx,.xls">
                            <button type="button" id="sgcAddBtn"
                                    class="${BTN_HUD_CREATE}">
                                ${window.svgIcon('plus', 'w-3.5 h-3.5')}
                                新增
                            </button>
                        </div>
                    </div>
                    <div class="mt-3 flex flex-wrap items-center gap-2" id="sgcTabBar">
                        ${tabHtml}
                    </div>
                    <div class="mt-3 relative max-w-xs">
                        <span class="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none text-ink-faint">
                            ${window.svgIcon('search', 'w-3.5 h-3.5')}
                        </span>
                        <input type="text" id="sgcGradeFilter" placeholder="搜索牌号…"
                               class="w-full h-8 pl-8 pr-3 text-[11px] font-mono bg-app-hud border border-line-hud text-ink placeholder:text-ink-faint focus:outline-none focus:border-brand-hud rounded-sm">
                    </div>
                </div>

                ${hudTableHtml({
                    prefix: 'sgc',
                    minWidth: '760px',
                    colgroupHtml: `
                            <col style="width: 8px;">
                            <col style="width: 26%;">
                            <col style="width: 16%;">
                            <col style="width: 28%;">
                            <col style="width: 16%;">
                            <col style="width: 88px;">`,
                    headHtml: `
                                <th class="p-0" aria-hidden="true"></th>
                                <th class="record-key px-2 py-2 text-left text-[9px] font-medium tracking-[0.08em] text-ink-faint">牌号</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-ink-faint">大类</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-ink-faint">备注</th>
                                <th class="px-2 py-2 text-left text-[9px] font-medium tracking-[0.06em] text-ink-faint">更新</th>
                                <th class="${OPS_TH}" aria-label="操作"></th>`,
                    empty: {
                        title: '暂无牌号',
                        hint: '请在本页手工新增；工艺或基价导入不会自动补档',
                        showIcon: false,
                        className: 'py-16 text-center bg-app-hud',
                    },
                    loading: { label: '加载中..', className: 'flex-col gap-2 bg-app-hud' },
                })}
            </div>
        </div>

        <div class="${DRAWER_BACKDROP} transition-opacity" id="sgcEditBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[420px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="sgcEditDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-line bg-app-surface shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-brand-hud"></span>
                    <h5 class="text-xs font-semibold text-ink tracking-wider" id="sgcEditTitle">新增牌号</h5>
                </div>
                <button type="button" id="sgcCloseEdit" class="text-ink-dim hover:text-ink w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto p-5">
                <form id="sgcEditForm" class="space-y-4">
                    <input type="hidden" id="sgcEditId" value="">
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">牌号 <span class="text-brand-hud">*</span></label>
                        <input type="text" id="sgcEditGrade" required maxlength="50"
                               class="w-full h-8 px-3 text-xs font-mono bg-app-hud border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active"
                               placeholder="如 DC01、DC51D+Z" autocomplete="off">
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">大类 <span class="text-brand-hud">*</span></label>
                        <select id="sgcEditCategory" required
                                class="w-full ${HUD_FILTER}">
                            <option value="">请选择</option>
                            <option value="冷轧">冷轧</option>
                            <option value="镀锌">镀锌</option>
                            <option value="酸洗">酸洗</option>
                        </select>
                    </div>
                    <div>
                        <label class="text-[10px] font-semibold text-ink-dim tracking-wider mb-1 block">备注</label>
                        <input type="text" id="sgcEditRemark" maxlength="200"
                               class="w-full h-8 px-3 text-xs bg-app-hud border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active"
                               placeholder="可选" autocomplete="off">
                    </div>
                </form>
            </div>
            <div class="px-5 py-3 border-t border-line flex items-center justify-end gap-2 bg-app-surface shrink-0">
                    <button type="button" id="sgcCancelEdit"
                        class="${BTN_GHOST}">取消</button>
                <button type="button" id="sgcSubmitEdit"
                        class="${BTN_SOLID}">保存</button>
            </div>
        </div>

        <div class="${DRAWER_BACKDROP}" id="sgcDeleteBackdrop" style="display:none"></div>
        <div class="${DRAWER_SHELL} w-[360px] transform translate-x-full transition-transform duration-300 ease-in-out"
             id="sgcDeleteDrawer" style="display:none; max-height: 100vh;">
            <div class="px-5 py-3.5 flex items-center justify-between border-b border-line bg-app-surface shrink-0">
                <div class="flex items-center gap-2">
                    <span class="w-1 h-3.5 bg-brand-hud"></span>
                    <h5 class="text-xs font-semibold text-ink tracking-wider">删除牌号</h5>
                </div>
                <button type="button" id="sgcCloseDelete" class="text-ink-dim hover:text-ink w-6 h-6 flex items-center justify-center">✕</button>
            </div>
            <div class="flex-1 p-5">
                <input type="hidden" id="sgcDeleteId" value="">
                <p class="text-xs text-ink-muted mb-2">确认删除牌号</p>
                <p id="sgcDeleteGrade" class="text-sm font-semibold text-ink font-mono"></p>
                <p class="text-[11px] text-ink-faint mt-3">只删档案行，不改零件和基价。</p>
            </div>
            <div class="px-5 py-3 border-t border-line flex items-center justify-end gap-2 bg-app-surface shrink-0">
                <button type="button" id="sgcCancelDelete"
                        class="${BTN_GHOST}">取消</button>
                <button type="button" id="sgcConfirmDelete"
                        class="${BTN_SOLID_DANGER}">删除</button>
            </div>
        </div>
    `;
}

export function renderTableRows(records) {
    if (!records || !records.length) return '';
    const canUpdate = canOp('op:steel-grade-category:update');
    const canDelete = canOp('op:steel-grade-category:delete');

    return records
        .map((record) => {
            const updated = formatDateTime(record.updated_at);
            return hudRowHtml({
                cellsHtml: `
            <td class="px-2 py-2 overflow-hidden">
                <div class="text-[14px] font-bold text-ink truncate" title="${esc(record.grade)}">${esc(record.grade)}</div>
            </td>
            <td class="px-2 py-2 overflow-hidden">
                <span class="text-ink-muted">${esc(record.category_name)}</span>
            </td>
            <td class="px-2 py-2 text-[10px] text-ink-faint overflow-hidden truncate" title="${esc(record.remark || '')}">${esc(record.remark || '—')}</td>
            <td class="px-2 py-2 text-[9px] text-ink-faint whitespace-nowrap overflow-hidden">
                <div>${esc(record.updated_by || '—')}</div>
                <div>${esc(updated)}</div>
            </td>`,
                opsHtml: `<div class="inline-flex items-center justify-center gap-0.5 whitespace-nowrap">${canUpdate ? opsIconButtonHtml({
                    action: 'edit',
                    title: '编辑',
                    icon: window.svgIcon('pencil', 'w-3.5 h-3.5'),
                    attrs: `data-id="${esc(record.id)}"`,
                }) : ''}${canDelete ? opsIconButtonHtml({
                    action: 'delete',
                    danger: true,
                    title: '删除',
                    icon: window.svgIcon('trash', 'w-3.5 h-3.5'),
                    attrs: `data-id="${esc(record.id)}" data-grade="${esc(record.grade)}"`,
                }) : ''}</div>`,
            });
        })
        .join('');
}


export function syncTabStyles(activeTab) {
    document.querySelectorAll('.sgc-tab').forEach((btn) => {
        const isActive = btn.getAttribute('data-tab') === activeTab;
        btn.className = isActive
            ? 'sgc-tab px-2.5 py-1 text-[11px] font-mono rounded-md border transition-colors bg-brand-hud/10 border-brand-hud/50 text-ink'
            : 'sgc-tab px-2.5 py-1 text-[11px] font-mono rounded-md border transition-colors bg-app-elevated border-line-hud text-ink-muted hover:text-ink';
    });
}

function formatDateTime(value) {
    if (!value) return '—';
    const text = String(value);
    if (text.length >= 16) return text.slice(0, 16).replace('T', ' ');
    return text;
}
