# 主数据 Service（`masterdata/`）

基地、项目、供应商、牌号分类。核价切片只读这些档案，不在这里算价。

| 你要做什么 | 打开 |
|---|---|
| 基地 | `location/` |
| 项目（车型） | `vehicle_model/` |
| 供应商 | `supplier/` |
| 牌号分类 | `steel_grade_category/` |

禁止本包 `__init__.py` 再导出。

HTTP：`/api/masterdata/locations`、`/api/masterdata/vehicle-models`、`/api/masterdata/suppliers`、`/api/masterdata/steel-grade-category`。

## 目录

| 目录 | 职责 |
|------|------|
| `location/` | 基地与别名 |
| `vehicle_model/` | 项目与生效窗 |
| `supplier/` | 供应商与别名 |
| `steel_grade_category/` | 牌号大类 |
