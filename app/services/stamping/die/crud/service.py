"""冲压模具查询、更新、按作用域删除。工程变更见 engineering/service.py。"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import audit_update
from app.common.period import resolve_as_of_month
from app.common.vehicle_model import normalize_vehicle_model
from app.exceptions.base import BusinessException, NotFoundException
from app.repositories.stamping.die.repository import (
    StampingDiePartRepository,
    StampingDieProcessRepository,
)
from app.schemas.dto.stamping_die_dto import (
    StampingDieAllocRatioUpdate,
    StampingDiePartQuery,
    StampingDieScopeDTO,
)
from app.schemas.vo.stamping_die_vo import (
    StampingDieBatchDeleteResultVO,
    StampingDiePartDetailVO,
    StampingDiePartListVO,
    StampingDieProcessVO,
    StampingDieScopeFilterVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.location.location_service import LocationService
from app.services.masterdata.vehicle_model.vehicle_model_service import VehicleModelService


class StampingDieService:
    def __init__(self) -> None:
        self.die_part_repo = StampingDiePartRepository()
        self.die_process_repo = StampingDieProcessRepository()

    def _require_scope(self, location: str, vehicle_model: str) -> tuple[str, str]:
        loc = (location or "").strip()
        vehicle = normalize_vehicle_model(vehicle_model) or ""
        if not loc:
            raise BusinessException("请选择采购基地")
        if not vehicle:
            raise BusinessException("请选择项目")
        return loc, vehicle

    def list_scope_filters(
        self,
        db: Session,
        location: str | None,
        *,
        year: int | None = None,
        month: int | None = None,
    ) -> StampingDieScopeFilterVO:
        location_service = LocationService()
        location_value = (location or "").strip() or None
        vehicle_svc = VehicleModelService()
        vehicle_models: list[str]
        if location_value and year is not None:
            if month is not None:
                vehicle_models = vehicle_svc.list_introducible(db, location_value, year, month)
            else:
                vehicle_models = vehicle_svc.list_overlaps_year(db, location_value, year)
        else:
            vehicle_models = vehicle_svc.list_filter_codes(db, location_value)
        return StampingDieScopeFilterVO(
            locations=location_service.list_enabled(db),
            vehicle_models=vehicle_models,
        )

    def paginate(
        self, db: Session, query: StampingDiePartQuery
    ) -> tuple[list[StampingDiePartListVO], int]:
        location_raw = (query.location or "").strip() or None
        locations: list[str] | None = None
        if location_raw:
            locations = LocationService().expand_for_query(db, location_raw)
            if not locations:
                return [], 0
        vehicle = normalize_vehicle_model(query.vehicle_model) if query.vehicle_model else None
        skip = (query.page - 1) * query.size
        as_of_year, as_of_month = resolve_as_of_month(query.year, query.month)
        parts, total = self.die_part_repo.paginate(
            db,
            locations=locations,
            vehicle_model=vehicle,
            part_number=query.part_number,
            skip=skip,
            limit=query.size,
            as_of_year=as_of_year,
            as_of_month=as_of_month,
            include_expired=query.include_expired,
        )
        counts = self.die_part_repo.count_processes_by_part_ids(db, [part.id for part in parts])
        rows: list[StampingDiePartListVO] = []
        for part in parts:
            row = StampingDiePartListVO.model_validate(part)
            rows.append(row.model_copy(update={"process_count": counts.get(part.id, 0)}))
        return rows, total

    def get_part(self, db: Session, part_id: int) -> StampingDiePartDetailVO:
        part = self.die_part_repo.get_by_id(db, part_id)
        if not part:
            raise NotFoundException(f"模具零件不存在: id={part_id}")
        return StampingDiePartDetailVO.model_validate(part)

    def update_alloc_ratio(
        self,
        db: Session,
        process_id: int,
        dto: StampingDieAllocRatioUpdate,
        current_user: UserVO,
    ) -> StampingDieProcessVO:
        process = self.die_process_repo.get_by_id(db, process_id)
        if not process:
            raise NotFoundException(f"模具工序不存在: id={process_id}")
        process.alloc_ratio = dto.alloc_ratio
        audit = audit_update(current_user)
        process.updated_by = audit["updated_by"]
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise
        return StampingDieProcessVO.model_validate(process)

    def delete_scope(self, db: Session, dto: StampingDieScopeDTO) -> StampingDieBatchDeleteResultVO:
        location, vehicle_model = self._require_scope(dto.location, dto.vehicle_model)
        locations = LocationService().expand_for_query(db, location)
        if not locations:
            return StampingDieBatchDeleteResultVO(deleted_parts=0)
        try:
            deleted = self.die_part_repo.delete_scope(
                db, locations=locations, vehicle_model=vehicle_model
            )
            db.commit()
        except IntegrityError:
            db.rollback()
            raise BusinessException("仍被冲压模具费引用，请先删除对应模具费后再删") from None
        except Exception:
            db.rollback()
            raise
        return StampingDieBatchDeleteResultVO(deleted_parts=deleted)

    def list_die_numbers_for_scope(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
    ) -> list[str]:
        return self.die_process_repo.list_die_numbers_for_scope(
            db, location=location, vehicle_model=vehicle_model
        )
