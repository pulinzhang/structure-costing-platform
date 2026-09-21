# 工程变更列表 Service（`engineering_change/list/`）

变更单查询与回滚。回滚调用上游切片 `engineering` 算法，本包不复制插行公式。

| 你要做什么 | 调 |
|---|---|
| 列表 / 详情 | `query.EngineeringChangeQueryService` |
| 回滚 | `rollback.EngineeringChangeRollbackService` |

禁止本包 `__init__.py` 再导出。HTTP 仍在 `/api/engineering-change`。

## 目录

| 文件 | 职责 |
|------|------|
| `query.py` | 列表与筛选 |
| `rollback.py` | 回滚编排 |
