# 牌号分类 Service（`masterdata/steel_grade_category/`）

钢材牌号大类档案与导出。一事一议政策按大类匹配，不在本包写阶梯价。

| 你要做什么 | 调 |
|---|---|
| 列表 / 增删改 | `service.SteelGradeCategoryService` |
| 一览导出 | `export.service.SteelGradeCategoryExportService` |
| 种子数据 | `seed` |

禁止本包 `__init__.py` 再导出。HTTP 仍在 `/api/masterdata/steel-grade-category`。

## 目录

| 文件 | 职责 |
|------|------|
| `service.py` | 对外入口 |
| `catalog.py` | 下拉与展示名 |
| `export/service.py` | Excel |
| `seed.py` | 初始分类 |
