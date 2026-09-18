"""冲压零件：工程变更合册插行 / 回滚（只 flush，由调用方 commit）。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.audit import audit_create, audit_update
from app.common.period import is_in_period
from app.exceptions.base import BusinessException, NotFoundException
from app.models.stamping import StampingPart, StampingProcess
from app.repositories.stamping.stamping_repository import (
    StampingPartRepository,
    StampingProcessRepository,
)
from app.schemas.dto.stamping_upload_dto import PartData, ProcessData
from app.schemas.vo.user_vo import UserVO


@dataclass(slots=True)
class EngineeringChangeProcessPartSpec:
    """合册待插的一件工艺 + 工序。"""

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
    seq_no: int | None = None
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
    """当月命中的零件号清单（合册找旧号 / 避重）。"""
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
                seq_no=row.seq_no,
                stamping_supplier=(row.stamping_supplier or "").strip(),
            )
        )
    return rows


def process_cost_ratios_by_seq(
    process_repo: StampingProcessRepository,
    db: Session,
    part_id: int,
) -> dict[str, Decimal]:
    """旧零件工序成本系数（按 process_seq 字符串键）。"""
    ratios: dict[str, Decimal] = {}
    for proc in process_repo.get_by_part_id(db, part_id):
        ratios[str(proc.process_seq)] = proc.cost_ratio
    return ratios


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
    excel_filename: str,
    excel_sheet_name: str | None,
    excel_row: int | None,
    excel_part_col: int | None,
    created_by: str | None,
    updated_by: str | None,
) -> tuple[PartData, list[ProcessData]]:
    """改图换号：除零件号、版本、生失效外整行抄旧号；工序整表相同。"""
    die_sets_default = 1
    part_data = PartData(
        location=str(old_part.location),
        vehicle_model=str(old_part.vehicle_model),
        version=version,
        stamping_supplier=str(old_part.stamping_supplier or ""),
        part_number=new_part_number,
        excel_filename=excel_filename,
        effective_year=effective_year,
        effective_month=effective_month,
        expiry_year=expiry_year,
        expiry_month=expiry_month,
        seq_no=getattr(old_part, "seq_no", None),
        part_name=getattr(old_part, "part_name", None),
        material=getattr(old_part, "material", None),
        thickness=getattr(old_part, "thickness", None),
        part_weight=getattr(old_part, "part_weight", None),
        sheet_length=getattr(old_part, "sheet_length", None),
        sheet_width=getattr(old_part, "sheet_width", None),
        parts_per_sheet=getattr(old_part, "parts_per_sheet", None),
        sheet_type=getattr(old_part, "sheet_type", None),
        is_offal_nested=bool(getattr(old_part, "is_offal_nested", False)),
        offal_source=getattr(old_part, "offal_source", None),
        is_scrap_byproduct=bool(getattr(old_part, "is_scrap_byproduct", False)),
        has_swing_shear=bool(getattr(old_part, "has_swing_shear", False)),
        die_type=getattr(old_part, "die_type", None),
        process_method=getattr(old_part, "process_method", None),
        automation=getattr(old_part, "automation", None),
        remark=getattr(old_part, "remark", None),
        sketch_url=getattr(old_part, "sketch_url", None),
        is_tailor_welded=bool(getattr(old_part, "is_tailor_welded", False)),
        excel_sheet_name=excel_sheet_name,
        excel_row=excel_row,
        excel_part_col=excel_part_col,
        created_by=created_by,
        updated_by=updated_by,
    )
    processes: list[ProcessData] = []
    for proc in old_processes:
        die_sets = getattr(proc, "die_sets", None)
        processes.append(
            ProcessData(
                part_id=0,
                process_seq=str(proc.process_seq),
                process_order=int(proc.process_order),
                die_sets=int(die_sets) if die_sets is not None else die_sets_default,
                process_code=getattr(proc, "process_code", None),
                die_number=getattr(proc, "die_number", None),
                tonnage=getattr(proc, "tonnage", None),
                cost_ratio=proc.cost_ratio,
                remark=getattr(proc, "remark", None),
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
    excel_filename: str,
    excel_sheet_name: str | None,
    excel_row: int | None,
    excel_part_col: int | None,
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
        excel_filename=excel_filename,
        excel_sheet_name=excel_sheet_name,
        excel_row=excel_row,
        excel_part_col=excel_part_col,
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
    """合册按号增行；可选失效前驱。只 flush。"""
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
