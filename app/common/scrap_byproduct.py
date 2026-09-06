"""家模废料副产品：料片四列全空且净重 > 0。

工艺确认表上传写入零件主表；模具布点用同一判定定分摊（副产品 alloc=0），不改工艺主表。
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

OFFAL_SOURCE_FAMILY_DIE = "家模"
_ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class ScrapByproductMark:
    """四列全空判定结果；成立时覆盖利废标为家模。"""

    is_scrap_byproduct: bool
    is_offal_nested: bool
    offal_source: str | None


def resolve_scrap_byproduct(
    *,
    part_number: object,
    part_weight: Decimal | None,
    sheet_length: Decimal | None,
    sheet_width: Decimal | None,
    parts_per_sheet: int | None,
    raw_sheet_type: object,
    is_offal_nested: bool,
    offal_source: str | None,
) -> ScrapByproductMark:
    """Excel 料片式样原文为空才可能是副产品；写了「利用××废料」不打本列。"""
    if not _is_scrap_byproduct(
        part_number=part_number,
        part_weight=part_weight,
        sheet_length=sheet_length,
        sheet_width=sheet_width,
        parts_per_sheet=parts_per_sheet,
        raw_sheet_type=raw_sheet_type,
    ):
        return ScrapByproductMark(
            is_scrap_byproduct=False,
            is_offal_nested=is_offal_nested,
            offal_source=offal_source,
        )
    return ScrapByproductMark(
        is_scrap_byproduct=True,
        is_offal_nested=True,
        offal_source=OFFAL_SOURCE_FAMILY_DIE,
    )


def _is_scrap_byproduct(
    *,
    part_number: object,
    part_weight: Decimal | None,
    sheet_length: Decimal | None,
    sheet_width: Decimal | None,
    parts_per_sheet: int | None,
    raw_sheet_type: object,
) -> bool:
    if not _has_part_number(part_number):
        return False
    if part_weight is None or part_weight <= _ZERO:
        return False
    if sheet_length is not None or sheet_width is not None:
        return False
    if parts_per_sheet is not None and parts_per_sheet > 0:
        return False
    return _is_blank_text(raw_sheet_type)


def _has_part_number(value: object) -> bool:
    if value is None:
        return False
    return bool(str(value).strip())


def _is_blank_text(value: object) -> bool:
    if value is None:
        return True
    return not str(value).strip()


def layout_is_scrap_byproduct(
    *,
    part_number: object,
    part_weight: Decimal | None,
    sheet_length: Decimal | None,
    sheet_width: Decimal | None,
    parts_per_sheet: int | None,
    raw_sheet_type: object,
) -> bool:
    """布点/工艺共用的四列全空判定，不含利废回写。"""
    return _is_scrap_byproduct(
        part_number=part_number,
        part_weight=part_weight,
        sheet_length=sheet_length,
        sheet_width=sheet_width,
        parts_per_sheet=parts_per_sheet,
        raw_sheet_type=raw_sheet_type,
    )


def layout_is_scrap_byproduct_part(part: object) -> bool:
    """从布点零件已存料片列判定；缺字段视为空。"""
    return layout_is_scrap_byproduct(
        part_number=getattr(part, "part_number", None),
        part_weight=getattr(part, "part_weight", None),
        sheet_length=getattr(part, "sheet_length", None),
        sheet_width=getattr(part, "sheet_width", None),
        parts_per_sheet=getattr(part, "parts_per_sheet", None),
        raw_sheet_type=getattr(part, "sheet_shape", None),
    )
