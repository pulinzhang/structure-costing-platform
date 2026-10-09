"""材料变更上传 Service 门面。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO
from app.schemas.vo.user_vo import UserVO
from app.services.engineering_change.material_change.upload.start_upload import start_upload
from app.services.engineering_change.material_change.upload.template import (
    MaterialChangeTemplateMeta,
    build_material_change_template,
)
from app.services.masterdata.vehicle_model.service import VehicleModelService


class MaterialChangeUploadService:
    @staticmethod
    def build_template(
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        effective_year: int,
        effective_month: int,
    ) -> tuple[bytes, str]:
        location, vehicle_model = VehicleModelService().require_introducible(
            db,
            location.strip(),
            vehicle_model.strip(),
            effective_year,
            effective_month,
        )
        meta = MaterialChangeTemplateMeta(
            location=location,
            vehicle_model=vehicle_model,
            change_version=f"MAT-{effective_year}{effective_month:02d}",
            period_label=f"{effective_year}年{effective_month:02d}月",
        )
        return build_material_change_template(meta)

    @staticmethod
    def start_upload(
        db: Session,
        *,
        file_content: bytes,
        filename: str,
        location: str,
        vehicle_model: str,
        effective_year: int,
        effective_month: int,
        current_user: UserVO,
    ) -> AsyncTaskAcceptedVO:
        return start_upload(
            db,
            file_content=file_content,
            filename=filename,
            location=location,
            vehicle_model=vehicle_model,
            effective_year=effective_year,
            effective_month=effective_month,
            current_user=current_user,
        )
