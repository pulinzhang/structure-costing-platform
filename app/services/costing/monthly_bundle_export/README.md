# 月度核对导出 Service（`costing/monthly_bundle_export/`）

同一 Workbook 串联各切片 `write_to_workbook`。不算账、不改结果表。

| 你要做什么 | 调 |
|---|---|
| 导出整本 | `export.service.MonthlyBundleExportService` |

禁止本包 `__init__.py` 再导出。HTTP 仍在 `/api/costing/monthly-bundle`。

## 目录

| 文件 | 职责 |
|------|------|
| `export/service.py` | 选切片、组册、出水印 xlsx |
