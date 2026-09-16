"""冲压工艺上传：落盘文件/简图，以及零件/工序写库。"""

from __future__ import annotations

import logging
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.common.audit import audit_create, display_name
from app.common.period import SOP_NEW_NUMBER_REJECT
from app.common.timezone import now
from app.config import settings
from app.exceptions.base import BusinessException
from app.parsers.stamping.models.part import Part
from app.parsers.stamping.models.process import Process
from app.parsers.stamping.models.tailor_weld import (
    TailorWeldAssemblyParsed,
    TailorWeldBlankParsed,
)
from app.repositories.persist import apply_payload_fields
from app.repositories.stamping.stamping_repository import (
    StampingPartRepository,
    StampingProcessRepository,
)
from app.schemas.dto.stamping_upload_dto import FileInfo, PartData, ProcessData
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.steel_grade_category import SteelGradeCategoryService
from app.services.masterdata.supplier import SupplierService
from app.services.masterdata.vehicle_model import VehicleModelService

logger = logging.getLogger("service.stamping_upload")


def canonicalize_materials(
    db: Session,
    parts: list[Part],
    assemblies: list[TailorWeldAssemblyParsed],
) -> None:
    holders: list[Part | TailorWeldAssemblyParsed | TailorWeldBlankParsed] = [*parts]
    for assembly in assemblies:
        holders.append(assembly)
        holders.extend(assembly.blanks)
    bound = SteelGradeCategoryService().bind_stored_grades(
        db,
        [holder.material for holder in holders],
    )
    for holder, grade in zip(holders, bound, strict=True):
        holder.material = grade


def save_file(
    file_content: bytes,
    filename: str,
    location: str,
    vehicle_model: str,
    version: str,
) -> FileInfo:
    """保存上传文件到磁盘，返回文件信息"""
    safe_location = location.replace("/", "_").replace("\\", "_")
    safe_vehicle = vehicle_model.replace("/", "_").replace("\\", "_")
    safe_version = version.replace("/", "_").replace("\\", "_").replace(" ", "_")
    timestamp_str = now().strftime("%H%M%S")
    new_filename = f"{safe_location}_{safe_vehicle}_{safe_version}_{timestamp_str}_{filename}"

    upload_subdir = settings.UPLOAD_DIR / safe_location / safe_vehicle / safe_version
    upload_subdir.mkdir(parents=True, exist_ok=True)
    file_path = upload_subdir / new_filename

    with open(file_path, "wb") as f:
        f.write(file_content)

    logger.info("文件保存成功: %s", file_path)

    return FileInfo(
        file_path=str(file_path),
        new_filename=new_filename,
        safe_location=safe_location,
        safe_vehicle=safe_vehicle,
        safe_version=safe_version,
        upload_subdir=str(upload_subdir),
    )


def save_part_images(
    images_by_part: dict[str, bytes],
    target_dir: str,
) -> int:
    """保存零件简图到磁盘"""
    if not images_by_part:
        return 0

    target_path = Path(target_dir)
    target_path.mkdir(parents=True, exist_ok=True)
    saved = 0
    for part_number, img_bytes in images_by_part.items():
        if not part_number or not img_bytes:
            continue
        safe_name = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in str(part_number))
        if not safe_name:
            continue
        img_path = target_path / f"{safe_name}.png"
        try:
            with open(img_path, "wb") as f:
                f.write(img_bytes)
            saved += 1
        except Exception as e:
            logger.warning("保存零件简图失败 %s: %s", part_number, e)

    logger.info("零件简图落盘: %d/%d -> %s", saved, len(images_by_part), target_dir)
    return saved


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
    """保存零件数据到数据库，返回 part_number -> part_id 映射"""
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
    """保存工序数据到数据库"""
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
