"""操作日志失败原因：对外句截断与 422 字段摘要（不含 input/ctx）。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TypedDict

ERROR_MESSAGE_MAX_LENGTH = 255
VALIDATION_FAIL_PREFIX = "请求参数校验失败"
HTTP_EXCEPTION_FALLBACK = "操作失败"
GENERIC_PUBLIC_ERROR = "系统内部错误，请稍后重试"


class ValidationErrorItem(TypedDict):
    field: str
    error: str


def clip_error_message(text: str) -> str:
    cleaned = text.strip()
    if len(cleaned) <= ERROR_MESSAGE_MAX_LENGTH:
        return cleaned
    return cleaned[: ERROR_MESSAGE_MAX_LENGTH - 1] + "…"


def http_exception_error_message(detail: object) -> str:
    if isinstance(detail, str):
        text = detail.strip()
        if text:
            return text
    return HTTP_EXCEPTION_FALLBACK


def parse_validation_errors(
    errors: Sequence[Mapping[str, object]],
) -> tuple[list[ValidationErrorItem], str]:
    items: list[ValidationErrorItem] = []
    for error in errors:
        msg_raw = error.get("msg")
        msg = str(msg_raw) if msg_raw is not None else ""
        items.append({"field": _field_from_loc(error.get("loc")), "error": msg})
    return items, _format_validation_audit_message(items)


def _format_validation_audit_message(items: Sequence[ValidationErrorItem]) -> str:
    if not items:
        return VALIDATION_FAIL_PREFIX
    parts: list[str] = []
    has_field = False
    for item in items:
        field = item["field"].strip()
        if field:
            has_field = True
            parts.append(f"{field}（{item['error']}）")
        else:
            parts.append(f"（{item['error']}）")
    if has_field:
        return f"{VALIDATION_FAIL_PREFIX}：" + "；".join(parts)
    if len(parts) == 1:
        return f"{VALIDATION_FAIL_PREFIX}{parts[0]}"
    return VALIDATION_FAIL_PREFIX + "；".join(parts)


def _field_from_loc(loc: object) -> str:
    if not isinstance(loc, list | tuple):
        return ""
    return ".".join(str(part) for part in loc if part != "body")
