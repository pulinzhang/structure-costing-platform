"""写入 clone 出的三样：零件一行、每一道工序、每一条材料变更历史。有旧号时停掉旧零件，并 clone 拼焊子片。只 flush。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.audit import audit_create
from app.exceptions.base import BusinessException, NotFoundException
from app.models.stamping import StampingPart
from app.repositories.stamping.part.process import StampingProcessRepository
from app.repositories.stamping.part.repository import StampingPartRepository
from app.repositories.stamping.part.tailor_weld_blank import StampingTailorWeldBlankRepository
from app.schemas.dto.stamping_tailor_weld_blank_dto import TailorWeldBlankWrite
from app.schemas.dto.stamping_upload_dto import ProcessData
from app.schemas.vo.user_vo import UserVO
from app.services.stamping.part.engineering.design_change.types import (
    EngineeringChangeMaterialHistoryClone,
    EngineeringChangeProcessPartSpec,
)
from app.services.stamping.part.engineering.material_change import (
    MaterialChangeHistorySpec,
    StampingMaterialChangeService,
)


def insert_part_for_engineering_change(
    part_repo: StampingPartRepository,
    db: Session,
    spec: EngineeringChangeProcessPartSpec,
    current_user: UserVO,
) -> tuple[int, int | None]:
    """写入 clone 出的零件一行。有旧号时停掉旧零件并 clone 拼焊子片。返回 (新零件 id, 旧零件 id)。"""
    audit = audit_create(current_user)
    part_data = spec.part_data
    part_data.created_by = audit["created_by"]
    part_data.updated_by = audit["updated_by"]
    new_part = part_repo.create(db, part_data)
    db.flush()
    if spec.expire_predecessor_id is not None:
        old_part = part_repo.get_by_id(db, spec.expire_predecessor_id)
        if old_part is None:
            raise NotFoundException(f"变更前冲压零件不存在: id={spec.expire_predecessor_id}")
        if spec.predecessor_expiry_year is None or spec.predecessor_expiry_month is None:
            raise BusinessException("变更前零件失效年月缺失")
        old_part.expiry_year = spec.predecessor_expiry_year
        old_part.expiry_month = spec.predecessor_expiry_month
        old_part.updated_by = audit["updated_by"]
        _clone_tailor_weld_blanks(
            db,
            old_part=old_part,
            new_part=new_part,
            created_by=audit["created_by"],
            updated_by=audit["updated_by"],
        )
    return new_part.id, spec.expire_predecessor_id


def insert_processes_for_engineering_change(
    process_repo: StampingProcessRepository,
    db: Session,
    *,
    part_id: int,
    processes: list[ProcessData],
    current_user: UserVO,
) -> None:
    """写入 clone 出的每一道工序，顺序与传入相同。"""
    audit = audit_create(current_user)
    for process in processes:
        process.part_id = part_id
        process.created_by = audit["created_by"]
        process.updated_by = audit["updated_by"]
        process_repo.create(db, process)


def insert_material_changes_for_engineering_change(
    db: Session,
    *,
    part_id: int,
    material_changes: list[EngineeringChangeMaterialHistoryClone],
    current_user: UserVO,
) -> list[tuple[int, int]]:
    """写入 clone 出的每一条材料变更历史，挂到新零件。返回逐条 (旧历史 id, 新历史 id)。"""
    new_history_ids = StampingMaterialChangeService().insert(
        db,
        [
            MaterialChangeHistorySpec(
                part_id=part_id,
                effective_year=row.effective_year,
                effective_month=row.effective_month,
                before_material=row.before_material,
                after_material=row.after_material,
                before_thickness=row.before_thickness,
                after_thickness=row.after_thickness,
            )
            for row in material_changes
        ],
        current_user,
    )
    return list(zip((row.source_id for row in material_changes), new_history_ids, strict=True))


def _remapped_blank_part_number(
    *,
    old_parent: str,
    new_parent: str,
    blank_part_number: str,
    blank_seq: int,
) -> str:
    if blank_part_number.startswith(old_parent):
        return new_parent + blank_part_number[len(old_parent) :]
    return f"{new_parent}-{blank_seq}"


def _clone_tailor_weld_blanks(
    db: Session,
    *,
    old_part: StampingPart,
    new_part: StampingPart,
    created_by: str | None,
    updated_by: str | None,
) -> None:
    """有旧号时，旧零件的每一片拼焊子片 clone 到新零件。子片号随新零件号改。"""
    blank_repo = StampingTailorWeldBlankRepository()
    old_blanks = blank_repo.list_by_part_id(db, old_part.id)
    if not old_blanks:
        return
    old_parent = str(old_part.part_number)
    new_parent = str(new_part.part_number)
    for blank in old_blanks:
        blank_repo.create(
            db,
            TailorWeldBlankWrite(
                part_id=new_part.id,
                parent_part_number=new_parent,
                blank_seq=int(blank.blank_seq),
                blank_part_number=_remapped_blank_part_number(
                    old_parent=old_parent,
                    new_parent=new_parent,
                    blank_part_number=str(blank.blank_part_number or ""),
                    blank_seq=int(blank.blank_seq),
                ),
                material=blank.material,
                thickness=blank.thickness,
                part_weight=blank.part_weight,
                sheet_length=blank.sheet_length,
                sheet_width=blank.sheet_width,
                parts_per_sheet=blank.parts_per_sheet,
                sheet_type=blank.sheet_type,
                remark=blank.remark,
                created_by=created_by,
                updated_by=updated_by,
            ),
        )
