"""冲压工艺（零件 + 工序）— 只读查询。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.common.part_number import escape_like_fragment, pick_part_row
from app.models.stamping.part import StampingPart, StampingProcess
from app.repositories.llm.location_in import location_in_clause


@dataclass(frozen=True, slots=True)
class StampingProcessPartRow:
    part_id: int
    part_number: str
    part_name: str | None
    location: str
    vehicle_model: str
    version: str
    stamping_supplier: str | None
    material: str | None
    thickness: Decimal | None
    is_tailor_welded: bool
    process_count: int
    max_tonnage: int | None


@dataclass(frozen=True, slots=True)
class StampingProcessDetailRow:
    process_seq: str
    process_order: int
    process_code: str | None
    tonnage: int | None
    die_sets: int | None


class StampingProcessAnalysisRepository:
    def query_part_rows(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        stamping_supplier: str | None = None,
        limit: int = 5000,
    ) -> list[StampingProcessPartRow]:
        """按筛选条件返回零件及工序汇总（LEFT JOIN 含零工序件）。"""
        process_stats = (
            db.query(
                StampingProcess.part_id.label("part_id"),
                func.count(StampingProcess.id).label("process_count"),
                func.max(StampingProcess.tonnage).label("max_tonnage"),
            )
            .group_by(StampingProcess.part_id)
            .subquery()
        )

        q = db.query(
            StampingPart,
            func.coalesce(process_stats.c.process_count, 0).label("process_count"),
            process_stats.c.max_tonnage.label("max_tonnage"),
        ).outerjoin(process_stats, StampingPart.id == process_stats.c.part_id)

        loc_filter = location_in_clause(db, StampingPart.location, location)
        if loc_filter is not None:
            q = q.filter(loc_filter)
        if vehicle_model:
            q = q.filter(StampingPart.vehicle_model == vehicle_model)
        if version:
            q = q.filter(StampingPart.version == version)
        if stamping_supplier:
            q = q.filter(StampingPart.stamping_supplier == stamping_supplier)
        if part_number:
            pattern = f"%{escape_like_fragment(part_number)}%"
            q = q.filter(StampingPart.part_number.like(pattern, escape="\\"))

        q = q.order_by(
            func.coalesce(process_stats.c.process_count, 0).desc(),
            StampingPart.part_number.asc(),
        ).limit(limit)

        rows: list[StampingProcessPartRow] = []
        for part, process_count, max_tonnage in q.all():
            rows.append(
                StampingProcessPartRow(
                    part_id=int(part.id),
                    part_number=str(part.part_number),
                    part_name=part.part_name,
                    location=str(part.location),
                    vehicle_model=str(part.vehicle_model),
                    version=str(part.version),
                    stamping_supplier=part.stamping_supplier,
                    material=part.material,
                    thickness=(
                        Decimal(str(part.thickness)) if part.thickness is not None else None
                    ),
                    is_tailor_welded=bool(part.is_tailor_welded),
                    process_count=int(process_count or 0),
                    max_tonnage=int(max_tonnage) if max_tonnage is not None else None,
                )
            )
        return rows

    def query_process_details(
        self,
        db: Session,
        *,
        part_number: str,
        location: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
    ) -> tuple[StampingProcessPartRow | None, list[StampingProcessDetailRow]]:
        """单件 drilldown：零件头 + 工序明细。"""
        part_rows = self.query_part_rows(
            db,
            location=location,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            limit=20,
        )
        exact = pick_part_row(
            part_rows,
            part_number,
            get_part_number=lambda row: row.part_number,
        )
        if exact is None:
            return None, []

        processes = (
            db.query(StampingProcess)
            .filter(StampingProcess.part_id == exact.part_id)
            .order_by(StampingProcess.process_order.asc())
            .all()
        )
        details = [
            StampingProcessDetailRow(
                process_seq=str(row.process_seq),
                process_order=int(row.process_order),
                process_code=row.process_code,
                tonnage=int(row.tonnage) if row.tonnage is not None else None,
                die_sets=int(row.die_sets) if row.die_sets is not None else None,
            )
            for row in processes
        ]
        return exact, details
