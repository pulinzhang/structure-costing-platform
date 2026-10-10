"""导出文件名：年月 + 基地 + 工厂 + 车型版本。"""

from __future__ import annotations

from app.common.timezone import now
from app.models.costing import StampingPartCost

_FILENAME_ILLEGAL = '<>:"/\\|?*'


def _filename_token(value: object) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    for char in _FILENAME_ILLEGAL:
        text = text.replace(char, "")
    text = " ".join(text.split())
    return text or None


def _unique_text(values: list[str]) -> str | None:
    present = {value.strip() for value in values if value.strip()}
    if len(present) != 1:
        return None
    return next(iter(present))


def _unique_int(values: list[int]) -> int | None:
    present = set(values)
    if len(present) != 1:
        return None
    return next(iter(present))


def build_process_sheet_filename(
    rows: list[StampingPartCost],
    *,
    year: int | None = None,
    month: int | None = None,
    location: str | None = None,
    stamping_supplier: str | None = None,
    vehicle_model: str | None = None,
    version: str | None = None,
) -> str:
    """冲压零件核价结果导出文件名：年月 + 基地 + 工厂 + 车型版本（有则带上）。"""
    year_value = year if year is not None else _unique_int([row.year for row in rows])
    month_value = month if month is not None else _unique_int([row.month for row in rows])
    location_value = location or _unique_text([row.location for row in rows])
    supplier_value = stamping_supplier or _unique_text([row.stamping_supplier for row in rows])
    vehicle_value = vehicle_model or _unique_text([row.vehicle_model for row in rows])
    version_value = version or _unique_text([row.version for row in rows])

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
