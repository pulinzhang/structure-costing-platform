# 材料变更列表 Service（`engineering_change/material_change/list/`）

变更单查询与回滚。回滚调用冲压服务删除材料变更历史，本包不自己删历史表。

| 你要做什么 | 调 |
|---|---|
| 列表 / 原件 | `query.MaterialChangeQueryService` |
| 回滚 | `rollback.MaterialChangeRollbackService` |

禁止本包 `__init__.py` 再导出。HTTP 仍在 `/api/engineering-change/material`。

## 目录

| 文件 | 职责 |
|------|------|
| `query.py` | 列表与筛选 |
| `rollback.py` | 回滚编排 |
