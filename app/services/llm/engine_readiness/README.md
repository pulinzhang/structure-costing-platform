# 核价就绪口语（`llm/engine_readiness/`）

把引擎硬门禁结果说成自然语言。门禁算法在 `costing/engine/gate/`，本包不复制检查。

| 你要做什么 | 调 |
|---|---|
| 口语化就绪 | `runner.EngineReadinessRunner` |

禁止本包 `__init__.py` 再导出。

## 目录

| 文件 | 职责 |
|------|------|
| `runner.py` | 读 GateChecker 结果 → 帮助文本 |
