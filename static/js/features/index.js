/**
 * Features Module Index
 * 功能模块导出
 *
 * 目录结构说明：
 * features/           : 功能模块目录
 *   ├── dashboard/    : 仪表盘
 *   ├── stamping/    : 冲压相关功能
 *   │   ├── upload/  : 上传工艺文件
 *   │   └── parts/   : 零件列表
 *   ├── quotation/   : 报价
 *   ├── costing/     : 核价
 *   └── settings/    : 系统设置
 *
 * 每个功能目录下：
 *   ├── template.js  : HTML 模板
 *   └── index.js     : 页面逻辑 + pageConfig 导出
 */

/**
 * 页面元数据
 * 用于导航栏显示和面包屑
 */
export const pageMeta = {
    dashboard: { title: '仪表盘', breadcrumb: '仪表盘' },
    'stamping-upload': { title: '上传工艺文件', breadcrumb: '上传工艺文件' },
    'stamping-parts': { title: '零件列表', breadcrumb: '零件列表' },
    'stamping-tonnage': { title: '冲次费率', breadcrumb: '冲压 / 冲次费率' },
    'steel-price-list': { title: '钢材价格表格浏览', breadcrumb: '钢材价格管理 / 表格浏览' },
    'steel-price-policy-upload': { title: '厚度加减价导入', breadcrumb: '钢价政策 / 政策导入' },
    'steel-price-policy-download': { title: '厚度加减价导出', breadcrumb: '钢价政策 / 政策导出' },
    'base-price-upload': { title: '基准价格导入', breadcrumb: '钢材基准价格 / 基准价格导入' },
    'base-price-download': { title: '基准价格导出', breadcrumb: '钢材基准价格 / 基准价格导出' },
    costing: { title: '核价', breadcrumb: '核价' },
    quotation: { title: '报价', breadcrumb: '报价' },
    settings: { title: '系统设置', breadcrumb: '系统设置' },
};
