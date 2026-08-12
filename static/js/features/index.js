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
 * - title: 文档/无障碍标题
 * - en: 顶栏英文刻度代号（data-en）
 * - breadcrumb: 路径段（不含品牌根 STAMPING），由 app.js 渲染为 STAMPING // …
 */
export const pageMeta = {
    dashboard: {
        title: '仪表盘',
        en: 'DASHBOARD_OVERVIEW',
        breadcrumb: ['仪表盘'],
    },
    'stamping-upload': {
        title: '上传工艺文件',
        en: 'PROCESS_FILE_UPLOAD',
        breadcrumb: ['冲压工程', '上传工艺文件'],
    },
    'stamping-parts': {
        title: '零件列表',
        en: 'PARTS_MASTER',
        breadcrumb: ['冲压工程', '零件列表'],
    },
    'stamping-tonnage': {
        title: '冲次费率',
        en: 'TONNAGE_RATES_MATRIX',
        breadcrumb: ['冲压工程', '冲次费率'],
    },
    'steel-price-list': {
        title: '钢材联动价格一览',
        en: 'STEEL_LINKAGE_LIST',
        breadcrumb: ['钢材联动价', '钢材联动价格一览'],
    },
    'steel-price-calc': {
        title: '钢材联动计算',
        en: 'STEEL_LINKAGE_CALC',
        breadcrumb: ['钢材联动价', '钢材联动计算'],
    },
    'steel-price-policy-upload': {
        title: '厚度加减价上传',
        en: 'THICKNESS_POLICY_UPLOAD',
        breadcrumb: ['一事一议', '厚度加减价', '上传'],
    },
    'steel-price-policy-download': {
        title: '厚度加减价列表',
        en: 'THICKNESS_POLICY_LIST',
        breadcrumb: ['一事一议', '厚度加减价', '厚度加减价列表'],
    },
    'base-price-upload': {
        title: '基准价格上传',
        en: 'BASE_PRICE_UPLOAD',
        breadcrumb: ['一事一议', '基准价格', '上传'],
    },
    'base-price-download': {
        title: '基准价格列表',
        en: 'BASE_PRICE_DATABASE',
        breadcrumb: ['一事一议', '基准价格', '基准价格列表'],
    },
    costing: {
        title: '自动核价引擎',
        en: 'AUTOMATED_COSTING',
        breadcrumb: ['核价'],
    },
    quotation: {
        title: '报价单管理',
        en: 'QUOTATION_GEN',
        breadcrumb: ['报价'],
    },
    settings: {
        title: '系统设置',
        en: 'SYSTEM_CONFIG',
        breadcrumb: ['设置', '系统设置'],
    },
    'settings-users': {
        title: '用户管理',
        en: 'USER_ADMIN',
        breadcrumb: ['设置', '用户管理'],
    },
    'settings-logs': {
        title: '操作日志',
        en: 'AUDIT_LOGS',
        breadcrumb: ['设置', '操作日志'],
    },
    'settings-profile': {
        title: '个人资料',
        en: 'USER_PROFILE',
        breadcrumb: ['设置', '个人资料'],
    },
};
