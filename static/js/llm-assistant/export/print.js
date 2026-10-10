/**
 * AI 回答「打印」：新标签页打开带网址的报告页（不自动调系统打印对话框）。
 * 弹窗被拦时回退全屏预览，用户可自行再点打印。
 */

import { buildAssistantDocumentHtml, canExportAssistantMessage } from './document.js?v=13';
import { llmIconClose, llmIconPrint, PANEL_ICON_BTN_CLASS } from '../icons.js';

/**
 * @param {number|string} reportId
 * @returns {string}
 */
export function analysisReportPageUrl(reportId) {
    return `/llm-analysis-report?report_id=${encodeURIComponent(String(reportId))}`;
}

const FULLSCREEN_OVERLAY_ID = 'llmPrintFullscreenOverlay';

/** @type {((event: KeyboardEvent) => void)|null} */
let escListener = null;

/**
 * 关闭全屏打印遮罩（弹窗被拦截时的回退层）。
 */
export function closePrintPreview() {
    const overlay = document.getElementById(FULLSCREEN_OVERLAY_ID);
    if (overlay) {
        overlay.remove();
    }
    if (escListener) {
        document.removeEventListener('keydown', escListener);
        escListener = null;
    }
}

/**
 * @param {object} msg
 */
export function printAssistantMessage(msg) {
    if (!canExportAssistantMessage(msg)) {
        if (typeof window.showToast === 'function') {
            window.showToast('暂无可打印的 AI 回答', 'warning');
        }
        return;
    }

    const reportId = msg.report_id;
    if (reportId != null && String(reportId).trim() !== '') {
        if (openReportPage(reportId)) {
            return;
        }
        fallbackFullscreen(msg);
        return;
    }

    const html = buildAssistantDocumentHtml(msg);
    if (openBlankDocument(html)) {
        return;
    }
    fallbackFullscreen(msg, html);
}

/**
 * @param {object} msg
 * @param {string} [html]
 */
function fallbackFullscreen(msg, html) {
    if (typeof window.showToast === 'function') {
        window.showToast('弹窗被拦截，已改用全屏预览', 'warning');
    }
    openFullscreenPreview(msg, html || buildAssistantDocumentHtml(msg));
}

/**
 * @param {number|string} reportId
 * @returns {boolean}
 */
function openReportPage(reportId) {
    const tab = window.open(analysisReportPageUrl(reportId), '_blank');
    if (!tab) {
        return false;
    }
    try {
        tab.opener = null;
    } catch {
        /* ignore */
    }
    tab.focus();
    return true;
}

/**
 * 无 report_id 时回退：about:blank 写入文档。
 * @param {string} html
 * @returns {boolean}
 */
function openBlankDocument(html) {
    const printWindow = window.open('', '_blank');
    if (!printWindow) {
        return false;
    }

    printWindow.document.open();
    printWindow.document.write(html);
    printWindow.document.close();
    printWindow.focus();
    return true;
}

/**
 * @param {object} msg
 * @param {string} html
 */
function openFullscreenPreview(msg, html) {
    closePrintPreview();

    const overlay = document.createElement('div');
    overlay.id = FULLSCREEN_OVERLAY_ID;
    overlay.className = 'fixed inset-0 z-[120] flex flex-col bg-app-deep';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-label', '打印预览');
    overlay.innerHTML = `
<div class="flex items-center justify-between gap-2 px-3 py-2 border-b border-line-subtle bg-app-surface shrink-0">
  <span class="text-[10px] text-ink-dim truncate px-1">打印预览 · 报告${msg.report_id ? ` #${msg.report_id}` : ''}</span>
  <div class="flex items-center gap-0.5 shrink-0">
    <button type="button" data-llm-print-action="print"
      class="${PANEL_ICON_BTN_CLASS}"
      title="打印" aria-label="打印">${llmIconPrint()}</button>
    <button type="button" data-llm-print-action="close"
      class="${PANEL_ICON_BTN_CLASS}"
      title="关闭" aria-label="关闭">${llmIconClose()}</button>
  </div>
</div>
<iframe data-llm-print-frame
  class="flex-1 w-full min-h-0 bg-white border-0"
  title="AI 回答打印预览"
  sandbox="allow-same-origin allow-modals"></iframe>`;

    document.body.appendChild(overlay);

    const frame = overlay.querySelector('[data-llm-print-frame]');
    if (!(frame instanceof HTMLIFrameElement)) {
        closePrintPreview();
        return;
    }

    frame.srcdoc = html;

    overlay.querySelector('[data-llm-print-action="print"]')?.addEventListener('click', () => {
        try {
            frame.contentWindow?.focus();
            frame.contentWindow?.print();
        } catch (error) {
            if (typeof window.showToast === 'function') {
                window.showToast(error?.message || '打印失败', 'error');
            }
        }
    });

    overlay.querySelector('[data-llm-print-action="close"]')?.addEventListener('click', () => {
        closePrintPreview();
    });

    escListener = (event) => {
        if (event.key === 'Escape') {
            closePrintPreview();
        }
    };
    document.addEventListener('keydown', escListener);
}
