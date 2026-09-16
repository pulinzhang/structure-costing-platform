"""焊接费查询：列表、导出、计算范围、汇总、下拉。"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import case, func
from sqlalchemy.orm import Query, Session, joinedload, noload

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING
from app.models.bom import BomNode, BomWeldingFee, BomWeldingProcessBreakdownNode
from app.repositories.bom.welding_fee.types import WeldingFeeFilterSummary
from app.schemas.dto.bom_welding_fee_dto import resolve_welding_fee_levels


class BomWeldingFeeQueries:
    def get_by_id(self, db: Session, fee_id: int) -> BomWeldingFee | None:
        return (
            db.query(BomWeldingFee)
            .options(joinedload(BomWeldingFee.items))
            .filter(BomWeldingFee.id == fee_id)
            .first()
        )

    def get_by_business_key(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        source_breakdown_node_id: int | None,
    ) -> BomWeldingFee | None:
        return (
            db.query(BomWeldingFee)
            .filter(
                BomWeldingFee.year == year,
                BomWeldingFee.location == location,
                BomWeldingFee.vehicle_model == vehicle_model,
                BomWeldingFee.source_breakdown_node_id == source_breakdown_node_id,
            )
            .first()
        )

    def _scope_query(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        bom_version: str | None = None,
        level: int | None = None,
        levels: list[int] | None = None,
    ) -> Query[BomWeldingFee]:
        q = db.query(BomWeldingFee).filter(
            BomWeldingFee.year == year,
            BomWeldingFee.location == location,
            BomWeldingFee.vehicle_model == vehicle_model,
        )
        if bom_version:
            q = q.filter(BomWeldingFee.bom_version == bom_version)
        return self._filter_levels(q, level=level, levels=levels)

    def count_by_calc_scope(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        bom_version: str | None = None,
        level: int | None = None,
    ) -> int:
        return int(
            self._scope_query(
                db,
                year=year,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                level=level,
            ).count()
        )

    def list_by_calc_scope(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        bom_version: str | None = None,
        level: int | None = None,
    ) -> list[BomWeldingFee]:
        return (
            self._scope_query(
                db,
                year=year,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                level=level,
            )
            .order_by(BomWeldingFee.part_number, BomWeldingFee.id.asc())
            .all()
        )

    def _build_list_query(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        calc_status: str | None = None,
        level: int | None = None,
        levels: list[int] | None = None,
    ) -> Query[BomWeldingFee]:
        q = db.query(BomWeldingFee)
        if year is not None:
            q = q.filter(BomWeldingFee.year == year)
        if locations is not None:
            q = q.filter(BomWeldingFee.location.in_(locations))
        elif location is not None:
            q = q.filter(BomWeldingFee.location == location)
        if vehicle_model is not None:
            q = q.filter(BomWeldingFee.vehicle_model == vehicle_model)
        if bom_version is not None:
            q = q.filter(BomWeldingFee.bom_version == bom_version)
        if part_number:
            q = q.filter(BomWeldingFee.part_number.like(f"%{part_number}%"))
        if audit_status:
            q = q.filter(BomWeldingFee.audit_status == audit_status)
        if calc_status:
            q = q.filter(BomWeldingFee.calc_status == calc_status)
        return self._filter_levels(q, level=level, levels=levels)

    @staticmethod
    def _filter_levels(
        q: Query[BomWeldingFee],
        *,
        level: int | None,
        levels: list[int] | None,
    ) -> Query[BomWeldingFee]:
        resolved = resolve_welding_fee_levels(level=level, levels=levels)
        if not resolved:
            return q
        if len(resolved) == 1:
            return q.filter(BomWeldingFee.level == resolved[0])
        return q.filter(BomWeldingFee.level.in_(resolved))

    @staticmethod
    def _order_like_bom_nodes(q: Query[BomWeldingFee]) -> Query[BomWeldingFee]:
        """与材料清单 ``list_by_snapshot`` 一致：level → sort_no → id。"""
        return (
            q.outerjoin(
                BomWeldingProcessBreakdownNode,
                BomWeldingFee.source_breakdown_node_id == BomWeldingProcessBreakdownNode.id,
            )
            .outerjoin(
                BomNode,
                BomWeldingProcessBreakdownNode.source_node_id == BomNode.id,
            )
            .order_by(
                BomWeldingFee.level.asc(),
                func.coalesce(
                    BomNode.sort_no,
                    BomWeldingProcessBreakdownNode.excel_row,
                    0,
                ).asc(),
                BomWeldingFee.id.asc(),
            )
        )

    def paginate(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        calc_status: str | None = None,
        level: int | None = None,
        levels: list[int] | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[BomWeldingFee], int]:
        q = self._build_list_query(
            db,
            year=year,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            audit_status=audit_status,
            calc_status=calc_status,
            level=level,
            levels=levels,
        )
        total = q.count()
        rows = (
            self._order_like_bom_nodes(q.options(noload(BomWeldingFee.items)))
            .offset(skip)
            .limit(limit)
            .all()
        )
        return rows, total

    def list_for_export(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        calc_status: str | None = None,
        level: int | None = None,
        levels: list[int] | None = None,
        ids: list[int] | None = None,
    ) -> list[BomWeldingFee]:
        if ids is not None and not ids:
            return []
        q = self._build_list_query(
            db,
            year=year,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            audit_status=audit_status,
            calc_status=calc_status,
            level=level,
            levels=levels,
        )
        if ids is not None:
            q = q.filter(BomWeldingFee.id.in_(ids))
        ordered_ids = [
            int(row.id)
            for row in self._order_like_bom_nodes(q.with_entities(BomWeldingFee.id)).all()
        ]
        if not ordered_ids:
            return []
        loaded = (
            db.query(BomWeldingFee)
            .options(joinedload(BomWeldingFee.items))
            .filter(BomWeldingFee.id.in_(ordered_ids))
            .all()
        )
        by_id = {int(record.id): record for record in loaded}
        return [by_id[fee_id] for fee_id in ordered_ids if fee_id in by_id]

    def summarize_by_filters(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        calc_status: str | None = None,
        level: int | None = None,
        levels: list[int] | None = None,
    ) -> WeldingFeeFilterSummary:
        q = self._build_list_query(
            db,
            year=year,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            audit_status=audit_status,
            calc_status=calc_status,
            level=level,
            levels=levels,
        )
        row = q.with_entities(
            func.count(BomWeldingFee.id).label("total_count"),
            func.coalesce(func.sum(BomWeldingFee.final_welding_fee), 0).label("total_fee"),
            func.sum(case((BomWeldingFee.audit_status == AUDIT_PENDING, 1), else_=0)).label(
                "pending_count"
            ),
            func.sum(case((BomWeldingFee.audit_status == AUDIT_APPROVED, 1), else_=0)).label(
                "approved_count"
            ),
            func.sum(case((BomWeldingFee.calc_status == "partial", 1), else_=0)).label(
                "partial_count"
            ),
            func.sum(case((BomWeldingFee.calc_status == "failed", 1), else_=0)).label(
                "failed_count"
            ),
            func.sum(BomWeldingFee.missing_price_count).label("missing_price_count"),
        ).one()

        return {
            "total_count": int(row.total_count or 0),
            "total_fee": Decimal(str(row.total_fee or 0)),
            "pending_count": int(row.pending_count or 0),
            "approved_count": int(row.approved_count or 0),
            "partial_count": int(row.partial_count or 0),
            "failed_count": int(row.failed_count or 0),
            "missing_price_count": int(row.missing_price_count or 0),
        }

    def count_by_scope_and_statuses(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        bom_version: str | None = None,
        statuses: list[str],
        level: int | None = None,
        levels: list[int] | None = None,
    ) -> int:
        return int(
            self._scope_query(
                db,
                year=year,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                level=level,
                levels=levels,
            )
            .filter(BomWeldingFee.audit_status.in_(statuses))
            .count()
        )

    def get_distinct_years(self, db: Session) -> list[int]:
        results = db.query(BomWeldingFee.year).distinct().order_by(BomWeldingFee.year.desc()).all()
        return [r[0] for r in results]

    def get_distinct_locations(self, db: Session, year: int | None = None) -> list[str]:
        q = db.query(BomWeldingFee.location).distinct()
        if year is not None:
            q = q.filter(BomWeldingFee.year == year)
        results = q.order_by(BomWeldingFee.location).all()
        return [r[0] for r in results if r[0]]

    def get_distinct_bom_versions(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
    ) -> list[str]:
        q = db.query(BomWeldingFee.bom_version).distinct()
        if year is not None:
            q = q.filter(BomWeldingFee.year == year)
        if locations is not None:
            q = q.filter(BomWeldingFee.location.in_(locations))
        elif location is not None:
            q = q.filter(BomWeldingFee.location == location)
        if vehicle_model is not None:
            q = q.filter(BomWeldingFee.vehicle_model == vehicle_model)
        results = q.order_by(BomWeldingFee.bom_version).all()
        return [r[0] for r in results if r[0]]
