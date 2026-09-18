"""
指挥家：只挥棒，不拉琴。违反指挥家宪法（orchestrator-constitution）即不合格。

材料清单导入编排（预备 → 管线 → 落库）
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.vo.bom_vo import BomImportResultVO
from app.schemas.vo.user_vo import UserVO
from app.services.bom.upload.orchestrator.persist import persist_bom_upload_result
from app.services.bom.upload.orchestrator.pipeline import run_bom_upload_pipeline
from app.services.bom.upload.orchestrator.prep import prepare_bom_upload_run
from app.services.bom.upload.orchestrator.types import (
    BomUploadExecuteArgs,
    ProgressCallback,
)


class BomUploadOrchestrator:
    """材料清单写入指挥家。"""

    def execute(
        self,
        db: Session,
        args: BomUploadExecuteArgs,
        current_user: UserVO,
        *,
        on_progress: ProgressCallback | None = None,
    ) -> BomImportResultVO:
        prepared = prepare_bom_upload_run(db, args, on_progress=on_progress)
        pipeline = run_bom_upload_pipeline(
            db, prepared, current_user=current_user, on_progress=on_progress
        )
        return persist_bom_upload_result(db, prepared, pipeline, on_progress=on_progress)
