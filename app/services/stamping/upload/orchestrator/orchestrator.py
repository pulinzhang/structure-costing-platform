"""
指挥家：只挥棒，不拉琴。违反指挥家宪法（orchestrator-constitution）即不合格。

冲压工艺导入编排（预备 → 管线 → 落库）
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.dto.stamping_upload_dto import UploadResult
from app.schemas.vo.user_vo import UserVO
from app.services.stamping.upload.orchestrator.persist import persist_stamping_upload_result
from app.services.stamping.upload.orchestrator.pipeline import run_stamping_upload_pipeline
from app.services.stamping.upload.orchestrator.prep import prepare_stamping_upload_run
from app.services.stamping.upload.orchestrator.types import (
    ProgressCallback,
    StampingUploadExecuteArgs,
)


class StampingUploadOrchestrator:
    """冲压工艺写入指挥家。"""

    def execute(
        self,
        db: Session,
        args: StampingUploadExecuteArgs,
        current_user: UserVO,
        *,
        on_progress: ProgressCallback | None = None,
    ) -> UploadResult:
        prepared = prepare_stamping_upload_run(db, args, on_progress=on_progress)
        pipeline = run_stamping_upload_pipeline(
            db, prepared, current_user=current_user, on_progress=on_progress
        )
        return persist_stamping_upload_result(db, prepared, pipeline, on_progress=on_progress)
