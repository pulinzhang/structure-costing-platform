# 钢材价格 Repository（`steel_price/`）

对外入口：`SteelPriceRepository`（`steel_price_repository.py`）。

## 架构

```text
SteelPriceRepository
  SteelPriceQueries
  SteelPriceWrites(queries)
```

## 职责

| 模块 | 职责 |
|------|------|
| `steel_price_repository.py` | 门面委托 |
| `queries.py` | 分页列表、导出、HUD 汇总、下拉、牌号料厚匹配 |
| `writes.py` | 增删改、按期审核/反审、删未审 |
| `types.py` | 列表筛选 TypedDict |
| `steel_price_calc_log_repository.py` | 计算锁 / 日志 |
