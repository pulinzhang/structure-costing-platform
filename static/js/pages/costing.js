/**
 * Costing Page Module
 * 核价页面逻辑
 */
import { costingTemplate } from '../templates/costing.html.js';

export const CostingPage = {
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
        return costingTemplate();
    }
};
