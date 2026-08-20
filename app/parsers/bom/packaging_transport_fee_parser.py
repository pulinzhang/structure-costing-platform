"""
BOM 包装运输费 Excel 解析器（纯函数，无副作用）

支持两种版式：
1) 生产样例：双行表头（料号 / 包装类型 / … / 包装运输费合计），基地/年/项目由表单传入
2) 平台扁平模板：单行表头（零件号、单件包装费、…）
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any

from openpyxl import load_workbook

from app.common.money import Q4, quantize_money

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


@dataclass(frozen=True)
class PackagingTransportFeeParsedRow:
    """解析后的一行"""

    row_number: int
    part_number: str
    part_name: str | None
    packaging_type: str | None
    pieces_per_pack: int | None
    fixture_length_mm: int | None
    fixture_width_mm: int | None
    fixture_height_mm: int | None
    oem_stock_qty: int | None
    transit_qty: int | None
    company_stock_qty: int | None
    total_fixture_qty: int | None
    fixture_unit_price: Decimal | None
    fixture_invest_amount: Decimal | None
    unit_packaging_fee: Decimal
    round_trip_transport_price: Decimal | None
    unit_transport_fee: Decimal
    fixture_maint_fee: Decimal
    other_fee: Decimal
    packaging_transport_total: Decimal
    remark: str | None


@dataclass(frozen=True)
class PackagingTransportFeeParseResult:
    rows: list[PackagingTransportFeeParsedRow]
    errors: list[str]
    sheet_name: str | None = None


def _cell_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _normalize_header(text: str) -> str:
    return (
        text.replace("\n", "")
        .replace(" ", "")
        .replace("（", "(")
        .replace("）", ")")
        .strip()
    )


def _parse_money(value: Any, *, allow_empty: bool = False) -> Decimal | None:
    if value is None or value == "":
        return Decimal("0") if allow_empty else None
    try:
        if isinstance(value, Decimal):
            number = value
        elif isinstance(value, (int, float)):
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


def _parse_int(value: Any) -> int | None:
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


def _is_skip_row(part_number: str, part_name: str) -> bool:
    if not part_number and not part_name:
        return True
    if part_number.startswith("【"):
        return True
    if "计算公式" in part_number or "计算公式" in part_name:
        return True
    if part_number in ("序号", "料号", "零件号"):
        return True
    return False


def _looks_like_production_header(sheet: Any, row_idx: int) -> bool:
    texts = [
        _normalize_header(_cell_text(sheet.cell(row_idx, c).value))
        for c in range(1, min(28, (sheet.max_column or 1) + 1))
    ]
    joined = "|".join(texts)
    has_part = any(t in ("料号", "零件号") for t in texts)
    has_pack = any("包装类型" in t for t in texts)
    has_total = any("包装运输费合计" in t for t in texts) or any(
        "包装运输费" in t for t in texts
    )
    # 生产样例：料号 + 包装类型，合计可能在同行或下一行合并区
    if has_part and has_pack:
        return True
    return has_part and has_total and "单价" not in joined


def _find_flat_header(sheet: Any) -> tuple[int, dict[str, int]] | None:
    aliases: dict[str, set[str]] = {
        H_PART_NUMBER: {"零件号", "料号", "part_number"},
        H_PART_NAME: {"产品", "零件名称", "产品名称", "part_name"},
        H_PACKAGING_TYPE: {"包装类型", "packaging_type"},
        H_PIECES: {"单包装数", "单包装数(件)", "单包装数（件）", "pieces_per_pack"},
        H_LEN: {"器具长", "长(mm)", "长（mm）", "fixture_length_mm"},
        H_WID: {"器具宽", "宽(mm)", "宽（mm）", "fixture_width_mm"},
        H_HEI: {"器具高", "高(mm)", "高（mm）", "fixture_height_mm"},
        H_OEM: {"上线库存数量", "上线及主机厂库存", "oem_stock_qty"},
        H_TRANSIT: {"在途周转数量", "在途及返还周转", "transit_qty"},
        H_COMPANY: {"公司库存数量", "普威公司库存周转", "company_stock_qty"},
        H_TOTAL_QTY: {"总投入数量", "total_fixture_qty"},
        H_FIX_PRICE: {"器具单价", "fixture_unit_price"},
        H_FIX_AMOUNT: {"投入总金额", "fixture_invest_amount"},
        H_PKG_FEE: {"单件包装费", "unit_packaging_fee"},
        H_TRIP: {"往返运输价格", "9.6米双飞翼运输价格(往返)", "round_trip_transport_price"},
        H_TRANS_FEE: {"单件运输费", "unit_transport_fee"},
        H_MAINT: {"器具年损维护费", "器具年损、维护费", "fixture_maint_fee"},
        H_OTHER: {"其它费用", "其它费用合计", "other_fee"},
        H_TOTAL: {"包装运输费合计", "packaging_transport_total"},
        H_REMARK: {"备注", "remark"},
    }
    max_scan = min(sheet.max_row or 1, 15)
    max_col = min(sheet.max_column or 1, 40)

    for row_idx in range(1, max_scan + 1):
        mapping: dict[str, int] = {}
        for col_idx in range(1, max_col + 1):
            raw = _cell_text(sheet.cell(row_idx, col_idx).value)
            if not raw:
                continue
            normalized = _normalize_header(raw)
            for field, names in aliases.items():
                norm_names = {_normalize_header(n) for n in names}
                if (raw in names or normalized in norm_names) and field not in mapping:
                    mapping[field] = col_idx
        if (
            H_PART_NUMBER in mapping
            and H_PKG_FEE in mapping
            and H_TRANS_FEE in mapping
            and H_TOTAL in mapping
        ):
            # 生产双行头也会命中「料号」，但通常没有同行「单件包装费」文字
            # 若同行同时有「包装类型」且无「单件包装费」列名，走生产固定列
            return row_idx, mapping
    return None


def _build_row(
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


def _parse_production_sheet(sheet: Any, header_row: int) -> PackagingTransportFeeParseResult:
    rows: list[PackagingTransportFeeParsedRow] = []
    errors: list[str] = []
    seen: set[str] = set()
    data_start = header_row + 1
    # 若下一行是子表头（长/宽/高），再跳一行
    next_texts = [
        _normalize_header(_cell_text(sheet.cell(header_row + 1, c).value))
        for c in range(6, 15)
    ]
    if any(t.startswith("长") or t == "器具单价" or "总投入" in t for t in next_texts):
        data_start = header_row + 2

    for row_idx in range(data_start, (sheet.max_row or data_start) + 1):
        part_number = _cell_text(sheet.cell(row_idx, PROD_COL["part_number"]).value)
        part_name = _cell_text(sheet.cell(row_idx, PROD_COL["part_name"]).value)
        if _is_skip_row(part_number, part_name):
            continue
        if not part_number:
            errors.append(f"第 {row_idx} 行：料号为空")
            continue
        if not (part_number[0].isdigit() or part_number[0].isalpha()):
            continue
        if part_number in seen:
            errors.append(f"第 {row_idx} 行：料号「{part_number}」重复")
            continue

        pkg_fee = _parse_money(sheet.cell(row_idx, PROD_COL["unit_packaging_fee"]).value)
        trans_fee = _parse_money(sheet.cell(row_idx, PROD_COL["unit_transport_fee"]).value)
        maint_fee = _parse_money(
            sheet.cell(row_idx, PROD_COL["fixture_maint_fee"]).value,
            allow_empty=True,
        )
        other_fee = _parse_money(
            sheet.cell(row_idx, PROD_COL["other_fee"]).value,
            allow_empty=True,
        )
        total = _parse_money(
            sheet.cell(row_idx, PROD_COL["packaging_transport_total"]).value
        )
        if pkg_fee is None:
            errors.append(f"第 {row_idx} 行：单件包装费无效")
            continue
        if trans_fee is None:
            errors.append(f"第 {row_idx} 行：单件运输费无效")
            continue
        if total is None:
            errors.append(f"第 {row_idx} 行：包装运输费合计无效")
            continue

        seen.add(part_number)
        rows.append(
            _build_row(
                row_number=row_idx,
                part_number=part_number,
                part_name=part_name or None,
                packaging_type=_cell_text(
                    sheet.cell(row_idx, PROD_COL["packaging_type"]).value
                )
                or None,
                pieces_per_pack=_parse_int(
                    sheet.cell(row_idx, PROD_COL["pieces_per_pack"]).value
                ),
                fixture_length_mm=_parse_int(
                    sheet.cell(row_idx, PROD_COL["fixture_length_mm"]).value
                ),
                fixture_width_mm=_parse_int(
                    sheet.cell(row_idx, PROD_COL["fixture_width_mm"]).value
                ),
                fixture_height_mm=_parse_int(
                    sheet.cell(row_idx, PROD_COL["fixture_height_mm"]).value
                ),
                oem_stock_qty=_parse_int(
                    sheet.cell(row_idx, PROD_COL["oem_stock_qty"]).value
                ),
                transit_qty=_parse_int(sheet.cell(row_idx, PROD_COL["transit_qty"]).value),
                company_stock_qty=_parse_int(
                    sheet.cell(row_idx, PROD_COL["company_stock_qty"]).value
                ),
                total_fixture_qty=_parse_int(
                    sheet.cell(row_idx, PROD_COL["total_fixture_qty"]).value
                ),
                fixture_unit_price=_parse_money(
                    sheet.cell(row_idx, PROD_COL["fixture_unit_price"]).value,
                    allow_empty=True,
                ),
                fixture_invest_amount=_parse_money(
                    sheet.cell(row_idx, PROD_COL["fixture_invest_amount"]).value,
                    allow_empty=True,
                ),
                unit_packaging_fee=pkg_fee,
                round_trip_transport_price=_parse_money(
                    sheet.cell(row_idx, PROD_COL["round_trip_transport_price"]).value,
                    allow_empty=True,
                ),
                unit_transport_fee=trans_fee,
                fixture_maint_fee=maint_fee or Decimal("0"),
                other_fee=other_fee or Decimal("0"),
                packaging_transport_total=total,
                remark=None,
            )
        )

    if not rows and not errors:
        errors.append("未解析到有效数据行")
    return PackagingTransportFeeParseResult(
        rows=rows,
        errors=errors,
        sheet_name=getattr(sheet, "title", None),
    )


def _parse_flat_sheet(
    sheet: Any, header_row: int, columns: dict[str, int]
) -> PackagingTransportFeeParseResult:
    rows: list[PackagingTransportFeeParsedRow] = []
    errors: list[str] = []
    seen: set[str] = set()

    def col(name: str) -> int | None:
        return columns.get(name)

    for row_idx in range(header_row + 1, (sheet.max_row or header_row) + 1):
        part_number = _cell_text(sheet.cell(row_idx, columns[H_PART_NUMBER]).value)
        part_name_col = col(H_PART_NAME)
        part_name = (
            _cell_text(sheet.cell(row_idx, part_name_col).value) if part_name_col else ""
        )
        if _is_skip_row(part_number, part_name):
            continue
        if not part_number:
            errors.append(f"第 {row_idx} 行：零件号为空")
            continue
        if part_number in seen:
            errors.append(f"第 {row_idx} 行：零件号「{part_number}」重复")
            continue

        pkg_fee = _parse_money(sheet.cell(row_idx, columns[H_PKG_FEE]).value)
        trans_fee = _parse_money(sheet.cell(row_idx, columns[H_TRANS_FEE]).value)
        maint_col = col(H_MAINT)
        other_col = col(H_OTHER)
        total = _parse_money(sheet.cell(row_idx, columns[H_TOTAL]).value)
        maint_fee = (
            _parse_money(sheet.cell(row_idx, maint_col).value, allow_empty=True)
            if maint_col
            else Decimal("0")
        )
        other_fee = (
            _parse_money(sheet.cell(row_idx, other_col).value, allow_empty=True)
            if other_col
            else Decimal("0")
        )
        if pkg_fee is None:
            errors.append(f"第 {row_idx} 行：单件包装费无效")
            continue
        if trans_fee is None:
            errors.append(f"第 {row_idx} 行：单件运输费无效")
            continue
        if total is None:
            errors.append(f"第 {row_idx} 行：包装运输费合计无效")
            continue

        def opt_int(header: str) -> int | None:
            c = col(header)
            return _parse_int(sheet.cell(row_idx, c).value) if c else None

        def opt_money(header: str) -> Decimal | None:
            c = col(header)
            return (
                _parse_money(sheet.cell(row_idx, c).value, allow_empty=True)
                if c
                else None
            )

        remark_col = col(H_REMARK)
        packaging_col = col(H_PACKAGING_TYPE)
        seen.add(part_number)
        rows.append(
            _build_row(
                row_number=row_idx,
                part_number=part_number,
                part_name=part_name or None,
                packaging_type=(
                    _cell_text(sheet.cell(row_idx, packaging_col).value) or None
                    if packaging_col
                    else None
                ),
                pieces_per_pack=opt_int(H_PIECES),
                fixture_length_mm=opt_int(H_LEN),
                fixture_width_mm=opt_int(H_WID),
                fixture_height_mm=opt_int(H_HEI),
                oem_stock_qty=opt_int(H_OEM),
                transit_qty=opt_int(H_TRANSIT),
                company_stock_qty=opt_int(H_COMPANY),
                total_fixture_qty=opt_int(H_TOTAL_QTY),
                fixture_unit_price=opt_money(H_FIX_PRICE),
                fixture_invest_amount=opt_money(H_FIX_AMOUNT),
                unit_packaging_fee=pkg_fee,
                round_trip_transport_price=opt_money(H_TRIP),
                unit_transport_fee=trans_fee,
                fixture_maint_fee=maint_fee or Decimal("0"),
                other_fee=other_fee or Decimal("0"),
                packaging_transport_total=total,
                remark=(
                    _cell_text(sheet.cell(row_idx, remark_col).value) or None
                    if remark_col
                    else None
                ),
            )
        )

    if not rows and not errors:
        errors.append("未解析到有效数据行")
    return PackagingTransportFeeParseResult(
        rows=rows,
        errors=errors,
        sheet_name=getattr(sheet, "title", None),
    )


def parse_packaging_transport_fee_excel(
    file_content: bytes,
) -> PackagingTransportFeeParseResult:
    """解析包装运输费 Excel（.xlsx）。"""
    if not file_content:
        return PackagingTransportFeeParseResult(rows=[], errors=["文件内容为空"])

    try:
        workbook = load_workbook(BytesIO(file_content), data_only=True, read_only=True)
    except Exception as exc:
        return PackagingTransportFeeParseResult(
            rows=[], errors=[f"无法读取 Excel：{exc}"]
        )

    try:
        if not workbook.worksheets:
            return PackagingTransportFeeParseResult(
                rows=[], errors=["Excel 中没有工作表"]
            )
        sheet = workbook.worksheets[0]

        # 优先识别生产双行表头
        max_scan = min(sheet.max_row or 1, 10)
        for row_idx in range(1, max_scan + 1):
            if _looks_like_production_header(sheet, row_idx):
                # 若同行已有「单件包装费」文字且列映射完整，走扁平
                flat = _find_flat_header(sheet)
                if (
                    flat
                    and flat[0] == row_idx
                    and H_PKG_FEE in flat[1]
                    and flat[1][H_PKG_FEE] != PROD_COL["unit_packaging_fee"]
                ):
                    return _parse_flat_sheet(sheet, flat[0], flat[1])
                # 生产样例：料号在 B，包装费在 O（15）
                cell_o = _normalize_header(
                    _cell_text(sheet.cell(row_idx, PROD_COL["unit_packaging_fee"]).value)
                )
                if "单件包装费" in cell_o or cell_o == "":
                    return _parse_production_sheet(sheet, row_idx)

        flat = _find_flat_header(sheet)
        if flat:
            return _parse_flat_sheet(sheet, flat[0], flat[1])

        return PackagingTransportFeeParseResult(
            rows=[],
            errors=[
                "未找到表头。请使用生产样例（含「料号」「包装类型」）"
                "或平台模板（含「零件号」「单件包装费」「包装运输费合计」）"
            ],
        )
    finally:
        workbook.close()
