/**
 * Quotation Page
 * 报价页面逻辑
 */

import { quotationTemplate } from './template.js';

export const QuotationPage = {
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
    render: quotationTemplate,
    init: () => QuotationPage.init(),
};
