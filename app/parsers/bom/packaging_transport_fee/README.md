# 包装运输费 Excel 解析（`packaging_transport_fee/`）

生产样例（双行表头固定列）与平台扁平模板共用单元格转换。

对外入口：`app.parsers.bom.packaging_transport_fee_parser.parse_packaging_transport_fee_excel`。

## 职责

| 模块 | 职责 |
|------|------|
| `types.py` | 解析行 / 结果 dataclass |
| `cells.py` | 列名常量、金额/整数、跳过行、组行 |
| `production.py` | 生产样例表头识别与按固定列读行 |
| `flat.py` | 扁平模板列映射与读行 |
