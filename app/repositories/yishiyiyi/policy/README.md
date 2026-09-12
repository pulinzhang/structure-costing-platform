# 钢价政策 Repository（`policy/`）

对外入口：`SteelPricePolicyRepository`、`PolicyFilter`、`MatchFilter`（`steel_price_policy_repository.py`）。

## 架构

```text
SteelPricePolicyRepository
  SteelPricePolicyQueries
  SteelPricePolicyWrites(queries)
  SteelPricePolicyExport
```

## 职责

| 模块 | 职责 |
|------|------|
| `steel_price_policy_repository.py` | 门面委托 |
| `types.py` | `PolicyFilter` / `MatchFilter` |
| `filters.py` | 品类范围、可选业务键、导出共用筛选 |
| `queries.py` | 分页列表、下拉、业务键匹配、按期加载 |
| `writes.py` | 主表/明细增删改、条件批量删除 |
| `export.py` | 导出主表、扁平化行、明细统计 |
| `dto.py` | 筛选下拉 / 导出行 DTO |
