"""供应商主数据 VO。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_serializer

from app.common.timezone import datetime_to_iso


class SupplierChoiceVO(BaseModel):
    """下游下拉：展示缩写（工商名称），value 为工商名称。"""

    full_name: str
    abbreviation: str


class SupplierVO(BaseModel):
    """供应商一行（含别名列表）。"""

    model_config = ConfigDict(from_attributes=True)

    full_name: str
    abbreviation: str
    erp_code: str
    is_enabled: bool
    sort_order: int
    aliases: list[str] = []
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)


class SupplierUploadResultVO(BaseModel):
    """同步上传结果。"""

    created_count: int
    skipped_count: int
