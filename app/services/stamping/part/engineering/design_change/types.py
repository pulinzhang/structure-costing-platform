"""设计变更工艺零件的写入规格与当月命中行。"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.schemas.dto.stamping_upload_dto import PartData, ProcessData

MISS_SUPPLIER_UNKNOWN = "supplier_unknown"
MISS_NOT_AS_OF = "not_as_of"


@dataclass(slots=True)
class EngineeringChangeMaterialHistoryClone:
    """从旧零件 clone 出的一条材料变更历史，尚未挂新零件。"""

    source_id: int
    effective_year: int
    effective_month: int
    before_material: str
    after_material: str
    before_thickness: Decimal
    after_thickness: Decimal


@dataclass(slots=True)
class EngineeringChangeProcessPartSpec:
    """工程变更待插的一件：零件、工序、材料变更历史。"""

    part_data: PartData
    processes: list[ProcessData]
    material_changes: list[EngineeringChangeMaterialHistoryClone] = field(default_factory=list)
    expire_predecessor_id: int | None = None
    predecessor_expiry_year: int | None = None
    predecessor_expiry_month: int | None = None


@dataclass(slots=True)
class EngineeringChangeProcessPartResult:
    part_id: int
    predecessor_id: int | None = None
    material_history_ids: list[tuple[int, int]] = field(default_factory=list)


@dataclass(slots=True)
class EngineeringChangePartAsOfRow:
    id: int
    part_number: str
    stamping_supplier: str = ""
    location: str = ""
    vehicle_model: str = ""
    version: str = ""
    part_name: str = ""
    material: str | None = None
    thickness: Decimal | None = None
    effective_year: int = 0
    effective_month: int = 0
    expiry_year: int | None = None
    expiry_month: int | None = None
    is_tailor_welded: bool = False
    is_offal_nested: bool = False
    is_scrap_byproduct: bool = False
