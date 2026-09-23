"""材料变更管线：门禁已过，切点原样交给 persist。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.engineering_change.material_change.upload.orchestrator.types import (
    MaterialChangePrepared,
    ProgressCallback,
)


def run_material_change_pipeline(
    db: Session,
    prepared: MaterialChangePrepared,
    *,
    on_progress: ProgressCallback | None = None,
) -> MaterialChangePrepared:
    _ = db
    if on_progress:
        on_progress(55, "正在准备切点")
    return prepared
