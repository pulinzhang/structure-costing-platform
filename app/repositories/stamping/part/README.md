# 冲压零件 Repository（`part/`）

对外入口：上一级 `stamping_part_repository.py` 的 `StampingPartRepository`。

## 架构

```text
StampingPartRepository
  StampingPartQueries
  StampingPartFilterOptions
  StampingPartWrites(queries)
  StampingPartMaterialSpecs
```

## 职责

| 模块 | 职责 |
|------|------|
| `queries.py` | 分页列表、导出加载、范围查询 |
| `filter_options.py` | 下拉与级联筛选 |
| `writes.py` | 创建/更新/按范围删零件+工序+拼焊子片 |
| `material_specs.py` | 钢价 Step1：主表 ∪ 拼焊子片规格 |
| `filters.py` | 工厂单值/多值过滤 |
| `types.py` | TypedDict 形状 |
