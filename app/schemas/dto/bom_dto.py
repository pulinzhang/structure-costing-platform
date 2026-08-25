"""BOM DTO - 请求参数 / 仓库写入载荷"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.common.money import Q4, optional_quantize_money


class BomSnapshotCreate(BaseModel):
    """创建 BOM 清单版本"""

    location: str = Field(..., min_length=1, max_length=50, description="采购基地")
    vehicle_model: str = Field(..., min_length=1, max_length=50, description="车型")
    bom_version: str = Field(..., min_length=1, max_length=20, description="清单版本")
    product_category: str | None = Field(None, max_length=50, description="产品类别")
    customer_name: str | None = Field(None, max_length=100, description="顾客名称")
    stage: str = Field("initial", description="阶段：initial / mass")
    doc_no: str | None = Field(None, max_length=50, description="单据编号")
    prepare_dept: str | None = Field(None, max_length=100, description="编制部门")
    doc_date: date | None = Field(None, description="编制日期")
    revision_date: date | None = Field(None, description="修订日期")
    title: str | None = Field(None, max_length=200, description="清单标题")
    source_filename: str = Field(..., min_length=1, max_length=255, description="来源文件名")
    source_file_hash: str | None = Field(None, max_length=64, description="源文件哈希")
    status: str = Field("active", description="状态：draft / active / archived")
    remark: str | None = Field(None, description="备注")


class BomSnapshotQuery(BaseModel):
    """BOM 清单分页查询"""

    location: str | None = Field(None, description="采购基地")
    vehicle_model: str | None = Field(None, description="车型")
    bom_version: str | None = Field(None, description="材料清单版本")
    status: str | None = Field(None, description="状态")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=200, description="每页条数")


class BomNodeCreate(BaseModel):
    """创建 BOM 树节点（最小手工录入）"""

    parent_id: int | None = Field(None, description="父节点 ID；L0 为空")
    level: int = Field(..., ge=0, le=2, description="层级 0/1/2")
    sort_no: int = Field(0, ge=0, description="同级排序")
    seq_no: int | None = Field(None, description="表头序号")
    internal_number: str | None = Field(None, max_length=50)
    part_number: str = Field(..., min_length=1, max_length=50)
    part_name: str | None = Field(None, max_length=200)
    qty: Decimal | None = Field(None, description="相对父件用量")
    qty_unit: str = Field("pcs", max_length=20)
    qty_text: str | None = Field(None, max_length=50)
    node_role: str = Field(
        ...,
        description="supply / structure / make / buy / consumable（冲焊件域，无电子/电气）",
    )
    is_supply_unit: bool = Field(False, description="是否供货总成")
    material: str | None = Field(None, max_length=50)
    thickness_mm: Decimal | None = None
    thickness_text: str | None = Field(None, max_length=50)
    material_mill: str | None = Field(None, max_length=100)
    part_weight: Decimal | None = None
    gauge_developed: str | None = Field(None, max_length=10)
    weld_info: str | None = None
    remark: str | None = None
    sketch_url: str | None = Field(None, max_length=500)

    @field_validator("qty", "thickness_mm", "part_weight", mode="before")
    @classmethod
    def _coerce_q4(cls, value: Any) -> Decimal | None:
        return optional_quantize_money(value, Q4, allow_negative=True)


@dataclass(slots=True)
class BomSnapshotWrite:
    """BOM 清单版本落库（HTTP 创建 + Excel 导入共用）。"""

    location: str
    vehicle_model: str
    bom_version: str
    source_filename: str
    created_by: str
    updated_by: str
    product_category: str | None = None
    customer_name: str | None = None
    stage: str = "initial"
    doc_no: str | None = None
    prepare_dept: str | None = None
    doc_date: date | None = None
    revision_date: date | None = None
    title: str | None = None
    source_sheet_name: str | None = None
    source_file_path: str | None = None
    source_file_hash: str | None = None
    status: str = "active"
    remark: str | None = None


@dataclass(slots=True)
class BomNodeWrite:
    """BOM 树节点落库（HTTP 创建 + Excel 导入共用）。"""

    snapshot_id: int
    level: int
    part_number: str
    node_role: str
    created_by: str
    updated_by: str
    parent_id: int | None = None
    sort_no: int = 0
    seq_no: int | None = None
    internal_number: str | None = None
    part_name: str | None = None
    qty: Decimal | None = None
    qty_unit: str = "pcs"
    qty_text: str | None = None
    is_supply_unit: bool = False
    material: str | None = None
    thickness_mm: Decimal | None = None
    thickness_text: str | None = None
    material_mill: str | None = None
    part_weight: Decimal | None = None
    gauge_developed: str | None = None
    weld_info: str | None = None
    remark: str | None = None
    sketch_url: str | None = None
    excel_filename: str | None = None
    excel_sheet_name: str | None = None
    excel_row: int | None = None
    excel_part_col: int | None = None
