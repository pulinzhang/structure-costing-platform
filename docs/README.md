# 文档目录

平台规范放在本目录根下。领域设计按垂直切片分文件夹，与 `app/` / `static/js/features/` 对齐。

## 平台（根）

| 文档 | 说明 |
|------|------|
| [architecture.md](architecture.md) | 架构导读；文末有规范索引 |
| [architecture-constitution.mdc](architecture-constitution.mdc) | 分层与切片依赖硬规则（与 `.cursor/rules` 同步） |
| [orchestrator-constitution.mdc](orchestrator-constitution.mdc) | 核算 Orchestrator 只编排不执行（与 `.cursor/rules` 同步） |
| [front-end.mdc](front-end.mdc) | SPA / Brabus / HUD 表 |
| [light-theme-design.md](light-theme-design.md) | 浅色主题 |
| [naming-convention.mdc](naming-convention.mdc) | 标识符命名 |
| [api-type-safety.md](api-type-safety.md) | `ApiResponse` / `PageResult` / Decimal |
| [permission-design.md](permission-design.md) | 权限码与菜单树 |
| [fastapi-guide.md](fastapi-guide.md) | FastAPI 约定 |
| [deploy-windows-production.md](deploy-windows-production.md) | Windows 生产安装 |

## 冲压 `stamping/`

| 文档 | 状态 |
|------|------|
| [stamping-process-confirmation-design.md](stamping/stamping-process-confirmation-design.md) | 冲压工艺确认表（已落地）：加工费 + 材料/利废依据 |
| [stamping-die-management-design.md](stamping/stamping-die-management-design.md) | 模具布点依据（已落地） |
| [stamping-die-unit-price-design.md](stamping/stamping-die-unit-price-design.md) | 模具单价档案（已落地） |
| [stamping-gauge-fee-design.md](stamping/stamping-gauge-fee-design.md) | 检具费档案（已落地） |
| [stamping-die-fee-design.md](stamping/stamping-die-fee-design.md) | 年度模具费（已落地；不含检具） |

## 焊接 / BOM `bom/`

| 文档 | 状态 |
|------|------|
| [bom-annual-part-prices-design.md](bom/bom-annual-part-prices-design.md) | 年度零件价（已上线） |
| [welding-fee-design.md](bom/welding-fee-design.md) | 焊接费（已上线）：`bom_welding_fees` + `level`；财务读 `level=0` |
| [welding-process-breakdown-design.md](bom/welding-process-breakdown-design.md) | 焊接工艺拆解（已上线）：有原文即拆（含分总成），不计费 |
| [bom-procurement-objects-design.md](bom/bom-procurement-objects-design.md) | 采购对象清单（已落地）：退化供货件 / 分总成 / 冲压件，生成落库、检测、确认 |

## 一事一议 `yishiyiyi/`

| 文档 | 状态 |
|------|------|
| [steel-grade-category-design.md](yishiyiyi/steel-grade-category-design.md) | 牌号分类（已落地） |
| [thickness-policy-category-level-design.md](yishiyiyi/thickness-policy-category-level-design.md) | 分类级厚度加减价（设计） |

## 核价 `costing/`

| 文档 | 状态 |
|------|------|
| [costing-engine-design.md](costing/costing-engine-design.md) | 月度引擎（已上线） |
| [l0-assembly-costing-design.md](costing/l0-assembly-costing-design.md) | L0 成品核价（已上线） |
| [outsourced-assembly-costing-design.md](costing/outsourced-assembly-costing-design.md) | 委外应成本（草案）：核价定公式；集合见采购对象清单 |
| [effective-period-design.md](costing/effective-period-design.md) | 协议价生效期（设计） |
| [provisional-final-settlement-design.md](costing/provisional-final-settlement-design.md) | 暂估 / 正式（设计） |
| [anchor-true-up-design.md](costing/anchor-true-up-design.md) | 锚点送货与价差（设计） |
| [t13j-offal-nesting-simulation.md](costing/t13j-offal-nesting-simulation.md) | T13J 利废件材料核算模拟（不改代码） |
| [offal-nested-material-design.md](costing/offal-nested-material-design.md) | 利废件材料价（已落地）：`R = 成品净重×废料单价` |

## 文件溯源 `file-trace/`

| 文档 | 状态 |
|------|------|
| [file-trace-design.md](file-trace/file-trace-design.md) | 已落盘 Excel 登记（已上线） |

## 智能分析 `llm/`

| 文档 | 状态 |
|------|------|
| [llm-costing-analysis-report-design.md](llm/llm-costing-analysis-report-design.md) | AI 助理解释层（已定稿） |
