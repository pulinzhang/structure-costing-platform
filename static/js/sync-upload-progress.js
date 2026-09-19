/**
 * 同步 Excel 上传进度面板：进行中假进度 → 结束满条，避免操作员以为还在跑。
 *
 * @param {{
 *   zoneId?: string,
 *   idleId?: string,
 *   panelId: string,
 *   iconId: string,
 *   titleId: string,
 *   barId: string,
 *   msgId: string,
 *   runningTitle?: string,
 * }} ids
 */
export function bindSyncUploadProgress(ids) {
    const runningTitle = ids.runningTitle || '正在导入...';

    function el(id) {
        return id ? document.getElementById(id) : null;
    }

    function showPanel() {
        el(ids.idleId)?.classList.add('hidden');
        el(ids.panelId)?.classList.remove('hidden');
    }

    function setRunning(msg = '解析并写入数据库，请稍候') {
        showPanel();
        el(ids.zoneId)?.classList.add('pointer-events-none');
        const icon = el(ids.iconId);
        if (icon) icon.innerHTML = window.svgIcon('spinner', 'w-4 h-4 text-[#d32f2f]');
        const title = el(ids.titleId);
        if (title) title.textContent = runningTitle;
        const bar = el(ids.barId);
        if (bar) {
            bar.style.width = '60%';
            bar.classList.add('animate-pulse');
        }
        const msgEl = el(ids.msgId);
        if (msgEl) msgEl.textContent = msg;
    }

    function setDone(message, { hasSkip = false } = {}) {
        const text = String(message || '导入完成').trim() || '导入完成';
        showPanel();
        el(ids.zoneId)?.classList.remove('pointer-events-none');
        const icon = el(ids.iconId);
        if (icon) {
            icon.innerHTML = window.svgIcon(
                hasSkip ? 'exclamation-triangle' : 'check-circle',
                hasSkip ? 'w-4 h-4 text-[#ffb74d]' : 'w-4 h-4 text-[#66bb6a]',
            );
        }
        const title = el(ids.titleId);
        if (title) title.textContent = hasSkip ? '导入完成（有跳过）' : '导入完成';
        const bar = el(ids.barId);
        if (bar) {
            bar.style.width = '100%';
            bar.classList.remove('animate-pulse');
        }
        const msgEl = el(ids.msgId);
        if (msgEl) msgEl.textContent = text;
    }

    function setFail(message) {
        const text = String(message || '操作失败').trim() || '操作失败';
        showPanel();
        el(ids.zoneId)?.classList.remove('pointer-events-none');
        const icon = el(ids.iconId);
        if (icon) icon.innerHTML = window.svgIcon('exclamation-circle', 'w-4 h-4 text-[#d32f2f]');
        const title = el(ids.titleId);
        if (title) title.textContent = '导入失败';
        const bar = el(ids.barId);
        if (bar) {
            bar.style.width = '100%';
            bar.classList.remove('animate-pulse');
        }
        const msgEl = el(ids.msgId);
        if (msgEl) msgEl.textContent = text;
    }

    function hide() {
        el(ids.idleId)?.classList.remove('hidden');
        el(ids.panelId)?.classList.add('hidden');
        el(ids.zoneId)?.classList.remove('pointer-events-none');
    }

    return { setRunning, setDone, setFail, hide };
}
