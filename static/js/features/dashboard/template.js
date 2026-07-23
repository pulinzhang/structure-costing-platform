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
                        <p class="text-[10px] font-semibold uppercase tracking-[0.15em] mb-3 text-[#616161]">零件总数</p>
                        <p class="stat-number text-2xl font-bold" id="totalParts">—</p>
                    </div>
                    <div class="stat-icon w-8 h-8 rounded-sm flex items-center justify-center">
                        ${window.svgIcon('box', 'w-4 h-4')}
                    </div>
                </div>
            </div>
            <div class="dashboard-card px-5 py-4">
                <div class="flex items-start justify-between gap-3">
                    <div class="flex-1 min-w-0">
                        <p class="text-[10px] font-semibold uppercase tracking-[0.15em] mb-3 text-[#616161]">工序总数</p>
                        <p class="stat-number text-2xl font-bold" id="totalProcesses">—</p>
                    </div>
                    <div class="stat-icon w-8 h-8 rounded-sm flex items-center justify-center">
                        ${window.svgIcon('list-ol', 'w-4 h-4')}
                    </div>
                </div>
            </div>
            <div class="dashboard-card px-5 py-4">
                <div class="flex items-start justify-between gap-3">
                    <div class="flex-1 min-w-0">
                        <p class="text-[10px] font-semibold uppercase tracking-[0.15em] mb-3 text-[#616161]">车型数量</p>
                        <p class="stat-number text-2xl font-bold" id="totalModels">—</p>
                    </div>
                    <div class="stat-icon w-8 h-8 rounded-sm flex items-center justify-center">
                        ${window.svgIcon('arrows-split', 'w-4 h-4')}
                    </div>
                </div>
            </div>
            <div class="dashboard-card px-5 py-4">
                <div class="flex items-start justify-between gap-3">
                    <div class="flex-1 min-w-0">
                        <p class="text-[10px] font-semibold uppercase tracking-[0.15em] mb-3 text-[#616161]">最近上传</p>
                        <p class="stat-number text-2xl font-bold" id="recentUploads">—</p>
                    </div>
                    <div class="stat-icon w-8 h-8 rounded-sm flex items-center justify-center">
                        ${window.svgIcon('upload', 'w-4 h-4')}
                    </div>
                </div>
            </div>
        </div>

        <!-- 概览面板 -->
        <div class="dashboard-card p-6 mb-6">
            <!-- 左红条 + 标题 -->
            <div class="flex items-center gap-2.5 mb-5">
                <div class="overview-bar"></div>
                <h3 class="text-[10px] font-semibold uppercase tracking-[0.15em] text-[#616161]">系统概览</h3>
            </div>
            <p class="text-sm mb-6 leading-relaxed text-[#9e9e9e]">
                本系统提供冲压件工艺文件上传、零件管理、成本核算和报价生成等功能。
            </p>
            <div class="flex gap-2">
                <!-- 主操作按钮：Brabus 机械舱质感 -->
                <a href="#" class="inline-flex items-center gap-2 text-xs font-medium active:scale-[0.98] transition-all duration-150 upload-cta" data-page="stamping-upload">
                    ${window.svgIcon('upload', 'w-3.5 h-3.5')}
                    上传工艺文件
                </a>
                <!-- 次要操作 -->
                <a href="#" class="inline-flex items-center gap-2 text-xs font-medium active:scale-[0.98] transition-all duration-150 overview-cta" data-page="stamping-parts">
                    ${window.svgIcon('box', 'w-3.5 h-3.5')}
                    查看零件列表
                </a>
            </div>
        </div>
    `;
}
