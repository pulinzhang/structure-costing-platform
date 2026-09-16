"""冲压零件查询：分页、筛选下拉、导出加载。"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func
from sqlalchemy.orm import Query, Session

from app.common.types.repository_types import StampingPartFilterSummary
from app.models.stamping import StampingPart, StampingProcess
from app.repositories.period_query import period_hit_clause, period_overlaps_year_clause
from app.repositories.stamping.part.filters import _PART_LIST_ORDER, _filter_supplier
from app.repositories.stamping.part.types import (
    StampingPartDieMatchIdentity,
    StampingPartScopeIdentity,
)


class StampingPartQueries:
    def count_all(self, db: Session) -> int:
        """零件总数。"""
        return db.query(StampingPart).count()

    def count_distinct_vehicle_models(self, db: Session) -> int:
        """去重车型数量。"""
        return db.query(StampingPart.vehicle_model).distinct().count()

    def exists_location_vehicle_model(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
    ) -> bool:
        return (
            db.query(StampingPart.id)
            .filter(
                StampingPart.location == location,
                StampingPart.vehicle_model == vehicle_model,
            )
            .first()
            is not None
        )

    def list_distinct_parts_for_scope(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
    ) -> list[StampingPartScopeIdentity]:
        rows = (
            db.query(StampingPart.part_number, StampingPart.part_name, StampingPart.id)
            .filter(
                StampingPart.location == location,
                StampingPart.vehicle_model == vehicle_model,
            )
            .order_by(StampingPart.part_number.asc(), StampingPart.id.desc())
            .all()
        )
        seen: dict[str, str] = {}
        order: list[str] = []
        for part_number, part_name, _part_id in rows:
            number = (part_number or "").strip()
            if not number or number in seen:
                continue
            seen[number] = (part_name or "").strip()
            order.append(number)
        return [{"part_number": number, "part_name": seen[number]} for number in order]

    def list_die_match_identities(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
    ) -> list[StampingPartDieMatchIdentity]:
        rows = (
            db.query(
                StampingPart.part_number,
                StampingPart.stamping_supplier,
                StampingPart.version,
            )
            .filter(
                StampingPart.location == location,
                StampingPart.vehicle_model == vehicle_model,
            )
            .all()
        )
        return [
            {
                "part_number": (part_number or "").strip(),
                "stamping_supplier": (stamping_supplier or "").strip(),
                "version": (version or "").strip(),
            }
            for part_number, stamping_supplier, version in rows
        ]

    def list_scrap_byproduct_keys(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
    ) -> frozenset[tuple[str, str, str]]:
        """基地+项目下废料副产品身份（供应商、版本、零件号）。"""
        rows = (
            db.query(
                StampingPart.stamping_supplier,
                StampingPart.version,
                StampingPart.part_number,
            )
            .filter(
                StampingPart.location == location,
                StampingPart.vehicle_model == vehicle_model,
                StampingPart.is_scrap_byproduct.is_(True),
            )
            .all()
        )
        return frozenset(
            (
                (stamping_supplier or "").strip(),
                (version or "").strip(),
                (part_number or "").strip(),
            )
            for stamping_supplier, version, part_number in rows
            if (part_number or "").strip()
        )

    def get_by_id(self, db: Session, part_id: int) -> StampingPart | None:
        from sqlalchemy.orm import selectinload

        return (
            db.query(StampingPart)
            .options(selectinload(StampingPart.processes))
            .filter(StampingPart.id == part_id)
            .first()
        )

    def get_by_part_number(self, db: Session, part_number: str) -> StampingPart | None:
        return db.query(StampingPart).filter(StampingPart.part_number == part_number).first()

    def filter_by_vehicle_version(
        self,
        db: Session,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        part_name: str | None = None,
        stamping_supplier: str | None = None,
    ) -> tuple[list[StampingPart], int]:
        """查询零件，返回 (结果列表, 总数)"""
        q = db.query(StampingPart)
        if vehicle_model is not None:
            q = q.filter(StampingPart.vehicle_model == vehicle_model)
        if version is not None:
            q = q.filter(StampingPart.version == version)
        if part_number:
            q = q.filter(StampingPart.part_number.like(f"%{part_number}%"))
        if part_name:
            q = q.filter(StampingPart.part_name.like(f"%{part_name}%"))
        if stamping_supplier is not None:
            q = q.filter(StampingPart.stamping_supplier == stamping_supplier)

        total = q.count()
        from sqlalchemy.orm import selectinload

        parts = q.options(selectinload(StampingPart.processes)).order_by(StampingPart.seq_no).all()
        return parts, total

    def _build_list_query(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        part_name: str | None = None,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
        as_of_year: int | None = None,
        as_of_month: int | None = None,
        include_expired: bool = False,
    ) -> Query[StampingPart]:
        """构建与列表相同的筛选查询（不含排序/分页）。"""
        q = db.query(StampingPart)
        if locations is not None:
            q = q.filter(StampingPart.location.in_(locations))
        elif location is not None:
            q = q.filter(StampingPart.location == location)
        q = _filter_supplier(
            q,
            StampingPart.stamping_supplier,
            stamping_supplier,
            stamping_suppliers,
        )
        if vehicle_model is not None:
            q = q.filter(StampingPart.vehicle_model == vehicle_model)
        if version is not None:
            q = q.filter(StampingPart.version == version)
        if part_number:
            q = q.filter(StampingPart.part_number.like(f"%{part_number}%"))
        if part_name:
            q = q.filter(StampingPart.part_name.like(f"%{part_name}%"))
        if as_of_year is not None and as_of_month is not None and not include_expired:
            q = q.filter(
                period_hit_clause(
                    StampingPart.effective_year,
                    StampingPart.effective_month,
                    StampingPart.expiry_year,
                    StampingPart.expiry_month,
                    as_of_year,
                    as_of_month,
                )
            )
        return q

    def paginate(
        self,
        db: Session,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        part_name: str | None = None,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
        skip: int = 0,
        limit: int = 100,
        as_of_year: int | None = None,
        as_of_month: int | None = None,
        include_expired: bool = False,
    ) -> tuple[list[StampingPart], int]:
        """分页查询零件。排序与导出相同：基地 → 车型 → 版本 → 工厂 → id。"""
        q = self._build_list_query(
            db,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            part_name=part_name,
            stamping_supplier=stamping_supplier,
            stamping_suppliers=stamping_suppliers,
            as_of_year=as_of_year,
            as_of_month=as_of_month,
            include_expired=include_expired,
        )
        total = q.count()
        parts = q.order_by(*_PART_LIST_ORDER).offset(skip).limit(limit).all()
        return parts, total

    def summarize_by_filters(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        part_name: str | None = None,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
    ) -> StampingPartFilterSummary:
        """按与列表相同的筛选条件汇总去重维度数量。"""
        q = self._build_list_query(
            db,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            part_name=part_name,
            stamping_supplier=stamping_supplier,
            stamping_suppliers=stamping_suppliers,
        )
        row = q.with_entities(
            func.count(func.distinct(StampingPart.location)).label("location_count"),
            func.count(func.distinct(StampingPart.stamping_supplier)).label(
                "stamping_supplier_count"
            ),
            func.count(func.distinct(StampingPart.vehicle_model)).label("vehicle_model_count"),
            func.count(func.distinct(StampingPart.part_number)).label("part_number_count"),
            func.count(func.distinct(StampingPart.version)).label("version_count"),
        ).one()
        return {
            "location_count": int(row.location_count or 0),
            "stamping_supplier_count": int(row.stamping_supplier_count or 0),
            "vehicle_model_count": int(row.vehicle_model_count or 0),
            "part_number_count": int(row.part_number_count or 0),
            "version_count": int(row.version_count or 0),
        }

    def list_with_processes(
        self,
        db: Session,
        location: str,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        overlap_year: int | None = None,
        as_of_year: int | None = None,
        as_of_month: int | None = None,
    ) -> list[StampingPart]:
        """按基地等条件加载零件、工序与拼焊子片（加工费/零件核价用，不分页）"""
        from sqlalchemy.orm import selectinload

        q = db.query(StampingPart).filter(StampingPart.location == location)
        if stamping_supplier is not None:
            q = q.filter(StampingPart.stamping_supplier == stamping_supplier)
        if vehicle_model is not None:
            q = q.filter(StampingPart.vehicle_model == vehicle_model)
        if version is not None:
            q = q.filter(StampingPart.version == version)
        if as_of_year is not None and as_of_month is not None:
            q = q.filter(
                period_hit_clause(
                    StampingPart.effective_year,
                    StampingPart.effective_month,
                    StampingPart.expiry_year,
                    StampingPart.expiry_month,
                    as_of_year,
                    as_of_month,
                )
            )
        elif overlap_year is not None:
            q = q.filter(
                period_overlaps_year_clause(
                    StampingPart.effective_year,
                    StampingPart.expiry_year,
                    overlap_year,
                )
            )

        return (
            q.options(
                selectinload(StampingPart.processes),
                selectinload(StampingPart.tailor_weld_blanks),
            )
            .order_by(StampingPart.seq_no, StampingPart.id)
            .all()
        )

    def list_for_export(
        self,
        db: Session,
        *,
        location: str | None = None,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        part_name: str | None = None,
        as_of_year: int | None = None,
        as_of_month: int | None = None,
        include_expired: bool = False,
    ) -> list[StampingPart]:
        """按列表筛选加载零件 + 工序 + 拼焊子片（导出用，不分页）。

        排序与列表分页相同：基地 → 车型 → 版本 → 工厂 → id。
        """
        from sqlalchemy.orm import selectinload

        q = self._build_list_query(
            db,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            part_name=part_name,
            as_of_year=as_of_year,
            as_of_month=as_of_month,
            include_expired=include_expired,
        )
        return (
            q.options(
                selectinload(StampingPart.processes),
                selectinload(StampingPart.tailor_weld_blanks),
            )
            .order_by(*_PART_LIST_ORDER)
            .all()
        )

    def list_all(self, db: Session, skip: int = 0, limit: int = 100) -> list[StampingPart]:
        return db.query(StampingPart).offset(skip).limit(limit).all()

    def get_all_by_scope(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        version: str,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
    ) -> list[StampingPart]:
        """按基地 + 车型 + 版本查询零件；工厂传入则再缩小。"""
        q = db.query(StampingPart).filter(
            StampingPart.location == location,
            StampingPart.vehicle_model == vehicle_model,
            StampingPart.version == version,
        )
        q = _filter_supplier(
            q,
            StampingPart.stamping_supplier,
            stamping_supplier,
            stamping_suppliers,
        )
        return q.all()

    def list_identity_scope(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
    ) -> list[StampingPart]:
        q = db.query(StampingPart).filter(
            StampingPart.location == location,
            StampingPart.vehicle_model == vehicle_model,
        )
        q = _filter_supplier(
            q,
            StampingPart.stamping_supplier,
            stamping_supplier,
            stamping_suppliers,
        )
        return q.all()

    def get_by_unique_key(
        self,
        db: Session,
        *,
        location: str,
        stamping_supplier: str,
        vehicle_model: str,
        part_number: str,
    ) -> StampingPart | None:
        return (
            db.query(StampingPart)
            .filter(
                StampingPart.location == location,
                StampingPart.stamping_supplier == stamping_supplier,
                StampingPart.vehicle_model == vehicle_model,
                StampingPart.part_number == part_number,
            )
            .first()
        )

    def list_by_location_and_vehicle(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        overlap_year: int | None = None,
        as_of_year: int | None = None,
        as_of_month: int | None = None,
    ) -> list[StampingPart]:
        q = db.query(StampingPart).filter(
            StampingPart.location == location,
            StampingPart.vehicle_model == vehicle_model,
        )
        if as_of_year is not None and as_of_month is not None:
            q = q.filter(
                period_hit_clause(
                    StampingPart.effective_year,
                    StampingPart.effective_month,
                    StampingPart.expiry_year,
                    StampingPart.expiry_month,
                    as_of_year,
                    as_of_month,
                )
            )
        elif overlap_year is not None:
            q = q.filter(
                period_overlaps_year_clause(
                    StampingPart.effective_year,
                    StampingPart.expiry_year,
                    overlap_year,
                )
            )
        return q.all()

    def count_processes_by_part_ids(self, db: Session, part_ids: list[int]) -> dict[int, int]:
        """
        批量统计每个零件的工序数（一次 SQL, IN 子查询）。
        返回 {part_id: process_count}，缺省为 0。
        """
        if not part_ids:
            return {}
        rows = (
            db.query(StampingProcess.part_id, func.count(StampingProcess.id))
            .filter(StampingProcess.part_id.in_(part_ids))
            .group_by(StampingProcess.part_id)
            .all()
        )
        counts = {pid: cnt for pid, cnt in rows}
        return {pid: counts.get(pid, 0) for pid in part_ids}
