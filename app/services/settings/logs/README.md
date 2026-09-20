# 操作日志 Service（`settings/logs/`）

写操作审计查询。业务切片通过 `app.common.audit` 落库，不要在本包写业务规则。

| 你要做什么 | 调 |
|---|---|
| 列表 / 筛选 | `operation_log_service.OperationLogService` |

禁止本包 `__init__.py` 再导出。HTTP 仍在 `/api/settings/logs`。

## 目录

| 文件 | 职责 |
|------|------|
| `operation_log_service.py` | 查询入口 |
