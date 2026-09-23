"""项目：卡片列表与 CRUD。"""

from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import audit_create, audit_update
from app.common.timezone import now
from app.exceptions.base import BusinessException, NotFoundException
from app.models.masterdata.vehicle_model import VehicleModel
from app.repositories.masterdata.vehicle_model.vehicle_model_repository import (
    VehicleModelRepository,
)
from app.schemas.dto.vehicle_model_dto import (
    VehicleModelCreateDTO,
    VehicleModelInsert,
    VehicleModelPatch,
    VehicleModelUpdateDTO,
)
from app.schemas.vo.user_vo import UserVO
from app.schemas.vo.vehicle_model_vo import (
    PERIOD_INTRODUCIBLE,
    PERIOD_PENDING,
    LocationCardVO,
    VehicleModelListVO,
    VehicleModelVO,
)
from app.services.masterdata.location.service import LocationService
from app.services.masterdata.vehicle_model.identity import (
    normalize,
    period_status,
    require_row,
    to_vo,
    validate_period,
)
from app.services.settings.schema_comment.service import STILL_REFERENCED, ensure_deletable

logger = logging.getLogger("service.vehicle_model")


def list_page(
    repository: VehicleModelRepository,
    location_service: LocationService,
    db: Session,
) -> VehicleModelListVO:
    clock = now()
    as_of_year = clock.year
    as_of_month = clock.month
    location_rows = location_service.list_all(db)
    items_by_location: dict[str, list[VehicleModel]] = {}
    for row in repository.list_all(db):
        items_by_location.setdefault(row.location, []).append(row)

    cards: list[LocationCardVO] = []
    items: list[VehicleModelVO] = []
    for location_vo in location_rows:
        rows = items_by_location.get(location_vo.location, [])
        pending = 0
        introducible = 0
        expired = 0
        for row in rows:
            status = period_status(row, as_of_year, as_of_month)
            items.append(to_vo(row, status))
            if status == PERIOD_PENDING:
                pending += 1
            elif status == PERIOD_INTRODUCIBLE:
                introducible += 1
            else:
                expired += 1
        cards.append(
            LocationCardVO(
                location=location_vo.location,
                is_enabled=location_vo.is_enabled,
                project_count=len(rows),
                introducible_count=introducible if location_vo.is_enabled else 0,
                pending_count=pending,
                expired_count=expired,
            )
        )
    return VehicleModelListVO(
        as_of_year=as_of_year,
        as_of_month=as_of_month,
        locations=cards,
        items=items,
    )


def create_vehicle_model(
    repository: VehicleModelRepository,
    location_service: LocationService,
    db: Session,
    dto: VehicleModelCreateDTO,
    current_user: UserVO,
) -> VehicleModelVO:
    canonical = location_service.require_enabled(db, dto.location)
    code = normalize(dto.vehicle_model)
    if not code:
        raise BusinessException("项目代号无效")
    validate_period(
        dto.effective_year,
        dto.effective_month,
        dto.expiry_year,
        dto.expiry_month,
    )
    if repository.get(db, canonical, code) is not None:
        raise BusinessException("该基地已有此项目")
    audit = audit_create(current_user)
    try:
        record = repository.create(
            db,
            VehicleModelInsert(
                location=canonical,
                vehicle_model=code,
                effective_year=dto.effective_year,
                effective_month=dto.effective_month,
                expiry_year=dto.expiry_year,
                expiry_month=dto.expiry_month,
                current_supplied_units=dto.current_supplied_units,
                created_by=audit["created_by"],
                updated_by=audit["updated_by"],
            ),
        )
        db.commit()
        db.refresh(record)
    except IntegrityError:
        db.rollback()
        raise BusinessException("该基地已有此项目") from None
    except BusinessException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("创建项目失败")
        raise
    clock = now()
    return to_vo(record, period_status(record, clock.year, clock.month))


def update_vehicle_model(
    repository: VehicleModelRepository,
    db: Session,
    location: str,
    vehicle_model: str,
    dto: VehicleModelUpdateDTO,
    current_user: UserVO,
) -> VehicleModelVO:
    record = require_row(repository, location, vehicle_model, db)
    validate_period(
        dto.effective_year,
        dto.effective_month,
        dto.expiry_year,
        dto.expiry_month,
    )
    audit = audit_update(current_user)
    patch: VehicleModelPatch = {
        "effective_year": dto.effective_year,
        "effective_month": dto.effective_month,
        "expiry_year": dto.expiry_year,
        "expiry_month": dto.expiry_month,
        "current_supplied_units": dto.current_supplied_units,
        "updated_by": audit["updated_by"],
    }
    try:
        repository.apply_patch(db, record, patch)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise BusinessException("仍被引用，不能修改") from None
    except BusinessException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("更新项目失败")
        raise
    refreshed = repository.get(db, record.location, record.vehicle_model)
    if refreshed is None:
        raise NotFoundException("项目不存在")
    clock = now()
    return to_vo(refreshed, period_status(refreshed, clock.year, clock.month))


def delete_vehicle_model(
    repository: VehicleModelRepository,
    db: Session,
    location: str,
    vehicle_model: str,
) -> None:
    record = require_row(repository, location, vehicle_model, db)
    try:
        ensure_deletable(
            db,
            "vehicle_models",
            [{"location": record.location, "vehicle_model": record.vehicle_model}],
            subject=f"项目「{record.vehicle_model}」",
        )
        repository.delete(db, record)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise BusinessException(STILL_REFERENCED) from None
    except BusinessException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("删除项目失败")
        raise
