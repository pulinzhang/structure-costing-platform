"""焊接工艺拆解查询：列表、范围、汇总、下拉。"""

from __future__ import annotations

from sqlalchemy import and_, case, func
from sqlalchemy.orm import Query, Session, joinedload
from sqlalchemy.sql.elements import ColumnElement

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING
from app.models.bom import (
    BomWeldingProcessBreakdownLine,
    BomWeldingProcessBreakdownNode,
)
from app.repositories.bom.welding_process_breakdown.types import WeldingBreakdownFilterSummary


class WeldingBreakdownQueries:
    def get_node_by_id(self, db: Session, node_id: int) -> BomWeldingProcessBreakdownNode | None:
        return (
            db.query(BomWeldingProcessBreakdownNode)
            .options(joinedload(BomWeldingProcessBreakdownNode.lines))
            .filter(BomWeldingProcessBreakdownNode.id == node_id)
            .first()
        )

    def map_weld_info_by_ids(self, db: Session, node_ids: list[int]) -> dict[int, str]:
        """批量取焊接信息原文（仅 id + weld_info_raw）。"""
        ids = sorted({int(n) for n in node_ids if n})
        if not ids:
            return {}
        rows = (
            db.query(
                BomWeldingProcessBreakdownNode.id,
                BomWeldingProcessBreakdownNode.weld_info_raw,
            )
            .filter(BomWeldingProcessBreakdownNode.id.in_(ids))
            .all()
        )
        return {
            int(row.id): (row.weld_info_raw or "").strip()
            for row in rows
            if (row.weld_info_raw or "").strip()
        }

    def get_line_by_id(self, db: Session, line_id: int) -> BomWeldingProcessBreakdownLine | None:
        return (
            db.query(BomWeldingProcessBreakdownLine)
            .filter(BomWeldingProcessBreakdownLine.id == line_id)
            .first()
        )

    def _scope_filter(
        self,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> list[ColumnElement[bool]]:
        return [
            BomWeldingProcessBreakdownNode.location == location,
            BomWeldingProcessBreakdownNode.vehicle_model == vehicle_model,
            BomWeldingProcessBreakdownNode.bom_version == bom_version,
        ]

    def _apply_list_filters(
        self,
        q: Query[BomWeldingProcessBreakdownNode],
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        customer_name: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        level: int | None = None,
        audit_status: str | None = None,
        parse_status: str | None = None,
        process_line_count_eq: int | None = None,
    ) -> Query[BomWeldingProcessBreakdownNode]:
        if locations is not None:
            q = q.filter(BomWeldingProcessBreakdownNode.location.in_(locations))
        elif location:
            q = q.filter(BomWeldingProcessBreakdownNode.location == location)
        if customer_name:
            q = q.filter(BomWeldingProcessBreakdownNode.customer_name == customer_name)
        if vehicle_model:
            q = q.filter(BomWeldingProcessBreakdownNode.vehicle_model == vehicle_model)
        if bom_version:
            q = q.filter(BomWeldingProcessBreakdownNode.bom_version == bom_version)
        if part_number:
            q = q.filter(BomWeldingProcessBreakdownNode.part_number.like(f"%{part_number}%"))
        if level is not None:
            q = q.filter(BomWeldingProcessBreakdownNode.level == level)
        if audit_status:
            q = q.filter(BomWeldingProcessBreakdownNode.audit_status == audit_status)
        if parse_status:
            q = q.filter(BomWeldingProcessBreakdownNode.parse_status == parse_status)
        if process_line_count_eq is not None:
            q = q.filter(BomWeldingProcessBreakdownNode.process_line_count == process_line_count_eq)
        return q

    def _build_list_query(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        customer_name: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        level: int | None = None,
        audit_status: str | None = None,
        parse_status: str | None = None,
        process_line_count_eq: int | None = None,
        load_lines: bool = False,
    ) -> Query[BomWeldingProcessBreakdownNode]:
        # 列表/汇总只用 process_line_count，默认不拉取明细（明细走 get_node）
        q: Query[BomWeldingProcessBreakdownNode] = db.query(BomWeldingProcessBreakdownNode)
        if load_lines:
            q = q.options(joinedload(BomWeldingProcessBreakdownNode.lines))
        q = self._apply_list_filters(
            q,
            location=location,
            locations=locations,
            customer_name=customer_name,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            level=level,
            audit_status=audit_status,
            parse_status=parse_status,
            process_line_count_eq=process_line_count_eq,
        )
        return q

    def paginate(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        customer_name: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        level: int | None = None,
        audit_status: str | None = None,
        parse_status: str | None = None,
        process_line_count_eq: int | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[BomWeldingProcessBreakdownNode], int]:
        q = self._build_list_query(
            db,
            location=location,
            locations=locations,
            customer_name=customer_name,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            level=level,
            audit_status=audit_status,
            parse_status=parse_status,
            process_line_count_eq=process_line_count_eq,
            load_lines=False,
        )
        total = q.count()
        rows = (
            q.order_by(
                BomWeldingProcessBreakdownNode.level,
                BomWeldingProcessBreakdownNode.id,
                BomWeldingProcessBreakdownNode.supply_part_number,
                BomWeldingProcessBreakdownNode.part_number,
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
        return rows, total

    def list_l0_for_export(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        customer_name: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        process_line_count_eq: int | None = None,
    ) -> list[BomWeldingProcessBreakdownNode]:
        """
        L0 核对导出：主表 + 明细（joinedload）。
        强制 level=0；不含审核筛选。
        """
        q = self._build_list_query(
            db,
            location=location,
            locations=locations,
            customer_name=customer_name,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            level=0,
            process_line_count_eq=process_line_count_eq,
            load_lines=True,
        )
        return q.order_by(
            BomWeldingProcessBreakdownNode.location,
            BomWeldingProcessBreakdownNode.vehicle_model,
            BomWeldingProcessBreakdownNode.bom_version,
            BomWeldingProcessBreakdownNode.part_number,
            BomWeldingProcessBreakdownNode.id,
        ).all()

    def list_by_scope(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> list[BomWeldingProcessBreakdownNode]:
        return (
            db.query(BomWeldingProcessBreakdownNode)
            .options(joinedload(BomWeldingProcessBreakdownNode.lines))
            .filter(
                and_(
                    *self._scope_filter(
                        location=location,
                        vehicle_model=vehicle_model,
                        bom_version=bom_version,
                    )
                )
            )
            .order_by(
                BomWeldingProcessBreakdownNode.level,
                BomWeldingProcessBreakdownNode.part_number,
                BomWeldingProcessBreakdownNode.id,
            )
            .all()
        )

    def exists_by_bom_scope(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> bool:
        return (
            db.query(BomWeldingProcessBreakdownNode.id)
            .filter(
                and_(
                    *self._scope_filter(
                        location=location,
                        vehicle_model=vehicle_model,
                        bom_version=bom_version,
                    )
                )
            )
            .first()
            is not None
        )

    def count_by_scope(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> int:
        return (
            db.query(BomWeldingProcessBreakdownNode)
            .filter(
                and_(
                    *self._scope_filter(
                        location=location,
                        vehicle_model=vehicle_model,
                        bom_version=bom_version,
                    )
                )
            )
            .count()
        )

    def count_by_filters(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        customer_name: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        level: int | None = None,
        audit_status: str | None = None,
        parse_status: str | None = None,
        process_line_count_eq: int | None = None,
    ) -> int:
        """按明确过滤条件计数主表（业务口径由 Service 决定传参）。"""
        return self._build_list_query(
            db,
            location=location,
            locations=locations,
            customer_name=customer_name,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            level=level,
            audit_status=audit_status,
            parse_status=parse_status,
            process_line_count_eq=process_line_count_eq,
            load_lines=False,
        ).count()

    def sum_process_line_count_by_filters(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        customer_name: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        level: int | None = None,
        audit_status: str | None = None,
        parse_status: str | None = None,
        process_line_count_eq: int | None = None,
    ) -> int:
        """按过滤条件对 process_line_count 求和（列表冗余字段，不扫明细表）。"""
        q = self._build_list_query(
            db,
            location=location,
            locations=locations,
            customer_name=customer_name,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            level=level,
            audit_status=audit_status,
            parse_status=parse_status,
            process_line_count_eq=process_line_count_eq,
            load_lines=False,
        )
        total = q.with_entities(
            func.coalesce(func.sum(BomWeldingProcessBreakdownNode.process_line_count), 0)
        ).scalar()
        return int(total or 0)

    def summarize_by_filters(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        customer_name: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        level: int | None = None,
        audit_status: str | None = None,
        parse_status: str | None = None,
        process_line_count_eq: int | None = None,
    ) -> WeldingBreakdownFilterSummary:
        q = self._build_list_query(
            db,
            location=location,
            locations=locations,
            customer_name=customer_name,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            level=level,
            audit_status=audit_status,
            parse_status=parse_status,
            process_line_count_eq=process_line_count_eq,
        )
        row = q.with_entities(
            func.count(BomWeldingProcessBreakdownNode.id).label("total_count"),
            func.sum(
                case(
                    (BomWeldingProcessBreakdownNode.audit_status == AUDIT_PENDING, 1),
                    else_=0,
                )
            ).label("pending_count"),
            func.sum(
                case(
                    (BomWeldingProcessBreakdownNode.audit_status == AUDIT_APPROVED, 1),
                    else_=0,
                )
            ).label("approved_count"),
            func.sum(
                case(
                    (BomWeldingProcessBreakdownNode.level == 0, 1),
                    else_=0,
                )
            ).label("l0_count"),
        ).one()

        return {
            "total_count": int(row.total_count or 0),
            "pending_count": int(row.pending_count or 0),
            "approved_count": int(row.approved_count or 0),
            "l0_count": int(row.l0_count or 0),
        }

    def count_by_scope_and_statuses(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
        statuses: list[str],
    ) -> int:
        return (
            db.query(BomWeldingProcessBreakdownNode)
            .filter(
                and_(
                    *self._scope_filter(
                        location=location,
                        vehicle_model=vehicle_model,
                        bom_version=bom_version,
                    )
                ),
                BomWeldingProcessBreakdownNode.audit_status.in_(statuses),
            )
            .count()
        )

    def get_distinct_locations(self, db: Session) -> list[str]:
        rows = (
            db.query(BomWeldingProcessBreakdownNode.location)
            .distinct()
            .order_by(BomWeldingProcessBreakdownNode.location)
            .all()
        )
        return [r[0] for r in rows if r[0]]

    def get_distinct_bom_versions(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
    ) -> list[str]:
        q = db.query(BomWeldingProcessBreakdownNode.bom_version)
        if locations is not None:
            q = q.filter(BomWeldingProcessBreakdownNode.location.in_(locations))
        elif location:
            q = q.filter(BomWeldingProcessBreakdownNode.location == location)
        if vehicle_model:
            q = q.filter(BomWeldingProcessBreakdownNode.vehicle_model == vehicle_model)
        rows = q.distinct().order_by(BomWeldingProcessBreakdownNode.bom_version).all()
        return [r[0] for r in rows if r[0]]

    def get_distinct_customer_names(self, db: Session) -> list[str]:
        rows = (
            db.query(BomWeldingProcessBreakdownNode.customer_name)
            .distinct()
            .order_by(BomWeldingProcessBreakdownNode.customer_name)
            .all()
        )
        return [r[0] for r in rows if r[0]]
