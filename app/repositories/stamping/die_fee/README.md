# 冲压模具费仓储（`die_fee/`）

调本包：`repository.StampingDieFeeRepository`、`calc_log`。禁止上一级门面。

## 架构

```text
StampingDieFeeRepository
  StampingDieFeeQueries
  StampingDieFeeWrites(queries)
```

## 职责

| 模块 | 职责 |
|------|------|
| `repository.py` | 结果仓储门面（本包） |
| `calc_log.py` | 计算日志 |
| `queries.py` | 分页列表、导出、范围、HUD 汇总、下拉、零件费映射 |
| `writes.py` | 插入明细、按范围删除、审核/反审 |
| `types.py` | 列表筛选 TypedDict、金额转换 |
