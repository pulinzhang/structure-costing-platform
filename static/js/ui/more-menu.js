/**
 * 列表工具条「更多」下拉：外壳 HTML + 开合 / 外点关闭。
 * 菜单项业务由各页自行绑定；本模块不拼 id。
 */

import { BTN_MORE } from './classes.js?v=8';

const ITEM_CLASS =
    'w-full px-3.5 py-2 text-left text-[12px] text-ink-muted hover:bg-app-surface hover:text-ink transition-colors';

const ITEM_DANGER_CLASS =
    'w-full px-3.5 py-2 text-left text-[12px] text-ink-muted hover:bg-app-surface hover:text-danger transition-colors';

const MENU_CLASS =
    'hidden absolute right-0 top-full mt-1 z-[40] min-w-[132px] py-1 bg-app-surface border border-line shadow-[0_8px_24px_rgb(var(--overlay)/0.55)]';

/** @type {Map<string, () => void>} */
const unbindByWrapId = new Map();

/**
 * @param {{ wrapId: string, btnId: string, menuId: string, itemsHtml: string }} opts
 * @returns {string}
 */
export function moreMenuShellHtml({ wrapId, btnId, menuId, itemsHtml }) {
    return `
                            <div class="relative" id="${wrapId}">
                                <button type="button" id="${btnId}"
                                        class="${BTN_MORE}"
                                        aria-label="更多操作" title="更多">
                                    ${typeof window.svgIcon === 'function' ? window.svgIcon('ellipsis', 'w-4 h-4') : ''}
                                </button>
                                <div id="${menuId}"
                                     class="${MENU_CLASS}">
                                    ${itemsHtml}
                                </div>
                            </div>`;
}

/**
 * @param {{ id: string, label: string, danger?: boolean }} opts
 * @returns {string}
 */
export function moreMenuItemHtml({ id, label, danger = false }) {
    const className = danger ? ITEM_DANGER_CLASS : ITEM_CLASS;
    return `<button type="button" id="${id}"
                                            class="${className}">
                                        ${label}
                                    </button>`;
}

/**
 * @param {{
 *   wrapId: string,
 *   btnId: string,
 *   menuId: string,
 *   onToggle?: (isOpen: boolean) => void,
 * }} opts
 * @returns {{ setOpen: (isOpen: boolean) => void, close: () => void, unbind: () => void }}
 */
export function bindMoreMenu({ wrapId, btnId, menuId, onToggle }) {
    const prevUnbind = unbindByWrapId.get(wrapId);
    if (prevUnbind) prevUnbind();

    const setOpen = (isOpen) => {
        const menu = document.getElementById(menuId);
        if (!menu) return;
        menu.classList.toggle('hidden', !isOpen);
    };

    const close = () => setOpen(false);

    const onMoreBtnClick = (event) => {
        event.stopPropagation();
        const menu = document.getElementById(menuId);
        const isOpen = menu && !menu.classList.contains('hidden');
        const nextOpen = !isOpen;
        setOpen(nextOpen);
        onToggle?.(nextOpen);
    };

    const onDocumentClick = (event) => {
        const wrap = document.getElementById(wrapId);
        if (wrap && !wrap.contains(event.target)) {
            setOpen(false);
        }
    };

    document.getElementById(btnId)?.addEventListener('click', onMoreBtnClick);
    document.addEventListener('click', onDocumentClick);

    const unbind = () => {
        document.getElementById(btnId)?.removeEventListener('click', onMoreBtnClick);
        document.removeEventListener('click', onDocumentClick);
        if (unbindByWrapId.get(wrapId) === unbind) {
            unbindByWrapId.delete(wrapId);
        }
    };

    unbindByWrapId.set(wrapId, unbind);
    return { setOpen, close, unbind };
}
