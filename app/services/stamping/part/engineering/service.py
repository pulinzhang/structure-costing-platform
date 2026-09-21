"""工程变更工艺零件：当月命中、改图抄行、插行、回滚。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.stamping.part.process import StampingProcessRepository
from app.repositories.stamping.part.repository import StampingPartRepository
from app.schemas.dto.stamping_upload_dto import PartData, ProcessData
from app.schemas.vo.user_vo import UserVO
from app.services.stamping.part.engineering.change import (
    EngineeringChangePartAsOfRow,
    EngineeringChangeProcessPartResult,
    EngineeringChangeProcessPartSpec,
)
from app.services.stamping.part.engineering.change import (
    clone_revise_from_predecessor as clone_revise_from_predecessor_fn,
)
from app.services.stamping.part.engineering.change import (
    insert_for_engineering_change as insert_for_engineering_change_fn,
)
from app.services.stamping.part.engineering.change import (
    list_parts_as_of as list_parts_as_of_fn,
)
from app.services.stamping.part.engineering.change import (
    rollback_engineering_change_part as rollback_engineering_change_part_fn,
)
from app.services.stamping.part.rules.part_seq_validator import next_consecutive_seq_no

__all__ = [
    "EngineeringChangePartAsOfRow",
    "EngineeringChangeProcessPartResult",
    "EngineeringChangeProcessPartSpec",
    "StampingEngineeringService",
]


class StampingEngineeringService:
    """工程变更对工艺零件的读写。"""

    def __init__(self) -> None:
        self.repository = StampingPartRepository()
        self.process_repository = StampingProcessRepository()

    def list_parts_as_of_for_engineering_change(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        as_of_year: int,
        as_of_month: int,
    ) -> list[EngineeringChangePartAsOfRow]:
        """工程变更：当月命中零件号。"""
        return list_parts_as_of_fn(
            self.repository,
            db,
            location=location,
            vehicle_model=vehicle_model,
            as_of_year=as_of_year,
            as_of_month=as_of_month,
        )

    def next_seq_no_in_scope_for_engineering_change(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
    ) -> int:
        """工程变更增加零件：该厂该项目已有 seq_no（含已失效）的 max+1。"""
        existing_parts = self.repository.list_by_location_and_vehicle(
            db, location=location, vehicle_model=vehicle_model
        )
        return next_consecutive_seq_no(part.seq_no for part in existing_parts)

    def clone_revise_for_engineering_change(
        self,
        db: Session,
        *,
        predecessor_id: int,
        new_part_number: str,
        version: str,
        effective_year: int,
        effective_month: int,
        expiry_year: int | None,
        expiry_month: int | None,
        created_by: str | None,
        updated_by: str | None,
    ) -> tuple[PartData, list[ProcessData]]:
        """工程变更改图：除零件号、版本、生失效外整行抄旧号，工序相同。"""
        return clone_revise_from_predecessor_fn(
            self.repository,
            self.process_repository,
            db,
            predecessor_id=predecessor_id,
            new_part_number=new_part_number,
            version=version,
            effective_year=effective_year,
            effective_month=effective_month,
            expiry_year=expiry_year,
            expiry_month=expiry_month,
            created_by=created_by,
            updated_by=updated_by,
        )

    def insert_for_engineering_change(
        self,
        db: Session,
        specs: list[EngineeringChangeProcessPartSpec],
        current_user: UserVO,
    ) -> list[EngineeringChangeProcessPartResult]:
        """工程变更插工艺零件（不 commit）。"""
        return insert_for_engineering_change_fn(
            self.repository,
            self.process_repository,
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
        """工程变更回滚工艺零件（不 commit）。"""
        rollback_engineering_change_part_fn(
            self.repository,
            self.process_repository,
            db,
            after_part_id=after_part_id,
            before_part_id=before_part_id,
            current_user=current_user,
        )
