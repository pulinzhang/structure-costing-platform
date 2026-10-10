"""
拼焊件 Excel 解析器

与主工艺共用同一份冲压工艺确认表；不解析工序。

判定（样例 烟台海众 T28）：
- 零件号列合并行数 == 「长/卷料宽」合并行数 → 普通件（如 27–33）
- 不相等（卷料宽被切成多块）→ 拼焊件（如 34–40：H 拆成 34–37 与 38–40）
每块卷料宽合并 = 一片 TailorWeldBlankParsed。
父格料厚常为 ``0.70/1.00``，按 ``/`` 对齐各片（不用 parse_decimal 整格相除）。
"""

from __future__ import annotations

import time
from decimal import Decimal, InvalidOperation
from typing import Any

from openpyxl.worksheet.worksheet import Worksheet

from app.common.offal_nested import parse_offal_from_sheet_type
from app.parsers.stamping.excel_context import ExcelContext
from app.parsers.stamping.header_resolver import HeaderResolver
from app.parsers.stamping.models.header import HeaderContext
from app.parsers.stamping.models.part_no_range import PartNoRange
from app.parsers.stamping.models.tailor_weld import (
    TailorWeldAssemblyParsed,
    TailorWeldBlankParsed,
    TailorWeldParseResult,
)
from app.parsers.stamping.value_parser import parse_decimal, parse_int
from app.utils.logging_config import get_logger

logger = get_logger("parser.stamping.tailor_weld")


def _as_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _split_thickness_segments(raw: object) -> list[Decimal]:
    """
    将父格料厚拆成各片。

    ``0.70/1.00`` → [0.70, 1.00]
    不能走 parse_decimal 整串（其中 ``/`` 会被当成除法）。
    """
    text = _as_text(raw)
    if text is None:
        return []
    segments: list[Decimal] = []
    for chunk in text.split("/"):
        piece = chunk.strip()
        if not piece:
            continue
        try:
            segments.append(Decimal(piece))
        except (InvalidOperation, ValueError):
            parsed = parse_decimal(piece)
            if parsed is not None:
                segments.append(parsed)
    return segments


def _column_vertical_merges(
    sheet: Worksheet,
    col: int,
) -> list[tuple[int, int]]:
    """某列纵向合并块，按起始行排序：(start_row, end_row)。"""
    blocks: list[tuple[int, int]] = []
    for merged in sheet.merged_cells.ranges:
        if merged.min_col != col or merged.max_col != col:
            continue
        blocks.append((merged.min_row, merged.max_row))
    blocks.sort(key=lambda item: item[0])
    return blocks


def _clip_merges_to_range(
    merges: list[tuple[int, int]],
    start_row: int,
    end_row: int,
) -> list[tuple[int, int]]:
    clipped: list[tuple[int, int]] = []
    for merge_start, merge_end in merges:
        lo = max(merge_start, start_row)
        hi = min(merge_end, end_row)
        if lo <= hi:
            clipped.append((lo, hi))
    return clipped


def _fill_uncovered_gaps(
    covered: list[tuple[int, int]],
    start_row: int,
    end_row: int,
) -> list[tuple[int, int]]:
    """零件范围内未被卷料宽合并盖住的连续行，各成一块。"""
    if not covered:
        return [(start_row, end_row)]
    blocks = sorted(covered)
    filled: list[tuple[int, int]] = []
    cursor = start_row
    for lo, hi in blocks:
        if cursor < lo:
            filled.append((cursor, lo - 1))
        filled.append((lo, hi))
        cursor = hi + 1
    if cursor <= end_row:
        filled.append((cursor, end_row))
    return filled


def _is_tailor_weld(
    part_span: int,
    length_blocks: list[tuple[int, int]],
) -> bool:
    if len(length_blocks) > 1:
        return True
    if len(length_blocks) == 1:
        lo, hi = length_blocks[0]
        return (hi - lo + 1) != part_span
    return False


def _iter_part_ranges(excel_ctx: ExcelContext, data_start_row: int) -> list[PartNoRange]:
    seen: set[int] = set()
    ranges: list[PartNoRange] = []
    max_row = excel_ctx.max_row
    for row_idx in range(data_start_row, max_row + 1):
        part_range = excel_ctx.get_part_no_range(row_idx)
        if part_range is None or part_range.start_row in seen:
            continue
        seen.add(part_range.start_row)
        ranges.append(part_range)
    return ranges


def _value_at_merge_or_row(
    excel_ctx: ExcelContext,
    col: int,
    row_start: int,
    merges: list[tuple[int, int]],
) -> Any:
    for lo, hi in merges:
        if lo <= row_start <= hi:
            return excel_ctx.get_value(lo, col)
    return excel_ctx.get_value(row_start, col)


