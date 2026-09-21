# 系统设置 Service（`settings/`）

登录、用户、权限、系统参数、操作日志。

| 你要做什么 | 打开 |
|---|---|
| 登录 | `users.auth_service.AuthService` |
| 用户 | `users.user_service.UserService` |
| 权限 | `users.permission_service.PermissionService` |
| 系统参数 | `system.service.SettingsService` |
| 操作日志 | `logs.service.OperationLogService` |

禁止本包 `__init__.py` 再导出。

HTTP：`/api/auth`、`/api/settings/users`、`/api/settings`、`/api/settings/system`、`/api/settings/logs`。

## 目录

| 目录 | 职责 |
|------|------|
| `users/` | 认证、用户、权限 |
| `system/` | 系统参数 |
| `logs/` | 操作日志 |
