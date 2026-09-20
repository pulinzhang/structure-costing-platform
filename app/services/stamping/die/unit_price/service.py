"""冲压模具单价档案维护。"""

from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import audit_create, audit_update
from app.common.vehicle_model import normalize_vehicle_model
from app.exceptions.base import BusinessException, NotFoundException
from app.repositories.stamping.die.repository import StampingDiePartRepository
from app.repositories.stamping.die.unit_price import StampingDieUnitPriceRepository
from app.schemas.dto.stamping_die_unit_price_dto import (
    StampingDieUnitPriceCreate,
    StampingDieUnitPriceInsert,
    StampingDieUnitPricePatch,
    StampingDieUnitPriceQuery,
    StampingDieUnitPriceUpdate,
)
from app.schemas.vo.stamping_die_unit_price_vo import (
    StampingDieUnitPriceFilterVO,
    StampingDieUnitPriceVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.location.location_service import LocationService
from app.services.masterdata.vehicle_model.vehicle_model_service import VehicleModelService

logger = logging.getLogger("service.stamping_die_unit_price")


class StampingDieUnitPriceService:
    def __init__(self) -> None:
        self.repository = StampingDieUnitPriceRepository()
        self.die_part_repo = StampingDiePartRepository()

    def list_scope_filters(self, db: Session, location: str | None) -> StampingDieUnitPriceFilterVO:
        location_service = LocationService()
        location_value = (location or "").strip() or None
        return StampingDieUnitPriceFilterVO(
            locations=location_service.list_enabled(db),
            vehicle_models=VehicleModelService().list_filter_codes(db, location_value),
        )

    def paginate(
        self, db: Session, query: StampingDieUnitPriceQuery
    ) -> tuple[list[StampingDieUnitPriceVO], int]:
        location_raw = (query.location or "").strip() or None
        locations: list[str] | None = None
        if location_raw:
            locations = LocationService().expand_for_query(db, location_raw)
            if not locations:
                return [], 0
        vehicle = normalize_vehicle_model(query.vehicle_model) if query.vehicle_model else None
        skip = (query.page - 1) * query.size
        rows, total = self.repository.paginate(
            db,
            locations=locations,
            vehicle_model=vehicle,
            status=query.status,
            skip=skip,
            limit=query.size,
        )
        return [StampingDieUnitPriceVO.model_validate(row) for row in rows], total

    def get_by_id(self, db: Session, record_id: int) -> StampingDieUnitPriceVO:
        record = self.repository.get_by_id(db, record_id)
        if record is None:
            raise NotFoundException(f"模具单价不存在: id={record_id}")
        return StampingDieUnitPriceVO.model_validate(record)

    def create(
        self,
        db: Session,
        dto: StampingDieUnitPriceCreate,
        current_user: UserVO,
    ) -> StampingDieUnitPriceVO:
        location, vehicle_model = self._require_scope(db, dto.location, dto.vehicle_model)
        self._reject_duplicate_scope(db, location, vehicle_model)
        audit = audit_create(current_user)
        try:
            record = self.repository.create(
                db,
                StampingDieUnitPriceInsert(
                    location=location,
                    vehicle_model=vehicle_model,
                    steel_plate_unit_price=dto.steel_plate_unit_price,
                    progressive_die_unit_price=dto.progressive_die_unit_price,
                    allocation_qty=dto.allocation_qty,
                    status=dto.status,
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                ),
            )
            db.commit()
            return StampingDieUnitPriceVO.model_validate(record)
        except IntegrityError:
            db.rollback()
            raise BusinessException(
                self._duplicate_scope_message(location, vehicle_model),
                code=409,
            ) from None
        except Exception:
            db.rollback()
            logger.exception("创建模具单价失败: location=%s vehicle=%s", location, vehicle_model)
            raise

    def update(
        self,
        db: Session,
        record_id: int,
        dto: StampingDieUnitPriceUpdate,
        current_user: UserVO,
    ) -> StampingDieUnitPriceVO:
        if not dto.model_fields_set:
            raise BusinessException("没有提供任何更新字段")
        record = self.repository.get_by_id(db, record_id)
        if record is None:
            raise NotFoundException(f"模具单价不存在: id={record_id}")
        location = dto.location if "location" in dto.model_fields_set else record.location
        vehicle_model = (
            dto.vehicle_model if "vehicle_model" in dto.model_fields_set else record.vehicle_model
        )
        location, vehicle_model = self._require_scope(db, location or "", vehicle_model or "")
        self._reject_duplicate_scope(db, location, vehicle_model, exclude_id=record.id)
        audit = audit_update(current_user)
        patch: StampingDieUnitPricePatch = {"updated_by": audit["updated_by"]}
        if location != record.location:
            patch["location"] = location
        if vehicle_model != record.vehicle_model:
            patch["vehicle_model"] = vehicle_model
        if "steel_plate_unit_price" in dto.model_fields_set:
            if dto.steel_plate_unit_price is None:
                raise BusinessException("钢板模单价不能为空")
            patch["steel_plate_unit_price"] = dto.steel_plate_unit_price
        if "progressive_die_unit_price" in dto.model_fields_set:
            if dto.progressive_die_unit_price is None:
                raise BusinessException("级进模单价不能为空")
            patch["progressive_die_unit_price"] = dto.progressive_die_unit_price
        if "allocation_qty" in dto.model_fields_set:
            if dto.allocation_qty is None:
                raise BusinessException("项目分摊数量不能为空")
            patch["allocation_qty"] = dto.allocation_qty
        if "status" in dto.model_fields_set:
            if dto.status is None:
                raise BusinessException("状态不能为空")
            patch["status"] = dto.status
        try:
            record = self.repository.apply_patch(db, record, patch)
            db.commit()
            return StampingDieUnitPriceVO.model_validate(record)
        except IntegrityError:
            db.rollback()
            raise BusinessException(
                self._duplicate_scope_message(location, vehicle_model),
                code=409,
            ) from None
        except Exception:
            db.rollback()
            logger.exception("更新模具单价失败: id=%s", record_id)
            raise

    def delete(self, db: Session, record_id: int) -> None:
        record = self.repository.get_by_id(db, record_id)
        if record is None:
            raise NotFoundException(f"模具单价不存在: id={record_id}")
        try:
            self.repository.delete(db, record)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("删除模具单价失败: id=%s", record_id)
            raise

    @staticmethod
    def _duplicate_scope_message(location: str, vehicle_model: str) -> str:
        return (
            f"基地「{location}」、项目「{vehicle_model}」已维护模具单价，不能重复保存。"
            "请到列表中打开已有记录修改。"
        )

    def _reject_duplicate_scope(
        self,
        db: Session,
        location: str,
        vehicle_model: str,
        *,
        exclude_id: int | None = None,
    ) -> None:
        existing = self.repository.get_by_scope(
            db,
            location=location,
            vehicle_model=vehicle_model,
            exclude_id=exclude_id,
        )
        if existing:
            raise BusinessException(
                self._duplicate_scope_message(location, vehicle_model),
                code=409,
            )

    def _require_scope(self, db: Session, location: str, vehicle_model: str) -> tuple[str, str]:
        loc = (location or "").strip()
        vehicle = normalize_vehicle_model(vehicle_model) or ""
        if not loc:
            raise BusinessException("请选择采购基地")
        if not vehicle:
            raise BusinessException("请选择项目")
        loc = LocationService().require_enabled(db, loc)
        vehicle = VehicleModelService().require_registered(db, loc, vehicle)
        return loc, vehicle
