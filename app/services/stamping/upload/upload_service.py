"""冲压工艺上传 Service 门面（模板 + 入队入口转发）。"""

from __future__ import annotations

from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO
from app.schemas.vo.user_vo import UserVO
from app.services.stamping.upload.start_upload import start_upload as start_upload_fn
from app.services.stamping.upload.template_builder import build_stamping_process_template


class StampingUploadService:
    """Router 只依赖本类。"""

    @staticmethod
    def build_template() -> tuple[bytes, str]:
        return build_stamping_process_template()

    @staticmethod
    def start_upload(
        *,
        file_content: bytes,
        filename: str,
        current_user: UserVO,
    ) -> AsyncTaskAcceptedVO:
        return start_upload_fn(
            file_content=file_content,
            filename=filename,
            current_user=current_user,
        )
