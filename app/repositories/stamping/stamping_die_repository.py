"""冲压模具数据访问。"""

from typing import TypedDict

from sqlalchemy.orm import Session, selectinload

from app.models.stamping.die import StampingDiePart, StampingDieProcess
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

    def paginate(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        part_number: str | None,
        skip: int,
        limit: int,
    ) -> tuple[list[StampingDiePart], int]:
        query = db.query(StampingDiePart).filter(
            StampingDiePart.location == location,
            StampingDiePart.vehicle_model == vehicle_model,
        )
        if part_number:
            query = query.filter(StampingDiePart.part_number.like(f"%{part_number.strip()}%"))
        total = query.count()
        rows = (
            query.order_by(StampingDiePart.id.asc())
            .order_by(StampingDiePart.seq_no.asc(), StampingDiePart.id.asc())
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

    def list_for_export(
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
            .order_by(StampingDiePart.seq_no.asc(), StampingDiePart.id.asc())
            .all()
        )

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

    def delete_scope(self, db: Session, *, location: str, vehicle_model: str) -> int:
        part_ids = [
            part_id
            for (part_id,) in db.query(StampingDiePart.id)
            .filter(
                StampingDiePart.location == location,
                StampingDiePart.vehicle_model == vehicle_model,
            )
            .all()
        ]
        if not part_ids:
            return 0
        db.query(StampingDieProcess).filter(StampingDieProcess.die_part_id.in_(part_ids)).delete(
            synchronize_session=False
        )
        deleted = (
            db.query(StampingDiePart)
            .filter(
                StampingDiePart.location == location,
                StampingDiePart.vehicle_model == vehicle_model,
            )
            .delete(synchronize_session=False)
        )
        db.flush()
        return int(deleted)


class StampingDieProcessRepository:
    def get_by_id(self, db: Session, process_id: int) -> StampingDieProcess | None:
        return db.query(StampingDieProcess).filter(StampingDieProcess.id == process_id).first()

    def bulk_create(self, db: Session, rows: list[StampingDieProcessInsert]) -> None:
        for payload in rows:
            db.add(model_from_payload(StampingDieProcess, payload))
        db.flush()
