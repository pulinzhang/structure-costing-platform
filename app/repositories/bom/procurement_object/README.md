# 采购对象清单 Repository（`procurement_object/`）

对外入口：上一级 `procurement_object_repository.py` 的 `BomProcurementObjectRepository`、`empty_procurement_object_summary`。

## 架构

```text
BomProcurementObjectRepository
  BomProcurementObjectQueries
  BomProcurementObjectWrites(queries)
```

## 职责

| 模块 | 职责 |
|------|------|
| `queries.py` | 清单/对象查询、分页、导出、HUD 汇总、生成日志 |
| `writes.py` | 建清单、批量建对象、审核/反审、删待审、回写抬头 |
| `types.py` | HUD TypedDict、`empty_procurement_object_summary` |
