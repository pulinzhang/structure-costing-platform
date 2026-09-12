# 采购对象清单 Excel 导出

`export.py` 是对外门面。实现拆在同目录兄弟文件（避免与查询门面 `service.py` 撞名，编排放在 `export_service.py`）。

## 职责

| 模块 | 职责 |
|------|------|
| `export.py` | 对外 import |
| `export_service.py` | 取数、分 sheet、`export_excel()` |
| `columns.py` | 列、表头、列宽、分组区间 |
| `values.py` | 行值、检测摘要、文件名 |
| `styles.py` | 颜色、字体、sheet 页签色 |
| `workbook.py` | 合并供货总成/原件、冻结、页脚 |
