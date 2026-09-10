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
    ip_country: str | None = None
    ip_province: str | None = None
    ip_city: str | None = None
    detail: str | None = None
    permission_code: str | None = None
    created_at: datetime | None = None

    @field_serializer("created_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)

    model_config = {"from_attributes": True}


class OperationLogCatalogOptionVO(BaseModel):
    """权限目录筛选项。"""

    code: str
    label: str
    parent_code: str | None = None
    breadcrumb: str


class OperationLogFilterOptionsVO(BaseModel):
    """筛选下拉：来自 catalog.json，不是日志表 distinct。"""

    menus: list[OperationLogCatalogOptionVO] = Field(default_factory=list)
    operations: list[OperationLogCatalogOptionVO] = Field(default_factory=list)
