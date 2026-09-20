# 冲压加工费 Service（`stamping/process_fee/`）

列表、其它费用、审核删除。计算走 `calc/` 指挥家，不经 CRUD 类。

| 你要做什么 | 调 |
|---|---|
| 列表 / 改其它费用 / 审核 / 删除 | `crud.service.StampingProcessFeeService` |
| 异步计算 / 计算日志 | `calc.orchestrator.orchestrator.StampingProcessFeeCalcOrchestrator` |
| Excel 导出 | `export.service.StampingProcessFeeExportService` |

禁止本包 `__init__.py` 再导出。HTTP 仍在 `/api/stamping/process-fees`。

## 目录

| 目录 | 职责 |
|------|------|
| `crud/` | 列表与审核删除入口 |
| `calc/` | 计算编排、零件/拼焊算法、计算日志 |
| `export/` | 加工费 Excel |
| `rules/` | 范围校验、金额量化（CRUD 与计算共用） |
