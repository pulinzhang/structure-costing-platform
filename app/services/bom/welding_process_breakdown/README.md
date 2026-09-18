# 焊接工艺拆解 Service（`welding_process_breakdown/`）

查询 / 改明细 / 从 BOM 生成 / 审核。Router 只依赖门面。

对外入口：`BomWeldingProcessBreakdownService`（`service.py`）。

## 架构

门面委托 `query` / `lines` / `generate_task` / `generate_service` / `audit_service`。

## 职责

| 模块 | 职责 |
|------|------|
| `service.py` | 对外入口 |
| `query.py` | 列表分页、HUD、节点旁证 |
| `lines.py` | 未审核节点下工艺明细改写 |
| `generate_task.py` | 异步拆解入队 |
| `generate_service.py` | 从 BOM 生成；合册 `copy_for_new_tree`（抄旧结果，不重拆） |
| `audit_service.py` | 范围删除 / 审核 / 反审核 |
| `export/` | L0 导出编排 |
