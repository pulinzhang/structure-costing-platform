# 材料变更 Service（`engineering_change/material_change/`）

同号只切 `material`。工艺列不改字。设计见 [docs/engineering-change/material-change/](../../../../docs/engineering-change/material-change/README.md)。

| 你要做什么 | 调 |
|---|---|
| 列表 / 原件 | `list.query.MaterialChangeQueryService` |
| 整本回滚 | `list.rollback.MaterialChangeRollbackService` |
| 零件抽屉切点 | `list.records.list_part_records` |
| 模板 / 入队上传 | `upload.service.MaterialChangeUploadService` |
| 异步编排 | `upload.orchestrator.orchestrator.MaterialChangeOrchestrator` |
| 当月材料 | `overlay.resolve_material`；批量叠切点 `overlay.overlay_materials_for_parts` |
| 改图抄切点 / 删抄行 | `copy.copy_cutovers` / `copy.delete_copied_cutovers` |

禁止本包 `__init__.py` 再导出。HTTP 仍在 `/api/engineering-change/material`。

## 目录

| 目录 / 文件 | 职责 |
|------|------|
| `codes.py` | 门禁文案 |
| `overlay.py` | 当月材料叠切点 |
| `copy.py` | 改图抄历史、回滚删抄行 |
| `list/` | 列表、抽屉、整本回滚 |
| `upload/` | 模板、门禁、入队、编排 |
