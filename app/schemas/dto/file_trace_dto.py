"""文件溯源 DTO。"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class UploadFileListQuery(BaseModel):
    """溯源列表查询。"""

    skip: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)
    file_category: str | None = None
    location: str | None = None
    year: int | None = None
    month: int | None = Field(None, ge=1, le=12)
    vehicle_model: str | None = None
    filename: str | None = None
    created_by: str | None = None
    uploaded_from: date | None = None
    uploaded_to: date | None = None
    status: str | None = "active"
