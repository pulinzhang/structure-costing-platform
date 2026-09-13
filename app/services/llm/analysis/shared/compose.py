"""把 analyses 片段收成单一 result。"""

from __future__ import annotations

from typing import Any


def compose_result(parts_result: dict[str, Any], *, default_kind: str) -> dict[str, Any]:
    if len(parts_result) == 1:
        return next(iter(parts_result.values()))
    if parts_result:
        return {"kind": "composite", "parts": parts_result}
    return {"kind": default_kind}
