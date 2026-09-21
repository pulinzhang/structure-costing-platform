# Prompt 资源（`llm/prompts/`）

静态 markdown 与 `manifest.yaml`。改口径先改这里，不要把长文塞进 Python。

| 你要做什么 | 调 |
|---|---|
| 解析角色 + 用户壳 | `registry.PromptRegistry` |

禁止本包 `__init__.py` 再导出。

## 目录

| 文件 | 职责 |
|------|------|
| `registry.py` | 按角色取 Prompt |
| `manifest.yaml` | 角色清单 |
| `system_*.md` / `user_*.md` | 正文 |
| `_shared/` | 共用规则片段 |
