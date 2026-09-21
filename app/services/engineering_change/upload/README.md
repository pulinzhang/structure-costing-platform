# 工程变更上传 Service（`engineering_change/upload/`）

模板下载、Excel 入队。指挥家只编排：门禁 → persist → 上游抄行。

| 你要做什么 | 调 |
|---|---|
| Router 入口 | `upload_service.EngineeringChangeUploadService` |
| 入队 | `start_upload` |
| 异步编排 | `orchestrator.orchestrator.EngineeringChangeOrchestrator` |
| 模板 | `template_builder` |

禁止切片 `__init__.py` 再导出。HTTP 仍在 `/api/engineering-change`。

## 目录

| 目录 / 文件 | 职责 |
|------|------|
| `upload_service.py` | 门面 |
| `start_upload.py` | 校验文件并入队 |
| `template_builder.py` | 下载模板 |
| `gates/` | 表内与切片一致性门禁 |
| `persist/` | 按切片落库 |
| `orchestrator/` | 准备 → 流水线 → 落库 |
