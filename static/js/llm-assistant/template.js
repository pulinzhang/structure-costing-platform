/**
 * 浮动窗 DOM 模板
 */

export function shellHtml() {
    return `
<div id="llmAssistantMask" class="hidden fixed inset-0 z-[109] bg-transparent backdrop-blur-[1px]" aria-hidden="true"></div>

<button type="button" id="llmAssistantDock"
        class="hidden fixed z-[110] w-12 h-12 border border-[#2c2c2c] bg-[#1e1e1e] text-[#9e9e9e] hover:border-[#d32f2f] hover:text-white
               right-3 top-1/2 -translate-y-1/2 max-md:right-4 max-md:top-auto max-md:bottom-4 max-md:translate-y-0"
        aria-label="展开AI助理" title="AI助理">
  <svg class="w-5 h-5 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
          d="M9 7V6a3 3 0 116 0v1m-7 4h8a2 2 0 012 2v5a2 2 0 01-2 2H8a2 2 0 01-2-2v-5a2 2 0 012-2zm2 4h.01M14 15h.01"/>
  </svg>
</button>

<section id="llmAssistantPanel"
         class="hidden fixed z-[110] flex flex-col overflow-hidden border border-[#2c2c2c] bg-[#121212]
                w-[min(380px,calc(100vw-1.5rem))] top-4 bottom-4 right-4 h-auto
                shadow-[0_16px_48px_rgba(0,0,0,0.65)]"
         role="dialog" aria-label="AI助理">
  <header class="flex items-center justify-between gap-2 px-3 py-2 border-b border-[#222] bg-[#1e1e1e] shrink-0">
    <div class="min-w-0">
      <div class="text-xs font-semibold text-[#F0F0F2]">AI助理</div>
      <div id="llmAssistantStatus" class="text-[10px] text-[#616161] truncate">就绪</div>
    </div>
    <div class="flex items-center gap-0.5 shrink-0">
      <button type="button" id="llmBtnHistory" class="w-7 h-7 inline-flex items-center justify-center text-[#9e9e9e] hover:text-white hover:bg-[#262626]" title="分析历史" aria-label="分析历史">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
      </button>
      <button type="button" id="llmBtnMaximize" class="w-7 h-7 inline-flex items-center justify-center text-[#9e9e9e] hover:text-white hover:bg-[#262626]" title="最大化" aria-label="最大化">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 8V4h4M20 8V4h-4M4 16v4h4M20 16v4h-4"/></svg>
      </button>
      <button type="button" id="llmBtnDock" class="w-7 h-7 inline-flex items-center justify-center text-[#9e9e9e] hover:text-white hover:bg-[#262626]" title="收起" aria-label="最小化">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M5 12h14"/></svg>
      </button>
      <button type="button" id="llmBtnClose" class="w-7 h-7 inline-flex items-center justify-center text-[#9e9e9e] hover:text-[#ef5350] hover:bg-[#262626]" title="关闭" aria-label="关闭">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"/></svg>
      </button>
    </div>
  </header>

  <div class="relative flex-1 flex flex-col min-h-0">
    <div id="llmHistoryOverlay" class="hidden absolute inset-0 z-20 flex flex-col bg-[#121212]"></div>
    <div id="llmThread" class="flex-1 overflow-y-auto px-3 py-3 space-y-3 bg-[#0a0a0a] min-h-0" role="log" aria-live="polite"></div>
  </div>
  <div id="llmChips" class="px-3 pt-2 pb-1 border-t border-[#1a1a1a] bg-[#121212] shrink-0 overflow-x-auto"></div>
  <div id="llmComposer" class="px-3 py-2 border-t border-[#222] bg-[#1e1e1e] shrink-0"></div>
  <footer class="px-3 py-1.5 border-t border-[#1a1a1a] bg-[#0c0c0c] flex items-center justify-between gap-2 shrink-0">
    <button type="button" id="llmBtnClearChat" class="text-[10px] text-[#616161] hover:text-[#9e9e9e]">清空本机对话</button>
    <span id="llmPromptMeta" class="text-[10px] font-mono text-[#3a3a3a] truncate"></span>
  </footer>
</section>
`.trim();
}

export function entryButtonHtml() {
    return `
<button type="button" id="llmAssistantEntryBtn"
        class="flex items-center justify-center w-8 h-8 rounded-full border border-[#2c2c2c] text-[#9e9e9e] hover:border-[#d32f2f] hover:text-white transition-colors"
        aria-label="AI助手" title="AI助手">
  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
          d="M9 7V6a3 3 0 116 0v1m-7 4h8a2 2 0 012 2v5a2 2 0 01-2 2H8a2 2 0 01-2-2v-5a2 2 0 012-2zm2 4h.01M14 15h.01"/>
  </svg>
</button>
`.trim();
}
