/**
 * Quotation Page Module
 * 报价页面逻辑
 */
import { quotationTemplate } from '../templates/quotation.html.js';

export const QuotationPage = {
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
        return quotationTemplate();
    }
};
