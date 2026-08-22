"""自由输入意图解析（纯规则，不再调一次 LLM）。"""

from __future__ import annotations

import re
from dataclasses import dataclass

VALID_REPORT_TYPES = frozenset(
    {
        "dashboard",
        "steel",
        "stamping_part",
        "l0",
        "part_drilldown",
        "gate",
        "exec_brief",
        "auto",
    }
)

DEFAULT_AUDIENCE: dict[str, str] = {
    "dashboard": "buyer_lead",
    "steel": "buyer",
    "stamping_part": "buyer",
    "l0": "buyer_lead",
    "part_drilldown": "buyer",
    "gate": "buyer_lead",
    "exec_brief": "exec",
}

# P0：exec_brief 关键词落到 dashboard（宽装包），避免未实现精简模板
_KEYWORD_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("跑不起来", "门禁", "主数据", "算不出", "硬停"), "gate"),
    (("钢材", "吨价", "厚宽", "加减价", "钢厂", "钢价"), "steel"),
    (("冲压件", "材料净", "加工费", "冲压工厂"), "stamping_part"),
    (("总成", "间接", "对主机厂", "供货总成"), "l0"),
    (("缺价", "partial", "算不全"), "dashboard"),
    (("一页纸", "汇报", "领导"), "dashboard"),
)

_PART_NUMBER_RE = re.compile(
    r"(?<![A-Za-z0-9])([A-Z0-9]{8,}[A-Z0-9\-]*)(?![A-Za-z0-9])",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class IntentResolution:
    requested_report_type: str
    resolved_report_type: str
    audience: str
    intent_source: str
    part_number: str | None


def resolve_intent(
    *,
    report_type: str,
    user_question: str,
    audience: str | None = None,
    prompt_id: str | None = None,
    scope_part_number: str | None = None,
) -> IntentResolution:
    requested = (report_type or "").strip().lower() or "auto"
    if requested not in VALID_REPORT_TYPES:
        requested = "auto"

    question = (user_question or "").strip()
    extracted_part = _extract_part_number(question) or (
        scope_part_number.strip() if scope_part_number else None
    )

    if requested != "auto":
        resolved = requested
        # P0：exec_brief 仍可用，装精简 dashboard packs
        source = "chip" if prompt_id else "explicit"
        if resolved == "part_drilldown" and not extracted_part:
            # 无零件号时降级 dashboard，避免空钻取
            resolved = "dashboard"
            source = "default_dashboard"
        aud = (audience or DEFAULT_AUDIENCE.get(resolved) or "buyer_lead").strip()
        return IntentResolution(
            requested_report_type=requested,
            resolved_report_type=resolved,
            audience=aud,
            intent_source=source,
            part_number=extracted_part if resolved == "part_drilldown" else scope_part_number,
        )

    # auto
    if extracted_part and _looks_like_part_question(question):
        aud = (audience or DEFAULT_AUDIENCE["part_drilldown"]).strip()
        return IntentResolution(
            requested_report_type="auto",
            resolved_report_type="part_drilldown",
            audience=aud,
            intent_source="rule",
            part_number=extracted_part,
        )

    lower_q = question.lower()
    for keywords, target in _KEYWORD_RULES:
        if any(key.lower() in lower_q or key in question for key in keywords):
            aud = (audience or DEFAULT_AUDIENCE.get(target) or "buyer_lead").strip()
            return IntentResolution(
                requested_report_type="auto",
                resolved_report_type=target,
                audience=aud,
                intent_source="rule",
                part_number=scope_part_number,
            )

    aud = (audience or DEFAULT_AUDIENCE["dashboard"]).strip()
    return IntentResolution(
        requested_report_type="auto",
        resolved_report_type="dashboard",
        audience=aud,
        intent_source="default_dashboard",
        part_number=scope_part_number,
    )


def _extract_part_number(text: str) -> str | None:
    match = _PART_NUMBER_RE.search(text.upper())
    if not match:
        return None
    candidate = match.group(1).upper()
    # 过短纯数字排除
    if candidate.isdigit() and len(candidate) < 10:
        return None
    return candidate


def _looks_like_part_question(text: str) -> bool:
    markers = ("零件", "零件号", "解读", "议价", "供应商", "这个号")
    return any(marker in text for marker in markers) or bool(_PART_NUMBER_RE.search(text))
