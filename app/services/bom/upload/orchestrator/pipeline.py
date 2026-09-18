"""材料清单管线：落盘与 flush 写库。禁止 commit。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.vo.user_vo import UserVO
from app.services.bom.upload.orchestrator.types import (
    PipelineBundle,
    PreparedBundle,
    ProgressCallback,
    report_progress,
)
from app.services.bom.upload.persist.files import save_excel_file, save_node_sketches
from app.services.bom.upload.persist.nodes import flush_bom_upload


def run_bom_upload_pipeline(
    db: Session,
    prepared: PreparedBundle,
    *,
    current_user: UserVO,
    on_progress: ProgressCallback | None = None,
) -> PipelineBundle:
    report_progress(on_progress, 50, "正在保存文件与简图...")
    relative_path = save_excel_file(
        file_content=prepared.file_content,
        filename=prepared.original_name,
        location=prepared.location,
        vehicle_model=prepared.vehicle_model,
        bom_version=prepared.bom_version,
    )
    saved_images = save_node_sketches(
        prepared.parse_result.nodes,
        location=prepared.location,
        vehicle_model=prepared.vehicle_model,
        bom_version=prepared.bom_version,
    )
    report_progress(on_progress, 70, "正在写入数据库...")
    snapshot, replaced = flush_bom_upload(
        db,
        parse_result=prepared.parse_result,
        location=prepared.location,
        vehicle_model=prepared.vehicle_model,
        bom_version=prepared.bom_version,
        original_name=prepared.original_name,
        relative_path=relative_path,
        file_hash=prepared.file_hash,
        saved_images=saved_images,
        file_l0_numbers=prepared.file_l0_numbers,
        current_user=current_user,
    )
    return PipelineBundle(
        relative_path=relative_path,
        saved_images=saved_images,
        snapshot=snapshot,
        replaced=replaced,
    )
