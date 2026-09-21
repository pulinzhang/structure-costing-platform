# 系统参数 Service（`settings/system/`）

键值系统设置。核价公式版本不放这里（在各切片常量）。

| 你要做什么 | 调 |
|---|---|
| 读取 / 更新 | `service.SettingsService` |

禁止本包 `__init__.py` 再导出。HTTP 仍在 `/api/settings/system`。

## 目录

| 文件 | 职责 |
|------|------|
| `service.py` | 对外入口 |
