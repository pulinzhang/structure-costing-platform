"""基地主数据 VO。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_serializer

from app.common.timezone import datetime_to_iso


class LocationVO(BaseModel):
    """基地一行（含别名列表）。"""

    model_config = ConfigDict(from_attributes=True)

    location: str
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
