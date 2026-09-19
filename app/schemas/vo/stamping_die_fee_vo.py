"""冲压年度模具费 VO。"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.common.money import Q0, Q4, format_money, optional_format_money
from app.common.timezone import datetime_to_iso
from app.schemas.common.batch_result import BatchAuditCountsVO, BatchDeleteCountsVO
from app.schemas.vo.timing import DurationSecondsMixin


class StampingDieFeeItemVO(BaseModel):
    id: int | None = None
    source_die_process_id: int | None = None
    process_seq: str
    process_order: int
    process_code: str | None = None
    estimated_weight_t: Decimal
    alloc_ratio: Decimal
    die_sets: int | None = None
    unit_price: Decimal
    allocation_qty: Decimal
    price_kind: str
    line_die_fee: Decimal
    basis_text: str | None = None

    @field_serializer(
        "estimated_weight_t",
        "alloc_ratio",
        "unit_price",
        "line_die_fee",
    )
    def serialize_decimal(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q4, 4)

    @field_serializer("allocation_qty")
    def serialize_allocation_qty(self, value: Decimal) -> str:
        return format_money(value, Q0, 0)

    model_config = ConfigDict(from_attributes=True)


class StampingDieFeeVO(BaseModel):
    id: int
    year: int
    location: str
    vehicle_model: str
    stamping_supplier: str | None = None
    version: str | None = None
    part_number: str
    source_die_part_id: int | None = None
    seq_no: int | None = None
    part_name: str | None = None
    material: str | None = None
    thickness: Decimal | None = None
    part_weight: Decimal | None = None
    die_type: str | None = None
    die_method: str | None = None
    production_mode: str | None = None
    part_grade: str | None = None
    excel_filename: str | None = None
    price_kind: str
    unit_price: Decimal
    allocation_qty: Decimal
    die_fee: Decimal
    adjustment_amount: Decimal | None = None
    final_die_fee: Decimal
    remark: str | None = None
    audit_status: str = "pending"
    audited_by: str | None = None
    audited_at: datetime | None = None
    audit_remark: str | None = None
    reverse_audited_by: str | None = None
    reverse_audited_at: datetime | None = None
    reverse_audit_remark: str | None = None
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    items: list[StampingDieFeeItemVO] = Field(default_factory=list)

    @field_serializer(
        "thickness",
        "part_weight",
        "unit_price",
        "die_fee",
        "adjustment_amount",
        "final_die_fee",
    )
    def serialize_money(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q4, 4)

    @field_serializer("allocation_qty")
    def serialize_allocation_qty(self, value: Decimal) -> str:
        return format_money(value, Q0, 0)

    @field_serializer(
        "created_at",
        "updated_at",
        "audited_at",
        "reverse_audited_at",
    )
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)

    model_config = ConfigDict(from_attributes=True)


class StampingDieFeeCalcResultVO(BaseModel):
    year: int
    location: str
    vehicle_model: str
    stamping_supplier: str | None = None
    version: str | None = None
    calc_batch_id: str | None = None
    log_id: int | None = None
    status: str = "success"
    total_parts: int
    success_count: int
    skipped_no_die_count: int = 0
    failed_count: int = 0
    missing_die_number_count: int = 0
    missing_die_number_hints: list[str] = Field(default_factory=list)
    detail_text: str = ""
    started_at: str | None = None
    finished_at: str | None = None


class StampingDieFeeCalcLogVO(DurationSecondsMixin):
    id: int
    calc_batch_id: str
    year: int
    location: str
    vehicle_model: str
    stamping_supplier: str | None = None
    version: str | None = None
    status: str
    total_parts: int = 0
    success_count: int = 0
    skipped_no_die_count: int = 0
    failed_count: int = 0
    detail_text: str = ""
    operator_id: int | None = None
    operator_name: str | None = None
    created_by: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime | None = None

    @field_serializer("started_at", "finished_at", "created_at")
    def serialize_log_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)


class StampingDieFeeCalcReadyVO(BaseModel):
    year: int
    location: str | None = None
    vehicle_model: str | None = None
    stamping_supplier: str | None = None
    version: str | None = None
    part_count: int = 0
    calculable_count: int = 0
    has_unit_price: bool = False
    message: str | None = None


class StampingDieFeeFilterVO(BaseModel):
    years: list[int] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    vehicle_models: list[str] = Field(default_factory=list)
    stamping_suppliers: list[str] = Field(default_factory=list)
    versions: list[str] = Field(default_factory=list)


class StampingDieFeeBatchDeleteResultVO(BatchDeleteCountsVO):
    year: int
    location: str
    vehicle_model: str


class StampingDieFeeBatchAuditResultVO(BatchAuditCountsVO):
    year: int
    location: str
    vehicle_model: str


class DieFeeListFilters(BaseModel):
    year: int
    location: str
    vehicle_model: str
    stamping_supplier: str | None = None
    version: str | None = None
    part_number: str | None = None
    audit_status: str | None = None
    only_zero: bool = False
    total_count: int = 0
    pending_count: int = 0
    approved_count: int = 0
    zero_count: int = 0
    total_fee: Decimal = Decimal("0")
    avg_fee: Decimal = Decimal("0")

    @field_serializer("total_fee", "avg_fee")
    def serialize_summary_money(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q4, 4)
