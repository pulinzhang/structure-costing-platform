"""项目：Excel 整单导入。"""

from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import audit_create
from app.exceptions.base import BusinessException
from app.parsers.masterdata.vehicle_model_parser import parse_vehicle_model_excel
from app.repositories.masterdata.vehicle_model import VehicleModelRepository
from app.schemas.dto.vehicle_model_dto import VehicleModelInsert
from app.schemas.vo.user_vo import UserVO
from app.schemas.vo.vehicle_model_vo import VehicleModelUploadResultVO
from app.services.masterdata.location import LocationService
from app.services.masterdata.vehicle_model.identity import normalize, validate_period

logger = logging.getLogger("service.vehicle_model")


def process_upload(
    repository: VehicleModelRepository,
    location_service: LocationService,
    db: Session,
    file_content: bytes,
    current_user: UserVO,
) -> VehicleModelUploadResultVO:
    parsed = parse_vehicle_model_excel(file_content)
    if parsed.errors:
        raise BusinessException("；".join(parsed.errors))
    if not parsed.rows:
        raise BusinessException("没有可导入的项目行")

    pending: list[VehicleModelInsert] = []
    seen: dict[tuple[str, str], tuple[int, int, int | None, int | None, int]] = {}
    skipped_count = 0
    errors: list[str] = []
    audit = audit_create(current_user)

    for row in parsed.rows:
        try:
            canonical = location_service.require_enabled(db, row.location)
        except BusinessException as exc:
            errors.append(f"第 {row.row_number} 行：{exc.message}")
            continue
        code = normalize(row.vehicle_model)
        if not code:
            errors.append(f"第 {row.row_number} 行：项目代号无效")
            continue
        try:
            validate_period(
                row.effective_year,
                row.effective_month,
                row.expiry_year,
                row.expiry_month,
            )
        except BusinessException as exc:
            errors.append(f"第 {row.row_number} 行：{exc.message}")
            continue
        fingerprint = (
            row.effective_year,
            row.effective_month,
            row.expiry_year,
            row.expiry_month,
            row.current_supplied_units,
        )
        key = (canonical, code)
        if key in seen:
            if seen[key] == fingerprint:
                skipped_count += 1
                continue
            errors.append(
                f"第 {row.row_number} 行：与文件内已有「{canonical} / {code}」生效失效或供货台数不一致"
            )
            continue
        seen[key] = fingerprint
        if repository.get(db, canonical, code) is not None:
            skipped_count += 1
            continue
        pending.append(
            VehicleModelInsert(
                location=canonical,
                vehicle_model=code,
                effective_year=row.effective_year,
                effective_month=row.effective_month,
                expiry_year=row.expiry_year,
                expiry_month=row.expiry_month,
                current_supplied_units=row.current_supplied_units,
                created_by=audit["created_by"],
                updated_by=audit["updated_by"],
            )
        )

    if errors:
        raise BusinessException("；".join(errors))

    try:
        for payload in pending:
            repository.create(db, payload)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise BusinessException("该基地已有此项目") from None
    except BusinessException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("导入项目失败")
        raise
    return VehicleModelUploadResultVO(
        created_count=len(pending),
        skipped_count=skipped_count,
    )
