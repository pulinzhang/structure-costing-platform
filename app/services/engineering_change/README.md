# 工程变更 Service（`engineering_change/`）

Excel 入队改图、列表、回滚。算法在上游 `bom/`、`stamping/` 的 `engineering/`；本切片只编排与落库。

| 你要做什么 | 打开 |
|---|---|
| 列表 / 回滚 | `list.query_service.EngineeringChangeQueryService`、`list.rollback_service.EngineeringChangeRollbackService` |
| 下载模板 / 入队上传 | `upload.upload_service.EngineeringChangeUploadService` |
| 异步编排 | `upload.orchestrator.orchestrator.EngineeringChangeOrchestrator` |

禁止本包 `__init__.py` 再导出。HTTP 仍在 `/api/engineering-change`。

## 目录

| 目录 | 职责 |
|------|------|
| `list/` | 查询与回滚 |
| `upload/` | 模板、门禁、persist、编排 |
