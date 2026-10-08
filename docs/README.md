# 文档目录

**大名** [结构件自动核价平台](architecture.md) · **简称** 核价平台。  
English: **Structural Parts Automated Costing Platform** / short **Costing Platform**.  
核价对象：总成、分总成、冲压件。AI 只解释、不算价。领域词「冲压件」仍指自制叶子，不要当成产品名。

平台规范放在本目录根下。领域设计按垂直切片分文件夹，与 `app/` / `static/js/features/` 对齐。工程变更跨切片，单独放 [engineering-change/](engineering-change/README.md)。

## 平台（根）

| 文档 | 说明 |
|------|------|
| [architecture.md](architecture.md) | 架构导读；文末有规范索引 |
| [architecture-constitution.mdc](architecture-constitution.mdc) | 索引 → `.cursor/rules/architecture-constitution.mdc`（分层正文只维护一处） |
| [orchestrator-constitution.mdc](orchestrator-constitution.mdc) | 索引 → `.cursor/rules/orchestrator-constitution.mdc` |
| [front-end.mdc](front-end.mdc) | 索引 → `.cursor/rules/front-end.mdc` |
| [light-theme-design.md](light-theme-design.md) | 浅色主题 |
| [naming-convention.mdc](naming-convention.mdc) | 索引 → `.cursor/rules/naming-convention.mdc` |
| [api-type-safety.md](api-type-safety.md) | 索引 → `.cursor/rules/api-type-safety.mdc` |
| [permission-design.md](permission-design.md) | 权限流程与规则；**树以 `catalog.json` 为准** |
| [fastapi-guide.md](fastapi-guide.md) | FastAPI 约定 |
| [deploy-windows-production.md](deploy-windows-production.md) | Windows 生产安装 |

## 设置 `settings/`

| 文档 | 状态 |
|------|------|
| [schema-comment-design.md](settings/schema-comment-design.md) | 表注释与删除前引用检查（设计定稿，未落地）：动态发现子表，中文名来自种子，无维护页 |

## 主数据 `masterdata/`

| 文档 | 状态 |
|------|------|
| [location-design.md](masterdata/location-design.md) | 基地（设计定稿，未落地）：现网 `location`；绝对上游；启用/禁用；§4.3 引用保护（修改与删除） |
| [vehicle-model-design.md](masterdata/vehicle-model-design.md) | 项目（已落地）：挂基地；上传+一览 HUD 分卡；写门禁已接到工艺/布点/BOM/档案/计算/引擎；下一跳外键另做 |
| [supplier-design.md](masterdata/supplier-design.md) | 供应商（第一期已落地；第二期：采购对象可空门禁 + 下一跳 RESTRICT + 改/删） |
| [steel-grade-category-design.md](masterdata/steel-grade-category-design.md) | 牌号分类（已落地）：主数据手工档案；下游只读 |
| [steel-mill-design.md](masterdata/steel-mill-design.md) | 钢厂（已落地）：缩写 + 全称 + 别名；基准价与加减价写入 `steel_mill_id`，对不上整本退回 |

## 冲压 `stamping/`

| 文档 | 状态 |
|------|------|
| [stamping-apqp-die-before-process-design.md](stamping/stamping-apqp-die-before-process-design.md) | 产品质量先期策划（APQP）先布点后工艺（已落地）：布点/工艺均必选该月可引入项目；工艺仍不要求布点 |
| [stamping-process-confirmation-design.md](stamping/stamping-process-confirmation-design.md) | 冲压工艺确认表（已落地）：加工费 + 材料/利废依据 |
| [stamping-steel-purchase-export-design.md](stamping/stamping-steel-purchase-export-design.md) | 钢材采购测算导出（已落地）：零件列表填数量，Excel 公式出吨 |
| [stamping-family-die-byproduct-design.md](stamping/stamping-family-die-byproduct-design.md) | 家模废料副产品（上传已落地）：主表 `is_scrap_byproduct`；材料 H×Q，不算冲压费 |
| [stamping-die-management-design.md](stamping/stamping-die-management-design.md) | 模具布点依据（已落地；导入顺序见上一行 APQP 设计） |
| [stamping-die-unit-price-design.md](stamping/stamping-die-unit-price-design.md) | 模具单价档案（已落地） |
| [stamping-gauge-fee-design.md](stamping/stamping-gauge-fee-design.md) | 检具费档案（已落地） |
| [stamping-die-fee-design.md](stamping/stamping-die-fee-design.md) | 年度模具费（已落地；不含检具） |

## 焊接 / BOM `bom/`

