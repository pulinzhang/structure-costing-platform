# 冲压零件核价 Repository（`stamping_part_cost/`）

对外入口：`StampingPartCostRepository`（`stamping_part_cost_repository.py`）。

## 架构

```text
StampingPartCostRepository
  StampingPartCostQueries
  StampingPartCostWrites(queries)
```

## 职责

| 模块 | 职责 |
|------|------|
| `stamping_part_cost_repository.py` | 门面委托 |
| `queries.py` | 分页列表、导出、HUD 汇总、成功行、下拉 |
| `writes.py` | upsert、按范围删未审、审核/反审 |
| `types.py` | HUD TypedDict、`empty_part_cost_summary` |
| `stamping_part_cost_calc_log_repository.py` | 计算锁 / 日志 |
