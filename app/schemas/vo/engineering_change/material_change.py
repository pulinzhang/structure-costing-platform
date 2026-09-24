"""材料变更 VO。"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_serializer

from app.common.timezone import datetime_to_iso


class MaterialChangeUploadListRowVO(BaseModel):
    """列表一行 = 变更单行。删除用 upload_log_id 整本回滚。无切点时零件列为空。"""

    order_id: int | None = None
    upload_log_id: int
    excel_row: int | None = None
    location: str
    vehicle_model: str
    stamping_supplier: str | None = None
    change_version: str | None = None
    effective_year: int
    effective_month: int
    part_number: str | None = None
    part_name: str | None = None
    before_material: str | None = None
    after_material: str | None = None
    before_thickness: Decimal | None = None
    after_thickness: Decimal | None = None
    interchangeability: str | None = None
    status: str
    original_filename: str
    message: str | None = None
    created_by: str | None = None
    created_at: datetime | None = None

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)


class MaterialChangeUploadResultVO(BaseModel):
    log_id: int
    order_ids: list[int] = Field(default_factory=list)
