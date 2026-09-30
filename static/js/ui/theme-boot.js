/**
 * Head 同步：在首屏 CSS 前写入 data-theme，避免先闪一下深色。
 * 未选过时手机默认浅色，桌面默认深色。键名与 ui/theme.js 一致。
 */
(function bootTheme() {
    try {
        var phone = window.matchMedia('(max-width: 639.98px)').matches;
        var stored = localStorage.getItem('brabus_theme');
        var light = stored === 'light' || (stored !== 'dark' && phone);
        if (light) {
            document.documentElement.setAttribute('data-theme', 'light');
        }
    } catch (_) {
        /* private mode */
    }
})();
