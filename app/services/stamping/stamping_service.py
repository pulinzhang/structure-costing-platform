"""
冲压工艺 Service（门面，符号路径保持不变）。
业务逻辑层，处理业务规则和事务。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.stamping import StampingPart
from app.repositories.stamping.stamping_part_repository import MaterialSpecRow
from app.repositories.stamping.stamping_repository import (
    StampingPartRepository,
    StampingProcessRepository,
)
from app.schemas.dto.stamping_part_dto import (
    StampingCascadeFilterQuery,
    StampingMaterialQuery,
    StampingPartBatchDeleteDTO,
    StampingPartOffalUpdateDTO,
    StampingPartQuery,
    StampingProcessItemUpdate,
    StampingProcessUpdate,
)
from app.schemas.dto.stamping_upload_dto import PartData, ProcessData, StampingPartPatch
from app.schemas.vo.stamping_vo import (
    StampingCascadeFilterOptionsVO,
    StampingMaterialResponse,
    StampingPartBatchDeleteResultVO,
    StampingPartListFilterOptions,
    StampingPartListResponse,
    StampingPartResponse,
    StampingPartWithProcessesResponse,
    StampingProcessResponse,
)
from app.schemas.vo.user_vo import UserVO
from app.services.stamping.part.engineering_change import (
    EngineeringChangePartAsOfRow,
    EngineeringChangeProcessPartResult,
    EngineeringChangeProcessPartSpec,
)
from app.services.stamping.part.engineering_change import (
    clone_revise_from_predecessor as clone_revise_from_predecessor_fn,
)
from app.services.stamping.part.engineering_change import (
    insert_for_engineering_change as insert_for_engineering_change_fn,
)
from app.services.stamping.part.engineering_change import (
    list_parts_as_of as list_parts_as_of_fn,
)
from app.services.stamping.part.engineering_change import (
    rollback_engineering_change_part as rollback_engineering_change_part_fn,
)
from app.services.stamping.part.list import (
    count_parts as count_parts_fn,
)
from app.services.stamping.part.list import (
    count_processes as count_processes_fn,
)
from app.services.stamping.part.list import (
    count_vehicle_models as count_vehicle_models_fn,
)
from app.services.stamping.part.list import (
    get_by_id as get_by_id_fn,
)
from app.services.stamping.part.list import (
    get_cascade_filter_options as get_cascade_filter_options_fn,
)
from app.services.stamping.part.list import (
    get_filter_options as get_filter_options_fn,
)
from app.services.stamping.part.list import (
    list_parts as list_parts_fn,
)
from app.services.stamping.part.list import (
    summarize_master as summarize_master_fn,
)
from app.services.stamping.part.materials import (
    count_material_specs as count_material_specs_fn,
)
from app.services.stamping.part.materials import (
    list_distinct_spec_grades as list_distinct_spec_grades_fn,
)
from app.services.stamping.part.materials import (
    list_material_specs as list_material_specs_fn,
)
from app.services.stamping.part.materials import (
    list_materials as list_materials_fn,
)
from app.services.stamping.part.mutations import (
    batch_delete_parts,
    bulk_create_parts,
    create_part,
    delete_part,
    update_part,
)
from app.services.stamping.part.mutations import (
    batch_update_processes as batch_update_processes_fn,
)
from app.services.stamping.part.mutations import (
    update_offal as update_offal_fn,
)
from app.services.stamping.part.mutations import (
    update_process as update_process_fn,
)
from app.services.stamping.part_seq_validator import next_consecutive_seq_no


class StampingPartService:
    """零件业务逻辑"""

    def __init__(self) -> None:
        self.repository = StampingPartRepository()
        self.process_repository = StampingProcessRepository()

    def count_parts(self, db: Session) -> int:
        """零件总数。"""
        return count_parts_fn(self.repository, db)

    def count_processes(self, db: Session) -> int:
        """工序总数。"""
        return count_processes_fn(self.process_repository, db)

    def count_vehicle_models(self, db: Session) -> int:
        """去重车型数量。"""
        return count_vehicle_models_fn(self.repository, db)

    def summarize_master(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
    ) -> dict[str, int]:
        return summarize_master_fn(
            self.repository,
            self.process_repository,
            db,
            location=location,
            vehicle_model=vehicle_model,
        )

    def list_parts(
        self, db: Session, query: StampingPartQuery
    ) -> tuple[list[StampingPartListResponse], int, StampingPartListFilterOptions]:
        return list_parts_fn(self.repository, db, query)

    def get_filter_options(self, db: Session) -> StampingPartListFilterOptions:
        return get_filter_options_fn(self.repository, db)

    def get_cascade_filter_options(
        self,
        db: Session,
        query: StampingCascadeFilterQuery,
    ) -> StampingCascadeFilterOptionsVO:
        return get_cascade_filter_options_fn(self.repository, db, query)

    def list_materials(
        self, db: Session, query: StampingMaterialQuery
    ) -> tuple[list[StampingMaterialResponse], int, StampingPartListFilterOptions]:
        return list_materials_fn(self.repository, db, query)

    def count_material_specs(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
    ) -> int:
        return count_material_specs_fn(
            self.repository, db, location=location, vehicle_model=vehicle_model
        )

    def list_distinct_spec_grades(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
    ) -> list[str]:
        return list_distinct_spec_grades_fn(
            self.repository, db, location=location, vehicle_model=vehicle_model
        )

    def list_material_specs(self, db: Session, *, location: str) -> list[MaterialSpecRow]:
        return list_material_specs_fn(self.repository, db, location=location)

    def get_by_id(self, db: Session, part_id: int) -> StampingPartWithProcessesResponse:
        return get_by_id_fn(self.repository, db, part_id)

    def delete(self, db: Session, part_id: int) -> None:
        delete_part(self.repository, db, part_id)

    def create(
        self,
        db: Session,
        part_data: PartData,
        current_user: UserVO,
    ) -> StampingPart:
        return create_part(self.repository, db, part_data, current_user)

    def bulk_create(
        self,
        db: Session,
        parts_data: list[PartData],
        current_user: UserVO,
    ) -> list[StampingPart]:
        return bulk_create_parts(self.repository, db, parts_data, current_user)

    def update(
        self,
        db: Session,
        part_id: int,
        update_data: StampingPartPatch,
        current_user: UserVO,
    ) -> StampingPart | None:
        return update_part(self.repository, db, part_id, update_data, current_user)

    def update_offal(
        self,
        db: Session,
        part_id: int,
        dto: StampingPartOffalUpdateDTO,
        current_user: UserVO,
    ) -> StampingPartResponse:
        return update_offal_fn(self.repository, db, part_id, dto, current_user)

    def batch_delete(
        self,
        db: Session,
        dto: StampingPartBatchDeleteDTO,
    ) -> StampingPartBatchDeleteResultVO:
        return batch_delete_parts(self.repository, db, dto)

    def update_process(
        self,
        db: Session,
        process_id: int,
        dto: StampingProcessUpdate,
        current_user: UserVO,
    ) -> StampingProcessResponse:
        return update_process_fn(db, process_id, dto, current_user)

    def batch_update_processes(
        self,
        db: Session,
        items: list[StampingProcessItemUpdate],
        current_user: UserVO,
    ) -> int:
        return batch_update_processes_fn(db, items, current_user)

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
