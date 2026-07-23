"""
工序数据模型

表示冲压工艺表中的一个工序。

工序是指零件的加工步骤，如：拉伸、冲孔、翻边、落料等。
一个零件可能有多个工序。
"""

from dataclasses import dataclass


@dataclass(slots=True)
class Process:
    """
    表示冲压工艺表中的一个工序。

    由 RowParser.parse_process_row() 创建。

    由 StampingExcelParser 收集到 ParserResult.processes 中。

    工序属于某个零件，通过 part_number 关联。
    """
    # 所属零件号
    part_number: str

    # 工序序号（如 "OP10"、"OP20"）
    process_seq: str

    # 工序代码/名称（如 "拉伸"、"冲孔"、"落料"）
    process_code: str

    # 模具套数
    die_sets: int = 1

    # 吨位（吨）
    tonnage: int = 0

    # 备注
    remark: str = ""
