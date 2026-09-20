# LLM Snapshot（`llm/context/`）

按 AnalysisQuery 从各切片只读取数，拼成报告上下文。不算账、不写库。

| 你要做什么 | 调 |
|---|---|
| 组装 Snapshot | `snapshot_builder.SnapshotBuilder` |

禁止本包 `__init__.py` 再导出。

## 目录

| 文件 | 职责 |
|------|------|
| `snapshot_builder.py` | 按 analyses[] 取数 |
