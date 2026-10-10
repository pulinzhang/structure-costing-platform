"""冲压模具费查询：列表、导出、范围、汇总、下拉。"""

from decimal import Decimal

from sqlalchemy import case, func
from sqlalchemy.orm import Query, Session, joinedload, noload

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING
from app.models.stamping.die_fee import StampingDieFee
from app.repositories.stamping.die_fee.types import DieFeeFilterSummary, sql_money


class StampingDieFeeQueries:
    def get_by_id(self, db: Session, fee_id: int) -> StampingDieFee | None:
        return (
            db.query(StampingDieFee)
            .options(joinedload(StampingDieFee.items))
            .filter(StampingDieFee.id == fee_id)
            .first()
        )

    def list_by_ids(self, db: Session, fee_ids: list[int]) -> list[StampingDieFee]:
        if not fee_ids:
            return []
        return (
            db.query(StampingDieFee)
            .options(joinedload(StampingDieFee.items))
            .filter(StampingDieFee.id.in_(fee_ids))
            .all()
        )

    def get_by_year_location_vehicle_part(
        self,
        db: Session,
        *,
        year: int,
        location: str | None = None,
        vehicle_model: str,
        part_number: str,
    ) -> StampingDieFee | None:
        return (
            db.query(StampingDieFee)
            .options(noload(StampingDieFee.items))
            .filter(
                StampingDieFee.year == year,
                StampingDieFee.location == location,
                StampingDieFee.vehicle_model == vehicle_model,
                StampingDieFee.part_number == part_number,
            )
            .first()
        )

    def list_by_part_from_year(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        part_number: str,
        from_year: int,
    ) -> list[StampingDieFee]:
        """某零件 year >= from_year 的模具费结果（含各序）。"""
        return (
            db.query(StampingDieFee)
            .options(joinedload(StampingDieFee.items))
            .filter(
                StampingDieFee.location == location,
                StampingDieFee.vehicle_model == vehicle_model,
                StampingDieFee.part_number == part_number,
                StampingDieFee.year >= from_year,
            )
            .order_by(StampingDieFee.year.asc(), StampingDieFee.id.asc())
            .all()
        )

    def count_by_year_location(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str | None = None,
    ) -> int:
        query = db.query(StampingDieFee).filter(
            StampingDieFee.year == year,
            StampingDieFee.location == location,
        )
        if vehicle_model:
            query = query.filter(StampingDieFee.vehicle_model == vehicle_model)
        return query.count()

    def _scope_query(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
    ) -> Query[StampingDieFee]:
        query = db.query(StampingDieFee)
        if year is not None:
            query = query.filter(StampingDieFee.year == year)
        if vehicle_model:
            query = query.filter(StampingDieFee.vehicle_model == vehicle_model)
        if locations is not None:
            query = query.filter(StampingDieFee.location.in_(locations))
        elif location:
            query = query.filter(StampingDieFee.location == location)
        return query

    def _apply_identity_filters(
        self,
        query: Query[StampingDieFee],
        *,
        stamping_supplier: str | None,
        version: str | None,
    ) -> Query[StampingDieFee]:
        if stamping_supplier:
            query = query.filter(StampingDieFee.stamping_supplier == stamping_supplier)
        if version:
            query = query.filter(StampingDieFee.version == version)
        return query

    def count_by_scope_and_statuses(
        self,
        db: Session,
        *,
        year: int,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str,
        statuses: list[str],
        stamping_supplier: str | None = None,
        version: str | None = None,
    ) -> int:
        query = self._apply_identity_filters(
            self._scope_query(
                db,
                year=year,
                location=location,
                locations=locations,
                vehicle_model=vehicle_model,
            ),
            stamping_supplier=stamping_supplier,
            version=version,
        )
        return query.filter(StampingDieFee.audit_status.in_(statuses)).count()

    def _build_list_query(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        part_number: str | None,
        audit_status: str | None,
        only_zero: bool,
        stamping_supplier: str | None = None,
        version: str | None = None,
    ) -> Query[StampingDieFee]:
        query = self._apply_identity_filters(
            self._scope_query(
                db,
                year=year,
                location=location,
                locations=locations,
                vehicle_model=vehicle_model,
            ),
            stamping_supplier=stamping_supplier,
            version=version,
        )
        if part_number:
            query = query.filter(StampingDieFee.part_number.like(f"%{part_number}%"))
        if audit_status:
            query = query.filter(StampingDieFee.audit_status == audit_status)
        if only_zero:
            query = query.filter(StampingDieFee.final_die_fee == 0)
        return query

    def paginate(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        part_number: str | None,
        audit_status: str | None,
        only_zero: bool,
        skip: int,
        limit: int,
        stamping_supplier: str | None = None,
        version: str | None = None,
    ) -> tuple[list[StampingDieFee], int]:
        query = self._build_list_query(
            db,
            year=year,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            part_number=part_number,
            audit_status=audit_status,
            only_zero=only_zero,
            stamping_supplier=stamping_supplier,
            version=version,
        )
        total = query.count()
        rows = (
            query.options(noload(StampingDieFee.items))
            .order_by(
                StampingDieFee.year.desc(),
                StampingDieFee.location.asc(),
                StampingDieFee.vehicle_model.asc(),
                StampingDieFee.id.asc(),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
        return rows, total

    def summarize_by_filters(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        part_number: str | None,
        audit_status: str | None,
        stamping_supplier: str | None = None,
        version: str | None = None,
    ) -> DieFeeFilterSummary:
        query = self._build_list_query(
            db,
            year=year,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            part_number=part_number,
            audit_status=audit_status,
            only_zero=False,
            stamping_supplier=stamping_supplier,
            version=version,
        )
        row = query.with_entities(
            func.count(StampingDieFee.id).label("total_count"),
            func.coalesce(func.sum(StampingDieFee.final_die_fee), 0).label("total_fee"),
            func.sum(case((StampingDieFee.audit_status == AUDIT_PENDING, 1), else_=0)).label(
                "pending_count"
            ),
            func.sum(case((StampingDieFee.audit_status == AUDIT_APPROVED, 1), else_=0)).label(
                "approved_count"
            ),
            func.sum(case((StampingDieFee.final_die_fee == 0, 1), else_=0)).label("zero_count"),
        ).one()
        total_count = int(row.total_count or 0)
        total_fee = sql_money(row.total_fee)
        avg_fee = (total_fee / Decimal(total_count)) if total_count else Decimal("0")
        return {
            "total_count": total_count,
            "pending_count": int(row.pending_count or 0),
            "approved_count": int(row.approved_count or 0),
            "zero_count": int(row.zero_count or 0),
            "total_fee": total_fee,
            "avg_fee": avg_fee,
        }

    def list_for_export(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        part_number: str | None,
        audit_status: str | None,
        only_zero: bool,
        stamping_supplier: str | None = None,
        version: str | None = None,
    ) -> list[StampingDieFee]:
        query = self._build_list_query(
            db,
            year=year,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            part_number=part_number,
            audit_status=audit_status,
            only_zero=only_zero,
            stamping_supplier=stamping_supplier,
            version=version,
        )
        return (
            query.options(joinedload(StampingDieFee.items))
            .order_by(
                StampingDieFee.year.desc(),
                StampingDieFee.location.asc(),
                StampingDieFee.vehicle_model.asc(),
                StampingDieFee.id.asc(),
            )
            .all()
        )

    def get_distinct_years(self, db: Session) -> list[int]:
        rows = db.query(StampingDieFee.year).distinct().order_by(StampingDieFee.year.desc()).all()
        return [row[0] for row in rows]

    def list_distinct_suppliers(
        self,
        db: Session,
        *,
        year: int | None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None,
    ) -> list[str]:
        if not year or not vehicle_model:
            return []
        if locations is not None:
            if not locations:
                return []
        elif not location:
            return []
        rows = (
            self._scope_query(
                db, year=year, location=location, locations=locations, vehicle_model=vehicle_model
            )
            .with_entities(StampingDieFee.stamping_supplier)
            .filter(
                StampingDieFee.stamping_supplier.isnot(None),
                StampingDieFee.stamping_supplier != "",
            )
            .distinct()
            .order_by(StampingDieFee.stamping_supplier.asc())
            .all()
        )
        return [row[0] for row in rows if row[0]]

    def map_final_die_fee_by_part_numbers(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        part_numbers: list[str],
    ) -> dict[str, tuple[Decimal, Decimal]]:
        """零件号 → (最终模具费 元/件, 分摊数量 万件)。"""
        if not part_numbers:
            return {}
        mapped: dict[str, tuple[Decimal, Decimal]] = {}
        unique_numbers = list(dict.fromkeys(part_numbers))
        for index in range(0, len(unique_numbers), 400):
            chunk = unique_numbers[index : index + 400]
            rows = (
                db.query(
                    StampingDieFee.part_number,
                    StampingDieFee.final_die_fee,
                    StampingDieFee.allocation_qty,
                )
                .filter(
                    StampingDieFee.year == year,
                    StampingDieFee.location == location,
                    StampingDieFee.vehicle_model == vehicle_model,
                    StampingDieFee.part_number.in_(chunk),
                )
                .all()
            )
            for part_number, final_die_fee, allocation_qty in rows:
                mapped[str(part_number)] = (
                    sql_money(final_die_fee),
                    sql_money(allocation_qty),
                )
        return mapped

    def list_distinct_versions(
        self,
        db: Session,
        *,
        year: int | None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None,
        stamping_supplier: str | None = None,
    ) -> list[str]:
        if not year or not vehicle_model:
            return []
        if locations is not None:
            if not locations:
                return []
        elif not location:
            return []
        query = self._apply_identity_filters(
            self._scope_query(
                db, year=year, location=location, locations=locations, vehicle_model=vehicle_model
            ),
            stamping_supplier=stamping_supplier,
            version=None,
        )
        rows = (
            query.with_entities(StampingDieFee.version)
            .filter(
                StampingDieFee.version.isnot(None),
                StampingDieFee.version != "",
            )
            .distinct()
            .order_by(StampingDieFee.version.asc())
            .all()
        )
        return [row[0] for row in rows if row[0]]
