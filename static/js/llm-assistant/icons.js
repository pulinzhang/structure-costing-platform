/**
 * LLM 助理局部图标（克制操作区，不扩展 main.js）
 */

/** @param {string} [extraClass] */
export function llmIconPrint(extraClass = 'w-3.5 h-3.5') {
    return `<svg class="inline-block ${extraClass}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M6 9V4a2 2 0 012-2h8a2 2 0 012 2v5"/><path stroke-linecap="round" stroke-linejoin="round" d="M6 14H4a2 2 0 00-2 2v4h20v-4a2 2 0 00-2-2h-2"/><path stroke-linecap="round" stroke-linejoin="round" d="M6 18h12v4H6z"/><path stroke-linecap="round" stroke-linejoin="round" d="M6 10h12"/></svg>`;
}

/** @param {string} [extraClass] */
export function llmIconWord(extraClass = 'w-3.5 h-3.5') {
    if (typeof window.svgIcon === 'function') {
        return window.svgIcon('file-earmark-text', `inline-block ${extraClass}`);
    }
    return `<svg class="inline-block ${extraClass}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>`;
}

/** @param {string} [extraClass] */
export function llmIconClose(extraClass = 'w-3.5 h-3.5') {
    if (typeof window.svgIcon === 'function') {
        return window.svgIcon('x-lg', `inline-block ${extraClass}`);
    }
    return `<svg class="inline-block ${extraClass}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>`;
}

export const EXPORT_ICON_BTN_CLASS =
    'w-6 h-6 inline-flex items-center justify-center text-ink-faint hover:text-ink-muted transition-colors rounded-sm';

export const PANEL_ICON_BTN_CLASS =
    'w-7 h-7 inline-flex items-center justify-center text-ink-muted hover:text-ink hover:bg-app-elevated transition-colors rounded-sm';
