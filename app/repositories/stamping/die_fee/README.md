# 冲压模具费 Repository（`die_fee/`）

对外入口：上一级 `die_fee_repository.py` 的 `StampingDieFeeRepository`。

## 架构

```text
StampingDieFeeRepository
  StampingDieFeeQueries
  StampingDieFeeWrites(queries)
```

## 职责

| 模块 | 职责 |
|------|------|
| `queries.py` | 分页列表、导出、范围、HUD 汇总、下拉、零件费映射 |
| `writes.py` | 插入明细、按范围删除、审核/反审 |
| `types.py` | 列表筛选 TypedDict、金额转换 |
