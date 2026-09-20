# BOM 焊接费 Service（`bom/welding_fee/`）

列表、审核、删除。计算编排在 `calc/`。

| 你要做什么 | 调 |
|---|---|
| 列表 / 审核 / 删除 | `service.BomWeldingFeeService` |
| 异步计算 | `calc.orchestrator.orchestrator.BomWeldingFeeCalcOrchestrator` |
| Excel 导出 | `export.service.BomWeldingFeeExportService` |

禁止本包 `__init__.py` 再导出。HTTP 仍在 `/api/bom/welding-fees`。

## 目录

| 目录 / 文件 | 职责 |
|------|------|
| `service.py` | CRUD / 审核入口 |
| `fee_math.py` | 金额公式 |
| `calc/` | 计算日志与编排 |
| `export/` | Excel 导出 |
