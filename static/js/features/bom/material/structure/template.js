/**
 * BOM 产品结构 — 模板
 * 项目卡片 → 供货总成选择
 */

import { HUD_LED } from '../../../../ui/classes.js?v=14';

export function bomStructureTemplate() {
    return `
        <div class="space-y-6">
            <!-- 项目列表 -->
            <div id="bomStructureProjectsView">
                <div class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
                    <div>
                        <p class="text-[10px] font-semibold tracking-[0.12em] text-ink-dim mb-2">基地</p>
                        <div id="bomStructureBaseContext" class="min-h-[36px]">
                            <!-- 单基地文案 / 多基地分段 / 加载态 -->
                        </div>
                    </div>
                    <p class="text-[11px] text-ink-dim max-w-md leading-relaxed">
                        选择项目进入供货总成结构。当前为产品结构浏览，不展示传统 BOM 表格。
                    </p>
                </div>

                <div class="mt-6">
                    <div class="flex items-center gap-2.5 mb-4">
                        <span class="${HUD_LED}"></span>
                        <h3 class="text-[10px] font-semibold tracking-[0.12em] text-ink-muted">项目</h3>
                        <span id="bomStructureProjectCount" class="text-[10px] font-mono text-ink-faint tracking-wider"></span>
                    </div>
                    <div id="bomStructureProjectGrid" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                        <!-- 运行时注入 -->
                    </div>
                </div>
            </div>

            <!-- 供货总成列表 -->
            <div id="bomStructureAssembliesView" class="hidden">
                <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-4">
                    <div class="flex items-center gap-2.5 min-w-0 flex-wrap">
                        <button type="button"
                                id="bomStructureBackToProjects"
                                class="inline-flex items-center gap-1 text-[11px] text-ink-dim hover:text-ink-muted transition-colors shrink-0"
                                title="返回项目">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 19l-7-7 7-7"></path>
                            </svg>
                            返回
                        </button>
                        <span class="text-ink-faint select-none">/</span>
                        <p id="bomStructureAssemblyPath" class="text-[11px] text-ink-muted tracking-wide truncate min-w-0"></p>
                        <span class="hidden sm:inline text-ink-faint select-none">·</span>
                        <div class="flex items-center gap-2 min-w-0">
                            <span class="${HUD_LED}"></span>
                            <h3 class="text-[10px] font-semibold tracking-[0.12em] text-ink-muted">供货总成</h3>
                            <span id="bomStructureAssemblyCount" class="text-[10px] font-mono text-ink-faint tracking-wider"></span>
                        </div>
                    </div>
                    <div class="flex items-end gap-2 shrink-0 flex-wrap justify-end">
                        <div class="relative w-full sm:w-64 shrink-0">
                        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <svg class="w-3.5 h-3.5 text-ink-dim" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                            </svg>
                        </div>
                        <input type="text"
                               id="bomStructureAssemblySearch"
                               autocomplete="off"
                               spellcheck="false"
                               placeholder="搜索零件号 / 名称…"
                               class="w-full h-8 pl-9 pr-3 text-xs bg-app-deep border border-line text-ink placeholder:text-ink-dim focus:outline-none focus:border-brand-active transition-all">
                    </div>
                    </div>
                </div>
                <div id="bomStructureAssemblyGrid"
                     class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-4">
                    <!-- 运行时注入总成卡片 -->
                </div>
            </div>
        </div>
    `;
}
