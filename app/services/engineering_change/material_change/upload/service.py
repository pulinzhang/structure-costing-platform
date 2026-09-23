"""材料变更上传 Service 门面。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO
from app.schemas.vo.user_vo import UserVO
from app.services.engineering_change.material_change.upload.start_upload import start_upload
from app.services.engineering_change.material_change.upload.template import (
    build_material_change_template,
)


class MaterialChangeUploadService:
    @staticmethod
    def build_template() -> tuple[bytes, str]:
        return build_material_change_template()

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
