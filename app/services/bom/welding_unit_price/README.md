# BOM 焊接单价 Service（`bom/welding_unit_price/`）

焊接单价档案：列表、导入、导出。核价取单价走本切片，不要抄进 welding_fee。

| 你要做什么 | 调 |
|---|---|
| 列表 / 增删改 | `service.BomWeldingUnitPriceService` |
| Excel 导入 | `import_service.BomWeldingUnitPriceImportService` |
| Excel 导出 | `export.service.BomWeldingUnitPriceExportService` |

禁止本包 `__init__.py` 再导出。HTTP 仍在 `/api/bom/welding-unit-price`。

## 目录

| 文件 | 职责 |
|------|------|
| `service.py` | 列表与增删改 |
| `import_service.py` | Excel 导入 |
| `export/service.py` | Excel 导出 |
