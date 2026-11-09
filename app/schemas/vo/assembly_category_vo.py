"""总成分类 VO。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_serializer

from app.common.timezone import datetime_to_iso


class AssemblyCategoryVO(BaseModel):
    """总成分类一行。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    sort_order: int
    is_enabled: bool
    remark: str | None = None
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)
