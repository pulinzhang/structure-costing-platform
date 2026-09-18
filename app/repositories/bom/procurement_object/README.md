# 采购对象清单 Repository（`procurement_object/`）

对外入口：上一级 `procurement_object_repository.py` 的
`BomProcurementObjectRepository`、`ProcurementObjectAuditSummary`、
`ProcurementObjectScopeFilters`、`empty_procurement_object_summary`、
`object_scope_filters`。

## 架构

```text
BomProcurementObjectRepository
  BomProcurementObjectQueries
  BomProcurementObjectWrites(queries)
```

## 职责

| 模块 | 职责 |
|------|------|
| `queries.py` | 清单/对象查询、分页、导出、HUD 汇总、`map_l0_periods`、生成日志；筛参走 `_apply_object_filters(scope)` |
| `writes.py` | 建清单、批量建对象、审核/反审、删待审、回写抬头 |
| `types.py` | `ProcurementObjectAuditSummary`、`ProcurementObjectScopeFilters`、`object_scope_filters`、`empty_procurement_object_summary`、`count_matching` |

列表 / HUD / 导出共用 `ProcurementObjectScopeFilters`。有效期只认所属 L0 树根：`as_of_year`+`as_of_month` 有值时 join 树根 + `period_hit_clause`；对象行不落生失效四列。
