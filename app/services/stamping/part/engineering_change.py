"""冲压零件：工程变更插行 / 回滚（只 flush，由调用方 commit）。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.common.audit import audit_create, audit_update
from app.common.period import is_in_period
from app.exceptions.base import BusinessException, NotFoundException
from app.models.stamping import StampingPart, StampingProcess
from app.repositories.stamping.stamping_part_repository import StampingPartRepository
from app.repositories.stamping.stamping_process_repository import (
    StampingProcessRepository,
)
from app.repositories.stamping.tailor_weld_blank_repository import (
    StampingTailorWeldBlankRepository,
)
from app.schemas.dto.stamping_tailor_weld_blank_dto import TailorWeldBlankWrite
from app.schemas.dto.stamping_upload_dto import PartData, ProcessData
from app.schemas.vo.user_vo import UserVO


@dataclass(slots=True)
class EngineeringChangeProcessPartSpec:
    """工程变更待插的一件工艺 + 工序。"""

    part_data: PartData
    processes: list[ProcessData]
    expire_predecessor_id: int | None = None
    predecessor_expiry_year: int | None = None
    predecessor_expiry_month: int | None = None


@dataclass(slots=True)
class EngineeringChangeProcessPartResult:
    part_id: int
    predecessor_id: int | None = None


@dataclass(slots=True)
class EngineeringChangePartAsOfRow:
    id: int
    part_number: str
    stamping_supplier: str = ""


def list_parts_as_of(
    part_repo: StampingPartRepository,
    db: Session,
    *,
    location: str,
    vehicle_model: str,
    as_of_year: int,
    as_of_month: int,
) -> list[EngineeringChangePartAsOfRow]:
    """当月命中的零件号清单（工程变更找旧号 / 避重）。"""
    rows: list[EngineeringChangePartAsOfRow] = []
    for row in part_repo.list_by_location_and_vehicle(
        db, location=location, vehicle_model=vehicle_model
    ):
        if not is_in_period(
            effective_year=row.effective_year,
            effective_month=row.effective_month,
            expiry_year=row.expiry_year,
            expiry_month=row.expiry_month,
            as_of_year=as_of_year,
            as_of_month=as_of_month,
        ):
            continue
        rows.append(
            EngineeringChangePartAsOfRow(
                id=row.id,
                part_number=row.part_number,
                stamping_supplier=(row.stamping_supplier or "").strip(),
            )
        )
    return rows


def clone_revise_part_payload(
    old_part: StampingPart,
    old_processes: Sequence[StampingProcess],
    *,
    new_part_number: str,
    version: str,
    effective_year: int,
    effective_month: int,
    expiry_year: int | None,
    expiry_month: int | None,
    created_by: str | None,
    updated_by: str | None,
) -> tuple[PartData, list[ProcessData]]:
    """改图换号：除零件号、版本、生失效、简图外整行抄旧号；工序整表相同。excel_row 抄旧零件，不用工程变更表。"""
    die_sets_default = 1
    part_data = PartData(
        location=str(old_part.location),
        vehicle_model=str(old_part.vehicle_model),
        version=version,
        stamping_supplier=str(old_part.stamping_supplier or ""),
        part_number=new_part_number,
        excel_filename=str(old_part.excel_filename or ""),
        effective_year=effective_year,
        effective_month=effective_month,
        expiry_year=expiry_year,
        expiry_month=expiry_month,
        seq_no=old_part.seq_no,
        part_name=old_part.part_name,
        material=old_part.material,
        thickness=old_part.thickness,
        part_weight=old_part.part_weight,
        sheet_length=old_part.sheet_length,
        sheet_width=old_part.sheet_width,
        parts_per_sheet=old_part.parts_per_sheet,
        sheet_type=old_part.sheet_type,
        is_offal_nested=bool(old_part.is_offal_nested),
        offal_source=old_part.offal_source,
        is_scrap_byproduct=bool(old_part.is_scrap_byproduct),
        has_swing_shear=bool(old_part.has_swing_shear),
        die_type=old_part.die_type,
        process_method=old_part.process_method,
        automation=old_part.automation,
        remark=old_part.remark,
        sketch_url=None,
        is_tailor_welded=bool(old_part.is_tailor_welded),
        excel_sheet_name=old_part.excel_sheet_name,
        excel_row=old_part.excel_row,
        excel_part_col=old_part.excel_part_col,
        created_by=created_by,
        updated_by=updated_by,
    )
    processes: list[ProcessData] = []
    for process in old_processes:
        die_sets = process.die_sets
        processes.append(
            ProcessData(
                part_id=0,
                process_seq=str(process.process_seq),
                process_order=int(process.process_order),
                die_sets=int(die_sets) if die_sets is not None else die_sets_default,
                process_code=process.process_code,
                die_number=process.die_number,
                tonnage=process.tonnage,
                cost_ratio=process.cost_ratio,
                remark=process.remark,
                created_by=created_by,
                updated_by=updated_by,
            )
        )
    return part_data, processes


def clone_revise_from_predecessor(
    part_repo: StampingPartRepository,
    process_repo: StampingProcessRepository,
    db: Session,
    *,
    predecessor_id: int,
    new_part_number: str,
    version: str,
    effective_year: int,
    effective_month: int,
    expiry_year: int | None,
    expiry_month: int | None,
    created_by: str | None,
    updated_by: str | None,
) -> tuple[PartData, list[ProcessData]]:
    """读旧号主从表，生成改图新行写入数据。"""
    old_part = part_repo.get_by_id(db, predecessor_id)
    if old_part is None:
        raise NotFoundException(f"变更前冲压零件不存在: id={predecessor_id}")
    old_processes = process_repo.get_by_part_id(db, predecessor_id)
    return clone_revise_part_payload(
        old_part,
        old_processes,
        new_part_number=new_part_number,
        version=version,
        effective_year=effective_year,
        effective_month=effective_month,
        expiry_year=expiry_year,
        expiry_month=expiry_month,
        created_by=created_by,
        updated_by=updated_by,
    )


def insert_for_engineering_change(
    part_repo: StampingPartRepository,
    process_repo: StampingProcessRepository,
    db: Session,
    specs: list[EngineeringChangeProcessPartSpec],
    current_user: UserVO,
) -> list[EngineeringChangeProcessPartResult]:
    """工程变更按号增行；可选失效前驱。只 flush。"""
    audit = audit_create(current_user)
    results: list[EngineeringChangeProcessPartResult] = []
    for spec in specs:
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

        for process in spec.processes:
            process.part_id = new_part.id
            process.created_by = audit["created_by"]
            process.updated_by = audit["updated_by"]
            process_repo.create(db, process)

        results.append(
            EngineeringChangeProcessPartResult(
                part_id=new_part.id,
                predecessor_id=spec.expire_predecessor_id,
            )
        )
    db.flush()
    return results


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


def rollback_engineering_change_part(
    part_repo: StampingPartRepository,
    process_repo: StampingProcessRepository,
    db: Session,
    *,
    after_part_id: int | None,
    before_part_id: int | None,
    current_user: UserVO,
) -> None:
    """回滚：删新零件（含工序），清空旧零件失效月。只 flush。"""
    if after_part_id is not None:
        process_repo.delete_by_part_ids(db, [after_part_id])
        part_repo.delete(db, after_part_id)
    if before_part_id is not None:
        old_part = part_repo.get_by_id(db, before_part_id)
        if old_part is not None:
            old_part.expiry_year = None
            old_part.expiry_month = None
            old_part.updated_by = audit_update(current_user)["updated_by"]
    db.flush()
