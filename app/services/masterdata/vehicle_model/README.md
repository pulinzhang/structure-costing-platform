# 项目主数据 Service（`vehicle_model/`）

CRUD、生效窗口门禁、上传与解析契约。

对外入口：`service.VehicleModelService`。禁止本包 `__init__.py` 再导出。

## 架构

门面委托 `identity` / `crud` / `upload` / `catalog`。

## 职责

| 模块 | 职责 |
|------|------|
| `service.py` | 对外入口 |
| `identity.py` | 代号规范化、生效/失效、可引入门禁 |
| `crud.py` | 卡片列表、增删改 |
| `upload.py` | Excel 整单导入 |
| `catalog.py` | 导入模板、一览导出 |
