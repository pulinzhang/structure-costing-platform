"""材料清单落库：commit 并组装导入结果。禁止再插节点。"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.schemas.vo.bom_vo import BomImportResultVO, BomSnapshotVO
from app.services.bom.bom.upload.orchestrator.types import (
    PipelineBundle,
    PreparedBundle,
    ProgressCallback,
    report_progress,
)

logger = logging.getLogger("service.bom.upload")


def persist_bom_upload_result(
    db: Session,
    prepared: PreparedBundle,
    pipeline: PipelineBundle,
    *,
    on_progress: ProgressCallback | None = None,
) -> BomImportResultVO:
    try:
        db.commit()
        db.refresh(pipeline.snapshot)
    except Exception:
        db.rollback()
        logger.exception("材料清单落库失败")
        raise

    report_progress(on_progress, 100, "写入完成")
    vo = BomSnapshotVO.model_validate(pipeline.snapshot)
    vo.node_count = len(prepared.parse_result.nodes)
    image_count = len(pipeline.saved_images)
    message = (
        f"{'再导更新' if pipeline.replaced else '导入'}成功："
        f"{prepared.vehicle_model} / {prepared.bom_version} / {prepared.location}，"
        f"{len(prepared.parse_result.nodes)} 个节点，{image_count} 张简图"
    )
    logger.info("%s file=%s hash=%s", message, pipeline.relative_path, prepared.file_hash[:12])
    return BomImportResultVO(
        snapshot=vo,
        node_count=len(prepared.parse_result.nodes),
        image_count=image_count,
        replaced=pipeline.replaced,
        message=message,
    )
