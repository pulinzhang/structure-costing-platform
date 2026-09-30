/**
 * 多层级 BOM — 产品结构可视化
 */

import { DRAWER_SHELL, DRAWER_CLOSE, HUD_LED, DRAWER_BACKDROP } from '../../../../ui/classes.js?v=14';

export function bomVizTemplate() {
    return `
        <div id="bomVizRoot" class="relative -mx-1 min-h-[calc(100vh-7.5rem)]">
            <div class="relative z-20 flex items-center justify-between gap-4 px-1 mb-2">
                <div class="min-w-0 flex items-center gap-3">
                    <button type="button"
                            id="bomVizBackAssemblies"
                            class="inline-flex items-center gap-1.5 shrink-0 text-[11px] text-ink-dim hover:text-ink-muted transition-colors">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 19l-7-7 7-7"></path>
                        </svg>
                        返回
                    </button>
                    <span class="w-px h-3 bg-app-surface shrink-0"></span>
                    <div class="min-w-0">
                        <h1 id="bomVizAssemblyName" class="text-sm font-semibold text-ink tracking-wide truncate"></h1>
                        <p id="bomVizPath" class="text-[10px] text-ink-faint tracking-wide truncate"></p>
                    </div>
                </div>
                <div id="bomVizCategoryLegend"
                     class="shrink-0 flex flex-wrap justify-end gap-x-3 gap-y-1 text-[10px] tracking-wide text-ink-dim max-w-md">
                </div>
            </div>

            <div id="bomVizStageShell"
                 class="relative bg-app-deep border border-line-subtle overflow-auto overscroll-contain"
                 style="min-height:min(78vh,820px);height:min(78vh,820px)">
                <div id="bomVizStage" class="relative"></div>

                <div id="bomVizPreview"
                     class="pointer-events-none fixed z-[90] w-[300px] opacity-0 scale-[0.98] transition-[opacity,transform] duration-100 ease-out"
                     aria-hidden="true">
                    <div class="bg-app-main/95 border border-line shadow-[0_16px_48px_rgb(var(--overlay)/0.55)] backdrop-blur-sm overflow-hidden">
                        <div id="bomVizPreviewImage"
                             class="h-44 bg-app-deep border-b border-app-surface overflow-hidden"></div>
                        <div class="px-4 py-3 space-y-1.5">
                            <div class="flex items-center justify-between gap-2">
                                <p id="bomVizPreviewQty" class="text-[11px] font-mono font-semibold tabular-nums text-ink"></p>
                                <p id="bomVizPreviewCategory" class="inline-flex items-center gap-1.5 text-[10px] tracking-wide text-ink-muted"></p>
                            </div>
                            <p id="bomVizPreviewDisplay" class="text-sm font-semibold text-ink leading-snug"></p>
                            <p id="bomVizPreviewName" class="text-[12px] text-ink-muted leading-snug"></p>
                            <p id="bomVizPreviewNo" class="text-[11px] font-mono text-ink-dim"></p>
                            <p id="bomVizPreviewParent" class="text-[11px] text-ink-dim"></p>
                            <p id="bomVizPreviewPeriod" class="text-[10px] text-ink-faint tracking-wide"></p>
                            <p id="bomVizPreviewHint" class="text-[11px] text-ink-dim leading-relaxed pt-1"></p>
                        </div>
                    </div>
                </div>

                <div id="bomVizStageEmpty"
                     class="hidden absolute inset-0 z-10 flex items-center justify-center bg-app-deep">
                    <div class="text-center px-6">
                        <p id="bomVizStageEmptyTitle" class="text-xs text-ink-muted mb-1"></p>
                        <p id="bomVizStageEmptyDesc" class="text-[11px] text-ink-dim"></p>
                    </div>
                </div>
            </div>

            <aside id="bomVizKnowledge"
                   class="${DRAWER_SHELL} w-full max-w-[400px] transform translate-x-full transition-transform duration-300"
                   aria-hidden="true">
                <div class="px-5 py-3.5 flex items-center justify-between shrink-0 border-b border-line-subtle bg-app-hud">
                    <div class="flex items-center gap-2.5 min-w-0">
                        <span class="${HUD_LED}"></span>
                        <h2 class="text-[11px] font-semibold tracking-wide text-ink-muted">零件详情</h2>
                    </div>
                    <button type="button" id="bomVizKnowledgeClose"
                            class="${DRAWER_CLOSE}">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                </div>
                <div id="bomVizKnowledgeBody" class="flex-1 overflow-y-auto overscroll-contain p-5 space-y-5"></div>
            </aside>
            <div id="bomVizKnowledgeBackdrop"
                 class="${DRAWER_BACKDROP} opacity-0 pointer-events-none transition-opacity duration-300"></div>
        </div>
    `;
}
