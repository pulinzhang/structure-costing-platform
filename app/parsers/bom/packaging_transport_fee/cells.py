"""包装运输费共用单元格：列名、数值转换、组行。"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from app.common.money import Q4, quantize_money

from .types import PackagingTransportFeeParsedRow

# 扁平模板列名
H_PART_NUMBER = "零件号"
H_PART_NAME = "产品"
H_PACKAGING_TYPE = "包装类型"
H_PIECES = "单包装数"
H_LEN = "器具长"
H_WID = "器具宽"
H_HEI = "器具高"
H_OEM = "上线库存数量"
H_TRANSIT = "在途周转数量"
H_COMPANY = "公司库存数量"
H_TOTAL_QTY = "总投入数量"
H_FIX_PRICE = "器具单价"
H_FIX_AMOUNT = "投入总金额"
H_PKG_FEE = "单件包装费"
H_TRIP = "往返运输价格"
H_TRANS_FEE = "单件运输费"
H_MAINT = "器具年损维护费"
H_OTHER = "其它费用"
H_TOTAL = "包装运输费合计"
H_REMARK = "备注"

# 生产样例固定列（1-based），表头在含「料号」的行
PROD_COL = {
    "part_number": 2,
    "part_name": 3,
    "packaging_type": 4,
    "pieces_per_pack": 5,
    "fixture_length_mm": 6,
    "fixture_width_mm": 7,
    "fixture_height_mm": 8,
    "oem_stock_qty": 9,
    "transit_qty": 10,
    "company_stock_qty": 11,
    "total_fixture_qty": 12,
    "fixture_unit_price": 13,
    "fixture_invest_amount": 14,
    "unit_packaging_fee": 15,
    "round_trip_transport_price": 16,
    "unit_transport_fee": 17,
    "fixture_maint_fee": 18,
    "other_fee": 26,
    "packaging_transport_total": 27,
}


def cell_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def normalize_header(text: str) -> str:
    return text.replace("\n", "").replace(" ", "").replace("（", "(").replace("）", ")").strip()


def parse_money(value: object, *, allow_empty: bool = False) -> Decimal | None:
    if value is None or value == "":
        return Decimal("0") if allow_empty else None
    try:
        if isinstance(value, Decimal):
            number = value
        elif isinstance(value, int | float):
            number = Decimal(str(value))
        else:
            text = str(value).strip().replace(",", "")
            if not text:
                return Decimal("0") if allow_empty else None
            number = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    if number < 0:
        return None
    return quantize_money(number, Q4)


def parse_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(round(value))
        text = str(value).strip().replace(",", "")
        if not text:
            return None
        return int(Decimal(text))
    except (InvalidOperation, ValueError):
        return None


def is_skip_row(part_number: str, part_name: str) -> bool:
    if not part_number and not part_name:
        return True
    if part_number.startswith("【"):
        return True
    if "计算公式" in part_number or "计算公式" in part_name:
        return True
    return part_number in ("序号", "料号", "零件号")


def build_row(
    *,
    row_number: int,
    part_number: str,
    part_name: str | None,
    packaging_type: str | None,
    pieces_per_pack: int | None,
    fixture_length_mm: int | None,
    fixture_width_mm: int | None,
    fixture_height_mm: int | None,
    oem_stock_qty: int | None,
    transit_qty: int | None,
    company_stock_qty: int | None,
    total_fixture_qty: int | None,
    fixture_unit_price: Decimal | None,
    fixture_invest_amount: Decimal | None,
    unit_packaging_fee: Decimal,
    round_trip_transport_price: Decimal | None,
    unit_transport_fee: Decimal,
    fixture_maint_fee: Decimal,
    other_fee: Decimal,
    packaging_transport_total: Decimal,
    remark: str | None,
) -> PackagingTransportFeeParsedRow:
    return PackagingTransportFeeParsedRow(
        row_number=row_number,
        part_number=part_number[:50],
        part_name=(part_name[:200] if part_name else None),
        packaging_type=(packaging_type[:50] if packaging_type else None),
        pieces_per_pack=pieces_per_pack,
        fixture_length_mm=fixture_length_mm,
        fixture_width_mm=fixture_width_mm,
        fixture_height_mm=fixture_height_mm,
        oem_stock_qty=oem_stock_qty,
        transit_qty=transit_qty,
        company_stock_qty=company_stock_qty,
        total_fixture_qty=total_fixture_qty,
        fixture_unit_price=fixture_unit_price,
        fixture_invest_amount=fixture_invest_amount,
        unit_packaging_fee=unit_packaging_fee,
        round_trip_transport_price=round_trip_transport_price,
        unit_transport_fee=unit_transport_fee,
        fixture_maint_fee=fixture_maint_fee,
        other_fee=other_fee,
        packaging_transport_total=packaging_transport_total,
        remark=remark or None,
    )
