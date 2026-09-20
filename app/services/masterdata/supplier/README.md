# 供应商主数据 Service（`supplier/`）

CRUD、别名、上传与解析契约。

对外入口：`supplier_service.SupplierService`。禁止本包 `__init__.py` 再导出。

## 架构

门面委托 `identity` / `crud` / `upload` / `catalog`。

## 职责

| 模块 | 职责 |
|------|------|
| `supplier_service.py` | 对外入口 |
| `identity.py` | 全称/缩写/对外代码/别名解析、占用断言 |
| `crud.py` | 列表、增删改、别名 |
| `upload.py` | Excel 整单导入 |
| `catalog.py` | 导入模板、一览导出 |
