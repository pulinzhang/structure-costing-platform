"""冲压模具数据访问。"""

from typing import TypedDict

from sqlalchemy.orm import Query, Session, selectinload

from app.models.stamping.die import StampingDiePart, StampingDieProcess
from app.repositories.period_query import period_hit_clause, period_overlaps_year_clause
from app.repositories.persist import model_from_payload
from app.schemas.dto.stamping_die_dto import StampingDiePartInsert, StampingDieProcessInsert


class StampingDiePartScopeIdentity(TypedDict):
    part_number: str
    part_name: str


class StampingDiePartRepository:
    def exists_location_vehicle_model(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
    ) -> bool:
        return (
            db.query(StampingDiePart.id)
            .filter(
                StampingDiePart.location == location,
                StampingDiePart.vehicle_model == vehicle_model,
            )
            .first()
            is not None
        )

    def list_parts_for_scope(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
    ) -> list[StampingDiePartScopeIdentity]:
        rows = (
            db.query(StampingDiePart.part_number, StampingDiePart.part_name)
            .filter(
                StampingDiePart.location == location,
                StampingDiePart.vehicle_model == vehicle_model,
            )
            .order_by(StampingDiePart.id.asc())
            .all()
        )
        return [
            {"part_number": (part_number or "").strip(), "part_name": (part_name or "").strip()}
            for part_number, part_name in rows
            if (part_number or "").strip()
        ]

    def _scope_query(
        self,
        db: Session,
        *,
        vehicle_model: str,
        location: str | None = None,
        locations: list[str] | None = None,
        stamping_supplier: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        as_of_year: int | None = None,
        as_of_month: int | None = None,
        include_expired: bool = False,
    ) -> Query[StampingDiePart]:
        query = db.query(StampingDiePart).filter(StampingDiePart.vehicle_model == vehicle_model)
        if locations is not None:
            query = query.filter(StampingDiePart.location.in_(locations))
        elif location:
            query = query.filter(StampingDiePart.location == location)
        if stamping_supplier:
            query = query.filter(StampingDiePart.stamping_supplier == stamping_supplier)
        if version:
            query = query.filter(StampingDiePart.version == version)
        if part_number:
            query = query.filter(StampingDiePart.part_number.like(f"%{part_number.strip()}%"))
        if as_of_year is not None and as_of_month is not None and not include_expired:
            query = query.filter(
                period_hit_clause(
                    StampingDiePart.effective_year,
                    StampingDiePart.effective_month,
                    StampingDiePart.expiry_year,
                    StampingDiePart.expiry_month,
                    as_of_year,
                    as_of_month,
                )
            )
        return query

    def paginate(
        self,
        db: Session,
        *,
        vehicle_model: str,
        part_number: str | None,
        skip: int,
        limit: int,
        location: str | None = None,
        locations: list[str] | None = None,
        stamping_supplier: str | None = None,
        version: str | None = None,
        as_of_year: int | None = None,
        as_of_month: int | None = None,
        include_expired: bool = False,
    ) -> tuple[list[StampingDiePart], int]:
        query = self._scope_query(
            db,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            stamping_supplier=stamping_supplier,
            version=version,
            part_number=part_number,
            as_of_year=as_of_year,
            as_of_month=as_of_month,
            include_expired=include_expired,
        )
        total = query.count()
        rows = (
            query.order_by(StampingDiePart.seq_no.asc(), StampingDiePart.id.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return rows, total

    def get_by_id(self, db: Session, part_id: int) -> StampingDiePart | None:
        return (
            db.query(StampingDiePart)
            .options(selectinload(StampingDiePart.processes))
            .filter(StampingDiePart.id == part_id)
            .first()
        )

    def get_identity_by_id(self, db: Session, part_id: int) -> StampingDiePart | None:
        """只取主表行，不加载工序（工程变更抄模具费用）。"""
        return db.query(StampingDiePart).filter(StampingDiePart.id == part_id).first()

    def get_by_location_vehicle_part(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        part_number: str,
    ) -> StampingDiePart | None:
        """唯一键单查，不加载工序。"""
        return (
            db.query(StampingDiePart)
            .filter(
                StampingDiePart.location == location,
                StampingDiePart.vehicle_model == vehicle_model,
                StampingDiePart.part_number == part_number,
            )
            .first()
        )

    def list_for_export(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        stamping_supplier: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        as_of_year: int | None = None,
        as_of_month: int | None = None,
        include_expired: bool = False,
    ) -> list[StampingDiePart]:
        rows: list[StampingDiePart] = (
            self._scope_query(
                db,
                location=location,
                vehicle_model=vehicle_model,
                stamping_supplier=stamping_supplier,
                version=version,
                part_number=part_number,
                as_of_year=as_of_year,
                as_of_month=as_of_month,
                include_expired=include_expired,
            )
            .options(selectinload(StampingDiePart.processes))
            .order_by(StampingDiePart.seq_no.asc(), StampingDiePart.id.asc())
            .all()
        )
        return rows

    def list_existing_in_scope(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
    ) -> list[StampingDiePart]:
        return (
            db.query(StampingDiePart)
            .options(selectinload(StampingDiePart.processes))
            .filter(
                StampingDiePart.location == location,
                StampingDiePart.vehicle_model == vehicle_model,
            )
            .all()
        )

    def count_processes_by_part_ids(self, db: Session, part_ids: list[int]) -> dict[int, int]:
        if not part_ids:
            return {}
        from sqlalchemy import func

        rows = (
            db.query(StampingDieProcess.die_part_id, func.count(StampingDieProcess.id))
            .filter(StampingDieProcess.die_part_id.in_(part_ids))
            .group_by(StampingDieProcess.die_part_id)
            .all()
        )
        return {int(part_id): int(count) for part_id, count in rows}

    def bulk_create_parts(
        self, db: Session, rows: list[StampingDiePartInsert]
    ) -> list[StampingDiePart]:
        created: list[StampingDiePart] = []
        for payload in rows:
            instance = model_from_payload(StampingDiePart, payload)
            db.add(instance)
            created.append(instance)
        db.flush()
        return created

    def delete_processes_by_part_ids(self, db: Session, part_ids: list[int]) -> int:
        if not part_ids:
            return 0
        deleted = (
            db.query(StampingDieProcess)
            .filter(StampingDieProcess.die_part_id.in_(part_ids))
            .delete(synchronize_session=False)
        )
        db.flush()
        return int(deleted)

    def delete_by_ids(self, db: Session, part_ids: list[int]) -> int:
        unique_ids = list(dict.fromkeys(part_ids))
        if not unique_ids:
            return 0
        deleted = (
            db.query(StampingDiePart)
            .filter(StampingDiePart.id.in_(unique_ids))
            .delete(synchronize_session=False)
        )
        db.flush()
        return int(deleted)

    def delete_scope(
        self,
        db: Session,
        *,
        vehicle_model: str,
        location: str | None = None,
        locations: list[str] | None = None,
    ) -> int:
        query = db.query(StampingDiePart.id).filter(StampingDiePart.vehicle_model == vehicle_model)
        if locations is not None:
            query = query.filter(StampingDiePart.location.in_(locations))
        elif location:
            query = query.filter(StampingDiePart.location == location)
        part_ids = [part_id for (part_id,) in query.all()]
        if not part_ids:
            return 0
        db.query(StampingDieProcess).filter(StampingDieProcess.die_part_id.in_(part_ids)).delete(
            synchronize_session=False
        )
        deleted = (
            db.query(StampingDiePart)
            .filter(StampingDiePart.id.in_(part_ids))
            .delete(synchronize_session=False)
        )
        db.flush()
        return int(deleted)

    def list_with_processes(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        overlap_year: int | None = None,
    ) -> list[StampingDiePart]:
        query = (
            db.query(StampingDiePart)
            .options(selectinload(StampingDiePart.processes))
            .filter(
                StampingDiePart.location == location,
                StampingDiePart.vehicle_model == vehicle_model,
            )
        )
        if overlap_year is not None:
            query = query.filter(
                period_overlaps_year_clause(
                    StampingDiePart.effective_year,
                    StampingDiePart.expiry_year,
                    overlap_year,
                )
            )
        return query.order_by(StampingDiePart.id.asc()).all()

    def list_locations(self, db: Session) -> list[str]:
        rows = (
            db.query(StampingDiePart.location)
            .distinct()
            .order_by(StampingDiePart.location.asc())
            .all()
        )
        return [row[0] for row in rows if row[0]]

    def list_vehicle_models(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        overlap_year: int | None = None,
    ) -> list[str]:
        query = db.query(StampingDiePart.vehicle_model).distinct()
        if locations is not None:
            query = query.filter(StampingDiePart.location.in_(locations))
        elif location:
            query = query.filter(StampingDiePart.location == location)
        if overlap_year is not None:
            query = query.filter(
                period_overlaps_year_clause(
                    StampingDiePart.effective_year,
                    StampingDiePart.expiry_year,
                    overlap_year,
                )
            )
        rows = query.order_by(StampingDiePart.vehicle_model.asc()).all()
        return [row[0] for row in rows if row[0]]

    def list_distinct_suppliers(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
    ) -> list[str]:
        rows = (
            db.query(StampingDiePart.stamping_supplier)
            .filter(
                StampingDiePart.location == location,
                StampingDiePart.vehicle_model == vehicle_model,
                StampingDiePart.stamping_supplier.isnot(None),
                StampingDiePart.stamping_supplier != "",
            )
            .distinct()
            .order_by(StampingDiePart.stamping_supplier.asc())
            .all()
        )
        return [row[0] for row in rows if row[0]]

    def list_distinct_versions(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        stamping_supplier: str | None = None,
    ) -> list[str]:
        query = db.query(StampingDiePart.version).filter(
            StampingDiePart.location == location,
            StampingDiePart.vehicle_model == vehicle_model,
            StampingDiePart.version.isnot(None),
            StampingDiePart.version != "",
        )
        if stamping_supplier:
            query = query.filter(StampingDiePart.stamping_supplier == stamping_supplier)
        rows = query.distinct().order_by(StampingDiePart.version.asc()).all()
        return [row[0] for row in rows if row[0]]


class StampingDieProcessRepository:
    def get_by_id(self, db: Session, process_id: int) -> StampingDieProcess | None:
        return db.query(StampingDieProcess).filter(StampingDieProcess.id == process_id).first()

    def list_by_ids(self, db: Session, process_ids: list[int]) -> list[StampingDieProcess]:
        unique_ids = list(dict.fromkeys(process_ids))
        if not unique_ids:
            return []
        return db.query(StampingDieProcess).filter(StampingDieProcess.id.in_(unique_ids)).all()

    def list_die_numbers_for_scope(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
    ) -> list[str]:
        rows = (
            db.query(StampingDieProcess.die_number)
            .join(StampingDiePart, StampingDieProcess.die_part_id == StampingDiePart.id)
            .filter(
                StampingDiePart.location == location,
                StampingDiePart.vehicle_model == vehicle_model,
                StampingDieProcess.die_number.isnot(None),
                StampingDieProcess.die_number != "",
            )
            .all()
        )
        return [number for (number,) in rows if (number or "").strip()]

    def bulk_create(self, db: Session, rows: list[StampingDieProcessInsert]) -> None:
        for payload in rows:
            db.add(model_from_payload(StampingDieProcess, payload))
        db.flush()
