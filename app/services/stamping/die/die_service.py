"""冲压模具查询、更新、按作用域删除。"""

from sqlalchemy.orm import Session

from app.common.audit import audit_update
from app.common.vehicle_model import normalize_vehicle_model
from app.exceptions.base import BusinessException, NotFoundException
from app.repositories.stamping.stamping_die_repository import (
    StampingDiePartRepository,
    StampingDieProcessRepository,
)
from app.repositories.stamping.stamping_part_repository import StampingPartRepository
from app.schemas.vo.stamping_die_vo import (
    StampingDieAllocRatioUpdate,
    StampingDieBatchDeleteResultVO,
    StampingDiePartDetailVO,
    StampingDiePartListVO,
    StampingDiePartQuery,
    StampingDieProcessVO,
    StampingDieScopeDTO,
    StampingDieScopeFilterVO,
)
from app.schemas.vo.user_vo import UserVO


class StampingDieService:
    def __init__(self) -> None:
        self.die_part_repo = StampingDiePartRepository()
        self.die_process_repo = StampingDieProcessRepository()
        self.stamping_part_repo = StampingPartRepository()

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
        vehicle_model: str | None = None,
        stamping_supplier: str | None = None,
    ) -> StampingDieScopeFilterVO:
        location_value = (location or "").strip() or None
        vehicle_value = normalize_vehicle_model(vehicle_model) or None
        supplier_value = (stamping_supplier or "").strip() or None
        raw = self.stamping_part_repo.get_cascade_filter_options(
            db,
            location=location_value,
            stamping_supplier=None,
            vehicle_model=None,
        )
        suppliers: list[str] = []
        versions: list[str] = []
        if location_value and vehicle_value:
            suppliers = self.die_part_repo.list_distinct_suppliers(
                db, location=location_value, vehicle_model=vehicle_value
            )
            versions = self.die_part_repo.list_distinct_versions(
                db,
                location=location_value,
                vehicle_model=vehicle_value,
                stamping_supplier=supplier_value,
            )
        return StampingDieScopeFilterVO(
            locations=list(raw["locations"]),
            vehicle_models=list(raw["vehicle_models"]),
            stamping_suppliers=suppliers,
            versions=versions,
        )

    def paginate(
        self, db: Session, query: StampingDiePartQuery
    ) -> tuple[list[StampingDiePartListVO], int]:
        location, vehicle_model = self._require_scope(query.location, query.vehicle_model)
        skip = (query.page - 1) * query.size
        parts, total = self.die_part_repo.paginate(
            db,
            location=location,
            vehicle_model=vehicle_model,
            stamping_supplier=query.stamping_supplier,
            version=query.version,
            part_number=query.part_number,
            skip=skip,
            limit=query.size,
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
        try:
            deleted = self.die_part_repo.delete_scope(
                db, location=location, vehicle_model=vehicle_model
            )
            db.commit()
        except Exception:
            db.rollback()
            raise
        return StampingDieBatchDeleteResultVO(deleted_parts=deleted)
