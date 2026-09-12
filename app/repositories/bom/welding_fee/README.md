# 焊接费 Repository（`welding_fee/`）

对外入口：上一级 `welding_fee_repository.py` 的 `BomWeldingFeeRepository`。

## 架构

```text
BomWeldingFeeRepository
  BomWeldingFeeQueries
  BomWeldingFeeWrites(queries)
```

## 职责

| 模块 | 职责 |
|------|------|
| `queries.py` | 分页列表、导出、计算范围、HUD 汇总、下拉 |
| `writes.py` | upsert、替换明细、按范围删未审、审核/反审 |
| `types.py` | 列表筛选 TypedDict |
