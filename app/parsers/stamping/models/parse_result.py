"""
解析结果数据模型

表示整个 Excel 文件的解析结果。
"""

from dataclasses import dataclass, field
from typing import List, Dict

from app.parsers.stamping.models.part import Part
from app.parsers.stamping.models.process import Process


@dataclass(slots=True)
class ParserResult:
    """
    表示冲压工艺 Excel 的完整解析结果。

    由 StampingExcelParser.parse() 创建并返回。

    数据类型：
    - parts: List[Part] - 零件列表（对象，而非 dict）
    - processes: List[Process] - 工序列表（对象，而非 dict）
    - images_by_part: Dict[str, bytes] - 零件简图
    """
    # 零件列表（对象列表）
    parts: List[Part] = field(default_factory=list)

    # 工序列表（对象列表）
    processes: List[Process] = field(default_factory=list)

    # 警告信息（不影响解析，但值得注意）
    warnings: List[str] = field(default_factory=list)

    # 错误信息（解析失败）
    errors: List[str] = field(default_factory=list)

    # Sheet 名称
    sheet_name: str = ""

    # 表头行号
    header_row: int = 0

    # 数据起始行号
    data_start_row: int = 0

    # 列映射
    col_map: dict = field(default_factory=dict)

    # Header 路径
    header_paths: dict = field(default_factory=dict)

    # 总行数
    total_rows: int = 0

    # 解析耗时（毫秒）
    parse_time_ms: float = 0

    # 零件简图：零件号 -> 图片二进制
    images_by_part: Dict[str, bytes] = field(default_factory=dict)

    # 冲压供应商名称
    stamping_supplier: str = ""

    # 车型（从Excel表头"项目"字段提取）
    vehicle_model: str = ""

    # 版本（从Excel表头"版本"字段提取）
    version: str = ""

    @property
    def part_count(self) -> int:
        """零件数量"""
        return len(self.parts)

    @property
    def process_count(self) -> int:
        """工序数量"""
        return len(self.processes)

    @property
    def image_count(self) -> int:
        """简图数量"""
        return len(self.images_by_part)
