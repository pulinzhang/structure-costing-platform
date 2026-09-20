# 冲压模具 Service（`stamping/die/`）

布点清单、导入导出、模具单价。工程变更插行/回滚不经 CRUD 类。

| 你要做什么 | 调 |
|---|---|
| 列表 / 详情 / 分摊比例 / 按项目删除 | `crud.service.StampingDieService` |
| 工程变更当月命中、改图抄行、插行、回滚 | `engineering.service.StampingDieEngineeringService` |
| 模具清单导出 | `export.service.StampingDieExportService` |
| 布点 Excel 导入 / 下载模板 | `upload.upload_service.StampingDieUploadService` |
| 模具单价档案 | `unit_price.service.StampingDieUnitPriceService` |

禁止本包 `__init__.py` 再导出。HTTP 仍在 `/api/stamping/die`。

## 目录

| 目录 | 职责 |
|------|------|
| `crud/` | 列表与增删改入口 |
| `engineering/` | 工程变更：`service.py` 入口，`change.py` 插行 / 回滚算法 |
| `upload/` | 布点 Excel：入队、模板、补模具号、分摊比例回写 |
| `export/` | 模具清单 Excel |
| `rules/` | 重量核对、布点身份匹配（上传与模具费共用） |
| `unit_price/` | 模具单价档案 |
