# 成品月核价 Repository（`assembly_cost/`）

数据访问：查询与写入是独立类，`AssemblyCostRepository` 门面委托。

对外入口：`from app.repositories.costing.assembly_cost.assembly_cost_repository import AssemblyCostRepository`。

## 架构

```text
AssemblyCostRepository
  AssemblyCostQueries
  AssemblyCostWrites(queries)
```

## 职责

| 模块 | 职责 |
|------|------|
| `assembly_cost_repository.py` | 门面委托 |
| `queries.py` | 列表筛选、HUD 汇总、导出取数、结算价窗口、按 id / 业务键取卡 |
| `writes.py` | upsert 子行、审核/反审、按范围删除 |
| `payloads.py` | 写入 dataclass、MAIN_FIELDS、汇总 TypedDict |
| `assembly_cost_calc_log_repository.py` | 计算锁 / 日志 |
