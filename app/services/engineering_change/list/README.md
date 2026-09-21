# 工程变更列表 Service（`engineering_change/list/`）

变更单查询与回滚。回滚调用上游切片 `engineering` 算法，本包不复制插行公式。

| 你要做什么 | 调 |
|---|---|
| 列表 / 详情 | `query_service.EngineeringChangeQueryService` |
| 回滚 | `rollback_service.EngineeringChangeRollbackService` |

禁止本包 `__init__.py` 再导出。HTTP 仍在 `/api/engineering-change`。

## 目录

| 文件 | 职责 |
|------|------|
| `query_service.py` | 列表与筛选 |
| `rollback_service.py` | 回滚编排 |
