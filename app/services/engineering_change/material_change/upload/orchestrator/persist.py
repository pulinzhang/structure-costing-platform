"""落本通道切点单、链接、成功头。历史已由管线写入冲压，这里不再插。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.audit import audit_create, audit_update
from app.exceptions.base import BusinessException, NotFoundException
from app.repositories.engineering_change.material_change.effect_link_repository import (
    MaterialChangeEffectLinkInsert,
    MaterialChangeEffectLinkRepository,
)
from app.repositories.engineering_change.material_change.order_repository import (
    MaterialChangeOrderInsert,
    MaterialChangeOrderRepository,
)
from app.repositories.engineering_change.material_change.upload_log_repository import (
    MaterialChangeUploadLogRepository,
    MaterialChangeUploadLogUpdate,
)
from app.schemas.vo.engineering_change.material_change import MaterialChangeUploadResultVO
from app.schemas.vo.user_vo import UserVO
from app.services.engineering_change.material_change.upload.orchestrator.types import (
    MaterialChangePipeline,
    MaterialChangePrepared,
    ProgressCallback,
)

_EFFECT_KIND = "material_cutover"
_log_repo = MaterialChangeUploadLogRepository()
_order_repo = MaterialChangeOrderRepository()
_link_repo = MaterialChangeEffectLinkRepository()


def persist_material_change_result(
    db: Session,
    prepared: MaterialChangePrepared,
    pipeline: MaterialChangePipeline,
    current_user: UserVO,
    *,
    on_progress: ProgressCallback | None = None,
) -> MaterialChangeUploadResultVO:
    if on_progress:
        on_progress(80, "正在写入切点")
    log_row = _log_repo.get_by_id(db, prepared.log_id)
    if log_row is None:
        raise NotFoundException("材料变更上传记录不存在")
    if len(pipeline.links) != len(prepared.rows):
        raise BusinessException("这次导入对不上材料变更单的行，没有保存成功。请再传一次。")
    audit = audit_create(current_user)
    order_ids: list[int] = []
    sample = prepared.rows[0].parsed
    for link in pipeline.links:
        gated = prepared.rows[link.row_index]
        parsed = gated.parsed
        order = _order_repo.create(
            db,
            MaterialChangeOrderInsert(
                upload_log_id=log_row.id,
                upload_file_id=log_row.upload_file_id,
                change_version=parsed.change_version,
                excel_row=parsed.excel_row,
                location=parsed.location,
                stamping_supplier=parsed.stamping_supplier,
                vehicle_model=parsed.vehicle_model,
                effective_year=parsed.effective_year,
                effective_month=parsed.effective_month,
                part_number=parsed.part_number,
                before_material=parsed.before_material,
                after_material=parsed.after_material,
                before_thickness=gated.before_thickness,
                after_thickness=gated.after_thickness,
                interchangeability=parsed.interchangeability,
                part_name=parsed.part_name,
                source_part_id=gated.source_part_id,
                created_by=audit["created_by"],
                updated_by=audit["updated_by"],
            ),
        )
        _link_repo.create(
            db,
            MaterialChangeEffectLinkInsert(
                upload_log_id=log_row.id,
                order_id=order.id,
                effect_kind=_EFFECT_KIND,
                before_id=link.before_id,
                after_id=link.after_id,
            ),
        )
        order_ids.append(order.id)
    _log_repo.update(
        db,
        log_row,
        MaterialChangeUploadLogUpdate(
            status="success",
            message=f"材料变更成功：{len(order_ids)} 行切点",
            stamping_supplier=sample.stamping_supplier,
            change_version=sample.change_version,
            part_count=len(order_ids),
            updated_by=audit_update(current_user)["updated_by"],
        ),
    )
    db.commit()
    if on_progress:
        on_progress(100, "材料变更导入完成")
    return MaterialChangeUploadResultVO(log_id=log_row.id, order_ids=order_ids)


def mark_material_change_failed(
    db: Session, log_id: int, message: str, current_user: UserVO
) -> None:
    log_row = _log_repo.get_by_id(db, log_id)
    if log_row is None:
        return
    _log_repo.update(
        db,
        log_row,
        MaterialChangeUploadLogUpdate(
            status="failed",
            message=message,
            updated_by=audit_update(current_user)["updated_by"],
        ),
    )
    db.commit()
