/**
 * LLM 助理局部图标（克制操作区，不扩展 main.js）
 */

/** @param {string} [extraClass] */
export function llmIconCopy(extraClass = 'w-3.5 h-3.5') {
    return `<svg class="inline-block ${extraClass}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5a1.125 1.125 0 01-1.125-1.125v-1.5a3.375 3.375 0 00-3.375-3.375H9.75"/></svg>`;
}

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
