"""零件用在哪 — 出参。"""

from decimal import Decimal

from pydantic import BaseModel, field_serializer

from app.common.money import Q4, optional_format_money


class BomWhereUsedSummaryVO(BaseModel):
    """HUD 件数，不含跨项目用量合计。"""

    hit_count: int
    snapshot_count: int
    vehicle_model_count: int


class BomWhereUsedNodeVO(BaseModel):
    """路径上的一层节点。"""

    node_id: int
    level: int
    part_number: str
    part_name: str | None = None
    internal_number: str | None = None
    qty: Decimal | None = None
    qty_text: str | None = None
    sketch_url: str | None = None
    material: str | None = None
    thickness_text: str | None = None
    material_mill: str | None = None
    part_weight: Decimal | None = None
    weld_info: str | None = None
    remark: str | None = None
    excel_filename: str | None = None
    excel_sheet_name: str | None = None
    excel_row: int | None = None

    @field_serializer("qty", "part_weight")
    def serialize_decimal(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q4, 4, allow_negative=True)


class BomWhereUsedPathVO(BaseModel):
    """一次挂载向上的路径。"""

    snapshot_id: int
    location: str
    vehicle_model: str
    bom_version: str
    nodes: list[BomWhereUsedNodeVO]
    path_qty: Decimal
    l0_node_id: int
    l0_part_number: str

    @field_serializer("path_qty")
    def serialize_path_qty(self, value: Decimal) -> str:
        formatted = optional_format_money(value, Q4, 4, allow_negative=True)
        return formatted or "0"


class BomWhereUsedVO(BaseModel):
    """零件用在哪完整结果。"""

    summary: BomWhereUsedSummaryVO
    paths: list[BomWhereUsedPathVO]
