"""BOM 年度零件价 Excel 导入 / 模板下载服务。"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, audit_create, audit_update
from app.config import settings
from app.exceptions.base import BusinessException
from app.parsers.bom.annual_part_price_parser import (
    AnnualPartPriceParsedRow,
    parse_annual_part_price_excel,
)
from app.repositories.bom.annual_part_price_repository import (
    BomAnnualPartPriceRepository,
)
from app.repositories.bom.bom_repository import BomNodeRepository, BomSnapshotRepository
from app.repositories.bom.procurement_object_repository import (
    BomProcurementObjectRepository,
    object_scope_filters,
)
from app.repositories.stamping.stamping_part_repository import StampingPartRepository
from app.schemas.dto.bom_annual_part_price_dto import (
    BomAnnualPartPriceCreate,
    BomAnnualPartPriceUpdate,
    quantize_unit_price,
)
from app.schemas.vo.bom_annual_part_price_vo import BomAnnualPartPriceImportResultVO
from app.schemas.vo.user_vo import UserVO
from app.services.bom.annual_part_price.template_builder import (
    render_import_template,
)
from app.services.bom.annual_part_price.template_source import (
    collect_template_rows_from_snapshot_nodes,
)
from app.services.bom.procurement_object.classify import SECTION_OTHER_LEAF
from app.services.file_trace.path_utils import to_upload_relpath
from app.services.file_trace.register import register_existing
from app.services.masterdata.location.location_service import LocationService
from app.utils.bom_annual_part_price_archive import save_annual_part_price_upload

logger = logging.getLogger("service.bom_annual_part_price_import")


def _require_location_year(db: Session, location: str | None, year: int) -> str:
    location_text = (location or "").strip()
    if not location_text:
        raise BusinessException("请选择采购基地")
    if year < 2000 or year > 2100:
        raise BusinessException("年度不正确")
    return LocationService().require_enabled(db, location_text)


def _require_vehicle_model(vehicle_model: str | None) -> str:
    vehicle_text = (vehicle_model or "").strip()
    if not vehicle_text:
        raise BusinessException("请选择项目")
    return vehicle_text


def _require_xlsx_upload(filename: str, file_content: bytes) -> str:
    original_name = Path(filename or "").name
    if Path(original_name).suffix.lower() != ".xlsx":
        raise BusinessException("仅支持 .xlsx 文件")
    if not file_content:
        raise BusinessException("文件内容为空")
    if len(file_content) > settings.MAX_UPLOAD_SIZE:
        max_mb = settings.MAX_UPLOAD_SIZE // (1024 * 1024)
        raise BusinessException(f"文件过大，最大支持 {max_mb}MB")
    return original_name


class BomAnnualPartPriceImportService:
    """年度零件价同步导入（不走异步任务）。"""

    def __init__(self) -> None:
        self.repository = BomAnnualPartPriceRepository()
        self.snapshot_repository = BomSnapshotRepository()
        self.node_repository = BomNodeRepository()
        self.stamping_part_repository = StampingPartRepository()
        self.procurement_object_repository = BomProcurementObjectRepository()

    def build_template(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        year: int,
    ) -> tuple[bytes, str]:
        """按该基地该项目 BOM 外购叶子生成导入模板。"""
        location = _require_location_year(db, location, year)
        vehicle_model = _require_vehicle_model(vehicle_model)
        snapshots = self.snapshot_repository.list_by_location_model(db, location, vehicle_model)
        if not snapshots:
            raise BusinessException("请先上传该基地该项目的材料清单")
        snapshots = sorted(snapshots, key=lambda item: (item.bom_version, item.id))

        stamping_part_numbers = {
            row["part_number"]
            for row in self.stamping_part_repository.list_distinct_parts_for_scope(
                db, location=location, vehicle_model=vehicle_model
            )
        }
        other_leaf_part_numbers = {
            (obj.part_number or "").strip()
            for obj in self.procurement_object_repository.list_objects_for_export(
                db,
                scope=object_scope_filters(
                    location=location,
                    vehicle_model=vehicle_model,
                    section=SECTION_OTHER_LEAF,
                ),
            )
            if (obj.part_number or "").strip()
        }

        snapshot_nodes = [
            (snapshot, self.node_repository.list_by_snapshot(db, snapshot.id))
            for snapshot in snapshots
        ]
        template_rows = collect_template_rows_from_snapshot_nodes(
            snapshot_nodes,
            other_leaf_part_numbers=other_leaf_part_numbers,
            stamping_part_numbers=stamping_part_numbers,
        )
        if not template_rows:
            raise BusinessException("该基地该项目没有需填年度价的外购叶子，无法生成模板")

        content = render_import_template(template_rows)
        filename = f"年度零件价导入模板_{location}_{vehicle_model}_{year}.xlsx"
        return content, filename

    def import_excel(
        self,
        db: Session,
        *,
        file_content: bytes,
        filename: str,
        location: str,
        year: int,
        current_user: UserVO,
    ) -> BomAnnualPartPriceImportResultVO:
        location = _require_location_year(db, location, year)
        original_name = _require_xlsx_upload(filename, file_content)

        archive_path = save_annual_part_price_upload(
            file_content=file_content,
            filename=original_name,
            year=year,
            location=location,
        )
        archived_rel = to_upload_relpath(archive_path)

        parse_result = parse_annual_part_price_excel(file_content)
        if parse_result.errors and not parse_result.rows:
            raise BusinessException("；".join(parse_result.errors))
        if not parse_result.rows:
            raise BusinessException("未解析到有效数据行")

        created_count = 0
        updated_count = 0
        skipped_approved = 0
        create_audit = audit_create(current_user)
        update_audit = audit_update(current_user)

        try:
            created_count, updated_count, skipped_approved = self._upsert_parsed_rows(
                db,
                location=location,
                year=year,
                rows=parse_result.rows,
                created_by=create_audit["created_by"],
                created_updated_by=create_audit["updated_by"],
                updated_by=update_audit["updated_by"],
            )
            register_existing(
                db,
                file_category="bom_annual_part_price",
                stored_relpath=archived_rel,
                original_filename=original_name,
                current_user=current_user,
                location=location,
                year=year,
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

        warnings = list(parse_result.errors)
        if skipped_approved:
            warnings.append(f"跳过已审核 {skipped_approved} 条（未覆盖）")
        message = (
            f"导入完成：基地「{location}」{year} 年，"
            f"新增 {created_count} 条，更新 {updated_count} 条"
        )
        if skipped_approved:
            if created_count == 0 and updated_count == 0:
                message += f"。这 {skipped_approved} 条已审核，导入不会覆盖；如需改价请先反审核"
            else:
                message += f"，跳过已审核 {skipped_approved} 条（未覆盖）"
        if parse_result.errors:
            message += f"；有 {len(parse_result.errors)} 行解析跳过"

        logger.info(
            "%s file=%s archived=%s created=%s updated=%s skipped_approved=%s warnings=%s",
            message,
            original_name,
            archived_rel,
            created_count,
            updated_count,
            skipped_approved,
            len(warnings),
        )
        return BomAnnualPartPriceImportResultVO(
            location=location,
            year=year,
            created_count=created_count,
            updated_count=updated_count,
            total_count=created_count + updated_count,
            skipped_count=len(parse_result.errors) + skipped_approved,
            skipped_approved_count=skipped_approved,
            warnings=warnings,
            message=message,
        )

    def _upsert_parsed_rows(
        self,
        db: Session,
        *,
        location: str,
        year: int,
        rows: list[AnnualPartPriceParsedRow],
        created_by: str,
        created_updated_by: str,
        updated_by: str,
    ) -> tuple[int, int, int]:
        created_count = 0
        updated_count = 0
        skipped_approved = 0
        for row in rows:
            unit_price = quantize_unit_price(row.unit_price)
            existing = self.repository.get_by_location_year_part_number(
                db, location, year, row.part_number
            )
            if existing:
                if existing.audit_status == AUDIT_APPROVED:
                    skipped_approved += 1
                    continue
                self.repository.update(
                    db,
                    existing.id,
                    BomAnnualPartPriceUpdate(
                        part_name=row.part_name,
                        specification=row.specification,
                        purchase_unit=row.purchase_unit,
                        purchase_unit_price=row.purchase_unit_price,
                        conversion_factor=row.conversion_factor,
                        unit=row.unit,
                        unit_price=unit_price,
                        supply_type=row.supply_type,
                        supplier_name=row.supplier_name,
                        remark=row.remark,
                    ),
                    updated_by=updated_by,
                )
                updated_count += 1
                continue
            self.repository.create(
                db,
                BomAnnualPartPriceCreate(
                    location=location,
                    year=year,
                    part_number=row.part_number,
                    part_name=row.part_name,
                    specification=row.specification,
                    purchase_unit=row.purchase_unit,
                    purchase_unit_price=row.purchase_unit_price,
                    conversion_factor=row.conversion_factor,
                    unit=row.unit,
                    unit_price=unit_price,
                    supply_type=row.supply_type,
                    supplier_name=row.supplier_name,
                    remark=row.remark,
                ),
                created_by=created_by,
                updated_by=created_updated_by,
            )
            created_count += 1
        return created_count, updated_count, skipped_approved
