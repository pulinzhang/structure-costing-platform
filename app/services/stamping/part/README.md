# 冲压零件 Service（`stamping/part/`）

列表、材料规格、增删改。

对外入口：`StampingPartService`（`../stamping_service.py`）。

## 架构

`StampingPartService` 委托本目录 `list` / `materials` / `mutations`。

## 职责

| 模块 | 职责 |
|------|------|
| `../stamping_service.py` | 对外入口 |
| `list.py` | 零件列表、级联筛、主数据汇总 |
| `materials.py` | 材料去重、拼焊子片尺寸、钢价规格 |
| `mutations.py` | 增删改、利废、工序系数 |
