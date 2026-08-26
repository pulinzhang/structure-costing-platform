"""
BOM 焊接工艺拆解 DTO
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, TypedDict

from pydantic import BaseModel, Field, field_validator


class BomWeldingProcessBreakdownGenerateDTO(BaseModel):
    """从 BOM 生成焊接工艺拆解（按基地+项目+版本）"""

    location: str = Field(..., min_length=1, max_length=50, description="采购基地")
    vehicle_model: str = Field(..., min_length=1, max_length=50, description="项目/车型")
    bom_version: str = Field(..., min_length=1, max_length=20, description="材料清单版本")
    customer_name: str | None = Field(
        None,
        max_length=100,
        description="顾客名称（可选校验，例：奇瑞公司）",
    )


class BomWeldingProcessBreakdownScopeDTO(BaseModel):
    """范围：基地 + 项目 + 版本"""

    location: str = Field(..., min_length=1, max_length=50, description="采购基地")
    vehicle_model: str = Field(..., min_length=1, max_length=50, description="项目/车型")
    bom_version: str = Field(..., min_length=1, max_length=20, description="材料清单版本")


class BomWeldingProcessBreakdownBatchDeleteDTO(BomWeldingProcessBreakdownScopeDTO):
    """批量删除（仅删未审核）"""


class BomWeldingProcessBreakdownBatchApproveDTO(BomWeldingProcessBreakdownScopeDTO):
    """批量审核通过"""

    audit_remark: str = Field(..., min_length=1, description="审核意见（必填）")


class BomWeldingProcessBreakdownBatchReverseAuditDTO(BomWeldingProcessBreakdownScopeDTO):
    """批量反审核"""

    reverse_audit_remark: str = Field(..., min_length=1, description="反审核原因（必填）")


class BomWeldingProcessBreakdownLineUpdateDTO(BaseModel):
    """修改明细行（单件过程量）；主表须未审核。

    map_status / rollup / qty_check 由 Service 重算，禁止客户端直写。
    """

    process_token: str | None = Field(None, min_length=1, max_length=50)
    process_qty: Decimal | None = Field(None, ge=0)
    process_qty_unit: str | None = Field(None, min_length=1, max_length=20)
    process_qty_secondary: Decimal | None = Field(None, ge=0)
    process_qty_secondary_unit: str | None = Field(None, max_length=20)
    standard_process_name: str | None = Field(
        None, max_length=100, description="标准焊接工艺名称（焊接单价 item_name）"
    )

    @field_validator("process_qty", "process_qty_secondary", mode="before")
    @classmethod
    def _coerce_decimal(cls, value: Any) -> Decimal | None:
        if value is None or value == "":
            return None
        return value if isinstance(value, Decimal) else Decimal(str(value).strip())


class BomWeldingProcessBreakdownLineBatchItemDTO(BomWeldingProcessBreakdownLineUpdateDTO):
    """节点内批量保存的一行（须带 line_id）"""

    line_id: int = Field(..., ge=1, description="明细行 id")


class BomWeldingProcessBreakdownNodeLinesUpdateDTO(BaseModel):
    """一次保存某节点下全部工艺明细"""

    lines: list[BomWeldingProcessBreakdownLineBatchItemDTO] = Field(
        ..., min_length=1, description="待保存的明细行"
    )


class BomWeldingProcessBreakdownQuery(BaseModel):
    """分页查询"""

    location: str | None = Field(None, description="采购基地")
    customer_name: str | None = Field(None, description="顾客名称")
    vehicle_model: str | None = Field(None, description="项目/车型")
    bom_version: str | None = Field(None, description="材料清单版本")
    part_number: str | None = Field(None, description="零件号（模糊）")
    level: int | None = Field(None, description="层级 0/1")
    audit_status: str | None = Field(None, description="审核状态")
    parse_status: str | None = Field(None, description="解析状态")
    process_line_count_eq: int | None = Field(
        None,
        description="工艺明细行数精确匹配；传 0 筛无有效工艺（异常）",
    )
    page: int = Field(1, ge=1)
    size: int = Field(50, ge=1, le=500)


@dataclass(slots=True)
class BomWeldingProcessBreakdownNodeWrite:
    """焊接工艺拆解主表新建。"""

    location: str
    vehicle_model: str
    bom_version: str
    part_number: str
    level: int
    node_role: str
    assembly_qty: Decimal
    weld_info_raw: str
    parse_status: str
    process_line_count: int
    created_by: str
    updated_by: str
    customer_name: str | None = None
    snapshot_id: int | None = None
    source_node_id: int | None = None
    part_name: str | None = None
    parent_part_number: str | None = None
    parent_part_name: str | None = None
    supply_part_number: str | None = None
    supply_part_name: str | None = None
    assembly_qty_unit: str | None = None
    excel_row: int | None = None
    qa_note: str | None = None
    audit_status: str = "pending"


@dataclass(slots=True)
class BomWeldingProcessBreakdownLineWrite:
    """焊接工艺拆解明细新建。"""

    breakdown_node_id: int
    part_number: str
    line_no: int
    process_token: str
    process_qty: Decimal
    process_qty_unit: str
    created_by: str
    updated_by: str
    matched_span: str | None = None
    process_qty_secondary: Decimal | None = None
    process_qty_secondary_unit: str | None = None
    standard_process_name: str | None = None
    standard_process_unit: str | None = None
    map_status: str = "unmapped"
    rollup_flag: str = "own"
    child_fastener_qty_sum: Decimal | None = None
    qty_check_status: str = "skipped"
    qty_check_detail: str | None = None


class BomWeldingProcessBreakdownLinePatch(TypedDict, total=False):
    """焊接工艺拆解明细部分更新（含 Service 重算字段）。"""

    process_token: str | None
    process_qty: Decimal | None
    process_qty_unit: str | None
    process_qty_secondary: Decimal | None
    process_qty_secondary_unit: str | None
    standard_process_name: str | None
    standard_process_unit: str | None
    map_status: str
    updated_by: str


class BomWeldingProcessBreakdownNodePatch(TypedDict, total=False):
    """焊接工艺拆解主表部分更新。"""

    updated_by: str


@dataclass(slots=True)
class BomWeldingProcessBreakdownGenerateLogCreate:
    """焊接工艺拆解生成日志新建。"""

    calc_batch_id: str
    location: str
    vehicle_model: str
    bom_version: str
    status: str
    detail_text: str
    started_at: datetime
    customer_name: str | None = None
    snapshot_id: int | None = None
    node_count: int = 0
    line_count: int = 0
    finished_at: datetime | None = None
    operator_id: int | None = None
    operator_name: str | None = None
    created_by: str | None = None
    updated_by: str | None = None


class BomWeldingProcessBreakdownGenerateLogPatch(TypedDict, total=False):
    """焊接工艺拆解生成日志部分更新。"""

    status: str
    customer_name: str | None
    snapshot_id: int | None
    node_count: int
    line_count: int
    detail_text: str
    finished_at: datetime
    updated_by: str
