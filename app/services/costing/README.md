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

## 改 X → 打开 Y

门面都是切片根 `service.py`（入队也在这里，没有 `calc_ops.py`）。引擎指挥文件例外：`engine/orchestrator/run_orchestrator.py`（别人叫 `orchestrator.py`）。

| 意图 | 冲压零件核价 | 成品月核价 |
|---|---|---|
| 列表 / 单条 | `service.py` → `queries.py` | `service.py` |
| 批量删除 / 审核 / 反审 | `audit/service.py` | `audit/service.py` |
| HTTP 导出 Excel | `export/service.py` → `export/process_sheet/` | `export/service.py` → `export/workbook/` |
| 计算过程报告 Excel | 没有 | `calc_report/service.py`（禁止 import `export/`） |
| 开始计算 / 计算日志 | `service.py` → `calc/orchestrator/` | `service.py` → `calc/orchestrator/` |
| 计算前齐套检查 | `calc/orchestrator/ready.py` | `calc/orchestrator/ready.py` |
| 核价卡还原 | 没有 | `restore/service.py` |
| 月度核对一本账 | `monthly_bundle_export/export/service.py` | 同一入口，叠成品 finance 视图 |

采购价格导出是 `procurement_contract_report/export/orchestrator.py` + `workbook.py`，没有 `workbook/` 包。

## 目录

| 目录 | 职责 |
|------|------|
| `engine/` | 范围、硬门禁、分阶段入队 |
| `steel_price/` | 钢价档案与公式计算 |
| `stamping_part_cost/` | 冲压件核价结果 |
| `assembly_cost/` | 成品核价结果 |
| `procurement_contract_report/` | 采购价格准备表 |
| `monthly_bundle_export/` | 多切片导出编排 |
