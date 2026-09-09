"""协议 Excel 单元格取值与文件名（不访问 DB、不渲染）。"""

from __future__ import annotations

import calendar
import re

from app.common.money import Q0, Q2, quantize_money
from app.services.costing.procurement_contract_report.assemble import (
    VIEW_ASSEMBLY,
    VIEW_PROCUREMENT,
    ReportBundle,
)
from app.services.costing.procurement_contract_report.export.columns import (
    MISSING_VALUE,
    QTY_UNIT,
    SINGLE_MONTH_PRICE_HEADER,
)
from app.services.costing.procurement_contract_report.window import month_header


def excel_int(value: object) -> int | str:
    if value is None:
        return MISSING_VALUE
    return int(quantize_money(value, Q0, allow_negative=True))


def excel_price(value: object) -> float | str:
    """与列表展示同一套四舍五入到分；Excel 用 0.00 显示。"""
    if value is None:
        return MISSING_VALUE
    return float(quantize_money(value, Q2, allow_negative=True))


def settlement_header(year: int, month: int, month_count: int) -> str:
    if month_count == 1:
        return SINGLE_MONTH_PRICE_HEADER
    return month_header(year, month)


def last_column(month_count: int) -> int:
    return 6 + month_count + 5


def party_b_name(bundle: ReportBundle) -> str:
    if bundle.scope.view != VIEW_PROCUREMENT:
        return ""
    if bundle.supplier_name:
        return bundle.supplier_name
    if len(bundle.supplier_names) == 1:
        return bundle.supplier_names[0]
    return ""


def _company_name(company_name: str | None) -> str:
    return (company_name or "").strip()


def party_a_label(company_name: str) -> str:
    return f"甲    方：{_company_name(company_name)}"


def party_b_label(bundle: ReportBundle) -> str:
    return f"乙   方：{party_b_name(bundle)}"


def party_a_date_label() -> str:
    return "日    期："


def party_b_date_label() -> str:
    return "日   期："


def qty_unit() -> str:
    return QTY_UNIT


def _fill_placeholders(template: str, values: dict[str, str]) -> str:
    filled = template
    for key, value in values.items():
        filled = filled.replace("{" + key + "}", value)
    return filled


def agreement_remarks(
    bundle: ReportBundle,
    company_name: str | None = None,
    remarks_template: str | None = None,
) -> tuple[str, ...]:
    start_year, start_month = bundle.months[0]
    end_year, end_month = bundle.months[-1]
    end_day = calendar.monthrange(end_year, end_month)[1]
    template = (remarks_template or "").strip()
    if not template:
        return ()
    filled = _fill_placeholders(
        template,
        {
            "company_name": _company_name(company_name),
            "start_year": str(start_year),
            "start_month": str(start_month),
            "end_year": str(end_year),
            "end_month": str(end_month),
            "end_day": str(end_day),
        },
    )
    parts = [part.strip() for part in re.split(r"\n\s*\n", filled) if part.strip()]
    return tuple(parts) if parts else (filled,)


def build_filename(bundle: ReportBundle) -> str:
    scope = bundle.scope
    flags: list[str] = []
    if not scope.qa_passed:
        flags.append("检测未通过")
    start = bundle.months[0]
    end = bundle.months[-1]
    window = f"{start[0]}{start[1]:02d}-{end[0]}{end[1]:02d}"
    if scope.view == VIEW_ASSEMBLY:
        pack = "总成"
    else:
        pack = bundle.supplier_name or (
            "多家"
            if len(bundle.supplier_names) > 1
            else (bundle.supplier_names[0] if bundle.supplier_names else "未指定")
        )
    prefix = "_".join(flags)
    stem = f"批量零部件价格协议_{scope.location}_{scope.vehicle_model}_{pack}_{window}"
    if prefix:
        return f"{prefix}_{stem}.xlsx"
    return f"{stem}.xlsx"


def agreement_title(bundle: ReportBundle, base_title: str) -> str:
    project_no = (bundle.scope.vehicle_model or "").strip()
    title = f"{project_no}{base_title}" if project_no else base_title
    if not bundle.scope.qa_passed:
        title = f"{title}（检测未通过）"
    return title
