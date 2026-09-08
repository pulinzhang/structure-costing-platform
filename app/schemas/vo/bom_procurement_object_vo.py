"""采购对象清单 VO。"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, field_serializer

from app.common.money import Q4, optional_format_money
from app.common.timezone import datetime_to_iso
from app.schemas.common.batch_result import BatchAuditCountsVO, BatchDeleteCountsVO


class BomProcurementObjectListVO(BaseModel):
    id: int
    snapshot_id: int
    location: str
    vehicle_model: str
    bom_version: str
    source_filename: str
    qa_passed: bool
    qa_error_text: str | None = None
    l0_count: int
    l0_with_children_count: int
    l2_count: int
    subassembly_child_sum: int
    object_l0_degenerate_count: int
    object_l1_subassembly_count: int
    object_l1_stamping_count: int
    other_leaf_count: int
    anomaly_count: int
    generated_at: datetime | None = None
    generated_by: str | None = None
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer("generated_at", "created_at", "updated_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)

    model_config = {"from_attributes": True}


class BomProcurementObjectVO(BaseModel):
    id: int
    list_id: int
    section: str
    object_kind: str | None = None
    degenerate_subtype: str | None = None
    source_node_id: int
    part_number: str
    part_name: str | None = None
    level: int
    node_role: str
    qty: Decimal | None = None
    qty_unit: str
    l0_part_number: str
    l0_part_name: str | None = None
    parent_part_number: str | None = None
    parent_part_name: str | None = None
    excel_filename: str | None = None
    excel_sheet_name: str | None = None
    excel_row: int | None = None
    child_count: int
    weld_info: str | None = None
    remark: str | None = None
    has_outsource_remark: bool
    material: str | None = None
    thickness_text: str | None = None
    material_mill: str | None = None
    data_gap: str | None = None
    alert_code: str | None = None
    confirm_status: str
    confirmed_by: str | None = None
    confirmed_at: datetime | None = None
    confirm_remark: str | None = None
    supplier_name: str | None = None
    audit_status: str
    audited_by: str | None = None
    audited_at: datetime | None = None
    audit_remark: str | None = None
    reverse_audited_by: str | None = None
    reverse_audited_at: datetime | None = None
    reverse_audit_remark: str | None = None
    location: str | None = None
    vehicle_model: str | None = None
    bom_version: str | None = None
    source_filename: str | None = None
    qa_passed: bool | None = None
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer("qty")
    def serialize_qty(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q4, 4)

    @field_serializer(
        "confirmed_at",
        "audited_at",
        "reverse_audited_at",
        "created_at",
        "updated_at",
    )
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)

    model_config = {"from_attributes": True}


class BomProcurementObjectGenerateResultVO(BaseModel):
    header: BomProcurementObjectListVO
    object_count: int
    other_leaf_count: int
    anomaly_count: int


class BomProcurementObjectPrepStatsVO(BaseModel):
    node_count: int = 0
    object_count: int = 0
    other_leaf_count: int = 0
    anomaly_count: int = 0
    approved_count: int = 0
    qa_passed: bool | None = None
    ready: bool = False
    message: str = ""


class BomProcurementObjectBatchAuditResultVO(BatchAuditCountsVO):
    location: str
    vehicle_model: str
    bom_version: str


class BomProcurementObjectBatchDeleteResultVO(BatchDeleteCountsVO):
    location: str
    vehicle_model: str
    bom_version: str


class BomProcurementObjectGenerateLogVO(BaseModel):
    id: int
    calc_batch_id: str
    location: str
    vehicle_model: str
    bom_version: str
    snapshot_id: int | None = None
    status: str
    node_count: int = 0
    object_count: int = 0
    other_leaf_count: int = 0
    anomaly_count: int = 0
    qa_passed: bool = False
    detail_text: str = ""
    operator_id: int | None = None
    operator_name: str | None = None
    created_by: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime | None = None

    @field_serializer("started_at", "finished_at", "created_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)

    model_config = {"from_attributes": True}
