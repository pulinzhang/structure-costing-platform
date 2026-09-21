# 核价引擎 Service（`costing/engine/`）

月度智能自动核价：范围发现、硬门禁、年度补算计划、分阶段编排。计算本身在各切片 `calc/`。

| 你要做什么 | 调 |
|---|---|
| 列表 / 预检 / 启动 / 删除 Run | `service.CostingEngineService` |
| 分阶段执行 | `orchestrator.run_orchestrator.RunOrchestrator` |
| 硬门禁 | `gate.checker.GateChecker` |
| 范围发现 | `scope.discovery.ScopeDiscovery` |
| 年度补算计划 | `plan.annual.AnnualCalcPlanner` |

禁止本包 `__init__.py` 再导出。HTTP 仍在 `/api/costing/engine`。

## 目录

| 目录 / 文件 | 职责 |
|------|------|
| `service.py` | 列表、预检、入队启动 |
| `scope/` | 当月 L0 范围发现 |
| `gate/` | 硬门禁编排与分组检查、去处理跳转 |
| `plan/` | 年度加工费 / 模具费 / 焊接补算计划 |
| `orchestrator/` | 准备 → 阶段 → 落库；进度映射 |

`GateChecker.check` 只编排各组检查，不落库。
