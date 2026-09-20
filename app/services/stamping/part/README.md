# 冲压零件 Service（`stamping/part/`）

列表、材料规格、增删改。工程变更插行/回滚不经 CRUD 类。

| 你要做什么 | 调 |
|---|---|
| 列表 / CRUD / 材料规格 | `crud.service.StampingPartService` |
| 工程变更当月命中、改图抄行、插行、回滚 | `engineering.service.StampingEngineeringService` |
| 拼焊子片 | `tailor_weld.service.StampingTailorWeldBlankService` |
| 工艺确认表 / 钢材测算导出 | `export.service.StampingPartExportService` |
| 工艺确认表 Excel 导入 | `upload.upload_service.StampingUploadService` |

禁止切片根 `stamping_service.py`。禁止本包 `__init__.py` 再导出。

## 目录

| 目录 | 职责 |
|------|------|
| `crud/` | 列表与增删改：`service.py` 入口，`list` / `materials` / `mutations` 实现 |
| `engineering/` | 工程变更：`service.py` 入口，`change.py` 插行 / 回滚算法 |
| `rules/` | 零件序号、同一零件下工序号不得重复（上传与模具布点共用） |
| `tailor_weld/` | 拼焊子片 |
| `export/` | 工艺确认表与钢材测算 Excel |
| `upload/` | 工艺确认表 Excel 导入（异步编排） |
