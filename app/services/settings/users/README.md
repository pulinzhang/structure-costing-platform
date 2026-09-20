# 用户与认证 Service（`settings/users/`）

登录、用户、权限码。看板与核价只读 `UserVO`，不在本包拼业务范围。

| 你要做什么 | 调 |
|---|---|
| 登录 | `auth_service.AuthService` |
| 用户 CRUD | `user_service.UserService` |
| 权限 | `permission_service.PermissionService` |

禁止本包 `__init__.py` 再导出。HTTP：`/api/auth`、`/api/settings/users`、`/api/settings`。

## 目录

| 文件 | 职责 |
|------|------|
| `auth_service.py` | 登录与会话 |
| `user_service.py` | 用户 |
| `permission_service.py` | 权限码 |
