# 冲压零件 Excel 导出（`part/export/`）

两张表共用取数排序，排版不同。

对外入口：`part.export.service.StampingPartExportService`。

## 架构

```text
StampingPartExportService
  ProcessConfirmExport(repository, style)
  SteelPurchaseExport(process_confirm, style)
```

## 职责

| 模块 | 职责 |
|------|------|
| `service.py` | 门面：注入 Repository、装配两个导出类 |
| `process_confirm.py` | 工艺确认表编排（表头、写块、共用取数/排序） |
| `part_block.py` | 零件块：主表合并、工序/拼焊行 |
| `sketch.py` | 简图缩放嵌入 |
| `steel_purchase.py` | 钢材测算（数量手填、吨公式） |
| `constants.py` | 列数、列宽、配色 |
| `helpers.py` | 简图路径、合并格、`PartExportStyle` |
