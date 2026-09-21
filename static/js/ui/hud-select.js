/**
 * 拦截可见原生 select 的系统菜单，换成 HUD 选项层
 *（交互对齐采购价格协议芯片：红底 + --text-on-brand，红条随鼠标）。
 */

const MENU_ID = 'hudSelectMenu';
const ITEM_CLASS =
    'hud-select-item block w-full text-left px-2.5 py-1.5 text-[11px] bg-transparent';

let menuEl = null;
let openSelect = null;

function escapeHtml(value) {
    if (typeof window.esc === 'function') return window.esc(value);
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

export function isHudNativeSelect(el) {
    if (!el || el.tagName !== 'SELECT' || el.disabled) return false;
    if (el.multiple || el.size > 1) return false;
    if (el.classList.contains('sr-only')) return false;
    if (el.classList.contains('hidden')) return false;
    if (el.classList.contains('engine-select-source')) return false;
    if (el.classList.contains('engine-select-source-sm')) return false;
    if (el.classList.contains('engine-select-native')) return false;
    if (el.getAttribute('aria-hidden') === 'true') return false;
    return true;
}

function ensureMenu() {
    if (menuEl) return menuEl;
    menuEl = document.createElement('div');
    menuEl.id = MENU_ID;
    menuEl.className = 'hud-select-menu hidden';
    menuEl.setAttribute('role', 'listbox');
    document.body.appendChild(menuEl);
    menuEl.addEventListener('click', (event) => {
        const item = event.target.closest('[data-hud-select-value]');
        if (!item || !openSelect) return;
        event.preventDefault();
        if (item.hasAttribute('disabled')) return;
        const next = item.getAttribute('data-hud-select-value') ?? '';
        if (openSelect.value !== next) {
            openSelect.value = next;
            openSelect.dispatchEvent(new Event('change', { bubbles: true }));
        }
        closeHudSelectMenu();
    });
    return menuEl;
}

export function closeHudSelectMenu() {
    if (!menuEl) return;
    menuEl.classList.add('hidden');
    menuEl.innerHTML = '';
    openSelect = null;
}

function placeMenu(select) {
    const menu = ensureMenu();
    const rect = select.getBoundingClientRect();
    const menuWidth = Math.max(rect.width, 160);
    let left = rect.left;
    if (left + menuWidth > window.innerWidth - 8) {
        left = Math.max(8, window.innerWidth - menuWidth - 8);
    }
    let top = rect.bottom + 4;
    menu.classList.remove('hidden');
    const height = menu.offsetHeight;
    if (top + height > window.innerHeight - 8 && rect.top - 4 - height > 8) {
        top = rect.top - 4 - height;
    }
    menu.style.minWidth = `${menuWidth}px`;
    menu.style.left = `${left}px`;
    menu.style.top = `${top}px`;
}

function openHudSelectMenu(select) {
    if (!isHudNativeSelect(select)) return;
    const menu = ensureMenu();
    if (openSelect === select) {
        closeHudSelectMenu();
        return;
    }
    closeHudSelectMenu();
    const selected = select.value;
    menu.innerHTML = Array.from(select.options).map((opt) => {
        const isOn = opt.value === selected;
        const disabled = opt.disabled ? ' disabled' : '';
        return `<button type="button" role="option" aria-selected="${isOn ? 'true' : 'false'}"
            data-hud-select-value="${escapeHtml(opt.value)}"
            class="${ITEM_CLASS}"${disabled}>${escapeHtml(opt.textContent || '')}</button>`;
    }).join('');
    openSelect = select;
    placeMenu(select);
}

function onPointerDownCapture(event) {
    if (event.button != null && event.button !== 0) return;
    const inMenu = event.target.closest?.(`#${MENU_ID}`);
    if (inMenu) return;
    const select = event.target.closest?.('select');
    if (!isHudNativeSelect(select)) {
        if (openSelect) closeHudSelectMenu();
        return;
    }
    event.preventDefault();
    select.focus({ preventScroll: true });
    openHudSelectMenu(select);
}

function isOpenKey(event) {
    if (event.altKey && event.key === 'ArrowDown') return true;
    if (event.key === ' ' || event.key === 'Spacebar') return true;
    if (event.key === 'Enter') return true;
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') return true;
    if (event.key === 'F4') return true;
    return false;
}

function onKeydownCapture(event) {
    if (event.key === 'Escape') {
        if (openSelect) {
            event.preventDefault();
            closeHudSelectMenu();
        }
        return;
    }
    const select = event.target.closest?.('select');
    if (!isHudNativeSelect(select) || !isOpenKey(event)) return;
    event.preventDefault();
    openHudSelectMenu(select);
}

function onViewportChange(event) {
    if (event?.type === 'scroll' && menuEl && (event.target === menuEl || menuEl.contains(event.target))) {
        return;
    }
    closeHudSelectMenu();
}

export function bindHudSelects() {
    document.addEventListener('pointerdown', onPointerDownCapture, true);
    document.addEventListener('keydown', onKeydownCapture, true);
    window.addEventListener('resize', onViewportChange);
    window.addEventListener('scroll', onViewportChange, true);
}
