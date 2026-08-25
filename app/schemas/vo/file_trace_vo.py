"""文件溯源 VO。"""

from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import BaseModel, field_serializer, model_validator

from app.common.timezone import datetime_to_iso
from app.services.file_trace.categories import category_label


def _format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.2f} MB"


def _build_scope_text(
    *,
    file_category: str,
    location: str | None,
    year: int | None,
    month: int | None,
    vehicle_model: str | None,
    bom_version: str | None,
    process_version: str | None,
    stamping_supplier: str | None,
) -> str:
    parts: list[str] = [category_label(file_category)]
    if location:
        parts.append(location)
    if year is not None:
        month_part = f"{year}"
        if month is not None:
            month_part += f"-{month:02d}"
        parts.append(month_part)
    if vehicle_model:
        parts.append(vehicle_model)
    if bom_version:
        parts.append(bom_version)
    if process_version:
        parts.append(process_version)
    if stamping_supplier:
        parts.append(stamping_supplier)
    return " · ".join(parts)


class UploadFileVO(BaseModel):
    """溯源文件列表 / 详情。"""

    model_config = {"from_attributes": True}

    id: int
    file_category: str
    original_filename: str
    file_size: int
    extension: str
    location: str | None = None
    year: int | None = None
    month: int | None = None
    vehicle_model: str | None = None
    bom_version: str | None = None
    process_version: str | None = None
    stamping_supplier: str | None = None
    file_hash: str
    status: str
    created_at: datetime
    created_by: str | None = None
    file_category_label: str = ""
    file_size_text: str = ""
    scope_text: str = ""

    @model_validator(mode="after")
    def populate_display_fields(self) -> Self:
        return self.model_copy(
            update={
                "file_category_label": category_label(self.file_category),
                "file_size_text": _format_file_size(self.file_size),
                "scope_text": _build_scope_text(
                    file_category=self.file_category,
                    location=self.location,
                    year=self.year,
                    month=self.month,
                    vehicle_model=self.vehicle_model,
                    bom_version=self.bom_version,
                    process_version=self.process_version,
                    stamping_supplier=self.stamping_supplier,
                ),
            }
        )

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str | None:
        return datetime_to_iso(value)


class UploadFileFiltersVO(BaseModel):
    """筛选项（仅用户可见分类）。"""

    allowed_categories: list[str]
    category_labels: dict[str, str]
    locations: list[str]
    years: list[int]
    months: list[int]
    vehicle_models: list[str]
    creators: list[str]
