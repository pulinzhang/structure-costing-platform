"""牌号分类档案 VO。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_serializer

from app.common.timezone import datetime_to_iso


class SteelGradeCategoryVO(BaseModel):
    """牌号分类一行。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    category_name: str
    category_seq: int
    grade: str
    remark: str | None = None
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)


class SteelGradeCategoryOptionVO(BaseModel):
    """下拉用的写死大类。"""

    category_seq: int
    category_name: str
