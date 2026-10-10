"""
表头上下文数据模型

表示 Excel 表头解析的结果。

表头解析需要确定：
- 表头在第几行
- 数据从第几行开始
- 每一列对应什么字段
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class HeaderContext:
    """
    表示 Excel 表头解析的结果。

    由 HeaderResolver.resolve() 创建。

    由 StampingExcelParser 使用，用于确定如何解析每一行数据。

    为什么用类而不是 Tuple？

    Tuple 的问题：
        header_row, data_start_row, col_map = header_resolver.resolve(sheet)
        # 调用方必须记住顺序，必须看文档才知道每个值是什么

    HeaderContext 的好处：
        context = header_resolver.resolve(sheet)
        context.header_row        # 语义清晰
        context.data_start_row    # 语义清晰
        context.col_map           # 语义清晰
    """

    # 表头行号（Excel 行号，1-based）
    header_row: int

    # 数据起始行号（表头行 + 2）
    data_start_row: int

    # 列映射：字段名 -> 列号
    # 例如：{"part_no": 2, "part_name": 3, "op": 12, ...}
    col_map: dict[str, int]

    # Header 路径：列号(字符串) -> 完整路径
    # 格式："一级/二级"，例如 "工艺/工序号"
    # 例如：{"2": "通用/零件号", "12": "工艺/工序号", ...}
    header_paths: dict[str, str] = field(default_factory=dict)
