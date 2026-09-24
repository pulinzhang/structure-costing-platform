# 冲压零件 Service（`stamping/part/`）

列表、材料规格、增删改。工程变更插行/回滚不经 CRUD 类。

| 你要做什么 | 调 |
|---|---|
| 列表 / CRUD / 材料规格 | `service.StampingPartService` |
| 设计变更当月命中、改图 clone、插行、回滚 | `engineering.design_change.service.StampingDesignChangeService` |
| 材料变更历史插入、删除、列出 | `engineering.material_change.StampingMaterialChangeService` |
| 拼焊子片 | `tailor_weld.service.StampingTailorWeldBlankService` |
| 工艺确认表 / 钢材测算导出 | `export.service.StampingPartExportService` |
| 工艺确认表 Excel 导入 | `upload.service.StampingUploadService` |

禁止切片根 `stamping_service.py`。禁止本包 `__init__.py` 再导出。

## 目录

| 目录 / 文件 | 职责 |
|------|------|
| `service.py` | 列表与增删改入口 |
| `list.py` / `materials.py` / `mutations.py` | 列表、材料规格、写操作 |
| `engineering/design_change/` | 设计变更工艺零件：`as_of` 当月命中，`clone` 改图三样，`insert` 写入零件、工序、材料变更历史与拼焊子片，`rollback` 回滚工艺零件，`service` 入口 |
| `engineering/material_change.py` | 材料变更历史 |
| `rules/` | 零件序号、同一零件下工序号不得重复（上传与模具布点共用） |
| `tailor_weld/` | 拼焊子片 |
| `export/` | 工艺确认表与钢材测算 Excel |
| `upload/` | 工艺确认表 Excel 导入（异步编排） |
