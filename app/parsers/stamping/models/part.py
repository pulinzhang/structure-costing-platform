"""
零件数据模型

表示冲压工艺表中的一个零件。

零件包含：
- 基本信息：零件号、名称、材质
- 尺寸信息：料厚、单重、料片尺寸
- 工艺信息：吨位、模具类型、成形方法、自动化
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass(slots=True)
class Part:
    """
    表示冲压工艺表中的一个零件。

    由 RowParser.parse_part_row() 创建。

    由 StampingExcelParser 收集到 ParserResult.parts 中。

    为什么用类而不是 Dict？

    当代码中看到 Part 类型时，立刻知道它代表一个零件；
    当代码中看到 dict 时，必须打开源码才能知道里面有什么字段。

    好的类型，本身就是最好的文档（Good Types Are Self-Documenting）。
    """
    # 序号
    seq_no: int = 0

    # 零件号（唯一标识）
    part_number: Optional[str] = None

    # 零件名称
    part_name: Optional[str] = None

    # 材质（如 DC04、BH220）
    material: Optional[str] = None

    # 料厚（mm）
    thickness: Optional[Decimal] = None

    # 单件重量（kg）
    part_weight: Optional[Decimal] = None

    # 料片长度（mm）
    sheet_length: Optional[Decimal] = None

    # 料片宽度（mm）
    sheet_width: Optional[Decimal] = None

    # 可制件数（一张料片能冲几个零件）
    parts_per_sheet: int = 0

    # 料片式样（卷料/板料）
    sheet_type: Optional[str] = None

    # 模具类型（单动/双动）
    die_type: Optional[str] = None

    # 成形方法（冲裁/拉伸/翻边...）
    process_method: Optional[str] = None

    # 自动化程度（自动/手动）
    automation: Optional[str] = None

    # 备注
    remark: Optional[str] = None
