/**
 * Settings Page Module
 * 设置页面逻辑
 */
import { settingsTemplate } from '../templates/settings.html.js';

export const SettingsPage = {
    /**
     * 初始化页面
     */
    init() {
        // 预留扩展
    },

    /**
     * 渲染页面内容
     */
    render() {
        return settingsTemplate();
    }
};
