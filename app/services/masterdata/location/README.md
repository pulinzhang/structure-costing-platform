# 基地主数据 Service（`masterdata/location/`）

基地 CRUD 与别名。项目、供应商不在本包。

| 你要做什么 | 调 |
|---|---|
| 列表 / 增删改 / 别名 | `location_service.LocationService` |

禁止本包 `__init__.py` 再导出。HTTP 仍在 `/api/masterdata/locations`。

## 目录

| 文件 | 职责 |
|------|------|
| `location_service.py` | 对外入口 |
