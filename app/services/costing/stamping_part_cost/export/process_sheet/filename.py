"""导出文件名：年月 + 基地 + 工厂 + 车型版本。"""

from __future__ import annotations

from typing import Any

from app.common.timezone import now

_FILENAME_ILLEGAL = '<>:"/\\|?*'


def _filename_token(value: object) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    for char in _FILENAME_ILLEGAL:
        text = text.replace(char, "")
    text = " ".join(text.split())
    return text or None


def _unique_row_value(rows: list[Any], attr: str) -> object | None:
    values = {getattr(row, attr, None) for row in rows}
    values.discard(None)
    values.discard("")
    if len(values) != 1:
        return None
    return next(iter(values))


def _unique_row_int(rows: list[Any], attr: str) -> int | None:
    raw = _unique_row_value(rows, attr)
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        text = raw.strip()
        if text.isdigit():
            return int(text)
    return None


def build_process_sheet_filename(
    rows: list[Any],
    *,
    year: int | None = None,
    month: int | None = None,
    location: str | None = None,
    stamping_supplier: str | None = None,
    vehicle_model: str | None = None,
    version: str | None = None,
) -> str:
    """冲压零件核价结果导出文件名：年月 + 基地 + 工厂 + 车型版本（有则带上）。"""
    year_value = year if year is not None else _unique_row_int(rows, "year")
    month_value = month if month is not None else _unique_row_int(rows, "month")
    location_value = location or _unique_row_value(rows, "location")
    supplier_value = stamping_supplier or _unique_row_value(rows, "stamping_supplier")
    vehicle_value = vehicle_model or _unique_row_value(rows, "vehicle_model")
    version_value = version or _unique_row_value(rows, "version")

    parts = ["冲压零件核价结果"]
    if year_value is not None and month_value is not None:
        parts.append(f"{year_value}年{month_value}月")
    elif year_value is not None:
        parts.append(f"{year_value}年")
    for token in (
        _filename_token(location_value),
        _filename_token(supplier_value),
        _filename_token(vehicle_value),
        _filename_token(version_value),
    ):
        if token:
            parts.append(token)
    stamp = now().strftime("%Y%m%d_%H%M%S")
    return "_".join(parts) + f"_{stamp}.xlsx"
