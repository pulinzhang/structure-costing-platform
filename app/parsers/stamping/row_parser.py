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

from typing import Any, Callable, Dict, Optional

from app.parsers.stamping.value_parser import parse_decimal, parse_int
from app.parsers.stamping.models.part import Part
from app.parsers.stamping.models.process import Process


class RowParser:
    """行数据解析器"""

    def __init__(self, get_value_fn: Callable, col_map: Dict[str, int]):
        """
        Args:
            get_value_fn: 单元格值获取函数 (row, col) -> Any
            col_map: 列映射 {字段名: 列号}
        """
        self._get_value = get_value_fn
        self._col_map = col_map

    def parse_part_row(self, row_idx: int) -> Part:
        """
        解析零件行。

        Returns:
            Part 对象，包含该零件的所有字段。
        """
        col_map = self._col_map

        return Part(
            seq_no=parse_int(self._get_value(row_idx, col_map.get("seq", 1))),
            part_number=self._get_value(row_idx, col_map.get("part_no", 2)),
            part_name=self._get_value(row_idx, col_map.get("part_name", 3)),
            material=self._get_value(row_idx, col_map.get("material", 5)),
            thickness=parse_decimal(self._get_value(row_idx, col_map.get("thickness", 6))),
            part_weight=parse_decimal(self._get_value(row_idx, col_map.get("weight", 7))),
            sheet_length=parse_decimal(self._get_value(row_idx, col_map.get("length", 8))),
            sheet_width=parse_decimal(self._get_value(row_idx, col_map.get("width", 9))),
            parts_per_sheet=parse_int(self._get_value(row_idx, col_map.get("count", 10))),
            sheet_type=self._get_value(row_idx, col_map.get("sheet_type", 11)),
            die_type=self._get_value(row_idx, col_map.get("die_type", 16)),
            process_method=self._get_value(row_idx, col_map.get("method", 17)),
            automation=self._get_value(row_idx, col_map.get("auto", 18)),
            remark=self._get_value(row_idx, col_map.get("remark", 19)),
        )

    def parse_process_row(self, row_idx: int, part_number: str) -> Optional[Process]:
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
        col_map = self._col_map
        process_seq = self._get_value(row_idx, col_map.get("op", 12))

        if not process_seq:
            return None

        return Process(
            part_number=part_number,
            process_seq=process_seq,
            process_code=self._get_value(row_idx, col_map.get("code", 13)),
            die_sets=parse_int(self._get_value(row_idx, col_map.get("die_set", 14))),
            tonnage=parse_int(self._get_value(row_idx, col_map.get("tonnage", 15))),
            remark=self._get_value(row_idx, col_map.get("remark", 19)),
        )


class PartSaver:
    """零件保存器（处理警告逻辑）"""

    def __init__(self):
        self._warned_parts: set = set()

    def save_part(self, part_number: str, process_count: int, warnings: list) -> None:
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

    def reset(self) -> None:
        """重置警告状态（用于新文件解析）"""
        self._warned_parts = set()
