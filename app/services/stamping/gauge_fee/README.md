# 冲压检具费 Service（`stamping/gauge_fee/`）

列表、改删、导入导出。工程变更抄行/回滚仍走 CRUD 入口转发，不另立 Engineering 类。

| 你要做什么 | 调 |
|---|---|
| 列表 / 改删 / 整包删除 / 工程变更抄行与回滚 | `service.StampingGaugeFeeService` |
| 检具费 Excel 导入 / 下载模板 | `upload.service.StampingGaugeFeeUploadService` |
| 检具费 Excel 导出 | `export.service.StampingGaugeFeeExportService` |

禁止本包 `__init__.py` 再导出。HTTP 仍在 `/api/stamping/gauge-fees`。

## 目录

| 目录 / 文件 | 职责 |
|------|------|
| `service.py` | 列表与增删改入口；工程变更方法只转发 |
| `engineering/` | 改图抄写 / 回滚删除算法 |
| `upload/` | Excel 导入与模板 |
| `export/` | Excel 导出 |
