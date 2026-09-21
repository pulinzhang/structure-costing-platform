# 冲压 Service（`stamping/`）

冲压上游切片根。零件与工序主数据在 `part/`，本目录没有上帝类。

| 你要做什么 | 打开 |
|---|---|
| 零件 / 工序 / 工艺确认表上传与导出 | `part/` |
| 模具台账 / 布点导入 / 模具单价 | `die/` |
| 加工费列表与计算 | `process_fee/` |
| 模具费列表与计算 | `die_fee/` |
| 检具费 | `gauge_fee/` |
| 冲次单价 | `tonnage_price/` |

禁止本包 `__init__.py` 再导出。禁止再放 `stamping_service.py`、`part_export/`、切片根 `upload/`。

HTTP：`/api/stamping`、`/api/stamping/upload`、`/api/stamping/die`、`/api/stamping/die-unit-prices`、`/api/stamping/process-fees`、`/api/stamping/die-fees`、`/api/stamping/gauge-fees`、`/api/stamping/tonnage-price`。

## 目录

| 目录 | 职责 |
|------|------|
| `part/` | 零件与工序；工艺 Excel 属本切片 |
| `die/` | 模具布点与单价 |
| `process_fee/` | 加工费 |
| `die_fee/` | 模具费 |
| `gauge_fee/` | 检具费 |
| `tonnage_price/` | 冲次单价 |
