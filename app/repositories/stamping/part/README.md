# 冲压零件仓储（`part/`）

调本包：`repository.StampingPartRepository`、`process.StampingProcessRepository`、`tailor_weld_blank`。禁止切片根门面。

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
| `repository.py` | 零件仓储门面（本包） |
| `process.py` | 工序行 |
| `tailor_weld_blank.py` | 拼焊子片 |
| `queries.py` | 分页列表、导出加载、范围查询 |
| `filter_options.py` | 下拉与级联筛选 |
| `writes.py` | 创建/更新/按范围删零件+工序+拼焊子片 |
| `material_specs.py` | 钢价 Step1：主表 ∪ 拼焊子片规格 |
| `filters.py` | 工厂单值/多值过滤 |
| `types.py` | TypedDict 形状 |
