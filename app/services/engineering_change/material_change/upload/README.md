# 材料变更上传 Service（`engineering_change/material_change/upload/`）

模板下载、Excel 入队。指挥家只编排：准备 → 管线写入冲压历史 → 落本通道切点单。

| 你要做什么 | 调 |
|---|---|
| Router 入口 | `service.MaterialChangeUploadService` |
| 入队 | `start_upload` |
| 异步编排 | `orchestrator.orchestrator.MaterialChangeOrchestrator` |
| 模板 | `template` |

禁止切片 `__init__.py` 再导出。HTTP 仍在 `/api/engineering-change/material`。

## 目录

| 目录 / 文件 | 职责 |
|------|------|
| `service.py` | 门面 |
| `start_upload.py` | 校验文件并入队 |
| `template.py` | 下载模板 |
| `gates.py` | 表内与对库门禁 |
| `orchestrator/` | 准备 → 流水线 → 落库 |
