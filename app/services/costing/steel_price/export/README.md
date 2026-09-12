# 钢材联动价格 Excel 导出（`export/`）

核对风排版 + 完整溯源列（默认折叠）。

对外入口：`steel_price_export_service.py`。

## 职责

| 模块 | 职责 |
|------|------|
| `service.py` | 取数、`export()` / `write_to_workbook` |
| `columns.py` | 列、表头、列宽、分组区间、对齐列集合 |
| `values.py` | 0 价留空、规格格式、筛选摘要、文件名 |
| `styles.py` | 颜色、字体、边框 |
| `workbook.py` | 分组表头、溯源列折叠、冻结 |
