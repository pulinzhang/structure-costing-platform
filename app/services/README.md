# Service 层（`app/services/`）

先看本表进切片，再打开该切片 `README.md` 的「你要做什么」。不要在本目录堆上帝类。

| 你要做什么 | 打开 |
|---|---|
| 冲压零件 / 工序 / 模具 / 费 | `stamping/` |
| BOM 树 / 焊接 / 采购对象 / 年度价 | `bom/` |
| 月核价 / 钢价 / 引擎 | `costing/` |
| 一事一议钢价政策 / 基价 / 废料价 | `yishiyiyi/` |
| 工程变更 Excel 入队与回滚 | `engineering_change/` |
| 主数据（基地 / 项目 / 供应商 / 牌号分类） | `masterdata/` |
| 登录 / 用户 / 系统参数 / 操作日志 | `settings/` |
| 看板 | `dashboard/` |
| AI 助理问句与报告 | `llm/` |
| 异步任务状态与 worker | `async_task/` |
| 上传文件归档与溯源 | `file_trace/` |

禁止各切片 `__init__.py` 再导出（含 `orchestrator/`）。调用编排器写 `….orchestrator.orchestrator`（引擎写 `….orchestrator.run_orchestrator`）。HTTP 仍在 `app/routers/`，路径不随目录搬家。
