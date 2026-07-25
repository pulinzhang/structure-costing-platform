"""钢材价格 Excel 解析器。"""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any

from openpyxl import load_workbook


EXPECTED_HEADERS = (
    "年度",
    "月份",
    "钢种",
    "牌号",
    "参考规格",
    "钢厂",
    "中标价",
    "厚度",
    "厚度加减价",
    "加工费",
    "最终价/吨",
    "备注",
)
REQUIRED_FIELD_COUNT = 11


@dataclass(frozen=True)
class SteelPriceParseResult:
    """钢材价格文件解析结果。"""

    records: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _normalize_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _parse_integer(value: Any, field_name: str, row_number: int) -> int:
    try:
        decimal_value = Decimal(str(value).strip())
    except (InvalidOperation, AttributeError, ValueError) as error:
        raise ValueError(f"第 {row_number} 行“{field_name}”不是有效整数") from error
    if decimal_value != decimal_value.to_integral_value():
        raise ValueError(f"第 {row_number} 行“{field_name}”必须是整数")
    return int(decimal_value)


def _parse_decimal(value: Any, field_name: str, row_number: int) -> Decimal:
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, AttributeError, ValueError) as error:
        raise ValueError(f"第 {row_number} 行“{field_name}”不是有效数字") from error


def _resolve_numeric_value(source_value: Any, cached_value: Any) -> Any:
    if isinstance(source_value, str) and source_value.startswith("="):
        return cached_value
    return source_value


def parse_steel_price_excel(file_content: bytes) -> SteelPriceParseResult:
    """解析首个工作表，严格校验十二列表头并返回结构化价格记录。

    文件内同一 ``(年度, 月份, 牌号, 厚度)`` 的多行只保留最后一条，
    并将其标记为 ``warnings``，便于追溯。
    """

    try:
        formula_workbook = load_workbook(BytesIO(file_content), data_only=False, read_only=True)
        value_workbook = load_workbook(BytesIO(file_content), data_only=True, read_only=True)
    except Exception as error:
        raise ValueError(f"无法读取 Excel 文件: {error}") from error

    formula_sheet = formula_workbook.active
    value_sheet = value_workbook.active
    actual_headers = tuple(
        _normalize_text(formula_sheet.cell(row=1, column=column_index).value)
        for column_index in range(1, len(EXPECTED_HEADERS) + 1)
    )
    if actual_headers != EXPECTED_HEADERS:
        raise ValueError(
            "表头格式不正确，必须严格为：" + "、".join(EXPECTED_HEADERS)
        )

    records_by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
    duplicate_rows: list[int] = []

    formula_rows = formula_sheet.iter_rows(min_row=2, max_col=len(EXPECTED_HEADERS), values_only=True)
    value_rows = value_sheet.iter_rows(min_row=2, max_col=len(EXPECTED_HEADERS), values_only=True)
    for row_number, (formula_row, value_row) in enumerate(zip(formula_rows, value_rows), start=2):
        source_row = tuple(formula_row)
        if not any(value is not None and _normalize_text(value) for value in source_row[:10]):
            continue

        missing_headers = [
            EXPECTED_HEADERS[index]
            for index, value in enumerate(source_row[:REQUIRED_FIELD_COUNT])
            if value is None or not _normalize_text(value)
        ]
        if missing_headers:
            raise ValueError(
                f"第 {row_number} 行缺少必填字段：{'、'.join(missing_headers)}"
            )

        year = _parse_integer(source_row[0], "年度", row_number)
        month = _parse_integer(source_row[1], "月份", row_number)
        if not 2000 <= year <= 2100:
            raise ValueError(f"第 {row_number} 行“年度”必须在 2000 至 2100 之间")
        if not 1 <= month <= 12:
            raise ValueError(f"第 {row_number} 行“月份”必须在 1 至 12 之间")

        bid_price = _parse_decimal(
            _resolve_numeric_value(source_row[6], value_row[6]), "中标价", row_number
        )
        thickness = _parse_decimal(
            _resolve_numeric_value(source_row[7], value_row[7]), "厚度", row_number
        )
        thickness_adjustment = _parse_decimal(
            _resolve_numeric_value(source_row[8], value_row[8]), "厚度加减价", row_number
        )
        processing_fee = _parse_decimal(
            _resolve_numeric_value(source_row[9], value_row[9]), "加工费", row_number
        )
        cached_final_price = value_row[10]
        if cached_final_price is None or isinstance(source_row[10], str) and source_row[10].startswith("="):
            final_price_per_ton = bid_price + thickness_adjustment + processing_fee
        else:
            final_price_per_ton = _parse_decimal(cached_final_price, "最终价/吨", row_number)

        grade = _normalize_text(source_row[3])
        record = {
            "year": year,
            "month": month,
            "steel_type": _normalize_text(source_row[2]),
            "grade": grade,
            "reference_spec": _normalize_text(source_row[4]),
            "steel_mill": _normalize_text(source_row[5]),
            "bid_price": bid_price,
            "thickness": thickness,
            "thickness_adjustment": thickness_adjustment,
            "processing_fee": processing_fee,
            "final_price_per_ton": final_price_per_ton,
            "remark": _normalize_text(source_row[11]) or None,
        }
        business_key = (year, month, grade, thickness)
        if business_key in records_by_key:
            duplicate_rows.append(row_number)
        records_by_key[business_key] = record

    formula_workbook.close()
    value_workbook.close()
    records = list(records_by_key.values())
    if not records:
        raise ValueError("文件中没有可导入的钢材价格数据")

    warnings: list[str] = []
    if duplicate_rows:
        for row_number in duplicate_rows:
            warnings.append(
                f"第 {row_number} 行与文件中更靠后的记录主键重复，已按最后一条覆盖"
            )

    return SteelPriceParseResult(records=records, warnings=warnings)

