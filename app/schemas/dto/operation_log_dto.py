"""操作日志 DTO。"""

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, Field


@dataclass(slots=True)
class OperationLogCreate:
    """Repository 写入操作日志。"""

    method: str
    path: str
    action: str
    summary: str
    status_code: int = 200
    success: bool = True
    user_id: int | None = None
    username: str | None = None
    operator_name: str | None = None
    module: str | None = None
    client_ip: str | None = None
    detail: str | None = None


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
