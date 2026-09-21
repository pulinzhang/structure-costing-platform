"""冲压零件 / 工序写库。只 flush，不 commit。"""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.audit import audit_create, display_name
from app.common.period import SOP_NEW_NUMBER_REJECT
from app.exceptions.base import BusinessException
from app.parsers.stamping.models.part import Part
from app.parsers.stamping.models.process import Process
from app.repositories.persist import apply_payload_fields
from app.repositories.stamping.part.process import StampingProcessRepository
from app.repositories.stamping.part.repository import StampingPartRepository
from app.schemas.dto.stamping_upload_dto import FileInfo, PartData, ProcessData
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.supplier.service import SupplierService
from app.services.masterdata.vehicle_model.service import VehicleModelService

logger = logging.getLogger("service.stamping_upload")


def save_parts(
    db: Session,
    part_repo: StampingPartRepository,
    parts: list[Part],
    vehicle_model: str,
    version: str,
    file_info: FileInfo,
    images_by_part: dict[str, bytes],
    stamping_supplier: str = "",
    excel_filename: str = "",
    tailor_parent_numbers: set[str] | None = None,
    swing_shear_part_numbers: set[str] | None = None,
    *,
    current_user: UserVO,
) -> dict[str, int]:
    """保存零件数据到数据库，返回 part_number -> part_id 映射。"""
    tailor_parents = tailor_parent_numbers or set()
    swing_shear_parts = swing_shear_part_numbers or set()
    location = file_info.safe_location
    supplier_names = SupplierService().expand_for_query(db, stamping_supplier)
    existing_rows = part_repo.list_identity_scope(
        db,
        location=location,
        vehicle_model=vehicle_model,
        stamping_suppliers=supplier_names,
    )
    existing = {row.part_number: row for row in existing_rows if row.part_number}
    file_numbers = [part.part_number for part in parts if part.part_number]
    if existing:
        unknown = [number for number in file_numbers if number not in existing]
        if unknown:
            raise BusinessException(SOP_NEW_NUMBER_REJECT)

    effective_year, effective_month, expiry_year, expiry_month = (
        VehicleModelService().project_sop_period(db, location, vehicle_model)
    )
    audit = audit_create(current_user)
    part_map: dict[str, int] = {}
    to_create: list[PartData] = []

    for part in parts:
        part_number = part.part_number
        if not part_number:
            continue
        sketch_url = (
            f"{file_info.safe_location}/{file_info.safe_vehicle}/"
            f"{file_info.safe_version}/{part_number}.png"
            if part_number in images_by_part
            else None
        )
        payload = PartData(
            location=location,
            vehicle_model=vehicle_model,
            version=version,
            stamping_supplier=stamping_supplier,
            seq_no=part.seq_no,
            part_number=part_number,
            part_name=part.part_name,
            material=part.material,
            thickness=part.thickness,
            part_weight=part.part_weight,
            sheet_length=part.sheet_length,
            sheet_width=part.sheet_width,
            parts_per_sheet=part.parts_per_sheet,
            sheet_type=part.sheet_type,
            is_offal_nested=part.is_offal_nested,
            offal_source=part.offal_source,
            is_scrap_byproduct=part.is_scrap_byproduct,
            has_swing_shear=part_number in swing_shear_parts,
            die_type=part.die_type,
            process_method=part.process_method,
            automation=part.automation,
            remark=part.remark,
            sketch_url=sketch_url,
            is_tailor_welded=part_number in tailor_parents,
            excel_filename=excel_filename,
            excel_sheet_name=part.excel_sheet_name,
            excel_row=part.excel_row,
            excel_part_col=part.excel_part_col,
            effective_year=effective_year,
            effective_month=effective_month,
            expiry_year=expiry_year,
            expiry_month=expiry_month,
            created_by=audit["created_by"],
            updated_by=audit["updated_by"],
        )
        current = existing.get(part_number)
        if current is None:
            to_create.append(payload)
            continue
        apply_payload_fields(
            current,
            payload,
            skip=frozenset(
                {
                    "id",
                    "seq_no",
                    "version",
                    "effective_year",
                    "effective_month",
                    "expiry_year",
                    "expiry_month",
                    "created_by",
                    "created_at",
                }
            ),
        )
        part_map[part_number] = current.id

    if to_create:
        created = part_repo.bulk_create(db, to_create)
        db.flush()
        for row in created:
            part_map[row.part_number] = row.id

    logger.info(
        "导入零件: 更新 %d 新增 %d operator=%s",
        len(existing),
        len(to_create),
        display_name(current_user),
    )
    return part_map


def save_processes(
    db: Session,
    process_repo: StampingProcessRepository,
    processes: list[Process],
    part_map: dict[str, int],
    current_user: UserVO,
) -> int:
    """保存工序数据到数据库。"""
    audit = audit_create(current_user)
    processes_to_create: list[ProcessData] = []
    part_order_counter: dict[str, int] = {}

    for process in processes:
        part_number = process.part_number
        part_id = part_map.get(part_number)
        if not part_id:
            logger.warning(
                "工序被跳过: part_number=%s, seq=%s",
                part_number,
                process.process_seq,
            )
            continue

        order = part_order_counter.get(part_number, 0) + 1
        part_order_counter[part_number] = order

        processes_to_create.append(
            ProcessData(
                part_id=part_id,
                process_seq=process.process_seq,
                process_order=order,
                process_code=process.process_code,
                die_sets=process.die_sets,
                die_number=process.die_number,
                tonnage=process.tonnage,
                cost_ratio=process.cost_ratio
                if process.cost_ratio is not None
                else Decimal("1.00"),
                remark=process.remark,
            )
        )

    if processes_to_create:
        for process_row in processes_to_create:
            process_row.created_by = audit["created_by"]
            process_row.updated_by = audit["updated_by"]
        process_repo.bulk_create(db, processes_to_create)

    logger.info("导入工序: %d 个", len(processes_to_create))
    return len(processes_to_create)
