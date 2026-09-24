"""材料变更管线：只调冲压写入历史，返回效果链接。不写本通道切点单，不 commit。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.vo.user_vo import UserVO
from app.services.engineering_change.material_change.upload.orchestrator.types import (
    MaterialChangeHistoryLink,
    MaterialChangePipeline,
    MaterialChangePrepared,
    ProgressCallback,
)
from app.services.stamping.part.engineering.service import (
    MaterialChangeHistorySpec,
    StampingEngineeringService,
)


def run_material_change_pipeline(
    db: Session,
    prepared: MaterialChangePrepared,
    current_user: UserVO,
    *,
    on_progress: ProgressCallback | None = None,
) -> MaterialChangePipeline:
    if on_progress:
        on_progress(55, "正在写入材料变更历史")
    history_ids = StampingEngineeringService().insert_material_changes(
        db,
        [
            MaterialChangeHistorySpec(
                part_id=gated.source_part_id,
                effective_year=gated.parsed.effective_year,
                effective_month=gated.parsed.effective_month,
                before_material=gated.parsed.before_material,
                after_material=gated.parsed.after_material,
                before_thickness=gated.before_thickness,
                after_thickness=gated.after_thickness,
            )
            for gated in prepared.rows
        ],
        current_user,
    )
    links = [
        MaterialChangeHistoryLink(
            row_index=index,
            before_id=gated.source_part_id,
            after_id=history_id,
        )
        for index, (gated, history_id) in enumerate(zip(prepared.rows, history_ids, strict=True))
    ]
    return MaterialChangePipeline(links=links)
