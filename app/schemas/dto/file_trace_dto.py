"""文件溯源 DTO。"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from app.common.period import (
    MONTH_MAX,
    MONTH_MIN,
)


class UploadFileListQuery(BaseModel):
    """溯源列表查询。"""

    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)
    file_category: str | None = None
    location: str | None = None
    year: int | None = None
    month: int | None = Field(None, ge=MONTH_MIN, le=MONTH_MAX)
    vehicle_model: str | None = None
    filename: str | None = None
    created_by: str | None = None
    uploaded_from: date | None = None
    uploaded_to: date | None = None
    status: str | None = "active"
