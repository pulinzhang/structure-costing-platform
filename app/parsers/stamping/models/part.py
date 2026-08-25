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
    part_number: str | None = None

    # 零件名称
    part_name: str | None = None

    # 材质（如 DC04、BH220）
    material: str | None = None

    # 料厚（mm）
    thickness: Decimal | None = None

    # 单件重量（kg）
    part_weight: Decimal | None = None

    # 料片长度（mm）
    sheet_length: Decimal | None = None

    # 料片宽度（mm）
    sheet_width: Decimal | None = None

    # 可制件数：一张钢板/料片单独冲压本零件时可出的件数。
    # 例：1 张料出 2 件 → 2；出 1 件 → 1；左右件共模同冲时按单侧零件计则为 2。
    # 注意：不是利用率百分比，也不是左右件合计件数。
    parts_per_sheet: int = 0

    # 料片式样（卷料/板料）
    sheet_type: str | None = None

    # 模具类型（单动/双动）
    die_type: str | None = None

    # 成形方法（冲裁/拉伸/翻边...）
    process_method: str | None = None

    # 自动化：Excel「自动化」列原文（如自动/手动/半自动），原样落库，勿转成布尔
    automation: str | None = None

    # 备注
    remark: str | None = None

    # 冲压供应商（从Excel表头提取，如"烟台海众汽车零部件有限公司"）
    stamping_supplier: str | None = None

    # Excel 单元格溯源（防扯皮）
    excel_sheet_name: str | None = None
    excel_row: int | None = None
    excel_part_col: int | None = None
