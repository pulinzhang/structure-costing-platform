/**
 * AI 回答导出 Word（HTML 封装 .doc，Word / WPS 可直接打开）
 */

import { buildAssistantDocumentHtml, buildExportFilename, canExportAssistantMessage } from './document.js?v=13';

/**
 * @param {object} msg
 */
export function downloadWordDocument(msg) {
    if (!canExportAssistantMessage(msg)) {
        if (typeof window.showToast === 'function') {
            window.showToast('暂无可导出的 AI 回答', 'warning');
        }
        return;
    }
    if (typeof window.refuseWeChatDownload === 'function' && window.refuseWeChatDownload()) return;

    const html = buildAssistantDocumentHtml(msg);
    const blob = new Blob(['\ufeff', html], { type: 'application/msword;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = buildExportFilename(msg);
    anchor.style.display = 'none';
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);

    if (typeof window.showToast === 'function') {
        window.showToast('Word 文档已导出', 'success');
    }
}
