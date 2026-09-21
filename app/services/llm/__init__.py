"""
LLM 垂直切片 — Service 层。

| 子包/模块 | 职责 |
|-----------|------|
| `query/` | AnalysisQuery 解析（规则 + 可选 Structured Output + 词典对齐） |
| `analysis/` | 确定性业务分析（trend/driver/comparison/risk/drilldown） |
| `_money.py` / `comparison_basis.py` | 切片叶模块（金额、移月、口径）；query 与 analysis 只向下依赖 |
| `context/` | Snapshot 组装 |
| `generator.py` | Prompt + LLM 解释 |
| `report.py` | 任务 / 幂等 / 落库编排 |
| `prompts/` | Prompt 静态资源 |
| `client/` | 模型 HTTP |
"""
