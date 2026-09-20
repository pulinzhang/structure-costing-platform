"""冲压模具单价档案数据访问。"""

from sqlalchemy.orm import Session

from app.models.stamping.die_unit_price import STATUS_EFFECTIVE, StampingDieUnitPrice
from app.repositories.persist import apply_payload_fields, model_from_payload
from app.schemas.dto.stamping_die_unit_price_dto import (
    StampingDieUnitPriceInsert,
    StampingDieUnitPricePatch,
)


class StampingDieUnitPriceRepository:
    def get_by_id(self, db: Session, record_id: int) -> StampingDieUnitPrice | None:
        return db.query(StampingDieUnitPrice).filter(StampingDieUnitPrice.id == record_id).first()

    def get_by_scope(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        exclude_id: int | None = None,
    ) -> StampingDieUnitPrice | None:
        query = db.query(StampingDieUnitPrice).filter(
            StampingDieUnitPrice.location == location,
            StampingDieUnitPrice.vehicle_model == vehicle_model,
        )
        if exclude_id is not None:
            query = query.filter(StampingDieUnitPrice.id != exclude_id)
        return query.first()

    def get_effective(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
    ) -> StampingDieUnitPrice | None:
        return (
            db.query(StampingDieUnitPrice)
            .filter(
                StampingDieUnitPrice.location == location,
                StampingDieUnitPrice.vehicle_model == vehicle_model,
                StampingDieUnitPrice.status == STATUS_EFFECTIVE,
            )
            .first()
        )

    def paginate(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None,
        status: str | None,
        skip: int,
        limit: int,
    ) -> tuple[list[StampingDieUnitPrice], int]:
        query = db.query(StampingDieUnitPrice)
        if locations is not None:
            query = query.filter(StampingDieUnitPrice.location.in_(locations))
        elif location:
            query = query.filter(StampingDieUnitPrice.location == location)
        if vehicle_model:
            query = query.filter(StampingDieUnitPrice.vehicle_model == vehicle_model)
        if status:
            query = query.filter(StampingDieUnitPrice.status == status)
        total = query.count()
        rows = (
            query.order_by(
                StampingDieUnitPrice.location.asc(),
                StampingDieUnitPrice.vehicle_model.asc(),
                StampingDieUnitPrice.id.asc(),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
        return rows, total

    def create(self, db: Session, payload: StampingDieUnitPriceInsert) -> StampingDieUnitPrice:
        record = model_from_payload(StampingDieUnitPrice, payload)
        db.add(record)
        db.flush()
        return record

    def apply_patch(
        self,
        db: Session,
        record: StampingDieUnitPrice,
        patch: StampingDieUnitPricePatch,
    ) -> StampingDieUnitPrice:
        apply_payload_fields(record, patch)
        db.flush()
        return record

    def delete(self, db: Session, record: StampingDieUnitPrice) -> None:
        db.delete(record)
        db.flush()
