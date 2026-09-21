# LLM 客户端（`llm/client/`）

OpenAI 兼容 HTTP。解析与分析不直接打网，只经本包。

| 你要做什么 | 调 |
|---|---|
| 发 chat | `openai_compatible.OpenAiCompatibleClient` |

禁止本包 `__init__.py` 再导出。

## 目录

| 文件 | 职责 |
|------|------|
| `openai_compatible.py` | 请求 / 超时 / 错误 |
