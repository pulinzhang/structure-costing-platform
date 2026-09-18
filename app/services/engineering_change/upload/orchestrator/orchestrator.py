"""
指挥家：只挥棒，不拉琴。违反指挥家宪法（orchestrator-constitution）即不合格。

工程变更合册编排（预备 → 管线 → 落库）
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.vo.engineering_change_vo import EngineeringChangeUploadResultVO
from app.schemas.vo.user_vo import UserVO
from app.services.engineering_change.upload.orchestrator.persist import (
    mark_engineering_change_failed,
    persist_engineering_change_result,
)
from app.services.engineering_change.upload.orchestrator.pipeline import (
    run_engineering_change_pipeline,
)
from app.services.engineering_change.upload.orchestrator.prep import (
    prepare_engineering_change_run,
)
from app.services.engineering_change.upload.orchestrator.types import (
    EngineeringChangeExecuteArgs,
    ProgressCallback,
)


class EngineeringChangeOrchestrator:
    """合册写入指挥家。"""

    def execute(
        self,
        db: Session,
        args: EngineeringChangeExecuteArgs,
        current_user: UserVO,
        *,
        on_progress: ProgressCallback | None = None,
    ) -> EngineeringChangeUploadResultVO:
        prepared = prepare_engineering_change_run(db, args, on_progress=on_progress)
        pipeline = run_engineering_change_pipeline(
            db, prepared, current_user=current_user, on_progress=on_progress
        )
        return persist_engineering_change_result(
            db,
            prepared,
            pipeline,
            current_user=current_user,
            on_progress=on_progress,
        )

    def mark_log_failed(self, db: Session, log_id: int, message: str, current_user: UserVO) -> None:
        mark_engineering_change_failed(db, log_id, message, current_user)
