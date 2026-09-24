"""材料变更指挥家：prepare → persist。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.vo.engineering_change.material_change import MaterialChangeUploadResultVO
from app.schemas.vo.user_vo import UserVO
from app.services.engineering_change.material_change.upload.orchestrator.persist import (
    mark_material_change_failed,
    persist_material_change_result,
)
from app.services.engineering_change.material_change.upload.orchestrator.prep import (
    prepare_material_change_run,
)
from app.services.engineering_change.material_change.upload.orchestrator.types import (
    MaterialChangeExecuteArgs,
    ProgressCallback,
)


class MaterialChangeOrchestrator:
    def execute(
        self,
        db: Session,
        args: MaterialChangeExecuteArgs,
        current_user: UserVO,
        *,
        on_progress: ProgressCallback | None = None,
    ) -> MaterialChangeUploadResultVO:
        prepared = prepare_material_change_run(db, args, on_progress=on_progress)
        return persist_material_change_result(db, prepared, current_user, on_progress=on_progress)

    def mark_log_failed(self, db: Session, log_id: int, message: str, current_user: UserVO) -> None:
        mark_material_change_failed(db, log_id, message, current_user)
