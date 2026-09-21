/**
 * Carbon / Precision Light。默认不设 data-theme（Carbon）。
 * 仅当 localStorage brabus_theme=light 时挂 html[data-theme="light"]。
 */

export const THEME_STORAGE_KEY = 'brabus_theme';
export const THEME_LIGHT = 'light';

export function isLightTheme() {
    try {
        return localStorage.getItem(THEME_STORAGE_KEY) === THEME_LIGHT;
    } catch {
        return false;
    }
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
        if (enabled) {
            localStorage.setItem(THEME_STORAGE_KEY, THEME_LIGHT);
        } else {
            localStorage.removeItem(THEME_STORAGE_KEY);
        }
    } catch {
        /* private mode */
    }
    applyStoredTheme();
}

/**
 * @param {HTMLInputElement | null} input
 */
export function bindThemeSwitch(input) {
    if (!input || input.dataset.bound === '1') return;
    input.dataset.bound = '1';
    input.checked = isLightTheme();
    input.setAttribute('aria-checked', input.checked ? 'true' : 'false');
    input.addEventListener('change', () => {
        setLightTheme(input.checked);
        input.setAttribute('aria-checked', input.checked ? 'true' : 'false');
    });
}