| 文档 | 状态 |
|------|------|
| [bom-annual-part-prices-design.md](bom/bom-annual-part-prices-design.md) | 年度零件价（已上线） |
| [annual-part-price-import-template-design.md](bom/annual-part-price-import-template-design.md) | 年度零件价导入模板（基地+项目外购叶子） |
| [welding-fee-design.md](bom/welding-fee-design.md) | 焊接费（已上线）：`bom_welding_fees` + `level`；财务读 `level=0` |
| [welding-process-breakdown-design.md](bom/welding-process-breakdown-design.md) | 焊接工艺拆解（已上线）：有原文即拆（含分总成），不计费 |
| [bom-procurement-objects-design.md](bom/bom-procurement-objects-design.md) | 采购对象清单（已落地）：退化供货件 / 分总成 / 冲压件；生成落库、检测、确认。基地/项目写读见该文 §13 |
| [bom-procurement-object-supplier-design.md](bom/bom-procurement-object-supplier-design.md) | 采购对象指定供应商（已落地）：行上点选规范全称 |
| [bom-procurement-object-supplier-upload-design.md](bom/bom-procurement-object-supplier-upload-design.md) | 采购对象批量上传供应商（已落地）：范围三项 + 窄表导回 |
| [bom-where-used-design.md](bom/bom-where-used-design.md) | 零件用在哪（已落地）：现网 BOM 按零件号/短码/名称向上追到 L0；路径简图 + 供货总成汇总 |

## 一事一议 `yishiyiyi/`

| 文档 | 状态 |
|------|------|
| [scrap-price-design.md](yishiyiyi/scrap-price-design.md) | 废料月度销售价（已落地）：基地×钢材/铝板；行=已启用基地 |
| [thickness-policy-category-level-design.md](yishiyiyi/thickness-policy-category-level-design.md) | 分类级厚度加减价（设计） |

## 核价 `costing/`

| 文档 | 状态 |
|------|------|
| [costing-engine-design.md](costing/costing-engine-design.md) | 月度引擎（已上线） |
| [assembly-costing-design.md](costing/assembly-costing-design.md) | 总成月核价（已落地）：级别无关；财务总费用与采购应成本同一批行 |
| [assembly-cost-restore-design.md](costing/assembly-cost-restore-design.md) | 总成核价成本还原报告（已落地）：异常时新页签画册级静态报告 |
| [procurement-contract-report-design.md](costing/procurement-contract-report-design.md) | 采购价格协议（已落地）：按供应商出《批量零部件价格协议》 |
| [l0-assembly-costing-design.md](costing/l0-assembly-costing-design.md) | 冻结史料：原 L0 成品核价口径（现网见总成月核价） |
| [l1-assembly-costing-design.md](costing/l1-assembly-costing-design.md) | 历史：委外应成本口径（结果表方案已作废） |
| [effective-period-design.md](costing/effective-period-design.md) | 协议价生效期（已否决）：年度价保持一年一行 |
| [provisional-final-settlement-design.md](costing/provisional-final-settlement-design.md) | 暂估 / 正式（已否决） |
| [anchor-true-up-design.md](costing/anchor-true-up-design.md) | 锚点送货与价差（已否决） |
| [t13j-offal-nesting-simulation.md](costing/t13j-offal-nesting-simulation.md) | T13J 利废件材料核算模拟（不改代码） |
| [offal-nested-material-design.md](costing/offal-nested-material-design.md) | 利废件材料价（已落地）：`R = 成品净重×废料单价` |

## 工程变更 `engineering-change/`

| 文档 | 状态 |
|------|------|
| [README.md](engineering-change/README.md) | 敢改地图：入口 / 不变量 / 代码地图（工程变更已落地） |
| [bom-process-die-effective-period-design.md](engineering-change/bom-process-die-effective-period-design.md) | BOM / 冲压工艺 / 模具有效期（设计）：现网改造 |
| [part-number-revision-design.md](engineering-change/part-number-revision-design.md) | 领域契约 §4.6–4.7、§8–§10；状态以同目录 README 为准；样表 `samples/` |
| [material-change/](engineering-change/material-change/README.md) | 材料变更（已落地）：同号切材料、不影响互换性；挂在工程变更下与设计变更并列 |
| [t28-2025-07-import-bundle-test-design.md](engineering-change/t28-2025-07-import-bundle-test-design.md) | 测试：青岛 T28 · 五种改法一本即可上传 |

## 异步任务 `async-task/`

| 文档 | 状态 |
|------|------|
| [async-task-design.md](async-task/async-task-design.md) | 长任务 runner（已上线）：辅助库进度、进程内线程池、各业务路由轮询 |

## 文件溯源 `file-trace/`

| 文档 | 状态 |
|------|------|
| [file-trace-design.md](file-trace/file-trace-design.md) | 已落盘 Excel 登记（已上线） |

## 智能分析 `llm/`

| 文档 | 状态 |
|------|------|
| [llm-slice-design.md](llm/llm-slice-design.md) | 切片实现导读（已上线）：流水线、目录、分发、改哪里 |
| [llm-costing-analysis-report-design.md](llm/llm-costing-analysis-report-design.md) | 产品契约（已定稿）：用户保证、公式、API |
