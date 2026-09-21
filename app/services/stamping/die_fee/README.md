# 冲压模具费 Service（`stamping/die_fee/`）

列表、调整金额、审核删除。计算走 `calc/` 指挥家。工程变更抄行/回滚仍走 CRUD 入口转发，不另立 Engineering 类。

| 你要做什么 | 调 |
|---|---|
| 列表 / 改调整金额 / 审核 / 删除 / 工程变更抄行与回滚 | `service.StampingDieFeeService` |
| 异步计算 / 计算日志 | `calc.orchestrator.orchestrator.StampingDieFeeCalcOrchestrator` |
| Excel 导出 | `export.service.StampingDieFeeExportService` |

禁止本包 `__init__.py` 再导出。HTTP 仍在 `/api/stamping/die-fees`。

## 目录

| 目录 / 文件 | 职责 |
|------|------|
| `service.py` | 列表与审核删除入口；工程变更方法只转发 |
| `engineering/` | 改图抄写 / 回滚删除算法 |
| `calc/` | 计算编排、零件算法、计算日志 |
| `export/` | 模具费 Excel |
| `rules/` | 金额量化（CRUD 与计算共用） |
