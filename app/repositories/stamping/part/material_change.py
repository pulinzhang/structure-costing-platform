"""冲压零件材料变更历史数据访问。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.stamping import StampingPartMaterialChange
from app.repositories.persist import model_from_payload


@dataclass(slots=True)
class StampingPartMaterialChangeInsert:
    part_id: int
    effective_year: int
    effective_month: int
    before_material: str
    after_material: str
    before_thickness: Decimal
    after_thickness: Decimal
    created_by: str | None
    updated_by: str | None


class StampingPartMaterialChangeRepository:
    def create(
        self, db: Session, payload: StampingPartMaterialChangeInsert
    ) -> StampingPartMaterialChange:
        row = model_from_payload(StampingPartMaterialChange, payload)
        db.add(row)
        db.flush()
        return row

    def list_by_part_id(self, db: Session, part_id: int) -> list[StampingPartMaterialChange]:
        return (
            db.query(StampingPartMaterialChange)
            .filter(StampingPartMaterialChange.part_id == part_id)
            .order_by(
                StampingPartMaterialChange.effective_year.asc(),
                StampingPartMaterialChange.effective_month.asc(),
                StampingPartMaterialChange.id.asc(),
            )
            .all()
        )

    def list_by_part_ids(
        self, db: Session, part_ids: list[int]
    ) -> list[StampingPartMaterialChange]:
        if not part_ids:
            return []
        return (
            db.query(StampingPartMaterialChange)
            .filter(StampingPartMaterialChange.part_id.in_(part_ids))
            .order_by(
                StampingPartMaterialChange.part_id.asc(),
                StampingPartMaterialChange.effective_year.asc(),
                StampingPartMaterialChange.effective_month.asc(),
                StampingPartMaterialChange.id.asc(),
            )
            .all()
        )

    def has_later(
        self,
        db: Session,
        *,
        part_id: int,
        effective_year: int,
        effective_month: int,
    ) -> bool:
        return (
            db.query(StampingPartMaterialChange.id)
            .filter(
                StampingPartMaterialChange.part_id == part_id,
                or_(
                    StampingPartMaterialChange.effective_year > effective_year,
                    and_(
                        StampingPartMaterialChange.effective_year == effective_year,
                        StampingPartMaterialChange.effective_month > effective_month,
                    ),
                ),
            )
            .first()
            is not None
        )

    def delete(self, db: Session, row: StampingPartMaterialChange) -> None:
        db.delete(row)
        db.flush()

    def get_by_id(self, db: Session, history_id: int) -> StampingPartMaterialChange | None:
        return (
            db.query(StampingPartMaterialChange)
            .filter(StampingPartMaterialChange.id == history_id)
            .first()
        )
