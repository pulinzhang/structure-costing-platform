"""冲压加工费查询：列表、导出、范围、汇总、下拉。"""

from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import case, false, func
from sqlalchemy.orm import Query, Session, joinedload, noload

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING
from app.models.stamping import StampingProcessFee
from app.repositories.stamping.process_fee.types import (
    ProcessFeeFilterSummary,
    needs_price_fix_clause,
)


class StampingProcessFeeQueries:
    def get_by_id(self, db: Session, fee_id: int) -> StampingProcessFee | None:
        return (
            db.query(StampingProcessFee)
            .options(joinedload(StampingProcessFee.process_items))
            .filter(StampingProcessFee.id == fee_id)
            .first()
        )

    def list_by_ids(self, db: Session, fee_ids: list[int]) -> list[StampingProcessFee]:
        """按主键批量查询（含工序分项，供导出溯源）。"""
        if not fee_ids:
            return []
        return (
            db.query(StampingProcessFee)
            .options(joinedload(StampingProcessFee.process_items))
            .filter(StampingProcessFee.id.in_(fee_ids))
            .all()
        )

    def get_by_business_key(
        self,
        db: Session,
        year: int,
        location: str,
        stamping_supplier: str,
        vehicle_model: str,
        version: str,
        part_number: str,
    ) -> StampingProcessFee | None:
        q = db.query(StampingProcessFee).filter(
            StampingProcessFee.year == year,
            StampingProcessFee.location == location,
            StampingProcessFee.stamping_supplier == stamping_supplier,
            StampingProcessFee.vehicle_model == vehicle_model,
            StampingProcessFee.version == version,
            StampingProcessFee.part_number == part_number,
        )
        return q.first()

    def _scope_query(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
    ) -> Query[StampingProcessFee]:
        q = db.query(StampingProcessFee).filter(
            StampingProcessFee.year == year,
            StampingProcessFee.location == location,
        )
        if stamping_supplier:
            q = q.filter(StampingProcessFee.stamping_supplier == stamping_supplier)
        if vehicle_model:
            q = q.filter(StampingProcessFee.vehicle_model == vehicle_model)
        if version:
            q = q.filter(StampingProcessFee.version == version)
        return q

    def _build_list_query(
        self,
        db: Session,
        year: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        only_zero: bool = False,
    ) -> Query[StampingProcessFee]:
        q = db.query(StampingProcessFee)
        if year is not None:
            q = q.filter(StampingProcessFee.year == year)
        if locations is not None:
            q = q.filter(StampingProcessFee.location.in_(locations))
        elif location is not None:
            q = q.filter(StampingProcessFee.location == location)
        if stamping_suppliers is not None:
            if not stamping_suppliers:
                q = q.filter(false())
            else:
                q = q.filter(StampingProcessFee.stamping_supplier.in_(stamping_suppliers))
        elif stamping_supplier is not None:
            q = q.filter(StampingProcessFee.stamping_supplier == stamping_supplier)
        if vehicle_model is not None:
            q = q.filter(StampingProcessFee.vehicle_model == vehicle_model)
        if version is not None:
            q = q.filter(StampingProcessFee.version == version)
        if part_number:
            q = q.filter(StampingProcessFee.part_number.like(f"%{part_number}%"))
        if audit_status:
            q = q.filter(StampingProcessFee.audit_status == audit_status)
        if only_zero:
            q = q.filter(needs_price_fix_clause())
        return q

    def paginate(
        self,
        db: Session,
        year: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        only_zero: bool = False,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[StampingProcessFee], int]:
        q = self._build_list_query(
            db,
            year=year,
            location=location,
            locations=locations,
            stamping_supplier=stamping_supplier,
            stamping_suppliers=stamping_suppliers,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            audit_status=audit_status,
            only_zero=only_zero,
        )
        total = q.count()
        rows = (
            q.options(noload(StampingProcessFee.process_items))
            .order_by(
                StampingProcessFee.year.desc(),
                StampingProcessFee.location,
                StampingProcessFee.stamping_supplier,
                StampingProcessFee.id.asc(),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
        return rows, total

    def summarize_by_filters(
        self,
        db: Session,
        year: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
    ) -> ProcessFeeFilterSummary:
        """按筛选条件汇总：总金额 / 件均 / 待补价 / 待审 / 已审 / 版本标签。"""
        q = self._build_list_query(
            db,
            year=year,
            location=location,
            locations=locations,
            stamping_supplier=stamping_supplier,
            stamping_suppliers=stamping_suppliers,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            audit_status=audit_status,
            only_zero=False,
        )
        row = q.with_entities(
            func.count(StampingProcessFee.id).label("total_count"),
            func.coalesce(func.sum(StampingProcessFee.final_processing_fee), 0).label("total_fee"),
            func.avg(StampingProcessFee.final_processing_fee).label("avg_fee"),
            func.sum(case((needs_price_fix_clause(), 1), else_=0)).label("zero_count"),
            func.sum(case((StampingProcessFee.audit_status == AUDIT_PENDING, 1), else_=0)).label(
                "pending_count"
            ),
            func.sum(
                case(
                    (StampingProcessFee.audit_status == AUDIT_APPROVED, 1),
                    else_=0,
                )
            ).label("approved_count"),
        ).one()

        avg_value = row.avg_fee

        version_q = self._build_list_query(
            db,
            year=year,
            location=location,
            locations=locations,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            audit_status=audit_status,
            only_zero=False,
        )
        version_rows = (
            version_q.with_entities(StampingProcessFee.version)
            .distinct()
            .order_by(StampingProcessFee.version.asc())
            .all()
        )
        versions = [r[0] for r in version_rows if r[0]]
        if version:
            version_label = version
        elif len(versions) == 0:
            version_label = "—"
        elif len(versions) == 1:
            version_label = versions[0]
        else:
            version_label = f"{len(versions)} 个版本"

        return {
            "total_count": int(row.total_count or 0),
            "total_fee": Decimal(str(row.total_fee or 0)),
            "avg_fee": Decimal(str(avg_value)) if avg_value is not None else None,
            "zero_count": int(row.zero_count or 0),
            "pending_count": int(row.pending_count or 0),
            "approved_count": int(row.approved_count or 0),
            "version_label": version_label,
        }

    def list_for_export(
        self,
        db: Session,
        year: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
    ) -> list[StampingProcessFee]:
        q = self._build_list_query(
            db,
            year=year,
            location=location,
            locations=locations,
            stamping_supplier=stamping_supplier,
            stamping_suppliers=stamping_suppliers,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            audit_status=audit_status,
        )
        return (
            q.options(joinedload(StampingProcessFee.process_items))
            .order_by(
                StampingProcessFee.year.desc(),
                StampingProcessFee.location,
                StampingProcessFee.stamping_supplier,
                StampingProcessFee.id.asc(),
            )
            .all()
        )

    def list_tailor_weld_missing_other_fee_part_numbers(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        statuses: list[str],
    ) -> list[str]:
        """范围内待审拼焊件且未录入其它费用的零件号（用结算快照）。"""
        rows = (
            self._scope_query(
                db,
                year=year,
                location=location,
                stamping_supplier=stamping_supplier,
                vehicle_model=vehicle_model,
                version=version,
            )
            .filter(
                StampingProcessFee.audit_status.in_(statuses),
                StampingProcessFee.other_fee.is_(None),
                StampingProcessFee.is_tailor_welded.is_(True),
            )
            .with_entities(StampingProcessFee.part_number)
            .order_by(StampingProcessFee.part_number)
            .all()
        )
        return [row[0] for row in rows if row[0]]

    def list_by_scope(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str | None = None,
        version: str | None = None,
    ) -> list[StampingProcessFee]:
        return self._scope_query(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            version=version,
        ).all()

    def count_by_scope_and_statuses(
        self,
        db: Session,
        *,
        year: int,
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
                location=location,
                stamping_supplier=stamping_supplier,
                vehicle_model=vehicle_model,
                version=version,
            )
            .filter(StampingProcessFee.audit_status.in_(statuses))
            .count()
        )

    def get_distinct_years(self, db: Session) -> list[int]:
        results = (
            db.query(StampingProcessFee.year)
            .distinct()
            .order_by(StampingProcessFee.year.desc())
            .all()
        )
        return [r[0] for r in results]

    def get_distinct_locations(self, db: Session, year: int | None = None) -> list[str]:
        q = db.query(StampingProcessFee.location).distinct()
        if year is not None:
            q = q.filter(StampingProcessFee.year == year)
        results = q.order_by(StampingProcessFee.location).all()
        return [r[0] for r in results if r[0]]

    def get_distinct_suppliers(
        self,
        db: Session,
        year: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
    ) -> list[str]:
        q = db.query(StampingProcessFee.stamping_supplier).distinct()
        if year is not None:
            q = q.filter(StampingProcessFee.year == year)
        if locations is not None:
            q = q.filter(StampingProcessFee.location.in_(locations))
        elif location is not None:
            q = q.filter(StampingProcessFee.location == location)
        if vehicle_model is not None:
            q = q.filter(StampingProcessFee.vehicle_model == vehicle_model)
        if version is not None:
            q = q.filter(StampingProcessFee.version == version)
        results = q.order_by(StampingProcessFee.stamping_supplier).all()
        return [r[0] for r in results if r[0]]

    def get_distinct_versions(
        self,
        db: Session,
        year: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
    ) -> list[str]:
        q = db.query(StampingProcessFee.version).distinct()
        if year is not None:
            q = q.filter(StampingProcessFee.year == year)
        if locations is not None:
            q = q.filter(StampingProcessFee.location.in_(locations))
        elif location is not None:
            q = q.filter(StampingProcessFee.location == location)
        if stamping_supplier is not None:
            q = q.filter(StampingProcessFee.stamping_supplier == stamping_supplier)
        if vehicle_model is not None:
            q = q.filter(StampingProcessFee.vehicle_model == vehicle_model)
        results = q.order_by(StampingProcessFee.version).all()
        return [r[0] for r in results if r[0]]
