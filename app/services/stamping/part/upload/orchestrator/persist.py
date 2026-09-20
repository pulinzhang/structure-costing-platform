"""冲压工艺落库：commit 并组装导入结果。禁止再插零件。"""

from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions.base import BusinessException
from app.schemas.dto.stamping_upload_dto import UploadResult
from app.services.stamping.part.upload.orchestrator.types import (
    PipelineBundle,
    PreparedBundle,
    ProgressCallback,
    report_progress,
)

logger = logging.getLogger("service.stamping_upload")


def persist_stamping_upload_result(
    db: Session,
    prepared: PreparedBundle,
    pipeline: PipelineBundle,
    *,
    on_progress: ProgressCallback | None = None,
) -> UploadResult:
    report_progress(on_progress, 95, "正在提交事务...")
    result = UploadResult(
        filename=prepared.filename,
        new_filename=pipeline.file_info.new_filename,
        size=len(prepared.file_content),
        path=pipeline.file_info.file_path,
        location=prepared.location,
        vehicle_model=prepared.vehicle_model,
        version=prepared.version,
        parts_count=len(pipeline.part_map),
        processes_count=pipeline.process_count,
        images_count=pipeline.saved_images,
        tailor_weld_assembly_count=pipeline.tailor_assemblies,
        tailor_weld_blank_count=pipeline.tailor_blanks,
        warnings=pipeline.warnings,
        parse_time_ms=pipeline.parse_time_ms,
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise BusinessException("该范围零件号冲突，请重试覆盖上传") from None
    except Exception:
        db.rollback()
        logger.exception("冲压工艺上传落库失败")
        raise
    return result
