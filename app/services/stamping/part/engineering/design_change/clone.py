"""clone 改图的三样，不写库：零件一行，每一道工序各一行，每一条材料变更历史各一行。"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.exceptions.base import NotFoundException
from app.models.stamping import StampingPart, StampingProcess
from app.repositories.stamping.part.process import StampingProcessRepository
from app.repositories.stamping.part.repository import StampingPartRepository
from app.schemas.dto.stamping_upload_dto import PartData, ProcessData
from app.services.stamping.part.engineering.design_change.types import (
    EngineeringChangeMaterialHistoryClone,
)
from app.services.stamping.part.engineering.material_change import (
    MaterialChangeHistoryRow,
    list_material_changes,
)


def clone_revise_part_payload(
    old_part: StampingPart,
    old_processes: Sequence[StampingProcess],
    old_material_changes: Sequence[MaterialChangeHistoryRow],
    *,
    new_part_number: str,
    version: str,
    effective_year: int,
    effective_month: int,
    expiry_year: int | None,
    expiry_month: int | None,
    created_by: str | None,
    updated_by: str | None,
) -> tuple[PartData, list[ProcessData], list[EngineeringChangeMaterialHistoryClone]]:
    """零件、工序、材料变更历史都从旧零件 clone。零件换零件号、版本、生失效、简图。工序与历史保持原顺序。"""
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
    material_changes = [
        EngineeringChangeMaterialHistoryClone(
            source_id=row.id,
            effective_year=row.effective_year,
            effective_month=row.effective_month,
            before_material=row.before_material,
            after_material=row.after_material,
            before_thickness=row.before_thickness,
            after_thickness=row.after_thickness,
        )
        for row in old_material_changes
    ]
    return part_data, processes, material_changes


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
) -> tuple[PartData, list[ProcessData], list[EngineeringChangeMaterialHistoryClone]]:
    """读旧零件、全部工序、全部材料变更历史，clone 成待写的三样。"""
    old_part = part_repo.get_by_id(db, predecessor_id)
    if old_part is None:
        raise NotFoundException(f"变更前冲压零件不存在: id={predecessor_id}")
    old_processes = process_repo.get_by_part_id(db, predecessor_id)
    old_material_changes = list_material_changes(db, predecessor_id)
    return clone_revise_part_payload(
        old_part,
        old_processes,
        old_material_changes,
        new_part_number=new_part_number,
        version=version,
        effective_year=effective_year,
        effective_month=effective_month,
        expiry_year=expiry_year,
        expiry_month=expiry_month,
        created_by=created_by,
        updated_by=updated_by,
    )
