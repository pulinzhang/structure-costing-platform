"""焊接费导出 — 单元格取值、筛选摘要、文件名。"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.common.audit import audit_status_label
from app.common.bom.manufacturing_category import (
    short_part_number_digits,
    short_weld_part_number,
)
from app.common.money import Q4, excel_money_cell, format_money, quantize_money
from app.common.timezone import now
from app.models.bom import BomWeldingFee
from app.schemas.dto.bom_welding_fee_dto import resolve_welding_fee_levels
from app.services.bom.welding_fee.export.columns import DATA_H

_MATCH_LABEL = {
    "matched": "已匹配",
    "missing_price": "缺单价",
    "unmapped": "未映射",
}
_CALC_LABEL = {
    "ok": "正常",
    "partial": "缺单价",
    "failed": "失败",
}


def money_cell(value: object) -> Decimal | str:
    return excel_money_cell(value, Q4)


def level_label(level: int | None) -> str:
    if level is None:
        return ""
    return f"L{int(level)}"


def part_short_code(*, part_number: str | None, level: int | None) -> str:
    """L0 末四位；分总成带 -N 时保留字母尾（同拆解列表）。"""
    if int(level or 0) == 0:
        return short_part_number_digits(part_number) or ""
    return short_weld_part_number(part_number) or ""


def sum_money_field(records: list[BomWeldingFee], field_name: str) -> Decimal:
    total = Decimal("0")
    for record in records:
        value = getattr(record, field_name, None)
        if value is None or value == "":
            continue
        total += quantize_money(value, Q4, allow_negative=True)
    return total.quantize(Q4)


def sum_line_fee(records: list[BomWeldingFee]) -> Decimal:
    total = Decimal("0")
    for record in records:
        for item in record.items or []:
            value = getattr(item, "line_fee", None)
            if value is None or value == "":
                continue
            total += quantize_money(value, Q4, allow_negative=True)
    return total.quantize(Q4)


def _count_label(records: list[BomWeldingFee]) -> str:
    ok_count = sum(1 for record in records if record.calc_status == "ok")
    system_fee = format_money(sum_money_field(records, "total_welding_fee"), Q4, 4)
    other_fee = format_money(sum_money_field(records, "other_fee"), Q4, 4)
    final_fee = format_money(sum_money_field(records, "final_welding_fee"), Q4, 4)
    line_fee = format_money(sum_line_fee(records), Q4, 4)
    return (
        f"共 {len(records)} 条（核算正常 {ok_count}） · "
        f"本表合计　系统计算 {system_fee}　其它费用 {other_fee}　"
        f"确认单价 {final_fee}　行费 {line_fee}"
    )


def filter_text(
    *,
    year: int | None,
    location: str | None,
    vehicle_model: str | None,
    bom_version: str | None,
    part_number: str | None,
    audit_status: str | None,
    calc_status: str | None,
    level: int | None = None,
    levels: list[int] | None = None,
    ids: list[int] | None = None,
) -> str:
    parts: list[str] = []
    if year is not None:
        parts.append(f"年度={year}")
    if location:
        parts.append(f"基地={location}")
    if vehicle_model:
        parts.append(f"项目={vehicle_model}")
    if bom_version:
        parts.append(f"版本={bom_version}")
    resolved = resolve_welding_fee_levels(level=level, levels=levels)
    if resolved:
        parts.append("层级=" + "+".join(level_label(item) for item in resolved))
    if ids is not None:
        parts.append(f"核价卡焊费 {len(ids)} 条")
    if part_number:
        parts.append(f"零件号含={part_number}")
    if audit_status:
        parts.append(f"审核={audit_status_label(audit_status)}")
    if calc_status:
        parts.append(f"计算={_CALC_LABEL.get(calc_status, calc_status)}")
    return " · ".join(parts) if parts else "全部筛选"


def build_filename(
    *,
    year: int | None,
    location: str | None,
    vehicle_model: str | None,
    bom_version: str | None,
) -> str:
    scope_parts = [
        str(year) if year else None,
        location,
        vehicle_model,
        bom_version,
    ]
    scope = "_".join(part for part in scope_parts if part) or "全部"
    stamp = now().strftime("%Y%m%d_%H%M%S")
    return f"焊接费_{scope}_{stamp}.xlsx"


def row_height(record: BomWeldingFee) -> float:
    weld = (record.weld_info_raw or "").strip()
    extra = 0.0
    if len(weld) > 40:
        extra = min(36.0, (len(weld) // 40) * 8.0)
    return DATA_H + extra


def main_pairs(record: BomWeldingFee, *, seq_no: int) -> list[tuple[str, object]]:
    calc_status = record.calc_status or ""
    return [
        ("序号", seq_no),
        ("年度", record.year),
        ("基地", record.location),
        ("项目", record.vehicle_model),
        ("版本", record.bom_version),
        ("层级", level_label(record.level)),
        ("零件号", record.part_number),
        (
            "短代码",
            part_short_code(part_number=record.part_number, level=record.level),
        ),
        ("零件名称", record.part_name or ""),
        ("焊接信息原文", (record.weld_info_raw or "").strip()),
        ("工艺数", record.process_line_count),
        ("命中", record.matched_line_count),
        ("缺单价", record.missing_price_count),
        ("系统计算", money_cell(record.total_welding_fee)),
        ("其它费用", money_cell(record.other_fee)),
        ("确认单价", money_cell(record.final_welding_fee)),
        ("备注", (record.remark or "").strip()),
        ("计算状态", _CALC_LABEL.get(calc_status, calc_status)),
        ("审核状态", audit_status_label(record.audit_status)),
    ]


def detail_values(item: Any) -> list[object]:
    match_status = (item.match_status if item else "") or ""
    return [
        (item.standard_process_name or item.process_token or "") if item else "",
        money_cell(item.process_qty) if item else "",
        (item.process_qty_unit or "") if item else "",
        money_cell(item.unit_price) if item and item.unit_price is not None else "",
        (item.unit or "") if item else "",
        money_cell(item.line_fee) if item and item.line_fee is not None else "",
        _MATCH_LABEL.get(match_status, match_status) if item else "",
    ]


def match_status_of(item: Any) -> str:
    return (item.match_status if item else "") or ""
