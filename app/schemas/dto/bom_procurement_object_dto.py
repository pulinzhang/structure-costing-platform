"""采购对象清单 DTO。"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class BomProcurementObjectScopeDTO(BaseModel):
    """范围：基地 + 车型 + BOM 版本。"""

    location: str = Field(..., min_length=1, max_length=50)
    vehicle_model: str = Field(..., min_length=1, max_length=50)
    bom_version: str = Field(..., min_length=1, max_length=20)


class BomProcurementObjectGenerateDTO(BomProcurementObjectScopeDTO):
    """生成采购对象清单。"""


class BomProcurementObjectBatchDeleteDTO(BomProcurementObjectScopeDTO):
    """按范围批量删除待审采购对象。"""


class BomProcurementObjectBatchApproveDTO(BomProcurementObjectScopeDTO):
    """按范围批量审核。"""

    audit_remark: str = Field(..., min_length=1, description="审核意见（必填）")


class BomProcurementObjectBatchReverseAuditDTO(BomProcurementObjectScopeDTO):
    """按范围批量反审核。"""

    reverse_audit_remark: str = Field(..., min_length=1, description="反审核原因（必填）")


class BomProcurementObjectConfirmDTO(BaseModel):
    """单条确认三态。"""

    confirm_status: str = Field(..., min_length=1, max_length=20)
    confirm_remark: str | None = Field(None, max_length=500)


class BomProcurementObjectSupplierDTO(BaseModel):
    """指定或清空合同对方。空串由 Service 收成 NULL。"""

    supplier_name: str | None = Field(None, max_length=100)


class BomProcurementObjectSupplierChoiceQuery(BaseModel):
    """确认弹框：已启用供应商分页检索，禁止一次拉全量。"""

    q: str | None = Field(None, description="关键字：缩写 / 全称 / ERP / 别名")
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=50)

    @field_validator("q", mode="before")
    @classmethod
    def strip_keyword(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text if text else None


class BomProcurementObjectQuery(BaseModel):
    """列表查询。"""

    location: str | None = Field(None, max_length=50)
    vehicle_model: str | None = Field(None, max_length=50)
    bom_version: str | None = Field(None, max_length=20)
    section: str | None = Field(None, max_length=20)
    object_kind: str | None = Field(None, max_length=30)
    confirm_status: str | None = Field(None, max_length=20)
    audit_status: str | None = Field(None, max_length=20)
    part_number: str | None = Field(None, max_length=50)
    l0_part_number: str | None = Field(None, max_length=50)
    excel_row: int | None = Field(None, ge=1)
    supplier_name: str | None = Field(None, max_length=100)
    has_supplier: bool | None = Field(None, description="True=已指定对方；False=未指定")
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=200)


class BomProcurementObjectPrepQuery(BaseModel):
    """生成页就绪统计。"""

    location: str | None = Field(None, max_length=50)
    vehicle_model: str | None = Field(None, max_length=50)
    bom_version: str | None = Field(None, max_length=20)


class BomProcurementObjectGenerateLogQuery(BaseModel):
    """生成历史分页。"""

    location: str | None = Field(None, max_length=50)
    vehicle_model: str | None = Field(None, max_length=50)
    bom_version: str | None = Field(None, max_length=20)
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)


@dataclass(slots=True)
class BomProcurementObjectListWrite:
    snapshot_id: int
    location: str
    vehicle_model: str
    bom_version: str
    source_filename: str
    qa_passed: bool
    qa_error_text: str | None
    l0_count: int
    l0_with_children_count: int
    l2_count: int
    subassembly_child_sum: int
    object_l0_degenerate_count: int
    object_l1_subassembly_count: int
    object_l1_stamping_count: int
    other_leaf_count: int
    anomaly_count: int
    generated_at: datetime
    generated_by: str | None
    created_by: str | None
    updated_by: str | None


@dataclass(slots=True)
class BomProcurementObjectWrite:
    list_id: int
    section: str
    object_kind: str | None
    degenerate_subtype: str | None
    source_node_id: int
    part_number: str
    part_name: str | None
    internal_number: str | None
    level: int
    node_role: str
    qty: Decimal | None
    qty_unit: str
    l0_part_number: str
    l0_part_name: str | None
    parent_part_number: str | None
    parent_part_name: str | None
    excel_filename: str | None
    excel_sheet_name: str | None
    excel_row: int | None
    child_count: int
    weld_info: str | None
    remark: str | None
    has_outsource_remark: bool
    material: str | None
    thickness_text: str | None
    material_mill: str | None
    data_gap: str | None
    alert_code: str | None
    confirm_status: str
    confirmed_by: str | None
    confirmed_at: datetime | None
    confirm_remark: str | None
    supplier_name: str | None
    audit_status: str
    created_by: str | None
    updated_by: str | None


@dataclass(slots=True)
class BomProcurementObjectGenerateLogWrite:
    calc_batch_id: str
    location: str
    vehicle_model: str
    bom_version: str
    snapshot_id: int | None
    status: str
    node_count: int
    object_count: int
    other_leaf_count: int
    anomaly_count: int
    qa_passed: bool
    detail_text: str
    started_at: datetime
    finished_at: datetime | None
    operator_id: int | None
    operator_name: str | None
    created_by: str | None
    updated_by: str | None
