"""冲压零件材料变更历史：插入、删除、当月材料。只 flush。"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.audit import audit_create
from app.common.period import previous_month
from app.exceptions.base import NotFoundException
from app.models.stamping import StampingPartMaterialChange
from app.repositories.stamping.part.material_change import (
    StampingPartMaterialChangeInsert,
    StampingPartMaterialChangeRepository,
)
from app.schemas.vo.stamping_vo import StampingPartMaterialChangeResponse
from app.schemas.vo.user_vo import UserVO

_repo = StampingPartMaterialChangeRepository()


@dataclass(slots=True)
class MaterialChangeHistorySpec:
    part_id: int
    effective_year: int
    effective_month: int
    before_material: str
    after_material: str
    before_thickness: Decimal
    after_thickness: Decimal


@dataclass(slots=True)
class MaterialChangeHistoryRow:
    id: int
    effective_year: int
    effective_month: int
    before_material: str
    after_material: str
    before_thickness: Decimal
    after_thickness: Decimal


def _to_row(row: StampingPartMaterialChange) -> MaterialChangeHistoryRow:
    return MaterialChangeHistoryRow(
        id=row.id,
        effective_year=row.effective_year,
        effective_month=row.effective_month,
        before_material=row.before_material,
        after_material=row.after_material,
        before_thickness=row.before_thickness,
        after_thickness=row.after_thickness,
    )


class StampingMaterialChangeService:
    """材料变更历史的插入、删除、列出、当月叠材料。不改工艺行。"""

    def insert(
        self,
        db: Session,
        specs: list[MaterialChangeHistorySpec],
        current_user: UserVO,
    ) -> list[int]:
        """写入材料变更历史（不 commit）。"""
        audit = audit_create(current_user)
        history_ids: list[int] = []
        for spec in specs:
            row = _repo.create(
                db,
                StampingPartMaterialChangeInsert(
                    part_id=spec.part_id,
                    effective_year=spec.effective_year,
                    effective_month=spec.effective_month,
                    before_material=spec.before_material,
                    after_material=spec.after_material,
                    before_thickness=spec.before_thickness,
                    after_thickness=spec.after_thickness,
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                ),
            )
            history_ids.append(row.id)
        return history_ids

    def delete(self, db: Session, history_ids: list[int]) -> None:
        """按历史行 id 删除（不 commit）。"""
        for history_id in history_ids:
            row = _repo.get_by_id(db, history_id)
            if row is None:
                raise NotFoundException(f"材料变更历史不存在: id={history_id}")
            _repo.delete(db, row)

    def part_ids_with_history(self, db: Session, part_ids: list[int]) -> set[int]:
        return _repo.part_ids_with_history(db, part_ids)

    def list_for_part(self, db: Session, part_id: int) -> list[MaterialChangeHistoryRow]:
        return [_to_row(row) for row in _repo.list_by_part_id(db, part_id)]

    def has_later(
        self,
        db: Session,
        *,
        part_id: int,
        effective_year: int,
        effective_month: int,
    ) -> bool:
        return _repo.has_later(
            db,
            part_id=part_id,
            effective_year=effective_year,
            effective_month=effective_month,
        )

    def after_as_of(
        self,
        process_material: str | None,
        rows: list[MaterialChangeHistoryRow],
        *,
        as_of_year: int,
        as_of_month: int,
    ) -> str | None:
        """生效月不晚于 as_of 的最后一刀 after_material。没有历史则是工艺列。"""
        latest = process_material
        as_of = (as_of_year, as_of_month)
        for row in rows:
            if (row.effective_year, row.effective_month) <= as_of:
                latest = row.after_material
        return latest

    def for_detail(self, db: Session, part_id: int) -> list[StampingPartMaterialChangeResponse]:
        rows = self.list_for_part(db, part_id)
        details: list[StampingPartMaterialChangeResponse] = []
        for index, row in enumerate(rows):
            nxt = rows[index + 1] if index + 1 < len(rows) else None
            valid_until_year: int | None = None
            valid_until_month: int | None = None
            if nxt is not None:
                valid_until_year, valid_until_month = previous_month(
                    nxt.effective_year, nxt.effective_month
                )
            details.append(
                StampingPartMaterialChangeResponse(
                    effective_year=row.effective_year,
                    effective_month=row.effective_month,
                    valid_until_year=valid_until_year,
                    valid_until_month=valid_until_month,
                    before_material=row.before_material,
                    after_material=row.after_material,
                    before_thickness=row.before_thickness,
                    after_thickness=row.after_thickness,
                )
            )
        return details

    def overlay_by_part(
        self,
        db: Session,
        part_ids: list[int],
        process_material_by_part: dict[int, str],
        year: int,
        month: int,
    ) -> dict[int, str]:
        grouped: dict[int, list[MaterialChangeHistoryRow]] = defaultdict(list)
        for row in _repo.list_by_part_ids(db, part_ids):
            grouped[row.part_id].append(_to_row(row))
        resolved: dict[int, str] = {}
        for part_id in part_ids:
            material = self.after_as_of(
                process_material_by_part.get(part_id),
                grouped.get(part_id, []),
                as_of_year=year,
                as_of_month=month,
            )
            resolved[part_id] = material or ""
        return resolved
