"""冲压零件：增删改、利废纠错、工序系数。"""

from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import audit_create, display_name
from app.exceptions import BusinessException, NotFoundException
from app.models.stamping import StampingPart
from app.repositories.stamping.stamping_repository import (
    StampingPartRepository,
    StampingProcessRepository,
)
from app.schemas.dto.stamping_part_dto import (
    StampingPartBatchDeleteDTO,
    StampingPartOffalUpdateDTO,
    StampingProcessItemUpdate,
    StampingProcessUpdate,
)
from app.schemas.dto.stamping_upload_dto import (
    PartData,
    StampingPartPatch,
    StampingProcessPatch,
)
from app.schemas.vo.stamping_vo import (
    StampingPartBatchDeleteResultVO,
    StampingPartResponse,
    StampingProcessResponse,
)
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.steel_grade_category import SteelGradeCategoryService
from app.services.masterdata.supplier import SupplierService

logger = logging.getLogger("service.stamping")


def delete_part(repository: StampingPartRepository, db: Session, part_id: int) -> None:
    """删除零件（硬删除，不写审计字段）。"""
    try:
        deleted = repository.delete(db, part_id)
        if not deleted:
            raise NotFoundException(f"零件不存在: id={part_id}")
        db.commit()
    except IntegrityError:
        db.rollback()
        raise BusinessException("仍被引用，不能删除") from None


def create_part(
    repository: StampingPartRepository,
    db: Session,
    part_data: PartData,
    current_user: UserVO,
) -> StampingPart:
    audit = audit_create(current_user)
    part_data.created_by = audit["created_by"]
    part_data.updated_by = audit["updated_by"]
    part = repository.create(db, part_data)
    db.commit()
    db.refresh(part)
    return part


def bulk_create_parts(
    repository: StampingPartRepository,
    db: Session,
    parts_data: list[PartData],
    current_user: UserVO,
) -> list[StampingPart]:
    audit = audit_create(current_user)
    grades = SteelGradeCategoryService().bind_stored_grades(
        db, [row.material for row in parts_data]
    )
    for row, grade in zip(parts_data, grades, strict=True):
        row.material = grade
        row.created_by = audit["created_by"]
        row.updated_by = audit["updated_by"]
    parts = repository.bulk_create(db, parts_data)
    db.commit()
    return parts


def update_part(
    repository: StampingPartRepository,
    db: Session,
    part_id: int,
    update_data: StampingPartPatch,
    current_user: UserVO,
) -> StampingPart | None:
    payload: StampingPartPatch = {**update_data}
    if "material" in payload:
        payload["material"] = SteelGradeCategoryService().bind_stored_grade(
            db, payload.get("material")
        )
    payload["updated_by"] = display_name(current_user)
    part = repository.update(db, part_id, payload)
    if part is not None:
        db.commit()
        db.refresh(part)
    return part


def update_offal(
    repository: StampingPartRepository,
    db: Session,
    part_id: int,
    dto: StampingPartOffalUpdateDTO,
    current_user: UserVO,
) -> StampingPartResponse:
    """零件详情纠错：是否利废、利用哪类废料。关开关时清空废料来源。"""
    source = None if not dto.is_offal_nested else dto.offal_source
    payload: StampingPartPatch = {
        "is_offal_nested": dto.is_offal_nested,
        "offal_source": source,
        "updated_by": display_name(current_user),
    }
    part = repository.update(db, part_id, payload)
    if not part:
        raise NotFoundException(f"零件不存在: id={part_id}")
    db.commit()
    db.refresh(part)
    return StampingPartResponse.model_validate(part)


def batch_delete_parts(
    repository: StampingPartRepository,
    db: Session,
    dto: StampingPartBatchDeleteDTO,
) -> StampingPartBatchDeleteResultVO:
    """按基地 + 车型 + 版本批量删除零件；工厂可选。"""
    location = dto.location.strip()
    vehicle_model = dto.vehicle_model.strip()
    version = dto.version.strip()
    supplier = (dto.stamping_supplier or "").strip() or None
    if not location or not vehicle_model or not version:
        raise BusinessException("基地、车型和版本不能为空")

    supplier_names = SupplierService().names_for_query(db, supplier)
    if supplier and supplier_names is not None and not supplier_names:
        raise BusinessException("没有该供应商，请到供应商一览手工增加或上传（#/supplier-list）")

    try:
        deleted = repository.delete_by_scope(
            db,
            location=location,
            stamping_suppliers=supplier_names,
            vehicle_model=vehicle_model,
            version=version,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise BusinessException("仍被引用，不能删除") from None
    return StampingPartBatchDeleteResultVO(
        location=location,
        stamping_supplier=supplier,
        vehicle_model=vehicle_model,
        version=version,
        deleted_count=deleted,
    )


def update_process(
    db: Session,
    process_id: int,
    dto: StampingProcessUpdate,
    current_user: UserVO,
) -> StampingProcessResponse:
    """更新单个工序"""
    process_repo = StampingProcessRepository()
    payload: StampingProcessPatch = {
        "updated_by": display_name(current_user),
    }
    if "cost_ratio" in dto.model_fields_set and dto.cost_ratio is not None:
        payload["cost_ratio"] = dto.cost_ratio
    if "remark" in dto.model_fields_set:
        payload["remark"] = dto.remark
    if len(payload) == 1:
        logger.warning("process_id=%s 的更新字段为空", process_id)
    process = process_repo.update(db, process_id, payload)
    if not process:
        raise NotFoundException(f"工序不存在: id={process_id}")
    db.commit()
    db.refresh(process)
    return StampingProcessResponse.model_validate(process)


def batch_update_processes(
    db: Session,
    items: list[StampingProcessItemUpdate],
    current_user: UserVO,
) -> int:
    """批量更新工序成本系数"""
    operator_name = display_name(current_user)
    process_repo = StampingProcessRepository()
    count = 0
    for item in items:
        payload: StampingProcessPatch = {
            "updated_by": operator_name,
        }
        if "cost_ratio" in item.model_fields_set and item.cost_ratio is not None:
            payload["cost_ratio"] = item.cost_ratio
        if "remark" in item.model_fields_set:
            payload["remark"] = item.remark
        if len(payload) == 1:
            logger.warning("process_id=%s 的 update_data 为空，跳过", item.id)
            continue
        if process_repo.update(db, item.id, payload):
            count += 1
    db.commit()
    logger.info("batch_update_processes 完成，更新了 %s 条", count)
    return count
