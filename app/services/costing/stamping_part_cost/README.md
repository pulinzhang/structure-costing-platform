# 冲压零件核价 Service（`stamping_part_cost/`）

列表 / 审核门面。计算编排在 `calc/`。

对外入口：`StampingPartCostService`（`service.py`）。入队在门面类上，没有 `calc_ops.py`。

## 架构

门面委托 `queries` / `audit.service`；核价本身走 `calc.orchestrator.orchestrator.StampingPartCostCalcOrchestrator`。

## 职责

| 模块 | 职责 |
|------|------|
| `service.py` | 对外入口、计算入队、计算日志 |
| `queries.py` | 列表分页、展示字段（拼焊尺寸/钢价） |
| `audit/service.py` | 手工改价、范围删除/审核/反审核 |
| `calc/` | 单件/拼焊计价、费用匹配、批量落库 |
| `export/` | 核价结果 Excel（`export.service.StampingPartCostExportService`；含 `process_sheet/`） |
