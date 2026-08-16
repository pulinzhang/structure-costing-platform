"""
焊接工费单价 Excel 解析器（纯函数，无副作用）

约定四列：名称 | 单位 | 费用 | 备注
（「费用」列表示单位工费单价）
示例：
  焊点 | 个 | 0.0999 |
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any

from openpyxl import load_workbook

from app.common.money import Q4, quantize_money


HEADER_NAME = "名称"
HEADER_UNIT = "单位"
HEADER_UNIT_PRICE = "费用"
HEADER_REMARK = "备注"


@dataclass(frozen=True)
class WeldingUnitPriceParsedRow:
    """解析后的一行焊接工费单价"""

    row_number: int
    item_name: str
    unit: str
    unit_price: Decimal
    remark: str | None


@dataclass(frozen=True)
class WeldingUnitPriceParseResult:
    """解析结果"""

    rows: list[WeldingUnitPriceParsedRow]
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
        elif isinstance(value, (int, float)):
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
        HEADER_NAME: {HEADER_NAME, "名称", "项目", "费用项目", "操作项目"},
        HEADER_UNIT: {HEADER_UNIT, "单位"},
        HEADER_UNIT_PRICE: {
            HEADER_UNIT_PRICE,
            "费用",
            "单价",
            "工费",
            "工费单价",
            "单位价格",
            "价格",
        },
        HEADER_REMARK: {HEADER_REMARK, "备注", "说明"},
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
        if HEADER_NAME in mapping and HEADER_UNIT_PRICE in mapping:
            return row_idx, mapping
    return None


def parse_welding_unit_price_excel(file_content: bytes) -> WeldingUnitPriceParseResult:
    """
    解析焊接工费单价 Excel。
    仅支持 .xlsx（由调用方校验扩展名）。
    """
    if not file_content:
        return WeldingUnitPriceParseResult(rows=[], errors=["文件内容为空"])

    try:
        workbook = load_workbook(BytesIO(file_content), data_only=True, read_only=True)
    except Exception as exc:
        return WeldingUnitPriceParseResult(rows=[], errors=[f"无法读取 Excel：{exc}"])

    try:
        if not workbook.worksheets:
            return WeldingUnitPriceParseResult(rows=[], errors=["Excel 中没有工作表"])
        sheet = workbook.worksheets[0]

        header = _find_header_row(sheet)
        if not header:
            return WeldingUnitPriceParseResult(
                rows=[],
                errors=[
                    f"未找到表头，请使用四列：{HEADER_NAME} / {HEADER_UNIT} / "
                    f"{HEADER_UNIT_PRICE} / {HEADER_REMARK}"
                ],
            )

        header_row, columns = header
        name_col = columns[HEADER_NAME]
        unit_col = columns.get(HEADER_UNIT)
        price_col = columns[HEADER_UNIT_PRICE]
        remark_col = columns.get(HEADER_REMARK)

        rows: list[WeldingUnitPriceParsedRow] = []
        errors: list[str] = []
        seen_names: set[str] = set()

        for row_idx in range(header_row + 1, (sheet.max_row or header_row) + 1):
            name_raw = _cell_text(sheet.cell(row_idx, name_col).value)
            unit_raw = (
                _cell_text(sheet.cell(row_idx, unit_col).value) if unit_col else ""
            )
            price_raw = sheet.cell(row_idx, price_col).value
            remark_raw = (
                _cell_text(sheet.cell(row_idx, remark_col).value) if remark_col else ""
            )

            if not name_raw and (price_raw is None or price_raw == ""):
                continue

            if not name_raw:
                errors.append(f"第 {row_idx} 行：名称为空")
                continue

            unit_price = _parse_unit_price(price_raw)
            if unit_price is None:
                errors.append(f"第 {row_idx} 行：费用（单价）无效（{price_raw!r}）")
                continue

            unit = unit_raw or "个"
            if name_raw in seen_names:
                errors.append(f"第 {row_idx} 行：名称「{name_raw}」重复")
                continue
            seen_names.add(name_raw)

            rows.append(
                WeldingUnitPriceParsedRow(
                    row_number=row_idx,
                    item_name=name_raw,
                    unit=unit,
                    unit_price=unit_price,
                    remark=remark_raw or None,
                )
            )
    finally:
        workbook.close()

    if not rows and not errors:
        errors.append("未解析到有效数据行")

    return WeldingUnitPriceParseResult(rows=rows, errors=errors)
