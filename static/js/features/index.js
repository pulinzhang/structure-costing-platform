/**
 * Features Module Index
 * 功能模块导出 / 页面元数据
 *
 * 目录结构与 static/index.html 左侧菜单树对齐：
 *
 * features/
 * ├── dashboard/                 # 仪表盘
 * ├── stamping/                  # 冲压工程（年度：冲压加工费）
 * │   ├── process/               # 冲压工艺
 * │   │   ├── upload/            # 上传工艺文件
 * │   │   └── parts/             # 冲压零件列表
 * │   ├── die/                   # 冲压模具
 * │   │   ├── upload/            # 上传模具布点
 * │   │   ├── list/              # 模具清单
 * │   │   └── unit-price/        # 模具单价
 * │   ├── gauge-fee/             # 冲压检具费
 * │   │   ├── upload/
 * │   │   └── list/
 * │   ├── tonnage/               # 冲次单价
 * │   │   ├── upload/
 * │   │   └── list/
 * │   └── process-fee/           # 冲压加工费
 * │       ├── calc/
 * │       └── list/
 * ├── bom/                       # 焊接工程（年度：焊接费；技术目录仍为 bom）
 * │   ├── material/              # 材料清单
 * │   │   ├── upload/
 * │   │   ├── list/
 * │   │   ├── structure/
 * │   │   └── viz/
 * │   ├── welding-unit-price/    # 焊接单价
 * │   │   ├── upload/
 * │   │   └── list/
 * │   ├── packaging-transport-fee/  # 包装运输费
 * │   │   ├── upload/
 * │   │   └── list/
 * │   ├── procurement-object/     # 采购对象清单
 * │   │   ├── generate/
 * │   │   ├── list/
 * │   │   └── supplier-upload/
 * │   ├── annual-part-price/     # 年度零件价（采购对象之下）
 * │   │   ├── upload/
 * │   │   └── list/
 * │   ├── welding-process-breakdown/  # 焊接工艺拆解
 * │   │   ├── generate/
 * │   │   └── list/
 * │   └── welding-fee/           # 焊接费
 * │       ├── calc/
 * │       └── list/
 * ├── yishiyiyi/                 # 一事一议（钢材政策 / 月度废料价等）
 * │   ├── policy/                # 加减价政策
 * │   │   ├── upload/
 * │   │   └── list/
 * │   ├── base-price/            # 基准价格
 * │   │   ├── upload/
 * │   │   └── list/
 * │   ├── steel-grade-category/  # 牌号分类
 * │   ├── winning-thickness/     # 中标钢厂厚度价格一览表
 * │   │   └── list/
 * │   └── scrap-price/           # 废料月度销售价
 * ├── costing/                   # 核价
 * │   ├── steel-price/           # 冲压钢材联动价
 * │   │   ├── calc/
 * │   │   └── list/
 * │   ├── stamping-part-cost/    # 冲压零件价格核算
 * │   │   ├── calc/
 * │   │   └── list/
 * │   ├── assembly-cost/         # 总成核价
 * │   │   ├── calc/
 * │   │   └── list/
 * │   └── engine/                # 自动核价引擎
 * ├── file-trace/                # 文件溯源
 * ├── masterdata/                # 主数据
 * │   ├── location/              # 基地
 * │   ├── vehicle-model/         # 项目
 * │   │   ├── upload/
 * │   │   └── list/
 * │   └── supplier/{upload,list}/  # 供应商
 * ├── settings/                  # 设置
 * │   ├── profile/
 * │   ├── system/
 * │   ├── users/
 * │   └── logs/
 * └── login/                     # 登录（独立页，不在侧栏）
 *
 * 每个页面目录：
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
        en: 'MGMT_COSTING_BOARD',
        breadcrumb: ['仪表盘'],
    },
    'stamping-upload': {
        title: '上传工艺文件',
        en: 'PROCESS_FILE_UPLOAD',
        breadcrumb: ['冲压工程', '冲压工艺', '上传工艺文件'],
    },
    'stamping-parts': {
        title: '冲压零件列表',
        en: 'PARTS_MASTER',
        breadcrumb: ['冲压工程', '冲压工艺', '冲压零件列表'],
    },
    'stamping-die-upload': {
        title: '上传模具布点',
        en: 'DIE_LAYOUT_UPLOAD',
        breadcrumb: ['冲压工程', '冲压模具', '上传模具布点'],
    },
    'stamping-die-list': {
        title: '模具清单',
        en: 'DIE_LAYOUT_LIST',
        breadcrumb: ['冲压工程', '冲压模具', '模具清单'],
    },
    'stamping-die-unit-price': {
        title: '模具单价',
        en: 'DIE_UNIT_PRICE',
        breadcrumb: ['冲压工程', '冲压模具', '模具单价'],
    },
    'stamping-die-fee-calc': {
        title: '冲压模具费计算',
        en: 'DIE_FEE_CALC',
        breadcrumb: ['冲压工程', '冲压模具费', '冲压模具费计算'],
    },
    'stamping-die-fee': {
        title: '冲压模具费列表',
        en: 'DIE_FEE_LIST',
        breadcrumb: ['冲压工程', '冲压模具费', '冲压模具费列表'],
    },
    'stamping-gauge-fee-upload': {
        title: '检具费上传',
        en: 'GAUGE_FEE_UPLOAD',
        breadcrumb: ['冲压工程', '冲压检具费', '上传'],
    },
    'stamping-gauge-fee': {
        title: '检具费列表',
        en: 'GAUGE_FEE_LIST',
        breadcrumb: ['冲压工程', '冲压检具费', '检具费列表'],
    },
    'stamping-tonnage-upload': {
        title: '冲次单价上传',
        en: 'TONNAGE_RATE_UPLOAD',
        breadcrumb: ['冲压工程', '冲次单价', '上传'],
    },
    'stamping-tonnage': {
        title: '冲次单价列表',
        en: 'TONNAGE_RATES_MATRIX',
        breadcrumb: ['冲压工程', '冲次单价', '冲次单价列表'],
    },
    'stamping-process-fee-calc': {
        title: '冲压加工费计算',
        en: 'PROCESS_FEE_CALC',
        breadcrumb: ['冲压工程', '冲压加工费', '冲压加工费计算'],
    },
    'stamping-process-fee': {
        title: '冲压加工费列表',
        en: 'PROCESS_FEE_LIST',
        breadcrumb: ['冲压工程', '冲压加工费', '冲压加工费列表'],
    },
    'steel-price-list': {
        title: '冲压钢材联动价一览',
        en: 'STAMPING_STEEL_LINKAGE_LIST',
        breadcrumb: ['核价', '冲压钢材联动价', '冲压钢材联动价一览'],
    },
    'steel-price-calc': {
        title: '冲压钢材联动计算',
        en: 'STAMPING_STEEL_LINKAGE_CALC',
        breadcrumb: ['核价', '冲压钢材联动价', '冲压钢材联动计算'],
    },
    'stamping-part-cost-calc': {
        title: '冲压零件价格计算',
        en: 'PART_COST_CALC',
        breadcrumb: ['核价', '冲压零件价格核算', '冲压零件价格计算'],
    },
    'stamping-part-cost': {
        title: '冲压零件价格一览',
        en: 'PART_COST_LIST',
        breadcrumb: ['核价', '冲压零件价格核算', '冲压零件价格一览'],
    },
    'l0-assembly-cost-calc': {
        title: '总成核价计算',
        en: 'ASSEMBLY_COST_CALC',
        breadcrumb: ['核价', '总成核价', '总成核价计算'],
    },
    'l0-assembly-cost': {
        title: '总成核价一览',
        en: 'ASSEMBLY_COST_LIST',
        breadcrumb: ['核价', '总成核价', '总成核价一览'],
    },
    'assembly-cost-calc': {
        title: '总成核价计算',
        en: 'ASSEMBLY_COST_CALC',
        breadcrumb: ['核价', '总成核价', '总成核价计算'],
    },
    'assembly-cost': {
        title: '总成核价一览',
        en: 'ASSEMBLY_COST_LIST',
        breadcrumb: ['核价', '总成核价', '总成核价一览'],
    },
    'steel-price-policy-upload': {
        title: '加减价政策上传',
        en: 'PRICE_POLICY_UPLOAD',
        breadcrumb: ['一事一议', '加减价政策', '上传'],
    },
    'steel-price-policy-download': {
        title: '加减价政策列表',
        en: 'PRICE_POLICY_LIST',
        breadcrumb: ['一事一议', '加减价政策', '加减价政策列表'],
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
    'steel-grade-category': {
        title: '牌号分类',
        en: 'STEEL_GRADE_CATEGORY',
        breadcrumb: ['一事一议', '牌号分类'],
    },
    'winning-thickness-download': {
        title: '中标钢厂厚度价格一览表',
        en: 'WINNING_MILL_THICKNESS_PRICE_LIST',
        breadcrumb: ['一事一议', '中标钢厂厚度价格一览表'],
    },
    'scrap-price': {
        title: '废料月度销售价',
        en: 'SCRAP_MONTH_MATRIX',
        breadcrumb: ['一事一议', '废料月度销售价'],
    },
    'bom-structure': {
        title: '产品结构',
        en: '产品结构',
        breadcrumb: ['焊接工程', '材料清单', '产品结构'],
    },
    'bom-viz': {
        title: '产品结构图',
        en: '产品结构图',
        breadcrumb: ['焊接工程', '材料清单', '产品结构', '结构图'],
    },
    'bom-upload': {
        title: '上传材料清单',
        en: 'BOM_UPLOAD',
        breadcrumb: ['焊接工程', '材料清单', '上传材料清单'],
    },
    'bom-material': {
        title: '材料清单列表',
        en: 'BOM_MATERIAL_LIST',
        breadcrumb: ['焊接工程', '材料清单', '材料清单列表'],
    },
    'bom-welding-unit-price-upload': {
        title: '焊接单价上传',
        en: 'WELDING_UNIT_PRICE_UPLOAD',
        breadcrumb: ['焊接工程', '焊接单价', '上传'],
    },
    'bom-welding-unit-price': {
        title: '焊接单价列表',
        en: 'WELDING_UNIT_PRICE_MATRIX',
        breadcrumb: ['焊接工程', '焊接单价', '焊接单价列表'],
    },
    'bom-packaging-transport-fee-upload': {
        title: '包装运输费上传',
        en: 'PKG_TRANSPORT_FEE_UPLOAD',
        breadcrumb: ['焊接工程', '包装运输费', '上传'],
    },
    'bom-packaging-transport-fee': {
        title: '包装运输费列表',
        en: 'PKG_TRANSPORT_FEE_MATRIX',
        breadcrumb: ['焊接工程', '包装运输费', '包装运输费列表'],
    },
    'bom-procurement-object': {
        title: '生成采购对象清单',
        en: 'PROCUREMENT_OBJECT_GENERATE',
        breadcrumb: ['焊接工程', '采购对象', '生成'],
    },
    'bom-procurement-object-list': {
        title: '采购对象清单',
        en: 'PROCUREMENT_OBJECT_LIST',
        breadcrumb: ['焊接工程', '采购对象', '采购对象清单'],
    },
    'bom-procurement-object-supplier-upload': {
        title: '上传供应商',
        en: 'PROCUREMENT_OBJECT_SUPPLIER_UPLOAD',
        breadcrumb: ['焊接工程', '采购对象', '上传供应商'],
    },
    'bom-annual-part-price-upload': {
        title: '年度零件价上传',
        en: 'ANNUAL_PART_PRICE_UPLOAD',
        breadcrumb: ['焊接工程', '年度零件价', '上传'],
    },
    'bom-annual-part-price': {
        title: '年度零件价列表',
        en: 'ANNUAL_PART_PRICE_MATRIX',
        breadcrumb: ['焊接工程', '年度零件价', '年度零件价列表'],
    },
    'bom-welding-process-breakdown': {
        title: '焊接工艺拆解',
        en: 'WELDING_PROCESS_BREAKDOWN',
        breadcrumb: ['焊接工程', '焊接工艺拆解', '拆解'],
    },
    'bom-welding-process-breakdown-list': {
        title: '焊接工艺拆解列表',
        en: 'WELDING_PROCESS_BREAKDOWN_LIST',
        breadcrumb: ['焊接工程', '焊接工艺拆解', '拆解列表'],
    },
    'bom-welding-fee-calc': {
        title: '焊接费计算',
        en: 'WELDING_FEE_CALC',
        breadcrumb: ['焊接工程', '焊接费', '计算'],
    },
    'bom-welding-fee-list': {
        title: '焊接费列表',
        en: 'WELDING_FEE_LIST',
        breadcrumb: ['焊接工程', '焊接费', '列表'],
    },
    costing: {
        title: '自动核价引擎',
        en: 'AUTOMATED_COSTING',
        breadcrumb: ['核价', '自动核价引擎'],
    },
    'file-trace': {
        title: '文件溯源',
        en: 'FILE_TRACE',
        breadcrumb: ['文件溯源'],
    },
    location: {
        title: '基地',
        en: 'LOCATION',
        breadcrumb: ['主数据', '基地'],
    },
    'vehicle-model-upload': {
        title: '项目上传',
        en: 'PROJECT UPLOAD',
        breadcrumb: ['主数据', '项目', '上传'],
    },
    'vehicle-model-list': {
        title: '项目一览',
        en: 'PROJECT',
        breadcrumb: ['主数据', '项目', '一览表'],
    },
    'supplier-upload': {
        title: '供应商上传',
        en: 'SUPPLIER UPLOAD',
        breadcrumb: ['主数据', '供应商', '上传'],
    },
    'supplier-list': {
        title: '供应商一览',
        en: 'SUPPLIER',
        breadcrumb: ['主数据', '供应商', '一览表'],
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
