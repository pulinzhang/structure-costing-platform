# BOM 零件用在哪 Service（`bom/where_used/`）

按零件号反查 BOM 节点出现位置。只读。

| 你要做什么 | 调 |
|---|---|
| 查询 | `service.BomWhereUsedService` |
| Excel 导出 | `export.BomWhereUsedExportService` |

禁止本包 `__init__.py` 再导出。HTTP 仍在 `/api/bom`（where-used 路由）。

## 目录

| 文件 | 职责 |
|------|------|
| `service.py` | 查询入口 |
| `export.py` | Excel 导出 |
