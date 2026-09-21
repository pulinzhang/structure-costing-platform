# BOM 包装运输费 Service（`bom/packaging_transport_fee/`）

包装运输费 CRUD、审核、Excel 导入导出。工程变更抄行挂 `engineering_change.py`，不另立 Engineering 类。

| 你要做什么 | 调 |
|---|---|
| 列表 / 增删改 / 审核 | `service.BomPackagingTransportFeeService` |
| Excel 导入 | `importing.service.BomPackagingTransportFeeImportService` |
| Excel 导出 | `export.service.BomPackagingTransportFeeExportService` |

禁止本包 `__init__.py` 再导出。HTTP 仍在 `/api/bom/packaging-transport-fee`。

## 目录

| 文件 | 职责 |
|------|------|
| `service.py` | 列表与增删改入口 |
| `importing/service.py` | Excel 导入 |
| `export/service.py` | Excel 导出 |
| `engineering_change.py` | 改图抄写 / 回滚 |
