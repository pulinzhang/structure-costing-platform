# 核价 Service（`costing/`）

下游核算。钢价 / 冲压件核价 / 成品核价各算各的；月度引擎只编排。

| 你要做什么 | 打开 |
|---|---|
| 月度自动核价 Run | `engine/` |
| 钢材价格维护与联动计算 | `steel_price/` |
| 冲压零件核价 | `stamping_part_cost/` |
| 成品（总成）月核价 | `assembly_cost/` |
| 采购价格只读表 | `procurement_contract_report/` |
| 月度核对多表打成一本 Excel | `monthly_bundle_export/` |

禁止本包 `__init__.py` 再导出。不要再开 `costing/report/`（报告挂在各切片计算日志下）。

HTTP：`/api/costing/engine`、`/api/costing/steel-price`、`/api/costing/stamping-part-cost`、`/api/costing/assembly-costs`、`/api/costing/procurement-contract-report`、`/api/costing/monthly-bundle`。

## 目录

| 目录 | 职责 |
|------|------|
| `engine/` | 范围、硬门禁、分阶段入队 |
| `steel_price/` | 钢价档案与公式计算 |
| `stamping_part_cost/` | 冲压件核价结果 |
| `assembly_cost/` | 成品核价结果 |
| `procurement_contract_report/` | 采购价格准备表 |
| `monthly_bundle_export/` | 多切片导出编排 |
