"""PromptRegistry：加载 manifest + 拼接 _shared + 计算 hash。"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_PROMPTS_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True, slots=True)
class ResolvedPrompt:
    audience: str
    prompt_version: str
    system_prompt: str
    user_shell: str
    temperature: float
    max_tokens: int
    prompt_hash: str

    def render_user(
        self,
        *,
        user_question: str,
        report_type: str,
        audience: str,
        context_json: str,
    ) -> str:
        return (
            self.user_shell.replace("{user_question}", user_question)
            .replace("{report_type}", report_type)
            .replace("{audience}", audience)
            .replace("{context_json}", context_json)
        )


class PromptRegistry:
    def __init__(self, prompts_dir: Path | None = None) -> None:
        self._dir = prompts_dir or _PROMPTS_DIR
        self._manifest = self._load_manifest()

    def _load_manifest(self) -> dict[str, Any]:
        path = self._dir / "manifest.yaml"
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
        if not isinstance(data, dict):
            raise ValueError("prompts/manifest.yaml 格式错误")
        return data

    def _read_md(self, relative: str) -> str:
        path = self._dir / relative
        return path.read_text(encoding="utf-8").strip()

    def resolve(self, audience: str | None) -> ResolvedPrompt:
        defaults = self._manifest.get("defaults") or {}
        default_audience = str(defaults.get("audience") or "buyer_lead")
        resolved_audience = (audience or default_audience).strip() or default_audience

        audiences = self._manifest.get("audiences") or {}
        audience_cfg = audiences.get(resolved_audience) or audiences.get(default_audience)
        if not isinstance(audience_cfg, dict):
            raise KeyError(f"未知 audience: {resolved_audience}")

        shared_parts = [
            self._read_md(str(name))
            for name in (self._manifest.get("shared") or [])
        ]
        system_parts = [
            self._read_md(str(name))
            for name in (audience_cfg.get("system") or [])
        ]
        system_prompt = "\n\n".join([*system_parts, *shared_parts]).strip()
        user_shell = self._read_md(str(self._manifest.get("user_shell") or "user_report_shell.md"))

        version = str(self._manifest.get("version") or "v0.0.0")
        temperature = float(defaults.get("temperature") or 0.2)
        max_tokens = int(defaults.get("max_tokens") or 2500)
        digest = hashlib.sha256(
            f"{version}|{resolved_audience}|{system_prompt}|{user_shell}".encode("utf-8")
        ).hexdigest()[:16]

        return ResolvedPrompt(
            audience=resolved_audience,
            prompt_version=version,
            system_prompt=system_prompt,
            user_shell=user_shell,
            temperature=temperature,
            max_tokens=max_tokens,
            prompt_hash=digest,
        )

    def resolve_usage_help(self) -> ResolvedPrompt:
        """使用帮助专用 Prompt（不走 audience 分支）。"""
        shared_parts = [
            self._read_md(str(name))
            for name in (self._manifest.get("shared") or [])
            if str(name).endswith("chinese_style_rules.md")
        ]
        system_prompt = "\n\n".join(
            [self._read_md("system_usage_help.md"), *shared_parts]
        ).strip()
        user_shell = self._read_md("user_usage_shell.md")
        version = str(self._manifest.get("version") or "v0.0.0")
        defaults = self._manifest.get("defaults") or {}
        temperature = float(defaults.get("temperature") or 0.2)
        max_tokens = int(defaults.get("max_tokens") or 2500)
        digest = hashlib.sha256(
            f"{version}|usage_help|{system_prompt}|{user_shell}".encode("utf-8")
        ).hexdigest()[:16]
        return ResolvedPrompt(
            audience="usage_help",
            prompt_version=version,
            system_prompt=system_prompt,
            user_shell=user_shell,
            temperature=temperature,
            max_tokens=max_tokens,
            prompt_hash=digest,
        )

    def resolve_engine_readiness(self) -> ResolvedPrompt:
        """核算就绪检查专用 Prompt。"""
        shared_parts = [
            self._read_md(str(name))
            for name in (self._manifest.get("shared") or [])
            if str(name).endswith("chinese_style_rules.md")
        ]
        system_prompt = "\n\n".join(
            [self._read_md("system_engine_readiness.md"), *shared_parts]
        ).strip()
        user_shell = self._read_md("user_usage_shell.md")
        version = str(self._manifest.get("version") or "v0.0.0")
        defaults = self._manifest.get("defaults") or {}
        temperature = float(defaults.get("temperature") or 0.2)
        max_tokens = int(defaults.get("max_tokens") or 2500)
        digest = hashlib.sha256(
            f"{version}|engine_readiness|{system_prompt}|{user_shell}".encode("utf-8")
        ).hexdigest()[:16]
        return ResolvedPrompt(
            audience="engine_readiness",
            prompt_version=version,
            system_prompt=system_prompt,
            user_shell=user_shell,
            temperature=temperature,
            max_tokens=max_tokens,
            prompt_hash=digest,
        )
