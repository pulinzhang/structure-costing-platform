"""OpenAI 兼容 Chat Completions 客户端（DeepSeek / 千问等）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings
from app.utils.logging_config import get_logger

logger = get_logger("service.llm.client")


@dataclass(frozen=True, slots=True)
class LlmChatResult:
    content: str
    model: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    raw: dict[str, Any]


class LlmClientError(Exception):
    """调用模型失败。"""


class OpenAiCompatibleClient:
    """只读 Settings.LLM_*；不访问业务库。"""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        self.api_key = (api_key if api_key is not None else settings.LLM_API_KEY).strip()
        self.base_url = (base_url if base_url is not None else settings.LLM_BASE_URL).rstrip("/")
        self.model = (model if model is not None else settings.LLM_MODEL).strip()
        self.timeout_seconds = (
            timeout_seconds if timeout_seconds is not None else int(settings.LLM_TIMEOUT_SECONDS)
        )

    def chat(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 2500,
        response_format: dict[str, str] | None = None,
    ) -> LlmChatResult:
        if not self.api_key:
            raise LlmClientError("未配置 LLM_API_KEY")
        if not self.model:
            raise LlmClientError("未配置 LLM_MODEL")

        url = f"{self.base_url}/chat/completions"
        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if response_format is not None:
            payload["response_format"] = response_format
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise LlmClientError(f"LLM 网络错误: {exc}") from exc

        if response.status_code >= 400:
            raise LlmClientError(f"LLM HTTP {response.status_code}: {response.text[:500]}")

        try:
            body = response.json()
        except ValueError as exc:
            raise LlmClientError("LLM 响应非 JSON") from exc

        choices = body.get("choices") if isinstance(body, dict) else None
        if not isinstance(choices, list) or not choices:
            raise LlmClientError("LLM 响应缺少 choices")

        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = ""
        if isinstance(message, dict):
            content = str(message.get("content") or "").strip()
        if not content:
            raise LlmClientError("LLM 返回空正文")

        usage = body.get("usage") if isinstance(body, dict) else None
        prompt_tokens = None
        completion_tokens = None
        total_tokens = None
        if isinstance(usage, dict):
            prompt_tokens = _as_int(usage.get("prompt_tokens"))
            completion_tokens = _as_int(usage.get("completion_tokens"))
            total_tokens = _as_int(usage.get("total_tokens"))

        model_name = body.get("model") if isinstance(body, dict) else None
        return LlmChatResult(
            content=content,
            model=str(model_name) if model_name else self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            raw=body if isinstance(body, dict) else {},
        )


def _as_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None
