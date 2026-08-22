/**
 * AI 回答打印预览（面板内 iframe，避免浏览器拦截弹窗）
 */

import { buildAssistantDocumentHtml, canExportAssistantMessage } from './document.js?v=1';
import { llmIconClose, llmIconPrint, PANEL_ICON_BTN_CLASS } from '../icons.js';

/** @type {((event: KeyboardEvent) => void)|null} */
let escListener = null;

/**
 * @param {HTMLElement|null|undefined} overlayEl
 */
export function closePrintPreview(overlayEl) {
    if (!overlayEl) return;
    overlayEl.classList.add('hidden');
    overlayEl.innerHTML = '';
    overlayEl.setAttribute('aria-hidden', 'true');
    if (escListener) {
        document.removeEventListener('keydown', escListener);
        escListener = null;
    }
}

/**
 * @param {object} msg
 * @param {HTMLElement|null|undefined} overlayEl
 */
export function openPrintPreview(msg, overlayEl) {
    if (!canExportAssistantMessage(msg)) {
        if (typeof window.showToast === 'function') {
            window.showToast('暂无可预览的 AI 回答', 'warning');
        }
        return;
    }

    if (!overlayEl) {
        if (typeof window.showToast === 'function') {
            window.showToast('预览容器未就绪', 'error');
        }
        return;
    }

    closePrintPreview(overlayEl);

    const html = buildAssistantDocumentHtml(msg, { forPreview: false });
    overlayEl.classList.remove('hidden');
    overlayEl.setAttribute('aria-hidden', 'false');
    overlayEl.innerHTML = `
<div class="flex items-center justify-between gap-2 px-2 py-1 border-b border-[#222] bg-[#1e1e1e] shrink-0">
  <span class="text-[10px] text-[#616161] truncate px-1">打印预览</span>
  <div class="flex items-center gap-0.5 shrink-0">
    <button type="button" id="llmPreviewPrint"
      class="${PANEL_ICON_BTN_CLASS}"
      title="打印" aria-label="打印">${llmIconPrint()}</button>
    <button type="button" id="llmPreviewClose"
      class="${PANEL_ICON_BTN_CLASS}"
      title="关闭" aria-label="关闭">${llmIconClose()}</button>
  </div>
</div>
<iframe id="llmPreviewFrame"
  class="flex-1 w-full min-h-0 bg-white border-0"
  title="AI 回答打印预览"
  sandbox="allow-same-origin allow-modals"></iframe>`;

    const frame = overlayEl.querySelector('#llmPreviewFrame');
    if (!(frame instanceof HTMLIFrameElement)) return;

    frame.srcdoc = html;

    overlayEl.querySelector('#llmPreviewPrint')?.addEventListener('click', () => {
        try {
            frame.contentWindow?.focus();
            frame.contentWindow?.print();
        } catch (error) {
            if (typeof window.showToast === 'function') {
                window.showToast(error?.message || '打印失败', 'error');
            }
        }
    });

    overlayEl.querySelector('#llmPreviewClose')?.addEventListener('click', () => {
        closePrintPreview(overlayEl);
    });

    escListener = (event) => {
        if (event.key === 'Escape') {
            closePrintPreview(overlayEl);
        }
    };
    document.addEventListener('keydown', escListener);
}
