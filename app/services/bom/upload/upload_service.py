"""材料清单上传 Service 门面（模板 + 入队入口转发）。"""

from __future__ import annotations

from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO
from app.schemas.vo.user_vo import UserVO
from app.services.bom.upload.start_upload import start_upload as start_upload_fn
from app.services.bom.upload.template_builder import build_bom_material_template


class BomUploadService:
    """Router 只依赖本类。"""

    @staticmethod
    def build_template() -> tuple[bytes, str]:
        return build_bom_material_template()

    @staticmethod
    def start_upload(
        *,
        file_content: bytes,
        filename: str,
        location: str,
        vehicle_model: str,
        current_user: UserVO,
    ) -> AsyncTaskAcceptedVO:
        return start_upload_fn(
            file_content=file_content,
            filename=filename,
            location=location,
            vehicle_model=vehicle_model,
            current_user=current_user,
        )
