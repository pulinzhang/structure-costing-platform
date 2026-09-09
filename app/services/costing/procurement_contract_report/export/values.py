"""协议 Excel 单元格取值与文件名（不访问 DB、不渲染）。"""

from __future__ import annotations

import calendar

from app.common.money import Q0, Q2, quantize_money
from app.services.costing.procurement_contract_report.assemble import ReportBundle
from app.services.costing.procurement_contract_report.export.columns import (
    MISSING_VALUE,
    QTY_UNIT,
    REMARK_1_TEMPLATE,
    REMARK_5_TEMPLATE,
    REMARKS_HEAD,
    REMARKS_TAIL,
    SINGLE_MONTH_PRICE_HEADER,
)
from app.services.costing.procurement_contract_report.window import month_header
from app.services.settings.system.settings_service import DEFAULT_COMPANY_NAME


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
    if bundle.supplier_name:
        return bundle.supplier_name
    if len(bundle.supplier_names) == 1:
        return bundle.supplier_names[0]
    return ""


def _company_name(company_name: str | None) -> str:
    return (company_name or "").strip() or DEFAULT_COMPANY_NAME


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


def agreement_remarks(bundle: ReportBundle, company_name: str | None = None) -> tuple[str, ...]:
    start_year, start_month = bundle.months[0]
    end_year, end_month = bundle.months[-1]
    end_day = calendar.monthrange(end_year, end_month)[1]
    remark_1 = REMARK_1_TEMPLATE.format(company_name=_company_name(company_name))
    remark_5 = REMARK_5_TEMPLATE.format(
        start_year=start_year,
        start_month=start_month,
        end_year=end_year,
        end_month=end_month,
        end_day=end_day,
    )
    return (remark_1, *REMARKS_HEAD, remark_5, *REMARKS_TAIL)


def build_filename(bundle: ReportBundle) -> str:
    header = bundle.header
    flags: list[str] = []
    if not header.qa_passed:
        flags.append("检测未通过")
    start = bundle.months[0]
    end = bundle.months[-1]
    window = f"{start[0]}{start[1]:02d}-{end[0]}{end[1]:02d}"
    supplier = bundle.supplier_name or (
        "多家"
        if len(bundle.supplier_names) > 1
        else (bundle.supplier_names[0] if bundle.supplier_names else "未指定")
    )
    prefix = "_".join(flags)
    stem = f"批量零部件价格协议_{header.location}_{header.vehicle_model}_{supplier}_{window}"
    if prefix:
        return f"{prefix}_{stem}.xlsx"
    return f"{stem}.xlsx"


def agreement_title(bundle: ReportBundle, base_title: str) -> str:
    title = base_title
    if not bundle.header.qa_passed:
        title = f"{title}（检测未通过）"
    return title
