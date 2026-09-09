"""采购对象清单 — 按范围下载窄表 / 上传改供应商。"""

from __future__ import annotations

import logging
from collections import defaultdict
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, display_name
from app.config import settings
from app.exceptions.base import BusinessException, NotFoundException
from app.models.bom.procurement_object import BomProcurementObject, BomProcurementObjectList
from app.parsers.bom.procurement_object_supplier_parser import (
    ProcurementObjectSupplierParsedRow,
    parse_procurement_object_supplier_excel,
)
from app.repositories.bom.procurement_object_repository import BomProcurementObjectRepository
from app.schemas.vo.bom_procurement_object_vo import BomProcurementObjectSupplierUploadResultVO
from app.schemas.vo.user_vo import UserVO
from app.services.bom.procurement_object.classify import SECTION_OBJECT
from app.services.bom.procurement_object.supplier_template import (
    unique_object_rows_by_part_number,
    write_notes_sheet,
    write_object_sheet,
)
from app.services.file_trace.path_utils import to_upload_relpath
from app.services.file_trace.register import register_existing
from app.services.masterdata.location.location_service import LocationService
from app.services.masterdata.supplier import SupplierService
from app.utils.bom_procurement_object_supplier_archive import (
    save_procurement_object_supplier_upload,
)

logger = logging.getLogger("service.bom.procurement_object.supplier_upload")

_PAGE_HINT = "请到供应商一览表手工增加或上传（#/supplier-list）"


