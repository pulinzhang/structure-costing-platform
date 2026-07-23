/**
 * Dashboard Page
 * 仪表盘页面逻辑
 */

import { dashboardTemplate } from './template.js';

export const DashboardPage = {
    /**
     * 初始化仪表盘页面
     */
    init() {
        this.loadStats();
    },

    /**
     * 加载统计数据
     */
    async loadStats() {
        try {
            const [partsRes, processesRes, modelsRes] = await Promise.allSettled([
                HttpClient.get('/api/dashboard/stats/parts'),
                HttpClient.get('/api/dashboard/stats/processes'),
                HttpClient.get('/api/dashboard/stats/models'),
            ]);

            const totalParts = partsRes.status === 'fulfilled' ? (partsRes.value.data?.count || 0) : '-';
            const totalProcesses = processesRes.status === 'fulfilled' ? (processesRes.value.data?.count || 0) : '-';
            const totalModels = modelsRes.status === 'fulfilled' ? (modelsRes.value.data?.count || 0) : '-';

            const el = document.getElementById('totalParts');
            if (el) el.textContent = totalParts;

            const elProcesses = document.getElementById('totalProcesses');
            if (elProcesses) elProcesses.textContent = totalProcesses;

            const elModels = document.getElementById('totalModels');
            if (elModels) elModels.textContent = totalModels;

            const elRecent = document.getElementById('recentUploads');
            if (elRecent) elRecent.textContent = '-';
        } catch (error) {
            console.error('加载统计数据失败:', error);
        }
    },
};

/**
 * 页面导出 - 用于 app.js 注册
 */
export const pageConfig = {
    render: dashboardTemplate,
    init: () => DashboardPage.init(),
};
