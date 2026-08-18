"""操作日志 DTO。"""

from datetime import datetime

from pydantic import BaseModel, Field


class OperationLogQuery(BaseModel):
    """操作日志分页查询。"""

    username: str | None = None
    module: str | None = None
    action: str | None = None
    method: str | None = None
    success: bool | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=200)