class BomProcurementObjectSupplierUploadService:
    def __init__(self) -> None:
        self.repository = BomProcurementObjectRepository()

    def build_template(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> tuple[bytes, str]:
        header, rows = self._load_object_rows(db, location, vehicle_model, bom_version)
        workbook = Workbook()
        write_object_sheet(workbook, unique_object_rows_by_part_number(rows))
        SupplierService().write_catalog_to_workbook(db, workbook, is_enabled=True)
        write_notes_sheet(workbook)
        buffer = BytesIO()
        workbook.save(buffer)
        workbook.close()
        filename = (
            f"采购对象供应商_{header.location}_{header.vehicle_model}_{header.bom_version}.xlsx"
        )
        return buffer.getvalue(), filename

    def process_upload(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
        filename: str,
        file_content: bytes,
        current_user: UserVO,
    ) -> BomProcurementObjectSupplierUploadResultVO:
        header, object_rows = self._load_object_rows(db, location, vehicle_model, bom_version)
        if not header.qa_passed:
            raise BusinessException("检测未通过，禁止改供应商")
        original_name = self._require_xlsx(filename, file_content)
        try:
            parsed_rows = parse_procurement_object_supplier_excel(file_content)
        except ValueError as exc:
            raise BusinessException(str(exc)) from None
        by_part = self._group_by_part_number(object_rows)
        self._assert_unique_part_numbers(parsed_rows)
        supplier_service = SupplierService()
        operator = display_name(current_user)
        updated_count = 0
        cleared_count = 0
        unchanged_count = 0
        archive_path = save_procurement_object_supplier_upload(
            file_content=file_content,
            filename=original_name,
            location=header.location,
            vehicle_model=header.vehicle_model,
            bom_version=header.bom_version,
        )
        try:
            for parsed in parsed_rows:
                matches = by_part.get(parsed.part_number)
                if not matches:
                    raise BusinessException(
                        f"Excel 第{parsed.row_number}行：零件号不属于本范围采购对象"
                    )
                for row in matches:
                    outcome = self._apply_supplier(
                        db,
                        row,
                        parsed,
                        supplier_service=supplier_service,
                        operator=operator,
                    )
                    if outcome == "updated":
                        updated_count += 1
                    elif outcome == "cleared":
                        cleared_count += 1
                    else:
                        unchanged_count += 1
            register_existing(
                db,
                file_category="bom_procurement_object_supplier",
                stored_relpath=to_upload_relpath(archive_path),
                original_filename=original_name,
                current_user=current_user,
                location=header.location,
                vehicle_model=header.vehicle_model,
                bom_version=header.bom_version,
            )
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            detail = str(getattr(exc, "orig", exc))
            if "FOREIGN KEY" in detail.upper() or "suppliers" in detail.lower():
                raise BusinessException(f"没有该供应商，{_PAGE_HINT}") from None
            logger.exception("采购对象供应商上传失败")
            raise BusinessException("保存失败，请稍后重试") from None
        except BusinessException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("采购对象供应商上传失败")
            raise
        return BomProcurementObjectSupplierUploadResultVO(
            updated_count=updated_count,
            cleared_count=cleared_count,
            unchanged_count=unchanged_count,
        )

    def _load_object_rows(
        self,
        db: Session,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> tuple[BomProcurementObjectList, list[BomProcurementObject]]:
        location_text = LocationService().require_enabled(db, (location or "").strip())
        model_text = (vehicle_model or "").strip()
        version_text = (bom_version or "").strip()
        if not model_text:
            raise BusinessException("请选择项目")
        if not version_text:
            raise BusinessException("请选择版本")
        header = self.repository.get_list_by_scope(
            db,
            location=location_text,
            vehicle_model=model_text,
            bom_version=version_text,
        )
        if header is None:
            raise NotFoundException("尚未生成采购对象清单")
        rows = [
            row
            for row in self.repository.list_objects_by_list_id(db, header.id)
            if row.section == SECTION_OBJECT
        ]
        if not rows:
            raise BusinessException("没有可指定供应商的采购对象")
        rows.sort(
            key=lambda row: (
                row.l0_part_number or "",
                row.part_number or "",
                row.excel_row or 0,
            )
        )
        return header, rows

    def _require_xlsx(self, filename: str, file_content: bytes) -> str:
        original_name = Path(filename or "").name
        if Path(original_name).suffix.lower() != ".xlsx":
            raise BusinessException("仅支持 .xlsx 文件")
        if not file_content:
            raise BusinessException("文件内容为空")
        if len(file_content) > settings.MAX_UPLOAD_SIZE:
            max_mb = settings.MAX_UPLOAD_SIZE // (1024 * 1024)
            raise BusinessException(f"文件过大，最大支持 {max_mb}MB")
        return original_name

    def _group_by_part_number(
        self, rows: list[BomProcurementObject]
    ) -> dict[str, list[BomProcurementObject]]:
        grouped: dict[str, list[BomProcurementObject]] = defaultdict(list)
        for row in rows:
            key = row.part_number or ""
            if key:
                grouped[key].append(row)
        return grouped

    def _assert_unique_part_numbers(self, rows: list[ProcurementObjectSupplierParsedRow]) -> None:
        seen: set[str] = set()
        for row in rows:
            if row.part_number in seen:
                raise BusinessException(f"Excel 第{row.row_number}行：零件号重复")
            seen.add(row.part_number)

    def _apply_supplier(
        self,
        db: Session,
        row: BomProcurementObject,
        parsed: ProcurementObjectSupplierParsedRow,
        *,
        supplier_service: SupplierService,
        operator: str,
    ) -> str:
        incoming = (parsed.supplier_name or "").strip() or None
        current = (row.supplier_name or "").strip() or None
        if incoming is None:
            if current is None:
                return "unchanged"
            self._assert_can_change(row, parsed)
            row.supplier_name = None
            row.updated_by = operator
            return "cleared"
        if incoming == current:
            return "unchanged"
        canonical = supplier_service.resolve_canonical(db, incoming)
        if canonical is not None and canonical == current:
            return "unchanged"
        self._assert_can_change(row, parsed)
        if row.confirm_status == "in_house":
            raise BusinessException(f"Excel 第{parsed.row_number}行：自制禁止指定供应商")
        enabled = supplier_service.require_enabled(db, incoming)
        row.supplier_name = enabled
        row.updated_by = operator
        return "updated"

    def _assert_can_change(
        self,
        row: BomProcurementObject,
        parsed: ProcurementObjectSupplierParsedRow,
    ) -> None:
        if row.audit_status == AUDIT_APPROVED:
            raise BusinessException(
                f"Excel 第{parsed.row_number}行：已审核记录禁止改供应商，请先批量反审核"
            )
        if row.section != SECTION_OBJECT:
            raise BusinessException(f"Excel 第{parsed.row_number}行：核对区行禁止指定供应商")
