"""条件抽取：LLM 只把口语变成干净的 time_range / filters JSON。"""

from __future__ import annotations

import json
import re
from typing import Any

from app.services.llm.client import LlmClientError, OpenAiCompatibleClient

_EXTRACT_SYSTEM = """你是核价分析条件抽取器。用户用中文提问采购/核价相关问题。
你只输出一个 JSON 对象，不要 Markdown，不要解释。

JSON 字段（仅此）：
- time_range: { "start": "YYYY-MM", "end": "YYYY-MM" }  必填；单月则 start=end
- filters: 对象，可选键 location, vehicle_model, bom_version, part_number, tonnage（字符串；未知则省略该键）
- compare_locations: 字符串数组，跨基地对比时填写，否则 []

规则：
1. 只抽取时间与过滤条件，禁止编造金额、结论、分析类型。
2. 未提到的维度不要瞎填。
3. 「近N月」「今年以来」按常识换算成具体 YYYY-MM（缺少年份时用当前年）。
   若用户完全未提及时间，time_range 默认填充当前年月（start=end=当前年月）。
4. 零件号：完整码如 501006875AA，或口语 4 位数字简码如 8898，放入 filters.part_number。
5. 压机吨位如 40T、80吨 → filters.tonnage 填数字字符串（如 "40"），不要写入 vehicle_model。
"""


def _strip_json_fence(text: str) -> str:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


class ConditionExtractor:
    """自然语言 → {time_range, filters, compare_locations}；不算数、不定 analyses。"""

    def __init__(self, client: OpenAiCompatibleClient | None = None) -> None:
        self._client = client or OpenAiCompatibleClient()

    def extract(
        self,
        user_question: str,
        *,
        current_year: int,
        current_month: int,
    ) -> dict[str, Any]:
        question = (user_question or "").strip()
        if not question:
            raise LlmClientError("问题为空")

        anchor = f"{current_year:04d}-{current_month:02d}"
        user_prompt = (
            f"当前年月：{anchor}\n"
            f"用户问题：{question}\n"
            "请输出 JSON。"
        )
        result = self._client.chat(
            system_prompt=_EXTRACT_SYSTEM,
            user_prompt=user_prompt,
            temperature=0.0,
            max_tokens=500,
            response_format={"type": "json_object"},
        )
        raw = _strip_json_fence(result.content)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LlmClientError(f"条件抽取 JSON 解析失败: {raw[:200]}") from exc
        if not isinstance(data, dict):
            raise LlmClientError("条件抽取结果不是对象")
        return data
