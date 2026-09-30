/**
 * 电脑和手机都可切换深浅。未选过时手机默认浅色，桌面默认深色。
 * 键名与 theme-boot.js 一致。
 */

const PHONE_QUERY = '(max-width: 639.98px)';

export const THEME_STORAGE_KEY = 'brabus_theme';
export const THEME_LIGHT = 'light';
export const THEME_DARK = 'dark';

function isPhoneLayout() {
    return window.matchMedia(PHONE_QUERY).matches;
}

function storedTheme() {
    try {
        return localStorage.getItem(THEME_STORAGE_KEY);
    } catch {
        return null;
    }
}

export function isLightTheme() {
    const stored = storedTheme();
    if (stored === THEME_LIGHT) return true;
    if (stored === THEME_DARK) return false;
    return isPhoneLayout();
}

export function applyStoredTheme() {
    const root = document.documentElement;
    if (isLightTheme()) {
        root.setAttribute('data-theme', THEME_LIGHT);
    } else {
        root.removeAttribute('data-theme');
    }
}

/**
 * @param {boolean} enabled
 */
export function setLightTheme(enabled) {
    try {
        localStorage.setItem(THEME_STORAGE_KEY, enabled ? THEME_LIGHT : THEME_DARK);
    } catch {
        /* private mode */
    }
    applyStoredTheme();
}

/**
 * @param {HTMLInputElement | null} input
 */
export function bindThemeSwitch(input) {
    applyStoredTheme();
    if (!input || input.dataset.bound === '1') return;
    input.dataset.bound = '1';
    const paint = () => {
        input.checked = isLightTheme();
        input.setAttribute('aria-checked', input.checked ? 'true' : 'false');
    };
    paint();
    input.addEventListener('change', () => {
        setLightTheme(input.checked);
        paint();
    });
    window.matchMedia(PHONE_QUERY).addEventListener('change', () => {
        applyStoredTheme();
        paint();
    });
}
