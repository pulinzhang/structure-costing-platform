# 采购价格 Service（`costing/procurement_contract_report/`）

只读：准备表 + 价目汇总。范围按基地 + 项目 + 账期月，先爬 L0，禁止用 snapshot 定范围。

| 你要做什么 | 调 |
|---|---|
| 列表 / 预检 | `service.ProcurementContractReportService` |
| Excel 导出 | `export.orchestrator.ProcurementContractReportExportOrchestrator` |

禁止本包 `__init__.py` 再导出。导出必须全部版本（`bom_version` 空）。HTTP 仍在 `/api/costing/procurement-contract-report`。

## 目录

| 目录 / 文件 | 职责 |
|------|------|
| `service.py` | 查询入口 |
| `qty.py` | 数量口径 |
| `export/` | 工作簿编排 |
