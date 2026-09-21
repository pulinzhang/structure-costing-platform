# 问句解析（`llm/query/`）

口语 → `AnalysisQuery`。规则优先；LLM Structured Output 只作降级草稿。

| 你要做什么 | 调 |
|---|---|
| 解析入口 | `parser.pipeline.QueryParser` |
| 抽槽 | `condition_extractor.ConditionExtractor` |
| 词典对齐 | `entity_aligner.EntityAligner` |
| 钉月 | `time_range` |
| 规则流水线细节 | `parser/`（见该目录 README） |

禁止本包 `__init__.py` 再导出。`QueryParser.parse` 只编排，不是核算 Orchestrator。

## 目录

| 文件 / 目录 | 职责 |
|------|------|
| `parser/pipeline.py` | 对外入口 `QueryParser` |
| `condition_extractor.py` | 抽条件 |
| `entity_aligner.py` | 基地 / 项目 / 零件对齐 |
| `time_range.py` | 默认月 |
| `intent_router.py` | 就绪 / 帮助旁路 |
| `parser/` | 组合 analyses / subject / 上一问沿用 |
