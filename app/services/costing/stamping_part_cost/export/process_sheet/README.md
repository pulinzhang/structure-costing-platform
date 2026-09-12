# 冲压零件核价结果 Excel（`export/process_sheet/`）

工艺清单口径宽表。普通件一行一件；拼焊按子片分行，总成列合并。

包名 `export.process_sheet` 替代原 `process_sheet.py`，公开符号不变。

## 职责

| 模块 | 职责 |
|------|------|
| `writer.py` | 标题表头、列宽冻结、导出入口 |
| `columns.py` | 列定义、合并列集合 |
| `cells.py` | 身份列、成品费率公式、摆剪单价 |
| `rows.py` | 数据行 / 拼焊分行公式 |
| `note.py` | 「冲压核价口径」附录文案 |
| `filename.py` | 下载文件名 |
