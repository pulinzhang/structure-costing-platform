"""
钢材基准价格 Excel 解析入口。
宽表列 = 基地；location_lookup 必传；年月由上传表单决定。
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.parsers.yishiyiyi.base_price.cells import cell_decimal, cell_text, parse_spec
from app.parsers.yishiyiyi.base_price.layout import (
    DEFAULT_FEE_COL,
    DEFAULT_SPEC_COL,
    extract_base_configs,
    find_data_sheet,
    find_processing_fee_col,
    find_spec_column,
)
from app.parsers.yishiyiyi.base_price.models import ParsedContext, ParseResult
from app.parsers.yishiyiyi.base_price.xls_compat import open_workbook

_DEFAULT_PROCESSING_FEE = Decimal("120.00")
_DATA_START_ROW = 6


def parse_base_price_excel(
    file_content: bytes,
    *,
    location_lookup: dict[str, str],
) -> ParseResult:
    """未命中 lookup 的基地列跳过，不把表头原文当规范名。"""
    result = ParseResult()
    try:
        workbook = open_workbook(file_content)
    except Exception as exc:
        result.errors.append(f"无法打开 Excel 文件: {exc}")
        return result

    sheet = find_data_sheet(workbook)
    if sheet is None:
        result.errors.append("未找到包含有效数据的工作表（未找到钢种/牌号/规格等关键列）")
        return result
    if sheet.title != "Sheet1":
        result.warnings.append(f"使用工作表: {sheet.title}")

    base_configs, skipped_locations = extract_base_configs(sheet, location_lookup)
    if skipped_locations:
        result.warnings.append("跳过非本系统基地列：" + "、".join(skipped_locations))
    if not base_configs:
        if skipped_locations:
            result.errors.append(
                "表头没有已启用基地对应列（已跳过：" + "、".join(skipped_locations) + "）"
            )
        else:
            result.errors.append("未能识别任何基地列，请检查表头格式")
        return result

    spec_col = find_spec_column(sheet)
    if spec_col is None:
        spec_col = DEFAULT_SPEC_COL
        result.warnings.append(
            f"未找到规格列，使用默认列索引 {DEFAULT_SPEC_COL}（第{DEFAULT_SPEC_COL + 1}列）"
        )
    else:
        result.warnings.append(f"规格列位于第 {spec_col + 1} 列")

    fee_col = find_processing_fee_col(sheet)
    if fee_col is None:
        fee_col = DEFAULT_FEE_COL
        result.warnings.append(f"未找到加工费列，使用默认列索引 {DEFAULT_FEE_COL}")

    context = ParsedContext(
        base_configs=base_configs,
        spec_col=spec_col,
        sheet_name=sheet.title,
    )
    _append_data_rows(sheet, context, fee_col, result)
    result.records.sort(key=lambda row: (row.get("excel_col", 0), row.get("excel_row", 0)))
    return result


def _append_data_rows(
    sheet: Any,
    context: ParsedContext,
    fee_col: int,
    result: ParseResult,
) -> None:
    skip_count = 0
    processed_rows = 0
    for row in sheet.iter_rows(min_row=_DATA_START_ROW, values_only=True):
        seq = row[0]
        if seq is None:
            continue
        try:
            int(seq)
        except (ValueError, TypeError):
            continue
        excel_row_num = _DATA_START_ROW + processed_rows
        processing_fee = cell_decimal(row[fee_col]) or _DEFAULT_PROCESSING_FEE
        records = _map_row_to_records(row, context, excel_row_num, processing_fee)
        if records:
            result.records.extend(records)
        else:
            skip_count += 1
        processed_rows += 1
    if skip_count > 0:
        result.warnings.append(f"跳过 {skip_count} 行（钢种或牌号为空或无法解析）")


def _map_row_to_records(
    row: tuple[Any, ...],
    context: ParsedContext,
    excel_row_num: int,
    processing_fee: Decimal,
) -> list[dict[str, Any]]:
    def safe_get(index: int) -> str:
        return cell_text(row[index]) if len(row) > index else ""

    steel_type = safe_get(1)
    grade = safe_get(2).replace("//", "/")
    spec_str = safe_get(context.spec_col)
    if not steel_type or not grade:
        return []
    thick, width = parse_spec(spec_str) if spec_str else (None, None)
    records: list[dict[str, Any]] = []
    for config in context.base_configs:
        mill = safe_get(config.mill_col)
        price = cell_decimal(row[config.price_col]) if len(row) > config.price_col else None
        if not mill or price is None:
            continue
        records.append(
            {
                "location": config.location,
                "steel_mill": mill,
                "category_name": steel_type,
                "grade": grade,
                "spec": spec_str,
                "thick": thick,
                "width": width,
                "base_price": price,
                "processing_fee": processing_fee,
                "sheet_name": context.sheet_name,
                "excel_row": excel_row_num,
                "excel_col": config.price_col + 1,
            }
        )
    return records
