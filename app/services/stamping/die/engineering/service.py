"""工程变更模具布点：当月命中、改图抄行、插行、回滚。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.exceptions.base import NotFoundException
from app.repositories.stamping.die.repository import (
    StampingDiePartRepository,
    StampingDieProcessRepository,
)
from app.schemas.vo.user_vo import UserVO
from app.services.stamping.die.engineering.change import (
    EngineeringChangeDieAsOfRow,
    EngineeringChangeDiePartResult,
    EngineeringChangeDiePartSpec,
    clone_revise_die_spec,
    insert_for_engineering_change as insert_for_engineering_change_fn,
    list_parts_as_of as list_parts_as_of_fn,
    rollback_engineering_change_part as rollback_engineering_change_part_fn,
)

__all__ = [
    "EngineeringChangeDieAsOfRow",
    "EngineeringChangeDiePartResult",
    "EngineeringChangeDiePartSpec",
    "StampingDieEngineeringService",
]


class StampingDieEngineeringService:
    """工程变更对模具布点的读写。"""

    def __init__(self) -> None:
        self.die_part_repo = StampingDiePartRepository()
        self.die_process_repo = StampingDieProcessRepository()

    def list_parts_as_of_for_engineering_change(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        as_of_year: int,
        as_of_month: int,
    ) -> list[EngineeringChangeDieAsOfRow]:
        """工程变更：当月命中布点零件号。"""
        return list_parts_as_of_fn(
            self.die_part_repo,
            db,
            location=location,
            vehicle_model=vehicle_model,
            as_of_year=as_of_year,
            as_of_month=as_of_month,
        )

    def clone_revise_for_engineering_change(
        self,
        db: Session,
        *,
        predecessor_id: int,
        new_part_number: str,
        version: str | None,
        effective_year: int,
        effective_month: int,
        expiry_year: int | None,
        expiry_month: int | None,
        predecessor_expiry_year: int | None,
        predecessor_expiry_month: int | None,
        created_by: str,
        updated_by: str,
    ) -> EngineeringChangeDiePartSpec:
        """工程变更改图：整行抄旧布点（含工序 alloc_ratio）。"""
        old_part = self.die_part_repo.get_by_id(db, predecessor_id)
        if old_part is None:
            raise NotFoundException(f"变更前模具零件不存在: id={predecessor_id}")
        return clone_revise_die_spec(
            old_part,
            new_part_number=new_part_number,
            version=version,
            effective_year=effective_year,
            effective_month=effective_month,
            expiry_year=expiry_year,
            expiry_month=expiry_month,
            predecessor_expiry_year=predecessor_expiry_year,
            predecessor_expiry_month=predecessor_expiry_month,
            created_by=created_by,
            updated_by=updated_by,
        )

    def insert_for_engineering_change(
        self,
        db: Session,
        specs: list[EngineeringChangeDiePartSpec],
        current_user: UserVO,
    ) -> list[EngineeringChangeDiePartResult]:
        """工程变更按号插布点零件（不 commit）。"""
        return insert_for_engineering_change_fn(
            self.die_part_repo,
            self.die_process_repo,
            db,
            specs,
            current_user,
        )

    def rollback_engineering_change_part(
        self,
        db: Session,
        *,
        after_part_id: int | None,
        before_part_id: int | None,
        current_user: UserVO,
    ) -> None:
        """工程变更回滚布点零件（不 commit）。"""
        rollback_engineering_change_part_fn(
            self.die_part_repo,
            self.die_process_repo,
            db,
            after_part_id=after_part_id,
            before_part_id=before_part_id,
            current_user=current_user,
        )
