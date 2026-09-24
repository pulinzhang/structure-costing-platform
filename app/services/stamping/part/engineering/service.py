"""工程变更工艺零件：当月命中、改图抄行、插行、回滚。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.stamping.part.process import StampingProcessRepository
from app.repositories.stamping.part.repository import StampingPartRepository
from app.schemas.dto.stamping_upload_dto import PartData, ProcessData
from app.schemas.vo.user_vo import UserVO
from app.services.stamping.part.engineering.change import (
    MISS_NOT_AS_OF,
    MISS_SUPPLIER_UNKNOWN,
    EngineeringChangePartAsOfRow,
    EngineeringChangeProcessPartResult,
    EngineeringChangeProcessPartSpec,
)
from app.services.stamping.part.engineering.change import (
    clone_revise_from_predecessor as clone_revise_from_predecessor_fn,
)
from app.services.stamping.part.engineering.change import (
    get_part_as_of as get_part_as_of_fn,
)
from app.services.stamping.part.engineering.change import (
    insert_for_engineering_change as insert_for_engineering_change_fn,
)
from app.services.stamping.part.engineering.change import (
    list_parts_as_of as list_parts_as_of_fn,
)
from app.services.stamping.part.engineering.change import (
    process_material_on_file as process_material_on_file_fn,
)
from app.services.stamping.part.engineering.change import (
    rollback_engineering_change_part as rollback_engineering_change_part_fn,
)
from app.services.stamping.part.engineering.material_change import (
    MaterialChangeHistoryRow,
    MaterialChangeHistorySpec,
)
from app.services.stamping.part.engineering.material_change import (
    delete_material_changes as delete_material_changes_fn,
)
from app.services.stamping.part.engineering.material_change import (
    has_later_material_change as has_later_material_change_fn,
)
from app.services.stamping.part.engineering.material_change import (
    insert_material_changes as insert_material_changes_fn,
)
from app.services.stamping.part.engineering.material_change import (
    list_material_changes as list_material_changes_fn,
)
from app.services.stamping.part.engineering.material_change import (
    material_after_as_of as material_after_as_of_fn,
)
from app.services.stamping.part.rules.part_seq_validator import next_consecutive_seq_no

__all__ = [
    "EngineeringChangePartAsOfRow",
    "EngineeringChangeProcessPartResult",
    "EngineeringChangeProcessPartSpec",
    "MISS_NOT_AS_OF",
    "MISS_SUPPLIER_UNKNOWN",
    "MaterialChangeHistoryRow",
    "MaterialChangeHistorySpec",
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

    def get_part_as_of(
        self,
        db: Session,
        *,
        location: str,
        stamping_supplier: str,
        vehicle_model: str,
        part_number: str,
        as_of_year: int,
        as_of_month: int,
    ) -> tuple[EngineeringChangePartAsOfRow | None, str | None]:
        return get_part_as_of_fn(
            self.repository,
            db,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            part_number=part_number,
            as_of_year=as_of_year,
            as_of_month=as_of_month,
        )

    def process_material_on_file(self, db: Session, material: str) -> bool:
        return process_material_on_file_fn(db, material)

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

    def insert_material_changes(
        self,
        db: Session,
        specs: list[MaterialChangeHistorySpec],
        current_user: UserVO,
    ) -> list[int]:
        """写入材料变更历史（不 commit）。"""
        return insert_material_changes_fn(db, specs, current_user)

    def delete_material_changes(self, db: Session, history_ids: list[int]) -> None:
        """按历史行 id 删除（不 commit）。"""
        delete_material_changes_fn(db, history_ids)

    def list_material_changes(self, db: Session, part_id: int) -> list[MaterialChangeHistoryRow]:
        return list_material_changes_fn(db, part_id)

    def has_later_material_change(
        self,
        db: Session,
        *,
        part_id: int,
        effective_year: int,
        effective_month: int,
    ) -> bool:
        return has_later_material_change_fn(
            db,
            part_id=part_id,
            effective_year=effective_year,
            effective_month=effective_month,
        )

    def material_after_as_of(
        self,
        process_material: str | None,
        rows: list[MaterialChangeHistoryRow],
        *,
        as_of_year: int,
        as_of_month: int,
    ) -> str | None:
        return material_after_as_of_fn(
            process_material,
            rows,
            as_of_year=as_of_year,
            as_of_month=as_of_month,
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
