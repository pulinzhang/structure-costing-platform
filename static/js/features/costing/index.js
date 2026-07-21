/**
 * Costing Page
 * 核价页面逻辑
 */

import { costingTemplate } from './template.js';

export const CostingPage = {
    /**
     * 初始化页面
     */
    init() {
        // 预留扩展
    },
};

/**
 * 页面导出 - 用于 app.js 注册
 */
export const pageConfig = {
    render: costingTemplate,
    init: () => CostingPage.init(),
};
