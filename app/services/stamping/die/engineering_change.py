"""模具布点：工程变更按号插行 / 回滚（只 flush，由调用方 commit）。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.audit import audit_create, audit_update
from app.common.money import Q2, quantize_money
from app.common.period import is_in_period
from app.exceptions.base import BusinessException, NotFoundException
from app.models.stamping.die import StampingDiePart
from app.repositories.stamping.stamping_die_repository import (
    StampingDiePartRepository,
    StampingDieProcessRepository,
)
from app.schemas.dto.stamping_die_dto import StampingDiePartInsert, StampingDieProcessInsert
from app.schemas.vo.user_vo import UserVO


@dataclass(slots=True)
class EngineeringChangeDieProcessSpec:
    process_seq: str
    process_order: int
    process_code: str | None
    die_sets: int | None
    die_number: str | None
    die_length: Decimal | None
    die_width: Decimal | None
    die_height: Decimal | None
    hollow_factor: Decimal | None
    estimated_weight_t: Decimal | None
    tonnage: int | None
    alloc_ratio: Decimal
    remark: str | None = None


@dataclass(slots=True)
class EngineeringChangeDiePartSpec:
    """工程变更待插的一件布点 + 工序。"""

    part: StampingDiePartInsert
    processes: list[EngineeringChangeDieProcessSpec]
    expire_predecessor_id: int | None = None
    predecessor_expiry_year: int | None = None
    predecessor_expiry_month: int | None = None


@dataclass(slots=True)
class EngineeringChangeDiePartResult:
    part_id: int
    part_number: str
    predecessor_id: int | None = None


@dataclass(slots=True)
class EngineeringChangeDieAsOfRow:
    id: int
    part_number: str


def list_parts_as_of(
    die_part_repo: StampingDiePartRepository,
    db: Session,
    *,
    location: str,
    vehicle_model: str,
    as_of_year: int,
    as_of_month: int,
) -> list[EngineeringChangeDieAsOfRow]:
    """当月命中的布点零件号清单（工程变更找旧号 / 避重）。"""
    rows: list[EngineeringChangeDieAsOfRow] = []
    for row in die_part_repo.list_existing_in_scope(
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
        rows.append(EngineeringChangeDieAsOfRow(id=row.id, part_number=row.part_number))
    return rows


def clone_revise_die_spec(
    old_part: StampingDiePart,
    *,
    new_part_number: str,
    version: str | None,
    effective_year: int,
    effective_month: int,
    expiry_year: int | None,
    expiry_month: int | None,
    created_by: str,
    updated_by: str,
    predecessor_expiry_year: int | None = None,
    predecessor_expiry_month: int | None = None,
) -> EngineeringChangeDiePartSpec:
    """改图：除零件号、版本、生失效外整行抄旧布点，工序含 alloc_ratio。"""
    processes = [
        EngineeringChangeDieProcessSpec(
            process_seq=process.process_seq,
            process_order=int(process.process_order),
            process_code=process.process_code,
            die_sets=process.die_sets,
            die_number=process.die_number,
            die_length=process.die_length,
            die_width=process.die_width,
            die_height=process.die_height,
            hollow_factor=process.hollow_factor,
            estimated_weight_t=process.estimated_weight_t,
            tonnage=process.tonnage,
            alloc_ratio=quantize_money(process.alloc_ratio, Q2),
            remark=process.remark,
        )
        for process in old_part.processes
    ]
    return EngineeringChangeDiePartSpec(
        part=StampingDiePartInsert(
            location=old_part.location,
            vehicle_model=old_part.vehicle_model,
            stamping_supplier=old_part.stamping_supplier,
            version=version,
            seq_no=old_part.seq_no,
            part_number=new_part_number,
            part_name=old_part.part_name,
            material=old_part.material,
            thickness=old_part.thickness,
            part_weight=old_part.part_weight,
            sheet_length=old_part.sheet_length,
            sheet_width=old_part.sheet_width,
            sheet_shape=old_part.sheet_shape,
            parts_per_sheet=old_part.parts_per_sheet,
            material_consumption=old_part.material_consumption,
            material_utilization=old_part.material_utilization,
            estimated_weight_subtotal_t=old_part.estimated_weight_subtotal_t,
            die_type=old_part.die_type,
            die_method=old_part.die_method,
            production_mode=old_part.production_mode,
            needs_end_effector=old_part.needs_end_effector,
            part_grade=old_part.part_grade,
            remark=old_part.remark,
            excel_filename=old_part.excel_filename or "",
            excel_sheet_name=old_part.excel_sheet_name,
            excel_row=old_part.excel_row,
            excel_part_col=old_part.excel_part_col,
            created_by=created_by,
            updated_by=updated_by,
            effective_year=effective_year,
            effective_month=effective_month,
            expiry_year=expiry_year,
            expiry_month=expiry_month,
        ),
        processes=processes,
        expire_predecessor_id=old_part.id,
        predecessor_expiry_year=predecessor_expiry_year,
        predecessor_expiry_month=predecessor_expiry_month,
    )


def insert_for_engineering_change(
    die_part_repo: StampingDiePartRepository,
    die_process_repo: StampingDieProcessRepository,
    db: Session,
    specs: list[EngineeringChangeDiePartSpec],
    current_user: UserVO,
) -> list[EngineeringChangeDiePartResult]:
    """工程变更按号增行；可选失效前驱。只 flush。"""
    audit = audit_create(current_user)
    results: list[EngineeringChangeDiePartResult] = []
    for spec in specs:
        part_payload = spec.part
        part_payload.created_by = audit["created_by"]
        part_payload.updated_by = audit["updated_by"]
        created = die_part_repo.bulk_create_parts(db, [part_payload])[0]

        if spec.expire_predecessor_id is not None:
            old_part = die_part_repo.get_by_id(db, spec.expire_predecessor_id)
            if old_part is None:
                raise NotFoundException(f"变更前模具零件不存在: id={spec.expire_predecessor_id}")
            if spec.predecessor_expiry_year is None or spec.predecessor_expiry_month is None:
                raise BusinessException("变更前模具零件失效年月缺失")
            old_part.expiry_year = spec.predecessor_expiry_year
            old_part.expiry_month = spec.predecessor_expiry_month
            old_part.updated_by = audit["updated_by"]

        process_rows: list[StampingDieProcessInsert] = []
        for process in spec.processes:
            process_rows.append(
                StampingDieProcessInsert(
                    die_part_id=created.id,
                    process_seq=process.process_seq,
                    process_order=process.process_order,
                    process_code=process.process_code,
                    die_sets=process.die_sets,
                    die_number=process.die_number,
                    die_length=process.die_length,
                    die_width=process.die_width,
                    die_height=process.die_height,
                    hollow_factor=process.hollow_factor,
                    estimated_weight_t=process.estimated_weight_t,
                    tonnage=process.tonnage,
                    alloc_ratio=process.alloc_ratio,
                    remark=process.remark,
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                )
            )
        if process_rows:
            die_process_repo.bulk_create(db, process_rows)

        results.append(
            EngineeringChangeDiePartResult(
                part_id=created.id,
                part_number=str(created.part_number),
                predecessor_id=spec.expire_predecessor_id,
            )
        )
    db.flush()
    return results


def rollback_engineering_change_part(
    die_part_repo: StampingDiePartRepository,
    _die_process_repo: StampingDieProcessRepository,
    db: Session,
    *,
    after_part_id: int | None,
    before_part_id: int | None,
    current_user: UserVO,
) -> None:
    """回滚：删新布点（含工序），清空旧布点失效月。只 flush。"""
    if after_part_id is not None:
        die_part_repo.delete_processes_by_part_ids(db, [after_part_id])
        die_part_repo.delete_by_ids(db, [after_part_id])
    if before_part_id is not None:
        old_part = die_part_repo.get_by_id(db, before_part_id)
        if old_part is not None:
            old_part.expiry_year = None
            old_part.expiry_month = None
            old_part.updated_by = audit_update(current_user)["updated_by"]
    db.flush()
