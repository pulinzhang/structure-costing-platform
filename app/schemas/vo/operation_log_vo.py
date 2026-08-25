"""操作日志 VO。"""

from datetime import datetime

from pydantic import BaseModel, Field, field_serializer

from app.common.timezone import datetime_to_iso


class OperationLogVO(BaseModel):
    """单条操作日志。"""

    id: int
    user_id: int | None = None
    username: str | None = None
    operator_name: str | None = None
    method: str
    path: str
    module: str | None = None
    action: str
    summary: str
    status_code: int
    success: bool
    client_ip: str | None = None
    detail: str | None = None
    created_at: datetime | None = None

    @field_serializer("created_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)

    model_config = {"from_attributes": True}


class OperationLogFilterOptionsVO(BaseModel):
    """筛选下拉选项。"""

    modules: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    methods: list[str] = Field(default_factory=list)
