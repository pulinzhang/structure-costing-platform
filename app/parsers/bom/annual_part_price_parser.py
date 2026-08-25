"""
BOM 年度零件价 Excel 解析器（纯函数，无副作用）

约定列：零件号 | 零件名称 | 单位 | 单价 | 原供货类型 | 供应商 | 备注
基地 / 年度由上传表单传入，不从 Excel 读取。
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any

from openpyxl import load_workbook

from app.common.money import Q4, quantize_money

HEADER_PART_NUMBER = "零件号"
HEADER_PART_NAME = "零件名称"
HEADER_UNIT = "单位"
HEADER_UNIT_PRICE = "单价"
HEADER_SUPPLY_TYPE = "原供货类型"
HEADER_SUPPLIER = "供应商"
HEADER_REMARK = "备注"


@dataclass(frozen=True)
class AnnualPartPriceParsedRow:
    """解析后的一行年度零件价"""

    row_number: int
    part_number: str
    part_name: str | None
    unit: str
    unit_price: Decimal
    supply_type: str
    supplier_name: str | None
    remark: str | None


@dataclass(frozen=True)
class AnnualPartPriceParseResult:
    """解析结果"""

    rows: list[AnnualPartPriceParsedRow]
    errors: list[str]


def _cell_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _round4(value: Decimal) -> Decimal:
    return quantize_money(value, Q4)


def _parse_unit_price(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, Decimal):
            number = value
        elif isinstance(value, int | float):
            number = Decimal(str(value))
        else:
            text = str(value).strip().replace(",", "")
            if not text:
                return None
            number = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    if number < 0:
        return None
    return _round4(number)


def _find_header_row(sheet: Any) -> tuple[int, dict[str, int]] | None:
    """定位表头行，返回 (行号, 列名→列号)。"""
    aliases = {
        HEADER_PART_NUMBER: {HEADER_PART_NUMBER, "零件号", "料号", "part_number"},
        HEADER_PART_NAME: {HEADER_PART_NAME, "零件名称", "名称", "part_name"},
        HEADER_UNIT: {HEADER_UNIT, "单位", "unit"},
        HEADER_UNIT_PRICE: {
            HEADER_UNIT_PRICE,
            "单价",
            "价格",
            "单位价格",
            "unit_price",
        },
        HEADER_SUPPLY_TYPE: {
            HEADER_SUPPLY_TYPE,
            "供货类型",
            "原供货类型",
            "supply_type",
        },
        HEADER_SUPPLIER: {HEADER_SUPPLIER, "供应商", "供方", "supplier_name"},
        HEADER_REMARK: {HEADER_REMARK, "备注", "说明", "remark"},
    }
    max_scan = min(sheet.max_row or 1, 20)
    max_col = min(sheet.max_column or 1, 20)

    for row_idx in range(1, max_scan + 1):
        mapping: dict[str, int] = {}
        for col_idx in range(1, max_col + 1):
            text = _cell_text(sheet.cell(row_idx, col_idx).value)
            if not text:
                continue
            for field, names in aliases.items():
                if text in names and field not in mapping:
                    mapping[field] = col_idx
        if (
            HEADER_PART_NUMBER in mapping
            and HEADER_UNIT_PRICE in mapping
            and HEADER_SUPPLY_TYPE in mapping
        ):
            return row_idx, mapping
    return None


def parse_annual_part_price_excel(file_content: bytes) -> AnnualPartPriceParseResult:
    """
    解析年度零件价 Excel。
    仅支持 .xlsx（由调用方校验扩展名）。
    """
    if not file_content:
        return AnnualPartPriceParseResult(rows=[], errors=["文件内容为空"])

    try:
        workbook = load_workbook(BytesIO(file_content), data_only=True, read_only=True)
    except Exception as exc:
        return AnnualPartPriceParseResult(rows=[], errors=[f"无法读取 Excel：{exc}"])

    try:
        if not workbook.worksheets:
            return AnnualPartPriceParseResult(rows=[], errors=["Excel 中没有工作表"])
        sheet = workbook.worksheets[0]

        header = _find_header_row(sheet)
        if not header:
            return AnnualPartPriceParseResult(
                rows=[],
                errors=[
                    "未找到表头，请使用列："
                    f"{HEADER_PART_NUMBER} / {HEADER_PART_NAME} / {HEADER_UNIT} / "
                    f"{HEADER_UNIT_PRICE} / {HEADER_SUPPLY_TYPE} / "
                    f"{HEADER_SUPPLIER} / {HEADER_REMARK}"
                ],
            )

        header_row, columns = header
        part_number_col = columns[HEADER_PART_NUMBER]
        part_name_col = columns.get(HEADER_PART_NAME)
        unit_col = columns.get(HEADER_UNIT)
        price_col = columns[HEADER_UNIT_PRICE]
        supply_type_col = columns[HEADER_SUPPLY_TYPE]
        supplier_col = columns.get(HEADER_SUPPLIER)
        remark_col = columns.get(HEADER_REMARK)

        rows: list[AnnualPartPriceParsedRow] = []
        errors: list[str] = []
        seen_parts: set[str] = set()

        for row_idx in range(header_row + 1, (sheet.max_row or header_row) + 1):
            part_number = _cell_text(sheet.cell(row_idx, part_number_col).value)
            part_name = (
                _cell_text(sheet.cell(row_idx, part_name_col).value) if part_name_col else ""
            )
            unit_raw = _cell_text(sheet.cell(row_idx, unit_col).value) if unit_col else ""
            price_raw = sheet.cell(row_idx, price_col).value
            supply_type = _cell_text(sheet.cell(row_idx, supply_type_col).value)
            supplier_raw = (
                _cell_text(sheet.cell(row_idx, supplier_col).value) if supplier_col else ""
            )
            remark_raw = _cell_text(sheet.cell(row_idx, remark_col).value) if remark_col else ""

            if not part_number and (price_raw is None or price_raw == ""):
                continue

            if not part_number:
                errors.append(f"第 {row_idx} 行：零件号为空")
                continue

            if not supply_type:
                errors.append(f"第 {row_idx} 行：原供货类型为空")
                continue

            if len(supply_type) > 50:
                errors.append(f"第 {row_idx} 行：原供货类型超过 50 字符")
                continue

            unit_price = _parse_unit_price(price_raw)
            if unit_price is None:
                errors.append(f"第 {row_idx} 行：单价无效（{price_raw!r}）")
                continue

            if part_number in seen_parts:
                errors.append(f"第 {row_idx} 行：零件号「{part_number}」重复")
                continue
            seen_parts.add(part_number)

            unit = unit_raw or "pcs"
            if unit.upper() == "PCS":
                unit = "pcs"

            rows.append(
                AnnualPartPriceParsedRow(
                    row_number=row_idx,
                    part_number=part_number[:50],
                    part_name=(part_name[:200] if part_name else None),
                    unit=unit[:20],
                    unit_price=unit_price,
                    supply_type=supply_type[:50],
                    supplier_name=(supplier_raw[:100] if supplier_raw else None),
                    remark=remark_raw or None,
                )
            )
    finally:
        workbook.close()

    if not rows and not errors:
        errors.append("未解析到有效数据行")

    return AnnualPartPriceParseResult(rows=rows, errors=errors)
