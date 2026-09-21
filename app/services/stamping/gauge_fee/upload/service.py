"""冲压检具费同步上传与模板。"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import audit_create
from app.common.part_number import normalize_part_number_token
from app.common.timezone import now
from app.config import settings
from app.exceptions.base import BusinessException
from app.parsers.stamping.gauge_fee_parser import parse_gauge_fee_excel
from app.repositories.stamping.die.repository import StampingDiePartRepository
from app.repositories.stamping.gauge_fee.repository import StampingGaugeFeeRepository
from app.schemas.dto.stamping_gauge_fee_dto import StampingGaugeFeeInsert
from app.schemas.vo.stamping_gauge_fee_vo import StampingGaugeFeeImportResultVO
from app.schemas.vo.user_vo import UserVO
from app.services.file_trace.path_utils import to_upload_relpath
from app.services.file_trace.register import register_existing
from app.services.masterdata.location.service import LocationService
from app.services.masterdata.vehicle_model.service import VehicleModelService
from app.services.stamping.gauge_fee.upload.template_builder import build_gauge_fee_template

logger = logging.getLogger("service.stamping_gauge_fee_upload")


class StampingGaugeFeeUploadService:
    def __init__(self) -> None:
        self.repository = StampingGaugeFeeRepository()
        self.die_part_repo = StampingDiePartRepository()

    def build_template(
        self, db: Session, *, location: str, vehicle_model: str
    ) -> tuple[bytes, str]:
        loc, vehicle = self._require_die_scope(db, location, vehicle_model)
        parts = self.die_part_repo.list_parts_for_scope(db, location=loc, vehicle_model=vehicle)
        if not parts:
            raise BusinessException("该基地+项目没有模具布点，无需维护检具费。请先上传模具布点")
        return build_gauge_fee_template(parts, location=loc, vehicle_model=vehicle)

    def import_excel(
        self,
        db: Session,
        *,
        file_content: bytes,
        filename: str,
        location: str,
        vehicle_model: str,
        current_user: UserVO,
    ) -> StampingGaugeFeeImportResultVO:
        loc, vehicle = self._require_die_scope(db, location, vehicle_model)
        original_name = Path(filename or "").name
        suffix = Path(original_name).suffix.lower()
        if suffix != ".xlsx":
            raise BusinessException("仅支持 .xlsx 文件")
        if not file_content:
            raise BusinessException("文件内容为空")
        if len(file_content) > settings.MAX_UPLOAD_SIZE:
            max_mb = settings.MAX_UPLOAD_SIZE // (1024 * 1024)
            raise BusinessException(f"文件过大，最大支持 {max_mb}MB")

        parse_result = parse_gauge_fee_excel(file_content)
        if parse_result.errors:
            raise BusinessException("；".join(parse_result.errors))
        if not parse_result.rows:
            raise BusinessException("未解析到有效数据行")

        die_parts = self.die_part_repo.list_parts_for_scope(db, location=loc, vehicle_model=vehicle)
        die_by_number = {normalize_part_number_token(row["part_number"]): row for row in die_parts}
        missing = [
            row.part_number for row in parse_result.rows if row.part_number not in die_by_number
        ]
        if missing:
            preview = "、".join(missing[:20])
            extra = f" 等 {len(missing)} 个" if len(missing) > 20 else ""
            raise BusinessException(
                f"以下零件号不在该基地+项目模具布点中（无模具则无需检具费）：{preview}{extra}"
            )

        stored_path = self._save_file(file_content, original_name, loc, vehicle)
        audit = audit_create(current_user)
        payloads = [
            StampingGaugeFeeInsert(
                location=loc,
                vehicle_model=vehicle,
                part_number=die_by_number[row.part_number]["part_number"],
                part_name=die_by_number[row.part_number]["part_name"] or None,
                gauge_fee=row.gauge_fee,
                allocation_qty=row.allocation_qty,
                status=row.status,
                created_by=audit["created_by"],
                updated_by=audit["updated_by"],
            )
            for row in parse_result.rows
        ]
        try:
            self.repository.delete_by_scope(db, location=loc, vehicle_model=vehicle)
            self.repository.bulk_create(db, payloads)
            register_existing(
                db,
                file_category="stamping_gauge_fee",
                stored_relpath=to_upload_relpath(stored_path),
                original_filename=original_name,
                current_user=current_user,
                location=loc,
                vehicle_model=vehicle,
            )
            db.commit()
        except IntegrityError:
            db.rollback()
            raise BusinessException(
                "检具费零件号冲突，请检查文件后重新上传",
                code=409,
            ) from None
        except Exception:
            db.rollback()
            logger.exception("检具费上传失败: location=%s vehicle=%s", loc, vehicle)
            raise

        message = f"导入成功：基地「{loc}」、项目「{vehicle}」，覆盖写入 {len(payloads)} 条"
        return StampingGaugeFeeImportResultVO(
            location=loc,
            vehicle_model=vehicle,
            imported_count=len(payloads),
            message=message,
        )

    def _require_die_scope(self, db: Session, location: str, vehicle_model: str) -> tuple[str, str]:
        loc = LocationService().require_enabled(db, (location or "").strip())
        vehicle = VehicleModelService().require_registered(db, loc, vehicle_model)
        if not self.die_part_repo.exists_location_vehicle_model(
            db, location=loc, vehicle_model=vehicle
        ):
            raise BusinessException("该基地+项目没有模具布点，无需维护检具费。请先上传模具布点")
        return loc, vehicle

    def _save_file(
        self,
        file_content: bytes,
        filename: str,
        location: str,
        vehicle_model: str,
    ) -> Path:
        safe_location = location.replace("/", "_").replace("\\", "_")
        safe_vehicle = vehicle_model.replace("/", "_").replace("\\", "_")
        stamp = now().strftime("%Y%m%d_%H%M%S")
        folder = settings.UPLOAD_DIR / safe_location / safe_vehicle / "gauge_fee"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{stamp}_{filename}"
        target.write_bytes(file_content)
        return target
