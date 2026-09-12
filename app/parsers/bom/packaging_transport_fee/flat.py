"""平台扁平模板：单行表头 + 列名映射。"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from .cells import (
    H_COMPANY,
    H_FIX_AMOUNT,
    H_FIX_PRICE,
    H_HEI,
    H_LEN,
    H_MAINT,
    H_OEM,
    H_OTHER,
    H_PACKAGING_TYPE,
    H_PART_NAME,
    H_PART_NUMBER,
    H_PIECES,
    H_PKG_FEE,
    H_REMARK,
    H_TOTAL,
    H_TOTAL_QTY,
    H_TRANS_FEE,
    H_TRANSIT,
    H_TRIP,
    H_WID,
    build_row,
    cell_text,
    is_skip_row,
    normalize_header,
    parse_int,
    parse_money,
)
from .types import PackagingTransportFeeParsedRow, PackagingTransportFeeParseResult


def find_flat_header(sheet: Any) -> tuple[int, dict[str, int]] | None:
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
            raw = cell_text(sheet.cell(row_idx, col_idx).value)
            if not raw:
                continue
            normalized = normalize_header(raw)
            for field, names in aliases.items():
                norm_names = {normalize_header(n) for n in names}
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


def parse_flat_sheet(
    sheet: Any, header_row: int, columns: dict[str, int]
) -> PackagingTransportFeeParseResult:
    rows: list[PackagingTransportFeeParsedRow] = []
    errors: list[str] = []
    seen: set[str] = set()

    def col(name: str) -> int | None:
        return columns.get(name)

    for row_idx in range(header_row + 1, (sheet.max_row or header_row) + 1):
        part_number = cell_text(sheet.cell(row_idx, columns[H_PART_NUMBER]).value)
        part_name_col = col(H_PART_NAME)
        part_name = cell_text(sheet.cell(row_idx, part_name_col).value) if part_name_col else ""
        if is_skip_row(part_number, part_name):
            continue
        if not part_number:
            errors.append(f"第 {row_idx} 行：零件号为空")
            continue
        if part_number in seen:
            errors.append(f"第 {row_idx} 行：零件号「{part_number}」重复")
            continue

        pkg_fee = parse_money(sheet.cell(row_idx, columns[H_PKG_FEE]).value)
        trans_fee = parse_money(sheet.cell(row_idx, columns[H_TRANS_FEE]).value)
        maint_col = col(H_MAINT)
        other_col = col(H_OTHER)
        total = parse_money(sheet.cell(row_idx, columns[H_TOTAL]).value)
        maint_fee = (
            parse_money(sheet.cell(row_idx, maint_col).value, allow_empty=True)
            if maint_col
            else Decimal("0")
        )
        other_fee = (
            parse_money(sheet.cell(row_idx, other_col).value, allow_empty=True)
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

        def opt_int(header: str, row_idx: int = row_idx) -> int | None:
            c = col(header)
            return parse_int(sheet.cell(row_idx, c).value) if c else None

        def opt_money(header: str, row_idx: int = row_idx) -> Decimal | None:
            c = col(header)
            return parse_money(sheet.cell(row_idx, c).value, allow_empty=True) if c else None

        remark_col = col(H_REMARK)
        packaging_col = col(H_PACKAGING_TYPE)
        seen.add(part_number)
        rows.append(
            build_row(
                row_number=row_idx,
                part_number=part_number,
                part_name=part_name or None,
                packaging_type=(
                    cell_text(sheet.cell(row_idx, packaging_col).value) or None
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
                    cell_text(sheet.cell(row_idx, remark_col).value) or None if remark_col else None
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
