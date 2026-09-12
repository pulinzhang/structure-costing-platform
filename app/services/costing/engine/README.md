# 核价引擎门禁（`engine/`）

硬门禁：当期上游是否齐套。`GateChecker.check` 只编排各组检查，不落库。

对外入口：`GateChecker`（`gate_checker.py`）。  
跳转：`gate_navigate.py`。

## 架构

`GateChecker` 注入各切片 Repository，按组调用 `gate/` 下的检查函数。

## 职责

| 模块 | 职责 |
|------|------|
| `gate_checker.py` | 检查顺序、注入 Repo、汇总条目 |
| `gate/item.py` | 条目组装、跳转开关 |
| `gate/stamping.py` | 项目 / 冲压工艺 / 冲次单价 |
| `gate/welding.py` | 焊接单价 |
| `gate/bom.py` | BOM 快照 / 年度零件价 / 包装运输 |
| `gate/steel.py` | 基价与厚度政策覆盖 |
| `gate/scrap.py` | 废料月度价 |
| `gate/rates.py` | 系统费率 |
