# BOM 年度零件价 Service（`bom/annual_part_price/`）

年度零件价 CRUD、审核、Excel 导入导出。工程变更抄行挂 `engineering_change.py`，不另立 Engineering 类。

| 你要做什么 | 调 |
|---|---|
| 列表 / 增删改 / 审核 | `service.BomAnnualPartPriceService` |
| Excel 导入 | `importing.service.BomAnnualPartPriceImportService` |
| Excel 导出 | `export.service.BomAnnualPartPriceExportService` |

禁止本包 `__init__.py` 再导出。HTTP 仍在 `/api/bom/annual-part-price`。

## 目录

| 文件 | 职责 |
|------|------|
| `service.py` | 列表与增删改入口 |
| `importing/service.py` | Excel 导入 |
| `export/service.py` | Excel 导出 |
| `engineering_change.py` | 改图抄写 / 回滚 |
| `template_source.py` | 导入模板来源 |
| `template_builder.py` | 下载模板 |
