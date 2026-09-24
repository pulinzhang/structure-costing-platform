# 工程变更 Service（`engineering_change/`）

两条通道。设计变更是现网改图换号，代码在 `design_change/`。材料变更是同号切材料，代码在 `material_change/`。

Excel 入队改图、列表、回滚。算法在上游 `bom/`、`stamping/` 的 `engineering/`；本切片只编排与落库。

| 你要做什么 | 打开 |
|---|---|
| 列表 / 回滚 | `design_change.list.query.EngineeringChangeQueryService`、`design_change.list.rollback.EngineeringChangeRollbackService` |
| 下载模板 / 入队上传 | `design_change.upload.service.EngineeringChangeUploadService` |
| 异步编排 | `design_change.upload.orchestrator.orchestrator.EngineeringChangeOrchestrator` |
| 材料变更 | 见 `material_change/README.md` |

禁止本包、`design_change`、`material_change` 的 `__init__.py` 再导出。设计变更 HTTP 仍在 `/api/engineering-change`。材料变更前缀是 `/api/engineering-change/material`。

## 目录

| 目录 | 职责 |
|------|------|
| `design_change/list/` | 查询与回滚 |
| `design_change/upload/` | 模板、门禁、persist、编排 |
| `material_change/` | 同号切材料：上传、列表、回滚 |
