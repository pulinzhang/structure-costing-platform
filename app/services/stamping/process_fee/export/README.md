# 冲压加工费 Excel 导出（`process_fee/export/`）

左侧主表按零件合并；右侧工序明细一行一序。

对外入口：`stamping_process_fee_export_service.py`。

## 职责

| 模块 | 职责 |
|------|------|
| `service.py` | 取数、`export()` / `write_to_workbook` |
| `columns.py` | 列、表头、列宽、行高、列号 |
| `values.py` | 短码、吨位来源文案、筛选摘要、文件名 |
| `styles.py` | 颜色、字体、主表/明细分隔线 |
| `workbook.py` | 合并主表、冻结、斑马纹 |
