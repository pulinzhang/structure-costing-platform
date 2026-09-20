"""冲压零件数据访问。查询 / 筛选 / 写入拆在本包 queries、writes、material_specs。"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.common.types.repository_types import (
    StampingPartCascadeFilterOptions,
    StampingPartFilterSummary,
)
from app.models.stamping import StampingPart
from app.repositories.stamping.part.filter_options import StampingPartFilterOptions
from app.repositories.stamping.part.material_specs import StampingPartMaterialSpecs
from app.repositories.stamping.part.queries import StampingPartQueries
from app.repositories.stamping.part.types import (
    MaterialSpecRow,
    StampingPartDieMatchIdentity,
    StampingPartFilterOptionValues,
    StampingPartScopeIdentity,
)
from app.repositories.stamping.part.writes import StampingPartWrites
from app.schemas.dto.stamping_upload_dto import PartData, StampingPartPatch

__all__ = [
    "StampingPartRepository",
    "MaterialSpecRow",
    "StampingPartDieMatchIdentity",
    "StampingPartFilterOptionValues",
    "StampingPartScopeIdentity",
]


class StampingPartRepository:
    """零件数据访问。"""

    def __init__(self) -> None:
        self._queries = StampingPartQueries()
        self._filter_options = StampingPartFilterOptions()
        self._writes = StampingPartWrites(self._queries)
        self._material_specs = StampingPartMaterialSpecs()

    def count_all(self, db: Session) -> int:
        return self._queries.count_all(db)

    def count_distinct_vehicle_models(self, db: Session) -> int:
        return self._queries.count_distinct_vehicle_models(db)

    def exists_location_vehicle_model(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
    ) -> bool:
        return self._queries.exists_location_vehicle_model(
            db, location=location, vehicle_model=vehicle_model
        )

    def list_distinct_parts_for_scope(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
    ) -> list[StampingPartScopeIdentity]:
        return self._queries.list_distinct_parts_for_scope(
            db, location=location, vehicle_model=vehicle_model
        )

    def list_die_match_identities(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
    ) -> list[StampingPartDieMatchIdentity]:
        return self._queries.list_die_match_identities(
            db, location=location, vehicle_model=vehicle_model
        )

    def list_scrap_byproduct_keys(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
    ) -> frozenset[tuple[str, str, str]]:
        return self._queries.list_scrap_byproduct_keys(
            db, location=location, vehicle_model=vehicle_model
        )

    def get_by_id(self, db: Session, part_id: int) -> StampingPart | None:
        return self._queries.get_by_id(db, part_id)

    def get_by_unique_key(
        self,
        db: Session,
        *,
        location: str,
        stamping_supplier: str,
        vehicle_model: str,
        part_number: str,
    ) -> StampingPart | None:
        return self._queries.get_by_unique_key(
            db,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            part_number=part_number,
        )

    def list_identity_scope(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
    ) -> list[StampingPart]:
        return self._queries.list_identity_scope(
            db,
            location=location,
            vehicle_model=vehicle_model,
            stamping_supplier=stamping_supplier,
            stamping_suppliers=stamping_suppliers,
        )

    def get_by_part_number(self, db: Session, part_number: str) -> StampingPart | None:
        return self._queries.get_by_part_number(db, part_number)

    def filter_by_vehicle_version(
        self,
        db: Session,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        part_name: str | None = None,
        stamping_supplier: str | None = None,
    ) -> tuple[list[StampingPart], int]:
        return self._queries.filter_by_vehicle_version(
            db, vehicle_model, version, part_number, part_name, stamping_supplier
        )

    def paginate(
        self,
        db: Session,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        part_name: str | None = None,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
        skip: int = 0,
        limit: int = 100,
        as_of_year: int | None = None,
        as_of_month: int | None = None,
        include_expired: bool = False,
    ) -> tuple[list[StampingPart], int]:
        return self._queries.paginate(
            db,
            location,
            locations,
            vehicle_model,
            version,
            part_number,
            part_name,
            stamping_supplier,
            stamping_suppliers,
            skip,
            limit,
            as_of_year,
            as_of_month,
            include_expired,
        )

    def summarize_by_filters(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        part_name: str | None = None,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
    ) -> StampingPartFilterSummary:
        return self._queries.summarize_by_filters(
            db,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            part_name=part_name,
            stamping_supplier=stamping_supplier,
            stamping_suppliers=stamping_suppliers,
        )

    def list_with_processes(
        self,
        db: Session,
        location: str,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        overlap_year: int | None = None,
        as_of_year: int | None = None,
        as_of_month: int | None = None,
    ) -> list[StampingPart]:
        return self._queries.list_with_processes(
            db,
            location,
            stamping_supplier,
            vehicle_model,
            version,
            overlap_year,
            as_of_year,
            as_of_month,
        )

    def list_for_export(
        self,
        db: Session,
        *,
        location: str | None = None,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        part_name: str | None = None,
        as_of_year: int | None = None,
        as_of_month: int | None = None,
        include_expired: bool = False,
    ) -> list[StampingPart]:
        return self._queries.list_for_export(
            db,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            part_name=part_name,
            as_of_year=as_of_year,
            as_of_month=as_of_month,
            include_expired=include_expired,
        )

    def list_all(self, db: Session, skip: int = 0, limit: int = 100) -> list[StampingPart]:
        return self._queries.list_all(db, skip, limit)

    def get_all_by_scope(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        version: str,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
    ) -> list[StampingPart]:
        return self._queries.get_all_by_scope(
            db,
            location=location,
            vehicle_model=vehicle_model,
            version=version,
            stamping_supplier=stamping_supplier,
            stamping_suppliers=stamping_suppliers,
        )

    def list_by_location_and_vehicle(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        overlap_year: int | None = None,
        as_of_year: int | None = None,
        as_of_month: int | None = None,
    ) -> list[StampingPart]:
        return self._queries.list_by_location_and_vehicle(
            db,
            location=location,
            vehicle_model=vehicle_model,
            overlap_year=overlap_year,
            as_of_year=as_of_year,
            as_of_month=as_of_month,
        )

    def count_processes_by_part_ids(self, db: Session, part_ids: list[int]) -> dict[int, int]:
        return self._queries.count_processes_by_part_ids(db, part_ids)

    def get_filter_options(self, db: Session) -> StampingPartFilterOptionValues:
        return self._filter_options.get_filter_options(db)

    def get_cascade_filter_options(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        overlap_year: int | None = None,
        as_of_year: int | None = None,
        as_of_month: int | None = None,
    ) -> StampingPartCascadeFilterOptions:
        return self._filter_options.get_cascade_filter_options(
            db,
            location=location,
            locations=locations,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
            overlap_year=overlap_year,
            as_of_year=as_of_year,
            as_of_month=as_of_month,
        )

    def create(self, db: Session, part_data: PartData) -> StampingPart:
        return self._writes.create(db, part_data)

    def bulk_create(self, db: Session, parts_data: list[PartData]) -> list[StampingPart]:
        return self._writes.bulk_create(db, parts_data)

    def update(
        self, db: Session, part_id: int, update_data: StampingPartPatch
    ) -> StampingPart | None:
        return self._writes.update(db, part_id, update_data)

    def delete(self, db: Session, part_id: int) -> bool:
        return self._writes.delete(db, part_id)

    def delete_by_scope(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        version: str,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
    ) -> int:
        return self._writes.delete_by_scope(
            db,
            location=location,
            vehicle_model=vehicle_model,
            version=version,
            stamping_supplier=stamping_supplier,
            stamping_suppliers=stamping_suppliers,
        )

    def get_id_map_by_scope(
        self,
        db: Session,
        *,
        location: str,
        stamping_supplier: str,
        vehicle_model: str,
        version: str,
    ) -> dict[str, int]:
        return self._writes.get_id_map_by_scope(
            db,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
        )

    def list_parts_for_materials(
        self,
        db: Session,
        location: str | None = None,
        locations: list[str] | None = None,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
    ) -> list[StampingPart]:
        return self._material_specs.list_parts_for_materials(
            db, location, locations, stamping_supplier, stamping_suppliers, vehicle_model, version
        )

    def count_material_specs(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
    ) -> int:
        return self._material_specs.count_material_specs(
            db, location=location, vehicle_model=vehicle_model
        )

    def list_distinct_spec_grades(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
    ) -> list[str]:
        return self._material_specs.list_distinct_spec_grades(
            db, location=location, vehicle_model=vehicle_model
        )

    def list_material_specs(self, db: Session, *, location: str) -> list[MaterialSpecRow]:
        return self._material_specs.list_material_specs(db, location=location)
