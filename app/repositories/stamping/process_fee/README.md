# 冲压加工费仓储（`process_fee/`）

调本包：`repository.StampingProcessFeeRepository`、`calc_log`。禁止上一级门面。

## 架构

```text
StampingProcessFeeRepository
  StampingProcessFeeQueries
  StampingProcessFeeWrites(queries)
```

## 职责

| 模块 | 职责 |
|------|------|
| `repository.py` | 结果仓储门面（本包） |
| `calc_log.py` | 计算日志 |
| `queries.py` | 分页列表、导出、范围、HUD 汇总、下拉 |
| `writes.py` | upsert、替换工序分项、按范围删未审、审核/反审 |
| `types.py` | 列表筛选 TypedDict、待补价条件 |
