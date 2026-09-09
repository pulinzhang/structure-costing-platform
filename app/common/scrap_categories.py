"""废料月度价类别（库内存中文短码）。"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BeforeValidator

from app.exceptions.base import BusinessException

SCRAP_CATEGORY_STEEL = "钢材"
SCRAP_CATEGORY_ALUMINUM = "铝板"

SCRAP_CATEGORIES: tuple[str, ...] = (
    SCRAP_CATEGORY_STEEL,
    SCRAP_CATEGORY_ALUMINUM,
)

SCRAP_CATEGORY_LABELS: dict[str, str] = {
    SCRAP_CATEGORY_STEEL: "钢材料",
    SCRAP_CATEGORY_ALUMINUM: "铝材",
}


def parse_scrap_category(raw: str | None) -> str:
    text = (raw or "").strip()
    if text not in SCRAP_CATEGORIES:
        raise ValueError("废料类别只允许钢材或铝板")
    return text


def require_scrap_category(raw: str | None) -> str:
    try:
        return parse_scrap_category(raw)
    except ValueError as exc:
        raise BusinessException(str(exc)) from exc


def _coerce_scrap_category(value: Any) -> str:
    if value is None:
        return parse_scrap_category(None)
    return parse_scrap_category(str(value))


ScrapCategory = Annotated[str, BeforeValidator(_coerce_scrap_category)]
