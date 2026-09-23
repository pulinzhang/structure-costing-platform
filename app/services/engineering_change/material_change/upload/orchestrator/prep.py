"""先验表再对库。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.exceptions.base import NotFoundException
from app.repositories.engineering_change.material_change.upload_log_repository import (
    MaterialChangeUploadLogRepository,
)
from app.services.engineering_change.material_change.upload.gates import gate_workbook
from app.services.engineering_change.material_change.upload.orchestrator.types import (
    MaterialChangeExecuteArgs,
    MaterialChangePrepared,
    ProgressCallback,
)


def prepare_material_change_run(
    db: Session,
    args: MaterialChangeExecuteArgs,
    *,
    on_progress: ProgressCallback | None = None,
) -> MaterialChangePrepared:
    if on_progress:
        on_progress(10, "正在核验工程变更单（材质）")
    log_row = MaterialChangeUploadLogRepository().get_by_id(db, args.log_id)
    if log_row is None:
        raise NotFoundException("材料变更上传记录不存在")
    rows = gate_workbook(
        db,
        file_content=args.file_content,
        page_location=args.location,
        page_vehicle_model=args.vehicle_model,
        page_year=args.effective_year,
        page_month=args.effective_month,
        log_id=args.log_id,
    )
    return MaterialChangePrepared(log_id=args.log_id, rows=rows)
