"""
Parser 数据模型包

本包定义了冲压工艺 Excel 解析器的所有数据模型。

模块之间传递的是"领域对象（Domain Model）"，而不是匿名 Dict。

例如：
- parse_part_row() -> Part（零件）
- parse_process_row() -> Process（工序）
- header_resolver.resolve() -> HeaderContext（表头上下文）

这样设计的好处：
1. 调用方明确知道返回了什么
2. IDE 提供完整类型提示
3. 字段名称不会拼写错误
4. 代码本身就是最好的文档

数据流：
Excel
    ↓
ExcelContext
    ↓
HeaderContext（表头信息）
    ↓
PartNoRange（零件号范围）
    ↓
Part（零件）/ Process（工序）
    ↓
ParserResult（最终结果）
"""

from app.parsers.stamping.models.header import HeaderContext
from app.parsers.stamping.models.part import Part
from app.parsers.stamping.models.process import Process
from app.parsers.stamping.models.parse_result import ParserResult
from app.parsers.stamping.models.part_no_range import PartNoRange
from app.parsers.stamping.models.tailor_weld import (
    TailorWeldAssemblyParsed,
    TailorWeldBlankParsed,
    TailorWeldParseResult,
)

__all__ = [
    "HeaderContext",
    "Part",
    "Process",
    "ParserResult",
    "PartNoRange",
    "TailorWeldBlankParsed",
    "TailorWeldAssemblyParsed",
    "TailorWeldParseResult",
]
