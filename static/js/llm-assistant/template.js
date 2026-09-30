/**
 * 浮动窗 DOM 模板。对话是文稿，不是密表。
 * 入口在顶栏，不在这层。
 */

const PANEL_ICON =
    'w-7 h-7 inline-flex items-center justify-center rounded-full text-ink-faint hover:text-ink hover:bg-app-elevated transition-colors';

const PANEL_BASE =
    'fixed z-[110] flex flex-col overflow-hidden bg-app-main text-ink';

/**
 * @param {boolean} maximized
 * @returns {string}
 */
export function panelClass(maximized) {
    if (maximized) {
        return `${PANEL_BASE} inset-0 w-auto h-auto`;
    }
    return `${PANEL_BASE} top-0 bottom-0 right-0 h-full border-l border-line-subtle w-[min(440px,100vw)]`;
}

export function shellHtml() {
    return `
<div id="llmAssistantMask" class="hidden fixed inset-0 z-[109] bg-transparent" aria-hidden="true"></div>

<section id="llmAssistantPanel"
         class="hidden ${panelClass(false)}"
         role="dialog" aria-label="AI助理">
  <div id="llmPanelResize" role="separator" aria-orientation="vertical" aria-label="调整对话框宽度" title="拖动调整宽度"
       class="absolute left-0 top-0 bottom-0 z-30 w-2 cursor-ew-resize hover:bg-ink/20"></div>
  <header class="group flex items-center justify-between gap-2 px-4 py-2 shrink-0">
    <div class="min-w-0">
      <div class="text-[13px] font-medium text-ink">AI助理</div>
      <div id="llmAssistantStatus" class="hidden text-[11px] text-ink-faint truncate"></div>
    </div>
    <div class="flex items-center shrink-0">
      <div class="flex items-center opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
        <button type="button" id="llmBtnClearChat" class="${PANEL_ICON}" title="清空本机对话" aria-label="清空本机对话">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6M9 7V4a1 1 0 011-1h4a1 1 0 011 1v3M4 7h16"/></svg>
        </button>
        <button type="button" id="llmBtnHistory" class="${PANEL_ICON}" title="分析历史" aria-label="分析历史">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        </button>
        <button type="button" id="llmBtnMaximize" class="${PANEL_ICON}" title="最大化" aria-label="最大化">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 8V4h4M20 8V4h-4M4 16v4h4M20 16v4h-4"/></svg>
        </button>
      </div>
      <button type="button" id="llmBtnDock" class="${PANEL_ICON}" title="收起" aria-label="收起">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M5 12h14"/></svg>
      </button>
    </div>
  </header>

  <div class="relative flex-1 flex flex-col min-h-0">
    <div id="llmHistoryOverlay" class="hidden absolute inset-0 z-20 flex flex-col bg-app-main"></div>
    <div id="llmThread" class="flex-1 overflow-y-auto px-4 py-3 space-y-5 min-h-0" role="log" aria-live="polite"></div>
  </div>
  <div id="llmComposer" class="px-3 pt-2 pb-3 shrink-0"></div>
</section>
`.trim();
}

