/**
 * Settings Page
 * 设置页面逻辑
 */

import { settingsTemplate } from './template.js';

export const SettingsPage = {
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
    render: settingsTemplate,
    init: () => SettingsPage.init(),
};
