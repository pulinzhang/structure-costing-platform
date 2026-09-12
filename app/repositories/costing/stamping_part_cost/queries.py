"""冲压零件核价查询：列表、导出、成功行、汇总、下拉。"""

from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import case, false, func
from sqlalchemy.orm import Query, Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING
from app.models.costing import StampingPartCost
from app.repositories.costing.stamping_part_cost.types import PartCostFilterSummary


class StampingPartCostQueries:
    def get_by_id(self, db: Session, cost_id: int) -> StampingPartCost | None:
        return db.query(StampingPartCost).filter(StampingPartCost.id == cost_id).first()

    def get_by_business_key(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        stamping_supplier: str,
        vehicle_model: str,
        version: str,
        part_number: str,
    ) -> StampingPartCost | None:
        return (
            db.query(StampingPartCost)
            .filter(
                StampingPartCost.year == year,
                StampingPartCost.month == month,
                StampingPartCost.location == location,
                StampingPartCost.stamping_supplier == stamping_supplier,
                StampingPartCost.vehicle_model == vehicle_model,
                StampingPartCost.version == version,
                StampingPartCost.part_number == part_number,
            )
            .first()
        )

    def _scope_query(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
    ) -> Query[StampingPartCost]:
        return self._build_list_query(
            db,
            year=year,
            month=month,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
        )

    def _build_list_query(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
    ) -> Query[StampingPartCost]:
        q = db.query(StampingPartCost)
        if year is not None:
            q = q.filter(StampingPartCost.year == year)
        if month is not None:
            q = q.filter(StampingPartCost.month == month)
        if locations is not None:
            q = q.filter(StampingPartCost.location.in_(locations))
        elif location is not None:
            q = q.filter(StampingPartCost.location == location)
        if stamping_suppliers is not None:
            if not stamping_suppliers:
                q = q.filter(false())
            else:
                q = q.filter(StampingPartCost.stamping_supplier.in_(stamping_suppliers))
        elif stamping_supplier is not None:
            q = q.filter(StampingPartCost.stamping_supplier == stamping_supplier)
        if vehicle_model is not None:
            q = q.filter(StampingPartCost.vehicle_model == vehicle_model)
        if version is not None:
            q = q.filter(StampingPartCost.version == version)
        if part_number:
            q = q.filter(StampingPartCost.part_number.like(f"%{part_number}%"))
        if audit_status:
            q = q.filter(StampingPartCost.audit_status == audit_status)
        return q

    def paginate(
        self,
        db: Session,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[StampingPartCost], int]:
        q = self._build_list_query(
            db,
            year=year,
            month=month,
            location=location,
            locations=locations,
            stamping_supplier=stamping_supplier,
            stamping_suppliers=stamping_suppliers,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            audit_status=audit_status,
        )
        total = q.count()
        rows = (
            q.order_by(
                StampingPartCost.year.desc(),
                StampingPartCost.month.desc(),
                StampingPartCost.location,
                StampingPartCost.stamping_supplier,
                StampingPartCost.id.asc(),
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
        month: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
    ) -> PartCostFilterSummary:
        """按与列表相同的筛选条件汇总：总成本 / 件均 / 材料费 / 加工费 / 待审 / 已审。"""
        q = self._build_list_query(
            db,
            year=year,
            month=month,
            location=location,
            locations=locations,
            stamping_supplier=stamping_supplier,
            stamping_suppliers=stamping_suppliers,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            audit_status=audit_status,
        )
        row = q.with_entities(
            func.coalesce(func.sum(StampingPartCost.unit_cost), 0).label("unit_cost_sum"),
            func.avg(StampingPartCost.unit_cost).label("avg_unit_cost"),
            func.coalesce(func.sum(StampingPartCost.material_net_per_part), 0).label(
                "material_net_per_part_sum"
            ),
            func.coalesce(func.sum(StampingPartCost.process_fee_amount), 0).label(
                "process_fee_amount_sum"
            ),
            func.sum(case((StampingPartCost.audit_status == AUDIT_PENDING, 1), else_=0)).label(
                "pending_count"
            ),
            func.sum(case((StampingPartCost.audit_status == AUDIT_APPROVED, 1), else_=0)).label(
                "approved_count"
            ),
        ).one()
        avg_value = row.avg_unit_cost
        return {
            "unit_cost_sum": Decimal(str(row.unit_cost_sum or 0)),
            "avg_unit_cost": (Decimal(str(avg_value)) if avg_value is not None else None),
            "material_net_per_part_sum": Decimal(str(row.material_net_per_part_sum or 0)),
            "process_fee_amount_sum": Decimal(str(row.process_fee_amount_sum or 0)),
            "pending_count": int(row.pending_count or 0),
            "approved_count": int(row.approved_count or 0),
        }

    def list_for_export(
        self,
        db: Session,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
    ) -> list[StampingPartCost]:
        q = self._build_list_query(
            db,
            year=year,
            month=month,
            location=location,
            locations=locations,
            stamping_supplier=stamping_supplier,
            stamping_suppliers=stamping_suppliers,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            audit_status=audit_status,
        )
        return q.order_by(
            StampingPartCost.year.desc(),
            StampingPartCost.month.desc(),
            StampingPartCost.location,
            StampingPartCost.id.asc(),
        ).all()

    def count_by_scope_and_statuses(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        statuses: list[str],
    ) -> int:
        return (
            self._scope_query(
                db,
                year=year,
                month=month,
                location=location,
                stamping_supplier=stamping_supplier,
                vehicle_model=vehicle_model,
                version=version,
            )
            .filter(StampingPartCost.audit_status.in_(statuses))
            .count()
        )

    def get_distinct_years(self, db: Session) -> list[int]:
        results = (
            db.query(StampingPartCost.year).distinct().order_by(StampingPartCost.year.desc()).all()
        )
        return [r[0] for r in results]

    def get_distinct_months(self, db: Session, year: int | None = None) -> list[int]:
        q = db.query(StampingPartCost.month).distinct()
        if year is not None:
            q = q.filter(StampingPartCost.year == year)
        results = q.order_by(StampingPartCost.month.desc()).all()
        return [r[0] for r in results if r[0]]

    def count_calc_success_with_unit_cost(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
    ) -> int:
        return (
            db.query(StampingPartCost)
            .filter(
                StampingPartCost.location == location,
                StampingPartCost.vehicle_model == vehicle_model,
                StampingPartCost.year == year,
                StampingPartCost.month == month,
                StampingPartCost.calc_status == "success",
                StampingPartCost.unit_cost.isnot(None),
            )
            .count()
        )

    def list_calc_success_with_unit_cost(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
    ) -> list[StampingPartCost]:
        return (
            db.query(StampingPartCost)
            .filter(
                StampingPartCost.location == location,
                StampingPartCost.vehicle_model == vehicle_model,
                StampingPartCost.year == year,
                StampingPartCost.month == month,
                StampingPartCost.calc_status == "success",
                StampingPartCost.unit_cost.isnot(None),
            )
            .order_by(StampingPartCost.part_number, StampingPartCost.id.asc())
            .all()
        )

    def list_success_by_part_numbers(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
        part_numbers: list[str],
    ) -> list[StampingPartCost]:
        if not part_numbers:
            return []
        unique = list(dict.fromkeys(part_numbers))
        rows: list[StampingPartCost] = []
        for offset in range(0, len(unique), 400):
            chunk = unique[offset : offset + 400]
            rows.extend(
                db.query(StampingPartCost)
                .filter(
                    StampingPartCost.location == location,
                    StampingPartCost.vehicle_model == vehicle_model,
                    StampingPartCost.year == year,
                    StampingPartCost.month == month,
                    StampingPartCost.part_number.in_(chunk),
                    StampingPartCost.calc_status == "success",
                    StampingPartCost.unit_cost.isnot(None),
                )
                .order_by(StampingPartCost.part_number, StampingPartCost.id.asc())
                .all()
            )
        return rows

    def get_distinct_locations(
        self, db: Session, year: int | None = None, month: int | None = None
    ) -> list[str]:
        q = db.query(StampingPartCost.location).distinct()
        if year is not None:
            q = q.filter(StampingPartCost.year == year)
        if month is not None:
            q = q.filter(StampingPartCost.month == month)
        results = q.order_by(StampingPartCost.location).all()
        return [r[0] for r in results if r[0]]

    def get_distinct_suppliers(
        self,
        db: Session,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
    ) -> list[str]:
        q = db.query(StampingPartCost.stamping_supplier).distinct()
        if year is not None:
            q = q.filter(StampingPartCost.year == year)
        if month is not None:
            q = q.filter(StampingPartCost.month == month)
        if locations is not None:
            q = q.filter(StampingPartCost.location.in_(locations))
        elif location is not None:
            q = q.filter(StampingPartCost.location == location)
        if vehicle_model is not None:
            q = q.filter(StampingPartCost.vehicle_model == vehicle_model)
        if version is not None:
            q = q.filter(StampingPartCost.version == version)
        results = q.order_by(StampingPartCost.stamping_supplier).all()
        return [r[0] for r in results if r[0]]

    def get_distinct_versions(
        self,
        db: Session,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        stamping_supplier: str | None = None,
    ) -> list[str]:
        q = db.query(StampingPartCost.version).distinct()
        if year is not None:
            q = q.filter(StampingPartCost.year == year)
        if month is not None:
            q = q.filter(StampingPartCost.month == month)
        if locations is not None:
            q = q.filter(StampingPartCost.location.in_(locations))
        elif location is not None:
            q = q.filter(StampingPartCost.location == location)
        if vehicle_model is not None:
            q = q.filter(StampingPartCost.vehicle_model == vehicle_model)
        if stamping_supplier is not None:
            q = q.filter(StampingPartCost.stamping_supplier == stamping_supplier)
        results = q.order_by(StampingPartCost.version).all()
        return [r[0] for r in results if r[0]]
