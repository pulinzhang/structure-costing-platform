# AI 助理 Service（`llm/`）

问句解析 → 确定性分析 → 组 Snapshot → Prompt + 模型。不算账。

| 你要做什么 | 打开 |
|---|---|
| 任务 / 幂等 / 落库 | `report_service.LlmAnalysisReportService` |
| 问句 → AnalysisQuery | `query/` |
| 确定性业务分析 | `analysis/` |
| 组 Snapshot | `context/` |
| Prompt 文本 | `prompts/` |
| 模型 HTTP | `client/` |
| 核价就绪口语 | `engine_readiness/` |
| 用法帮助口语 | `usage/` |
| 字段中文名 | `catalog/` |

禁止本包 `__init__.py` 再导出。HTTP 仍在 `/api/llm`。

## 目录

| 目录 / 文件 | 职责 |
|------|------|
| `query/` | 规则解析与词典对齐 |
| `analysis/` | trend / driver / comparison / risk |
| `context/` | Snapshot |
| `prompts/` | 静态 Prompt |
| `client/` | OpenAI 兼容 HTTP |
| `engine_readiness/` | 硬门禁口语 |
| `usage/` | 用法帮助 |
| `catalog/` | 字段标签 |
| `generator.py` | Prompt + LLM 解释 |
| `report_service.py` | 报告任务编排 |
