/**
 * Module Index
 * 模板模块导出
 */

import { dashboardTemplate } from './dashboard.js';
import { uploadTemplate } from './upload.js';
import { partsTemplate } from './parts.js';
import { costingTemplate } from './costing.js';
import { quotationTemplate } from './quotation.js';
import { settingsTemplate } from './settings.js';

export const templates = {
    dashboard: dashboardTemplate,
    upload: uploadTemplate,
    parts: partsTemplate,
    costing: costingTemplate,
    quotation: quotationTemplate,
    settings: settingsTemplate,
};

export const pageMeta = {
    dashboard: { title: '仪表盘', breadcrumb: '仪表盘' },
    'stamping-upload': { title: '上传工艺文件', breadcrumb: '上传工艺文件' },
    'stamping-parts': { title: '零件列表', breadcrumb: '零件列表' },
    costing: { title: '核价', breadcrumb: '核价' },
    quotation: { title: '报价', breadcrumb: '报价' },
    settings: { title: '系统设置', breadcrumb: '系统设置' },
};
