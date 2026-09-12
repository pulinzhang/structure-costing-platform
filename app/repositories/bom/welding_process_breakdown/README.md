# 焊接工艺拆解 Repository（`welding_process_breakdown/`）

对外入口：上一级 `welding_process_breakdown_repository.py` 的 `BomWeldingProcessBreakdownRepository`。

## 架构

```text
BomWeldingProcessBreakdownRepository
  WeldingBreakdownQueries
  WeldingBreakdownWrites(queries)
```

## 职责

| 模块 | 职责 |
|------|------|
| `queries.py` | 分页列表、范围、导出、HUD 汇总、下拉 |
| `writes.py` | 节点/明细增改、按范围删未审、审核/反审 |
| `types.py` | 列表筛选 TypedDict |
