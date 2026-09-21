/**
 * Head 同步：在首屏 CSS 前写入 data-theme，避免 Carbon 闪一下。
 * 键名与 ui/theme.js 的 THEME_STORAGE_KEY 保持一致。
 */
(function bootTheme() {
    try {
        if (localStorage.getItem('brabus_theme') === 'light') {
            document.documentElement.setAttribute('data-theme', 'light');
        }
    } catch (_) {
        /* private mode */
    }
})();
