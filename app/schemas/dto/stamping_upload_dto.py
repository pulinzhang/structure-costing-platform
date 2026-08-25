"""
冲压上传服务内部 DTO

用于 Service 层与 Repository 层之间的数据传输。

为什么用 dataclass 而不是 dict？
1. 字段类型约束，IDE 自动补全
2. 运行时类型检查，防止字段名拼写错误
3. 代码即文档，一看就知道数据结构
4. 比 Pydantic 轻量，比 dict 严格
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TypedDict


@dataclass(slots=True)
class FileInfo:
    """文件保存结果"""

    file_path: str = field(metadata={"description": "文件路径"})
    new_filename: str = field(metadata={"description": "新文件名"})
    safe_location: str = field(metadata={"description": "基地"})
    safe_vehicle: str = field(metadata={"description": "车型"})
    safe_version: str = field(metadata={"description": "版本"})
    upload_subdir: str = field(metadata={"description": "上传子目录"})


@dataclass(slots=True)
class PartData:
    """零件数据库写入数据"""

    location: str = field(metadata={"description": "基地"})
    vehicle_model: str = field(metadata={"description": "车型"})
    version: str = field(metadata={"description": "版本"})
    stamping_supplier: str = field(metadata={"description": "冲压供应商"})
    part_number: str = field(metadata={"description": "零件号"})
    excel_filename: str = field(metadata={"description": "Excel文件名"})
    seq_no: int | None = field(default=None, metadata={"description": "顺序号"})
    part_name: str | None = field(default=None, metadata={"description": "零件名称"})
    material: str | None = field(default=None, metadata={"description": "材质"})
    thickness: Decimal | None = field(default=None, metadata={"description": "料厚(mm)"})
    part_weight: Decimal | None = field(default=None, metadata={"description": "零件重量(kg)"})
    sheet_length: Decimal | None = field(default=None, metadata={"description": "料长(mm)"})
    sheet_width: Decimal | None = field(default=None, metadata={"description": "料宽(mm)"})
    parts_per_sheet: int | None = field(
        default=None,
        metadata={
            "description": (
                "可制件数：一张钢板/料片单独冲本零件可出的件数"
                "（例：1出2记2；左右共模按单侧计则为2）"
            )
        },
    )
    sheet_type: str | None = field(default=None, metadata={"description": "板料类型"})
    die_type: str | None = field(default=None, metadata={"description": "模具类型"})
    process_method: str | None = field(default=None, metadata={"description": "工序方式"})
    automation: str | None = field(
        default=None,
        metadata={"description": "自动化：工艺文件原文（如自动/手动/半自动），非布尔"},
    )
    remark: str | None = field(default=None, metadata={"description": "备注"})
    sketch_url: str | None = field(default=None, metadata={"description": "零件简图URL"})
    is_tailor_welded: bool = field(default=False, metadata={"description": "是否拼焊总成"})
    excel_sheet_name: str | None = field(
        default=None, metadata={"description": "来源 Excel 工作表名"}
    )
    excel_row: int | None = field(
        default=None, metadata={"description": "来源 Excel 行号（1-based）"}
    )
    excel_part_col: int | None = field(
        default=None, metadata={"description": "零件号所在列号（1-based）"}
    )
    created_by: str | None = field(default=None, metadata={"description": "创建人"})
    updated_by: str | None = field(default=None, metadata={"description": "修改人"})


@dataclass(slots=True)
class ProcessData:
    """工序数据库写入数据"""

    part_id: int = field(metadata={"description": "零件ID"})
    process_seq: str = field(metadata={"description": "工序序号"})
    process_order: int = field(metadata={"description": "工序顺序"})
    die_sets: int = field(metadata={"description": "模具套数"})
    # 以下字段有默认值，放在后面
    process_code: str | None = field(default=None, metadata={"description": "工序代码"})
    tonnage: int | None = field(default=None, metadata={"description": "吨位(T)"})
    cost_ratio: Decimal = field(default=Decimal("1.00"), metadata={"description": "费用比例"})
    remark: str | None = field(default=None, metadata={"description": "备注"})
    created_by: str | None = field(default=None, metadata={"description": "创建人"})
    updated_by: str | None = field(default=None, metadata={"description": "修改人"})


@dataclass(slots=True)
class UploadResult:
    """上传处理结果（API 响应格式）"""

    filename: str = field(metadata={"description": "原文件名"})
    new_filename: str = field(metadata={"description": "新文件名"})
    size: int = field(metadata={"description": "文件大小(Bytes)"})
    path: str = field(metadata={"description": "保存路径"})
    location: str = field(metadata={"description": "基地"})
    vehicle_model: str = field(metadata={"description": "车型"})
    version: str = field(metadata={"description": "版本"})
    parts_count: int = field(metadata={"description": "零件数量"})
    processes_count: int = field(metadata={"description": "工序数量"})
    images_count: int = field(metadata={"description": "简图数量"})
    tailor_weld_assembly_count: int = field(default=0, metadata={"description": "拼焊总成数量"})
    tailor_weld_blank_count: int = field(default=0, metadata={"description": "拼焊子片数量"})
    warnings: list[str] = field(default_factory=list, metadata={"description": "警告信息"})
    parse_time_ms: float = field(default=0.0, metadata={"description": "解析耗时(ms)"})


class StampingPartPatch(TypedDict, total=False):
    """零件部分更新（只含要改的列）。"""

    location: str
    stamping_supplier: str | None
    vehicle_model: str
    version: str
    seq_no: int | None
    part_number: str
    part_name: str | None
    is_tailor_welded: bool
    material: str | None
    thickness: Decimal | None
    part_weight: Decimal | None
    sheet_length: Decimal | None
    sheet_width: Decimal | None
    parts_per_sheet: int | None
    sheet_type: str | None
    die_type: str | None
    process_method: str | None
    automation: str | None
    remark: str | None
    sketch_url: str | None
    excel_filename: str
    excel_sheet_name: str | None
    excel_row: int | None
    excel_part_col: int | None
    updated_by: str
    created_by: str


class StampingProcessPatch(TypedDict, total=False):
    """工序部分更新（只含要改的列）。"""

    process_seq: str
    process_order: int
    process_code: str | None
    die_sets: int | None
    tonnage: int | None
    cost_ratio: Decimal
    remark: str | None
    updated_by: str
