# 焊接费 Excel 导出（`export/`）

主表按节点纵向合并，右侧工艺明细分行。

对外入口：`export.service.BomWeldingFeeExportService`。

## 职责

| 模块 | 职责 |
|------|------|
| `service.py` | 取数、补焊接原文、`export()` / `write_to_workbook` |
| `columns.py` | 列、表头、列宽、行高、`WeldingSheetLayout` |
| `values.py` | 短代码、金额合计、筛选摘要、文件名 |
| `styles.py` | 颜色、字体、计算/审核/匹配着色 |
| `workbook.py` | 合并主表、合计行、冻结、斑马纹 |
