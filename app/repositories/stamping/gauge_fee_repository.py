"""冲压检具费档案数据访问。"""

from decimal import Decimal
from typing import TypedDict

from sqlalchemy import case, func
from sqlalchemy.orm import Query, Session

from app.common.part_number import part_number_like_pattern
from app.models.stamping.gauge_fee import STATUS_EFFECTIVE, STATUS_INVALID, StampingGaugeFee
from app.repositories.persist import apply_payload_fields, model_from_payload
from app.schemas.dto.stamping_gauge_fee_dto import StampingGaugeFeeInsert, StampingGaugeFeePatch


class StampingGaugeFeeFilterSummary(TypedDict):
    """HUD 汇总：与列表同一套筛选（含状态）。"""

    total_count: int
    effective_count: int
    invalid_count: int
    total_gauge_fee: Decimal


def _sql_money(value: object) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


class StampingGaugeFeeRepository:
    def get_by_id(self, db: Session, record_id: int) -> StampingGaugeFee | None:
        return db.query(StampingGaugeFee).filter(StampingGaugeFee.id == record_id).first()

    def get_effective_by_part(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        part_number: str,
    ) -> StampingGaugeFee | None:
        return (
            db.query(StampingGaugeFee)
            .filter(
                StampingGaugeFee.location == location,
                StampingGaugeFee.vehicle_model == vehicle_model,
                StampingGaugeFee.part_number == part_number,
                StampingGaugeFee.status == STATUS_EFFECTIVE,
            )
            .first()
        )

    def map_effective_by_part_numbers(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        part_numbers: list[str],
    ) -> dict[str, tuple[Decimal, Decimal]]:
        """生效检具档：零件号 → (gauge_fee 万元, allocation_qty 万台)。"""
        if not part_numbers:
            return {}
        mapped: dict[str, tuple[Decimal, Decimal]] = {}
        unique_numbers = list(dict.fromkeys(part_numbers))
        for index in range(0, len(unique_numbers), 400):
            chunk = unique_numbers[index : index + 400]
            rows = (
                db.query(
                    StampingGaugeFee.part_number,
                    StampingGaugeFee.gauge_fee,
                    StampingGaugeFee.allocation_qty,
                )
                .filter(
                    StampingGaugeFee.location == location,
                    StampingGaugeFee.vehicle_model == vehicle_model,
                    StampingGaugeFee.status == STATUS_EFFECTIVE,
                    StampingGaugeFee.part_number.in_(chunk),
                )
                .all()
            )
            for part_number, gauge_fee, allocation_qty in rows:
                mapped[str(part_number)] = (_sql_money(gauge_fee), _sql_money(allocation_qty))
        return mapped

    def count_effective(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str | None = None,
    ) -> int:
        query = db.query(StampingGaugeFee).filter(
            StampingGaugeFee.location == location,
            StampingGaugeFee.status == STATUS_EFFECTIVE,
        )
        if vehicle_model:
            query = query.filter(StampingGaugeFee.vehicle_model == vehicle_model)
        return query.count()

    def list_page(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None,
        part_number: str | None,
        status: str | None,
        skip: int,
        limit: int,
    ) -> list[StampingGaugeFee]:
        return (
            self._filtered_query(
                db,
                location=location,
                locations=locations,
                vehicle_model=vehicle_model,
                part_number=part_number,
                status=status,
            )
            .order_by(
                StampingGaugeFee.location.asc(),
                StampingGaugeFee.vehicle_model.asc(),
                StampingGaugeFee.part_number.asc(),
                StampingGaugeFee.id.asc(),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def list_for_export(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None,
        part_number: str | None,
        status: str | None,
    ) -> list[StampingGaugeFee]:
        return (
            self._filtered_query(
                db,
                location=location,
                locations=locations,
                vehicle_model=vehicle_model,
                part_number=part_number,
                status=status,
            )
            .order_by(
                StampingGaugeFee.location.asc(),
                StampingGaugeFee.vehicle_model.asc(),
                StampingGaugeFee.part_number.asc(),
                StampingGaugeFee.id.asc(),
            )
            .all()
        )

    def summarize_by_filters(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None,
        part_number: str | None,
        status: str | None,
    ) -> StampingGaugeFeeFilterSummary:
        query = self._filtered_query(
            db,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            part_number=part_number,
            status=status,
        )
        row = query.with_entities(
            func.count(StampingGaugeFee.id).label("total_count"),
            func.coalesce(func.sum(StampingGaugeFee.gauge_fee), 0).label("total_gauge_fee"),
            func.coalesce(
                func.sum(case((StampingGaugeFee.status == STATUS_EFFECTIVE, 1), else_=0)),
                0,
            ).label("effective_count"),
            func.coalesce(
                func.sum(case((StampingGaugeFee.status == STATUS_INVALID, 1), else_=0)),
                0,
            ).label("invalid_count"),
        ).one()
        return {
            "total_count": int(row.total_count or 0),
            "effective_count": int(row.effective_count or 0),
            "invalid_count": int(row.invalid_count or 0),
            "total_gauge_fee": _sql_money(row.total_gauge_fee),
        }

    def _filtered_query(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None,
        part_number: str | None,
        status: str | None,
    ) -> Query[StampingGaugeFee]:
        query = db.query(StampingGaugeFee)
        if locations is not None:
            query = query.filter(StampingGaugeFee.location.in_(locations))
        elif location:
            query = query.filter(StampingGaugeFee.location == location)
        if vehicle_model:
            query = query.filter(StampingGaugeFee.vehicle_model == vehicle_model)
        if part_number:
            query = query.filter(
                StampingGaugeFee.part_number.like(
                    part_number_like_pattern(part_number),
                    escape="\\",
                )
            )
        if status:
            query = query.filter(StampingGaugeFee.status == status)
        return query

    def delete_by_scope(self, db: Session, *, location: str, vehicle_model: str) -> int:
        return (
            db.query(StampingGaugeFee)
            .filter(
                StampingGaugeFee.location == location,
                StampingGaugeFee.vehicle_model == vehicle_model,
            )
            .delete(synchronize_session=False)
        )

    def bulk_create(self, db: Session, payloads: list[StampingGaugeFeeInsert]) -> None:
        records = [model_from_payload(StampingGaugeFee, payload) for payload in payloads]
        db.add_all(records)
        db.flush()

    def apply_patch(
        self,
        db: Session,
        record: StampingGaugeFee,
        patch: StampingGaugeFeePatch,
    ) -> StampingGaugeFee:
        apply_payload_fields(record, patch)
        db.flush()
        return record

    def delete(self, db: Session, record: StampingGaugeFee) -> None:
        db.delete(record)
        db.flush()
