/**
 * HUD 密表：滚动表区 + 默认分页 + 可选空态/加载；行壳与操作钮。
 * 各页只传表头/列宽/单元格，禁止再复制 wrap / paginationBarHtml / 行 LED。
 */

import { TH_ROW, TR_HUD, ROW_LED, OPS_TD, OPS_ICON, OPS_ICON_DANGER } from './classes.js?v=8';
import { paginationBarHtml } from './page-size.js?v=5';

/**
 * @param {string} prefix
 */
export function hudTableIds(prefix) {
    return {
        wrapId: `${prefix}TableWrap`,
        tableId: `${prefix}Table`,
        theadId: `${prefix}TableHead`,
        bodyId: `${prefix}TableBody`,
        infoId: `${prefix}PageInfo`,
        selectId: `${prefix}PageSize`,
        buttonsId: `${prefix}Pagination`,
        pagerId: `${prefix}Pager`,
        emptyId: `${prefix}Empty`,
        emptyTitleId: `${prefix}EmptyTitle`,
        emptyHintId: `${prefix}EmptyHint`,
        loadingId: `${prefix}Loading`,
    };
}

function emptyBlockHtml(ids, empty) {
    if (!empty) return '';
    const hiddenClass = empty.hidden === false ? '' : 'hidden ';
    const boxClass = empty.className || 'py-14';
    if (empty.html) {
        return `<div id="${ids.emptyId}" class="${hiddenClass}flex flex-col items-center justify-center ${boxClass}">${empty.html}</div>`;
    }
    const iconName = empty.icon || 'clipboard-list';
    const icon = typeof window.svgIcon === 'function'
        ? window.svgIcon(iconName, 'w-4 h-4 text-ink-faint')
        : '';
    const iconBlock = empty.showIcon === false
        ? ''
        : `<div class="w-10 h-10 flex items-center justify-center mb-3 rounded-md bg-app-main border border-line-hud">${icon}</div>`;
    return `
                <div id="${ids.emptyId}" class="${hiddenClass}flex flex-col items-center justify-center ${boxClass}">
                    ${iconBlock}
                    <h5 id="${ids.emptyTitleId}" class="text-[11px] font-medium text-ink-muted mb-1">${empty.title || ''}</h5>
                    <p id="${ids.emptyHintId}" class="text-[10px] text-ink-faint">${empty.hint || ''}</p>
                </div>`;
}

function loadingBlockHtml(ids, loading) {
    if (!loading) return '';
    const label = loading === true ? '' : (loading.label || '');
    const labelHtml = label
        ? `<span class="text-[11px] text-ink-faint">${label}</span>`
        : '';
    const extraClass = loading === true ? '' : (loading.className || '');
    const inner = loading !== true && loading.html
        ? loading.html
        : `<div class="w-5 h-5 border-2 border-brand-hud border-t-transparent rounded-full animate-spin"></div>${labelHtml}`;
    return `
                <div id="${ids.loadingId}" class="hidden flex items-center justify-center py-14 ${extraClass}">
                    ${inner}
                </div>`;
}

/**
 * @param {{
 *   prefix: string,
 *   tableId?: string,
 *   theadId?: string,
 *   bodyId?: string,
 *   wrapId?: string,
 *   bodyClass?: string,
 *   minWidth?: string,
 *   colgroupHtml?: string,
 *   headHtml: string,
 *   pagination?: false,
 *   empty?: false | { title?: string, hint?: string, hidden?: boolean, showIcon?: boolean, icon?: string, html?: string, className?: string },
 *   loading?: boolean | { label?: string, html?: string, className?: string },
 * }} spec
 */
export function hudTableHtml(spec) {
    const prefix = spec.prefix;
    const ids = hudTableIds(prefix);
    const wrapId = spec.wrapId || ids.wrapId;
    const tableId = spec.tableId || ids.tableId;
    const theadId = spec.theadId || ids.theadId;
    const bodyId = spec.bodyId || ids.bodyId;
    const bodyClass = spec.bodyClass === undefined ? 'bg-transparent' : spec.bodyClass;
    const minWidth = spec.minWidth ? ` style="min-width: ${spec.minWidth};"` : '';
    const tableFixed = spec.colgroupHtml ? ' table-fixed' : '';
    const colgroupId = spec.colgroupId ? ` id="${spec.colgroupId}"` : '';
    const colgroup = spec.colgroupHtml ? `<colgroup${colgroupId}>${spec.colgroupHtml}</colgroup>` : '';
    const pager = spec.pagination === false
        ? ''
        : paginationBarHtml({
            infoId: ids.infoId,
            selectId: ids.selectId,
            buttonsId: ids.buttonsId,
            wrapperId: ids.pagerId,
        });
    return `
                <div id="${wrapId}" class="overflow-x-auto brabus-bg-grid">
                    <table id="${tableId}" class="w-full bg-transparent border-separate border-spacing-0${tableFixed}"${minWidth}>
                        ${colgroup}
                        <thead id="${theadId}">
                            <tr class="${TH_ROW}">
                                ${spec.headHtml}
                            </tr>
                        </thead>
                        <tbody id="${bodyId}" class="${bodyClass}"></tbody>
                    </table>
                </div>
                ${pager}
                ${emptyBlockHtml(ids, spec.empty)}
                ${loadingBlockHtml(ids, spec.loading)}`;
}

/**
 * @param {{ attrs?: string, extraClass?: string, cellsHtml: string, opsHtml?: string }} spec
 */
export function hudRowHtml({ attrs = '', extraClass = '', cellsHtml, opsHtml }) {
    const classAttr = extraClass ? `${TR_HUD} ${extraClass}` : TR_HUD;
    const attr = attrs ? ` ${attrs}` : '';
    const ops = opsHtml == null || opsHtml === ''
        ? ''
        : `<td class="${OPS_TD}">${opsHtml}</td>`;
    return `
        <tr class="${classAttr}"${attr}>
            <td class="p-0 relative"><div class="${ROW_LED}"></div></td>
            ${cellsHtml}
            ${ops}
        </tr>`;
}

/**
 * @param {{
 *   action?: string,
 *   title: string,
 *   icon: string,
 *   danger?: boolean,
 *   extraClass?: string,
 *   attrs?: string,
 * }} spec
 */
export function opsIconButtonHtml({
    action,
    title,
    icon,
    danger = false,
    extraClass = '',
    attrs = '',
}) {
    const cls = `${danger ? OPS_ICON_DANGER : OPS_ICON}${extraClass ? ` ${extraClass}` : ''}`;
    const actionAttr = action ? ` data-action="${action}"` : '';
    const extra = attrs ? ` ${attrs}` : '';
    return `<button type="button" class="${cls}"${actionAttr}${extra} title="${title}" aria-label="${title}">${icon}</button>`;
}
