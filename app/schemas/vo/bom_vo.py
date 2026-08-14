"""BOM VO - 响应数据结构"""

from datetime import date, datetime
from decimal import Decimal
from typing import Union

from pydantic import BaseModel, field_serializer


def decimal_to_float(value: Union[Decimal, float, None]) -> float | None:
    return float(value) if isinstance(value, Decimal) else value


class BomSnapshotVO(BaseModel):
    """BOM 清单版本"""

    id: int
    location: str
    vehicle_model: str
    bom_version: str
    product_category: str | None = None
    customer_name: str | None = None
    stage: str
    doc_no: str | None = None
    prepare_dept: str | None = None
    doc_date: date | None = None
    revision_date: date | None = None
    title: str | None = None
    source_filename: str
    source_sheet_name: str | None = None
    source_file_path: str | None = None
    source_file_hash: str | None = None
    status: str
    remark: str | None = None
    node_count: int | None = None
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer("doc_date", "revision_date")
    def serialize_date(self, value: date | None) -> str | None:
        return value.isoformat() if value else None

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None

    model_config = {"from_attributes": True}


class BomNodeVO(BaseModel):
    """BOM 树节点（扁平）"""

    id: int
    snapshot_id: int
    parent_id: int | None = None
    level: int
    sort_no: int
    seq_no: int | None = None
    internal_number: str | None = None
    part_number: str
    part_name: str | None = None
    qty: float | None = None
    qty_unit: str
    qty_text: str | None = None
    node_role: str
    is_supply_unit: bool
    manufacturing_category: str | None = None
    material: str | None = None
    thickness_mm: float | None = None
    thickness_text: str | None = None
    material_mill: str | None = None
    part_weight: float | None = None
    gauge_developed: str | None = None
    weld_info: str | None = None
    remark: str | None = None
    sketch_url: str | None = None
    excel_filename: str | None = None
    excel_sheet_name: str | None = None
    excel_row: int | None = None
    excel_part_col: int | None = None
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer("qty", "thickness_mm", "part_weight")
    def serialize_decimal(self, value: Union[Decimal, float, None]) -> float | None:
        return decimal_to_float(value)

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None

    model_config = {"from_attributes": True}


class BomNodeTreeVO(BomNodeVO):
    """BOM 树节点（含子节点）"""

    children: list["BomNodeTreeVO"] = []


class BomImportResultVO(BaseModel):
    """Excel 导入结果"""

    snapshot: BomSnapshotVO
    node_count: int
    image_count: int = 0
    replaced: bool = False
    message: str = "导入成功"


BomNodeTreeVO.model_rebuild()
