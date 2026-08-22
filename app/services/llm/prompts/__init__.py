"""
Prompt 静态资源 + 注册表。

已落地：`manifest.yaml`、`system_*.md`、`user_report_shell.md`、`_shared/*.md`、`registry.py`
"""

from app.services.llm.prompts.registry import PromptRegistry, ResolvedPrompt

__all__ = ["PromptRegistry", "ResolvedPrompt"]
