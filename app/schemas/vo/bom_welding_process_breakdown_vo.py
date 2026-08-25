"""
BOM 焊接工艺拆解 VO
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, field_serializer

from app.common.timezone import datetime_to_iso


class BomWeldingProcessBreakdownLineVO(BaseModel):
    """明细行：单件焊接过程量"""

    id: int
    breakdown_node_id: int
    part_number: str
    line_no: int
    process_token: str
    matched_span: str | None = None
    process_qty: Decimal
    process_qty_unit: str
    process_qty_secondary: Decimal | None = None
    process_qty_secondary_unit: str | None = None
    standard_process_name: str | None = None
    standard_process_unit: str | None = None
    map_status: str
    rollup_flag: str
    child_fastener_qty_sum: Decimal | None = None
    qty_check_status: str
    qty_check_detail: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer(
        "process_qty",
        "process_qty_secondary",
        "child_fastener_qty_sum",
    )
    def serialize_decimal(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        return format(value, "f")

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)

    model_config = {"from_attributes": True}


class WeldingEvidenceContribVO(BaseModel):
    """L1 滚乘贡献一行（旁证明细）"""

    part_number: str
    part_name: str | None = None
    assembly_qty: Decimal
    process_qty: Decimal
    contrib: Decimal
    rollup_flag: str | None = None

    @field_serializer("assembly_qty", "process_qty", "contrib")
    def serialize_decimal(self, value: Decimal) -> str:
        return format(value, "f")


class WeldingEvidenceItemVO(BaseModel):
    """单工艺旁证：原文过程量 vs 结构旁证"""

    process_token: str
    source_process_qty: Decimal | None = None
    # 链 A：直接子件紧固件
    child_fastener_sum: Decimal | None = None
    child_status: str | None = None
    child_delta: Decimal | None = None
    child_detail: str | None = None
    # 链 B：L0 ↔ L1 滚乘（仅 L0）
    l1_rollup_sum: Decimal | None = None
    l1_status: str | None = None
    l1_delta: Decimal | None = None
    l1_detail: str | None = None
    l1_contribs: list[WeldingEvidenceContribVO] = []
    # 链 C：L0 ↔ L2 路径（仅 L0 + 凸焊类）
    l2_path_sum: Decimal | None = None
    l2_status: str | None = None
    l2_delta: Decimal | None = None
    l2_detail: str | None = None

    @field_serializer(
        "source_process_qty",
        "child_fastener_sum",
        "child_delta",
        "l1_rollup_sum",
        "l1_delta",
        "l2_path_sum",
        "l2_delta",
    )
    def serialize_decimal(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        return format(value, "f")


class WeldingNodeEvidenceVO(BaseModel):
    """节点旁证汇总（只读计算，不落库）"""

    level: int
    summary: str
    has_mismatch: bool = False
    items: list[WeldingEvidenceItemVO] = []


class BomWeldingProcessBreakdownNodeVO(BaseModel):
    """主表：节点 + 装配用量 + 原文；含明细行"""

    id: int
    location: str
    customer_name: str | None = None
    vehicle_model: str
    bom_version: str
    snapshot_id: int | None = None
    source_node_id: int | None = None
    part_number: str
    part_name: str | None = None
    level: int
    node_role: str
    parent_part_number: str | None = None
    parent_part_name: str | None = None
    supply_part_number: str | None = None
    supply_part_name: str | None = None
    assembly_qty: Decimal
    assembly_qty_unit: str | None = None
    weld_info_raw: str
    excel_row: int | None = None
    parse_status: str
    process_line_count: int = 0
    qa_note: str | None = None
    audit_status: str
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
    lines: list[BomWeldingProcessBreakdownLineVO] = []
    evidence: WeldingNodeEvidenceVO | None = None

    @field_serializer("assembly_qty")
    def serialize_assembly_qty(self, value: Decimal) -> str:
        return format(value, "f")

    @field_serializer(
        "created_at",
        "updated_at",
        "audited_at",
        "reverse_audited_at",
    )
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)

    model_config = {"from_attributes": True}


class BomWeldingProcessBreakdownGenerateResultVO(BaseModel):
    """生成结果（异步任务 result / 日志终态）"""

    location: str
    customer_name: str | None = None
    vehicle_model: str
    bom_version: str
    snapshot_id: int = 0
    node_count: int = 0
    line_count: int = 0
    message: str = ""
    calc_batch_id: str | None = None
    log_id: int | None = None
    status: str = "success"
    detail_text: str = ""
    started_at: str | None = None
    finished_at: str | None = None


class BomWeldingProcessBreakdownGenerateLogVO(BaseModel):
    """拆解生成历史记录 VO"""

    model_config = {"from_attributes": True}

    id: int
    calc_batch_id: str
    location: str
    vehicle_model: str
    bom_version: str
    customer_name: str | None = None
    snapshot_id: int | None = None
    status: str
    node_count: int = 0
    line_count: int = 0
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


class BomWeldingProcessBreakdownGeneratePrepStatsVO(BaseModel):
    """拆解前数据就绪统计"""

    location: str
    vehicle_model: str
    bom_version: str
    snapshot_id: int | None = None
    customer_name: str | None = None
    weld_node_count: int = 0
    breakdown_node_count: int = 0
    approved_count: int = 0
    ready: bool = False
    message: str = ""


class BomWeldingProcessBreakdownBatchDeleteResultVO(BaseModel):
    location: str
    vehicle_model: str
    bom_version: str
    deleted_count: int
    skipped_approved_count: int = 0
    message: str = ""


class BomWeldingProcessBreakdownBatchAuditResultVO(BaseModel):
    updated_count: int = 0
    skipped_count: int = 0
    location: str
    vehicle_model: str
    bom_version: str
