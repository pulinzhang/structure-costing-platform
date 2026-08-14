/**
 * 多层级 BOM — 产品结构可视化
 */

export function bomVizTemplate() {
    return `
        <div id="bomVizRoot" class="relative -mx-1 min-h-[calc(100vh-7.5rem)]">
            <div class="relative z-20 flex items-center justify-between gap-4 px-1 mb-2">
                <div class="min-w-0 flex items-center gap-3">
                    <button type="button"
                            id="bomVizBackAssemblies"
                            class="inline-flex items-center gap-1.5 shrink-0 text-[11px] text-[#616161] hover:text-[#9e9e9e] transition-colors">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 19l-7-7 7-7"></path>
                        </svg>
                        返回
                    </button>
                    <span class="w-px h-3 bg-[#2c2c2c] shrink-0"></span>
                    <div class="min-w-0">
                        <h1 id="bomVizAssemblyName" class="text-sm font-semibold text-[#ffffff] tracking-wide truncate"></h1>
                        <p id="bomVizPath" class="text-[10px] text-[#555555] tracking-wide truncate"></p>
                    </div>
                </div>
                <div id="bomVizCategoryLegend"
                     class="shrink-0 flex flex-wrap justify-end gap-x-3 gap-y-1 text-[10px] tracking-wide text-[#6b6b6b] max-w-md">
                </div>
            </div>

            <div id="bomVizStageShell"
                 class="relative bg-[#0e0e0e] border border-[#222222] overflow-auto overscroll-contain"
                 style="min-height:min(78vh,820px);height:min(78vh,820px)">
                <div id="bomVizStage" class="relative"></div>

                <div id="bomVizPreview"
                     class="pointer-events-none fixed z-[90] w-[300px] opacity-0 scale-[0.98] transition-[opacity,transform] duration-100 ease-out"
                     aria-hidden="true">
                    <div class="bg-[#141414]/95 border border-[#2a2a2a] shadow-[0_16px_48px_rgba(0,0,0,0.55)] backdrop-blur-sm overflow-hidden">
                        <div id="bomVizPreviewImage"
                             class="h-44 bg-[#0a0a0a] border-b border-[#1e1e1e] overflow-hidden"></div>
                        <div class="px-4 py-3 space-y-1.5">
                            <div class="flex items-center justify-between gap-2">
                                <p id="bomVizPreviewQty" class="text-[11px] font-mono font-semibold tabular-nums text-[#e8e8e8]"></p>
                                <p id="bomVizPreviewCategory" class="inline-flex items-center gap-1.5 text-[10px] tracking-wide text-[#9e9e9e]"></p>
                            </div>
                            <p id="bomVizPreviewDisplay" class="text-sm font-semibold text-[#ffffff] leading-snug"></p>
                            <p id="bomVizPreviewName" class="text-[12px] text-[#9e9e9e] leading-snug"></p>
                            <p id="bomVizPreviewNo" class="text-[11px] font-mono text-[#616161]"></p>
                            <p id="bomVizPreviewParent" class="text-[11px] text-[#777777]"></p>
                            <p id="bomVizPreviewHint" class="text-[11px] text-[#6b6b6b] leading-relaxed pt-1"></p>
                        </div>
                    </div>
                </div>

                <div id="bomVizStageEmpty"
                     class="hidden absolute inset-0 z-10 flex items-center justify-center bg-[#0e0e0e]">
                    <div class="text-center px-6">
                        <p id="bomVizStageEmptyTitle" class="text-xs text-[#9e9e9e] mb-1"></p>
                        <p id="bomVizStageEmptyDesc" class="text-[11px] text-[#616161]"></p>
                    </div>
                </div>
            </div>

            <aside id="bomVizKnowledge"
                   class="fixed inset-y-0 right-0 z-[85] w-full max-w-[400px] bg-[#141414] border-l border-[#2a2a2a] transform translate-x-full transition-transform duration-300 flex flex-col"
                   aria-hidden="true">
                <div class="px-5 py-3.5 flex items-center justify-between shrink-0 border-b border-[#222222] bg-[#171717]">
                    <div class="flex items-center gap-2.5 min-w-0">
                        <span class="w-0.5 h-3.5 bg-[#d32f2f] rounded-sm shadow-[0_0_8px_rgba(211,47,47,0.45)]"></span>
                        <h2 class="text-[11px] font-semibold tracking-wide text-[#9e9e9e]">零件详情</h2>
                    </div>
                    <button type="button" id="bomVizKnowledgeClose"
                            class="flex items-center justify-center w-8 h-8 text-[#707070] hover:text-white hover:bg-[#d32f2f] transition-all">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                </div>
                <div id="bomVizKnowledgeBody" class="flex-1 overflow-y-auto overscroll-contain p-5 space-y-5"></div>
            </aside>
            <div id="bomVizKnowledgeBackdrop"
                 class="fixed inset-0 z-[80] bg-black/50 backdrop-blur-[2px] opacity-0 pointer-events-none transition-opacity duration-300"></div>
        </div>
    `;
}
