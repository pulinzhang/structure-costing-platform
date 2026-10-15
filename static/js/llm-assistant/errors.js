/**
 * 面向操作员的错误文案（禁止把程序异常原样展示）
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
    if (/Failed to fetch|NetworkError|\bnetwork\b|timeout|AbortError|无法连接服务器|服务已启动/i.test(msg)) {
        return '网络连接中断，请检查网络后重试';
    }
    if (/too many requests|\b429\b/i.test(msg)) {
        return '同时分析的问题过多，请等当前分析完成后再问';
    }
    if (/LLM |HTTP \d{3}|Traceback|Exception|Error:|API_KEY|响应非 JSON|缺少 choices|模型暂不可用/i.test(msg)) {
        return '分析失败，请稍后重试';
    }
    if (/^分析失败[:：]/.test(msg) && /[A-Za-z]{4,}/.test(msg)) {
        return '分析失败，请稍后重试';
    }
    return msg;
}
