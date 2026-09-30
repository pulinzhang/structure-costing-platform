/**
 * 报告页「关闭」：先关脚本打开的页，关不掉再回到上一页。
 */
(function bindReportClose() {
    var button = document.getElementById('reportCloseBtn');
    if (!button) return;
    button.addEventListener('click', function () {
        window.close();
        window.setTimeout(function () {
            if (window.closed || document.visibilityState === 'hidden') return;
            if (window.history.length > 1) {
                window.history.back();
                return;
            }
            window.location.replace(document.referrer || '/');
        }, 200);
    });
})();
