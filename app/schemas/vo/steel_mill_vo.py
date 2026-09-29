"""钢厂档案 VO。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.common.timezone import datetime_to_iso


class SteelMillVO(BaseModel):
    """钢厂一行。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    abbreviation: str
    full_name: str
    is_enabled: bool
    sort_order: int
    remark: str | None = None
    aliases: list[str] = Field(default_factory=list)
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)


class SteelMillChoiceVO(BaseModel):
    """下拉：只给已启用。"""

    id: int
    abbreviation: str
    full_name: str
