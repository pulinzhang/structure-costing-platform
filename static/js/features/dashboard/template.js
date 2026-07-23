/**
 * Dashboard Template
 * 仪表盘页面 — Brabus Carbon & Precision Dark
 */

export function dashboardTemplate() {
    return `
        <!-- 指标卡片行：钛灰面板 + 悬停红边框 + 精密数字 -->
        <div class="grid grid-cols-2 xl:grid-cols-4 gap-px mb-6">
            <div class="dashboard-card px-5 py-4">
                <div class="flex items-start justify-between gap-3">
                    <div class="flex-1 min-w-0">
                        <p class="text-[10px] font-semibold uppercase tracking-[0.15em] mb-3" style="color: var(--text-disabled)">零件总数</p>
                        <p class="stat-number text-2xl font-bold" id="totalParts">—</p>
                    </div>
                    <div class="stat-icon w-8 h-8 rounded-sm">
                        <svg class="w-4 h-4" style="color: var(--text-disabled)" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"></path></svg>
                    </div>
                </div>
            </div>
            <div class="dashboard-card px-5 py-4">
                <div class="flex items-start justify-between gap-3">
                    <div class="flex-1 min-w-0">
                        <p class="text-[10px] font-semibold uppercase tracking-[0.15em] mb-3" style="color: var(--text-disabled)">工序总数</p>
                        <p class="stat-number text-2xl font-bold" id="totalProcesses">—</p>
                    </div>
                    <div class="stat-icon w-8 h-8 rounded-sm">
                        <svg class="w-4 h-4" style="color: var(--text-disabled)" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 6h16M4 10h16M4 14h16M4 18h16"></path></svg>
                    </div>
                </div>
            </div>
            <div class="dashboard-card px-5 py-4">
                <div class="flex items-start justify-between gap-3">
                    <div class="flex-1 min-w-0">
                        <p class="text-[10px] font-semibold uppercase tracking-[0.15em] mb-3" style="color: var(--text-disabled)">车型数量</p>
                        <p class="stat-number text-2xl font-bold" id="totalModels">—</p>
                    </div>
                    <div class="stat-icon w-8 h-8 rounded-sm">
                        <svg class="w-4 h-4" style="color: var(--text-disabled)" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"></path></svg>
                    </div>
                </div>
            </div>
            <div class="dashboard-card px-5 py-4">
                <div class="flex items-start justify-between gap-3">
                    <div class="flex-1 min-w-0">
                        <p class="text-[10px] font-semibold uppercase tracking-[0.15em] mb-3" style="color: var(--text-disabled)">最近上传</p>
                        <p class="stat-number text-2xl font-bold" id="recentUploads">—</p>
                    </div>
                    <div class="stat-icon w-8 h-8 rounded-sm">
                        <svg class="w-4 h-4" style="color: var(--text-disabled)" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path></svg>
                    </div>
                </div>
            </div>
        </div>

        <!-- 概览面板 -->
        <div class="dashboard-card p-6 mb-6">
            <!-- 左红条 + 标题 -->
            <div class="flex items-center gap-2.5 mb-5">
                <div class="overview-bar"></div>
                <h3 class="text-[10px] font-semibold uppercase tracking-[0.15em]" style="color: var(--text-disabled)">系统概览</h3>
            </div>
            <p class="text-sm mb-6 leading-relaxed" style="color: var(--text-muted)">
                本系统提供冲压件工艺文件上传、零件管理、成本核算和报价生成等功能。
            </p>
            <div class="flex gap-2">
                <!-- 主操作按钮：Brabus 机械舱质感 -->
                <a href="#" class="inline-flex items-center gap-2 text-xs font-medium active:scale-[0.98] transition-all duration-150 upload-cta" data-page="stamping-upload">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                    上传工艺文件
                </a>
                <!-- 次要操作 -->
                <a href="#" class="inline-flex items-center gap-2 text-xs font-medium active:scale-[0.98] transition-all duration-150 overview-cta" data-page="stamping-parts">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"></path></svg>
                    查看零件列表
                </a>
            </div>
        </div>
    `;
}
