# BOM Service（`bom/`）

BOM 上游切片根。零件树在 `bom/bom/`，本目录没有上帝类。

| 你要做什么 | 打开 |
|---|---|
| 快照 / 节点 / 生效窗 / 工程变更树 / Excel 上传 | `bom/`（子包 `app.services.bom.bom`） |
| 焊接工艺拆解 | `welding_process_breakdown/` |
| 焊接费列表与计算 | `welding_fee/` |
| 焊接单价 | `welding_unit_price/` |
| 包装运输费 | `packaging_transport_fee/` |
| 年度零件价 | `annual_part_price/` |
| 采购对象清单 | `procurement_object/` |
| 零件用在哪 | `where_used/` |

禁止本包 `__init__.py` 再导出。禁止在 `bom/` 根再放 `bom_service.py` 或第二套 `upload/`。

HTTP：`/api/bom`、`/api/bom/welding-process-breakdown`、`/api/bom/welding-fees`、`/api/bom/welding-unit-price`、`/api/bom/packaging-transport-fee`、`/api/bom/annual-part-price`、`/api/bom/procurement-objects`。

## 目录

| 目录 | 职责 |
|------|------|
| `bom/` | 树与版本；Excel 上传在 `bom/bom/upload/` |
| `welding_process_breakdown/` | 焊接工艺拆解 |
| `welding_fee/` | 焊接费 |
| `welding_unit_price/` | 焊接单价档案 |
| `packaging_transport_fee/` | 包装运输费 |
| `annual_part_price/` | 年度零件价 |
| `procurement_object/` | 采购对象清单 |
| `where_used/` | 零件用在哪 |
