/**
 * 面向用户的错误文案（禁止把 JS 运行时异常原样展示）
 */

/**
 * @param {unknown} raw
 * @returns {string}
 */
export function humanizeUserFacingError(raw) {
    const msg = String(raw || '').trim();
    if (!msg) return '分析失败，请稍后重试';
    if (/is not defined|ReferenceError|TypeError|SyntaxError|Cannot read properties of/i.test(msg)) {
        return '界面展示异常，请刷新页面后重试';
    }
    if (/Failed to fetch|NetworkError|network|timeout|AbortError|无法连接服务器/i.test(msg)) {
        return '无法连接服务器，请确认服务已启动或检查网络';
    }
    return msg;
}
