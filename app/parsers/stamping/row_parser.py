"""
行解析模块

负责：
- 零件数据解析
- 工序数据解析
- 零件警告生成

判断规则（由主循环基于零件号范围驱动）：
- 零件行：行号在零件号范围起始行
- 工序行：op 列（工序号）有值
- 工序结束：op 列（工序号）为空
"""

from collections.abc import Callable
from typing import Any

from app.common.offal_nested import parse_offal_from_sheet_type
from app.common.scrap_byproduct import resolve_scrap_byproduct
from app.common.swing_shear import contains_swing_shear
from app.parsers.stamping.models.part import Part
from app.parsers.stamping.models.process import Process
from app.parsers.stamping.value_parser import parse_decimal, parse_int


class RowParser:
    """行数据解析器"""

    def __init__(
        self,
        get_value_fn: Callable[..., Any],
        col_map: dict[str, int],
        get_merged_value_fn: Callable[..., Any] | None = None,
    ):
        """
        Args:
            get_value_fn: 单元格值获取函数 (row, col) -> Any；不解析合并区
            col_map: 列映射 {字段名: 列号}
            get_merged_value_fn: 合并区取左上角值；吨位列用户常纵向合并
        """
        self._get_value = get_value_fn
        self._get_merged_value = get_merged_value_fn or get_value_fn
        self._col_map = col_map

    def _cell(self, row_idx: int, key: str, default_col: int | None = None) -> Any:
        """按 col_map 取单元格；未映射且无默认列时返回 None，避免串列。"""
        col = self._col_map.get(key, default_col)
        if col is None:
            return None
        return self._get_value(row_idx, col)

    def _merged_cell(self, row_idx: int, key: str, default_col: int | None = None) -> Any:
        """按 col_map 取单元格，合并区返回左上角值。"""
        col = self._col_map.get(key, default_col)
        if col is None:
            return None
        return self._get_merged_value(row_idx, col)

    def parse_part_row(self, row_idx: int) -> Part:
        """
        解析零件行。

        Returns:
            Part 对象，包含该零件的所有字段。
        """
        raw_sheet_type = self._cell(row_idx, "sheet_type")
        offal = parse_offal_from_sheet_type(raw_sheet_type)
        part_number = self._cell(row_idx, "part_no", 2)
        part_weight = parse_decimal(self._cell(row_idx, "weight", 7))
        sheet_length = parse_decimal(self._cell(row_idx, "length", 8))
        sheet_width = parse_decimal(self._cell(row_idx, "width", 9))
        parts_per_sheet = parse_int(self._cell(row_idx, "count", 10)) or 0
        scrap = resolve_scrap_byproduct(
            part_number=part_number,
            part_weight=part_weight,
            sheet_length=sheet_length,
            sheet_width=sheet_width,
            parts_per_sheet=parts_per_sheet,
            raw_sheet_type=raw_sheet_type,
            is_offal_nested=offal.is_offal_nested,
            offal_source=offal.offal_source,
        )
        die_type = self._cell(row_idx, "die_type")
        process_method = self._cell(row_idx, "method")
        automation = self._cell(row_idx, "auto")
        remark = self._cell(row_idx, "remark")
        # 摆剪常写在零件首行「工序内容」「冲压吨位」，该行没有工序名称，不会进工序子表。
        header_process_code = self._cell(row_idx, "code", 13)
        header_tonnage_text = self._merged_cell(row_idx, "tonnage", 15)
        has_swing_shear = contains_swing_shear(
            header_process_code,
            header_tonnage_text,
            die_type,
            process_method,
            automation,
            remark,
        )
        return Part(
            seq_no=parse_int(self._cell(row_idx, "seq", 1)) or 0,
            part_number=part_number,
            part_name=self._cell(row_idx, "part_name", 3),
            material=self._cell(row_idx, "material", 5),
            thickness=parse_decimal(self._cell(row_idx, "thickness", 6)),
            part_weight=part_weight,
            sheet_length=sheet_length,
            sheet_width=sheet_width,
            parts_per_sheet=parts_per_sheet,
            sheet_type=offal.sheet_type,
            is_offal_nested=scrap.is_offal_nested,
            offal_source=scrap.offal_source,
            is_scrap_byproduct=scrap.is_scrap_byproduct,
            has_swing_shear=has_swing_shear,
            die_type=die_type,
            process_method=process_method,
            automation=automation,
            remark=remark,
            excel_row=row_idx,
            excel_part_col=self._col_map.get("part_no", 2),
        )

    def parse_process_row(self, row_idx: int, part_number: str) -> Process | None:
        """
        解析工序行。

        判断规则：
        - op 列（工序号）有值 → 工序行，返回 Process
        - op 列（工序号）为空 → 工序结束，返回 None

        Args:
            row_idx: 行号
            part_number: 所属零件号

        Returns:
            Process 对象，或 None（如果工序号为空）
        """
        process_seq = self._cell(row_idx, "op", 12)

        if not process_seq:
            return None
        process_seq = str(process_seq).strip()
        if not process_seq:
            return None

        return Process(
            part_number=part_number,
            process_seq=process_seq,
            process_code=self._cell(row_idx, "code", 13),
            die_sets=parse_int(self._cell(row_idx, "die_set", 14)) or 1,
            die_number=_as_die_number(self._cell(row_idx, "die_number")),
            tonnage=parse_int(self._merged_cell(row_idx, "tonnage", 15)),
            remark=self._cell(row_idx, "remark"),
            excel_row=row_idx,
        )


def _as_die_number(value: object) -> str | None:
    if value is None or value == "":
        return None
    text = str(value).strip()
    if not text or text.startswith("#"):
        return None
    if text.endswith(".0") and text[:-2].replace("-", "", 1).isdigit():
        return text[:-2]
    return text


class PartSaver:
    """零件保存器（处理警告逻辑）"""

    def __init__(self) -> None:
        self._warned_parts: set[Any] = set()

    def save_part(self, part_number: str, process_count: int, warnings: list[Any]) -> None:
        """
        保存零件（生成警告）

        Args:
            part_number: 零件号
            process_count: 该零件的工序数量
            warnings: 警告列表（引用）
        """
        if not part_number or part_number in self._warned_parts:
            return

        self._warned_parts.add(part_number)

        if process_count == 0:
            warnings.append(f"零件 {part_number} 没有任何工序")
        elif process_count == 1:
            warnings.append(f"零件 {part_number} 只有1道工序")
