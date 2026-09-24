"""设计变更工艺零件入口。

一个零件按顺序写完再写下个：clone 出的零件一行、每一道工序、每一条材料变更历史。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.stamping.part.process import StampingProcessRepository
from app.repositories.stamping.part.repository import StampingPartRepository
from app.schemas.dto.stamping_upload_dto import PartData, ProcessData
from app.schemas.vo.user_vo import UserVO
from app.services.stamping.part.engineering.design_change.as_of import (
    get_part_as_of,
    list_parts_as_of,
    process_material_on_file,
)
from app.services.stamping.part.engineering.design_change.clone import clone_revise_from_predecessor
from app.services.stamping.part.engineering.design_change.insert import (
    insert_material_changes_for_engineering_change,
    insert_part_for_engineering_change,
    insert_processes_for_engineering_change,
)
from app.services.stamping.part.engineering.design_change.rollback import (
    rollback_engineering_change_part,
)
from app.services.stamping.part.engineering.design_change.types import (
    EngineeringChangeMaterialHistoryClone,
    EngineeringChangePartAsOfRow,
    EngineeringChangeProcessPartResult,
    EngineeringChangeProcessPartSpec,
)
from app.services.stamping.part.rules.part_seq_validator import next_consecutive_seq_no


class StampingDesignChangeService:
    """设计变更对工艺零件的读写。一个零件写完 clone 出的零件、工序、材料变更历史，再写下个。"""

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
        """设计变更：当月命中零件号。"""
        return list_parts_as_of(
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
        return get_part_as_of(
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
        return process_material_on_file(db, material)

    def next_seq_no_in_scope_for_engineering_change(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
    ) -> int:
        """设计变更增加零件：该厂该项目已有 seq_no（含已失效）的 max+1。"""
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
    ) -> tuple[PartData, list[ProcessData], list[EngineeringChangeMaterialHistoryClone]]:
        """clone 旧零件的零件一行、全部工序、全部材料变更历史，不写库。"""
        return clone_revise_from_predecessor(
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
        """每个零件按顺序写入 clone 出的三样（不 commit）。增加零件没有材料变更历史。"""
        results: list[EngineeringChangeProcessPartResult] = []
        for spec in specs:
            part_id, predecessor_id = insert_part_for_engineering_change(
                self.repository,
                db,
                spec,
                current_user,
            )
            insert_processes_for_engineering_change(
                self.process_repository,
                db,
                part_id=part_id,
                processes=spec.processes,
                current_user=current_user,
            )
            history_ids = insert_material_changes_for_engineering_change(
                db,
                part_id=part_id,
                material_changes=spec.material_changes,
                current_user=current_user,
            )
            results.append(
                EngineeringChangeProcessPartResult(
                    part_id=part_id,
                    predecessor_id=predecessor_id,
                    material_history_ids=history_ids,
                )
            )
        return results

    def rollback_engineering_change_part(
        self,
        db: Session,
        *,
        after_part_id: int | None,
        before_part_id: int | None,
        current_user: UserVO,
    ) -> None:
        """设计变更回滚工艺零件（不 commit）。"""
        rollback_engineering_change_part(
            self.repository,
            self.process_repository,
            db,
            after_part_id=after_part_id,
            before_part_id=before_part_id,
            current_user=current_user,
        )
