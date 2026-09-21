# 用户与认证 Service（`settings/users/`）

登录、用户、权限码。看板与核价只读 `UserVO`，不在本包拼业务范围。

| 你要做什么 | 调 |
|---|---|
| 登录 | `auth.AuthService` |
| 用户 CRUD | `service.UserService` |
| 权限 | `permission.PermissionService` |

禁止本包 `__init__.py` 再导出。HTTP：`/api/auth`、`/api/settings/users`、`/api/settings`。

## 目录

| 文件 | 职责 |
|------|------|
| `auth.py` | 登录与会话 |
| `service.py` | 用户 |
| `permission.py` | 权限码 |
