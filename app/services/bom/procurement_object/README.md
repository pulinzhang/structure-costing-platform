# 采购对象清单 Service（`bom/procurement_object/`）

从 BOM 生成采购对象、审核、供应商上传、Excel 导出。

| 你要做什么 | 调 |
|---|---|
| 列表 / 查询 | `service.BomProcurementObjectService` |
| 生成 | `generate_service.BomProcurementObjectGenerateService` |
| 插入行 | `insert_service.BomProcurementObjectInsertService` |
| 审核 | `audit_service.BomProcurementObjectAuditService` |
| 供应商 Excel | `supplier_upload_service.BomProcurementObjectSupplierUploadService` |
| Excel 导出 | `export.service.BomProcurementObjectExportService` |

禁止本包 `__init__.py` 再导出。HTTP 仍在 `/api/bom/procurement-objects`。

## 目录

| 文件 | 职责 |
|------|------|
| `service.py` | 查询入口 |
| `generate_service.py` | 从 BOM 生成 |
| `insert_service.py` | 手工插行 |
| `audit_service.py` | 审核 |
| `supplier_upload_service.py` | 供应商列上传 |
| `coverage.py` | 覆盖检查 |
| `snapshot_scope.py` | 账期范围（查询用，不定导出范围） |
| `export/service.py` | 取数、分 sheet |
| `columns.py` / `values.py` / `styles.py` / `workbook.py` | 导出版式 |