class TailorWeldExcelParser:
    """
    拼焊件解析器。

    产出：``TailorWeldParseResult``。不解析工序。
    """

    def parse(self, file_path: str) -> TailorWeldParseResult:
        start = time.time()
        result = TailorWeldParseResult()
        excel_ctx = ExcelContext()
        try:
            excel_ctx.load(file_path)
            sheet = excel_ctx.find_sheet()
            result.sheet_name = sheet.title

            header_resolver = HeaderResolver(excel_ctx.get_value)
            header_ctx: HeaderContext = header_resolver.resolve(sheet)

            part_no_col = header_ctx.col_map.get("part_no", 2)
            length_col = header_ctx.col_map.get("length", 8)
            width_col = header_ctx.col_map.get("width", 9)
            material_col = header_ctx.col_map.get("material", 5)
            thickness_col = header_ctx.col_map.get("thickness", 6)
            weight_col = header_ctx.col_map.get("weight", 7)
            count_col = header_ctx.col_map.get("count", 10)
            sheet_type_col = header_ctx.col_map.get("sheet_type", 11)
            part_name_col = header_ctx.col_map.get("part_name", 3)

            excel_ctx.build_merged_cache(part_no_col)
            length_merges = _column_vertical_merges(sheet, length_col)
            width_merges = _column_vertical_merges(sheet, width_col)

            for part_range in _iter_part_ranges(excel_ctx, header_ctx.data_start_row):
                assembly = self._parse_part_range(
                    excel_ctx=excel_ctx,
                    part_range=part_range,
                    sheet_name=result.sheet_name,
                    length_col=length_col,
                    width_col=width_col,
                    material_col=material_col,
                    thickness_col=thickness_col,
                    weight_col=weight_col,
                    count_col=count_col,
                    sheet_type_col=sheet_type_col,
                    part_name_col=part_name_col,
                    length_merges=length_merges,
                    width_merges=width_merges,
                    warnings=result.warnings,
                )
                if assembly is not None:
                    result.assemblies.append(assembly)

            logger.info(
                "拼焊解析完成: sheet=%s assemblies=%s blanks=%s",
                result.sheet_name,
                result.assembly_count,
                result.blank_count,
            )
        except Exception as exc:
            logger.error("拼焊解析失败: %s", exc)
            raise
        finally:
            excel_ctx.close()
            result.parse_time_ms = (time.time() - start) * 1000
        return result

    def _parse_part_range(
        self,
        *,
        excel_ctx: ExcelContext,
        part_range: PartNoRange,
        sheet_name: str,
        length_col: int,
        width_col: int,
        material_col: int,
        thickness_col: int,
        weight_col: int,
        count_col: int,
        sheet_type_col: int,
        part_name_col: int,
        length_merges: list[tuple[int, int]],
        width_merges: list[tuple[int, int]],
        warnings: list[str],
    ) -> TailorWeldAssemblyParsed | None:
        parent_part_number = _as_text(part_range.value)
        if parent_part_number is None:
            return None

        start_row = part_range.start_row
        end_row = part_range.end_row
        part_span = end_row - start_row + 1

        covered = _clip_merges_to_range(length_merges, start_row, end_row)
        length_blocks = _fill_uncovered_gaps(covered, start_row, end_row)
        if not _is_tailor_weld(part_span, length_blocks):
            return None

        if len(length_blocks) < 2:
            warnings.append(
                f"{parent_part_number}（行{start_row}-{end_row}）判定为拼焊，"
                f"但卷料宽只切出 {len(length_blocks)} 块"
            )

        thickness_raw = _as_text(excel_ctx.get_value(start_row, thickness_col))
        thickness_segments = _split_thickness_segments(thickness_raw)
        material = _as_text(excel_ctx.get_value(start_row, material_col))
        part_name = _as_text(excel_ctx.get_value(start_row, part_name_col))
        sheet_type = parse_offal_from_sheet_type(
            excel_ctx.get_value(start_row, sheet_type_col)
        ).sheet_type
        parts_per_sheet = parse_int(excel_ctx.get_value(start_row, count_col))
        part_weight = parse_decimal(excel_ctx.get_value(start_row, weight_col))

        if thickness_segments and len(thickness_segments) != len(length_blocks):
            warnings.append(
                f"{parent_part_number} 料厚分段数 {len(thickness_segments)}"
                f"（{thickness_raw}）与子片数 {len(length_blocks)} 不一致"
            )

        blanks: list[TailorWeldBlankParsed] = []
        for index, (blank_start, blank_end) in enumerate(length_blocks, start=1):
            thickness = thickness_segments[index - 1] if index <= len(thickness_segments) else None
            blanks.append(
                TailorWeldBlankParsed(
                    blank_seq=index,
                    excel_row_start=blank_start,
                    excel_row_end=blank_end,
                    sheet_length=parse_decimal(
                        _value_at_merge_or_row(excel_ctx, length_col, blank_start, length_merges)
                    ),
                    sheet_width=parse_decimal(
                        _value_at_merge_or_row(excel_ctx, width_col, blank_start, width_merges)
                    ),
                    thickness=thickness,
                    material=material,
                    blank_part_number=f"{parent_part_number}-{index}",
                    parts_per_sheet=parts_per_sheet,
                    sheet_type=sheet_type,
                    excel_sheet_name=sheet_name or None,
                )
            )

        return TailorWeldAssemblyParsed(
            parent_part_number=parent_part_number,
            excel_row_start=start_row,
            excel_row_end=end_row,
            part_name=part_name,
            material=material,
            thickness_raw=thickness_raw,
            part_weight=part_weight,
            parts_per_sheet=parts_per_sheet,
            sheet_type=sheet_type,
            blanks=blanks,
            excel_sheet_name=sheet_name or None,
        )


def parse_tailor_weld_excel(file_path: str) -> TailorWeldParseResult:
    """模块级入口：解析拼焊 → TailorWeldParseResult。"""
    return TailorWeldExcelParser().parse(file_path)
