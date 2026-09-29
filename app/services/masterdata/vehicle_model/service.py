"""项目主数据 Service（门面，符号路径保持不变）。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.masterdata.vehicle_model.vehicle_model_repository import (
    VehicleModelRepository,
)
from app.schemas.dto.vehicle_model_dto import VehicleModelCreateDTO, VehicleModelUpdateDTO
from app.schemas.vo.user_vo import UserVO
from app.schemas.vo.vehicle_model_vo import (
    VehicleModelListVO,
    VehicleModelUploadResultVO,
    VehicleModelVO,
)
from app.services.masterdata.location.service import LocationService
from app.services.masterdata.vehicle_model.catalog import (
    build_template as build_catalog_template,
    export_excel as export_catalog_excel,
)
from app.services.masterdata.vehicle_model.crud import (
    create_vehicle_model,
    delete_vehicle_model,
    list_page,
    update_vehicle_model,
)
from app.services.masterdata.vehicle_model.identity import (
    assert_matches_selected,
    list_filter_codes,
    list_introducible,
    list_overlaps_year,
    list_registered,
    normalize,
    require_introducible,
    require_introducible_by_code,
    require_overlaps_year,
    require_registered,
    require_row,
)
from app.services.masterdata.vehicle_model.upload import process_upload as process_vehicle_upload


class VehicleModelService:
    """项目 CRUD、上传与解析契约。"""

    def __init__(self) -> None:
        self.repository = VehicleModelRepository()
        self.location_service = LocationService()

    def normalize(self, value: str | None) -> str | None:
        return normalize(value)

    def require_registered(
        self,
        db: Session,
        location: str,
        vehicle_model: str,
    ) -> str:
        return require_registered(self.repository, db, location, vehicle_model)

    def project_sop_period(
        self,
        db: Session,
        location: str,
        vehicle_model: str,
    ) -> tuple[int, int, int | None, int | None]:
        record = require_row(self.repository, location, vehicle_model, db)
        return (
            record.effective_year,
            record.effective_month,
            record.expiry_year,
            record.expiry_month,
        )

    def require_introducible(
        self,
        db: Session,
        location: str,
        vehicle_model: str,
        year: int,
        month: int,
    ) -> tuple[str, str]:
        return require_introducible(
            self.repository,
            self.location_service,
            db,
            location,
            vehicle_model,
            year,
            month,
        )

    def require_introducible_by_code(
        self,
        db: Session,
        vehicle_model: str,
        year: int,
        month: int,
    ) -> tuple[str, str]:
        return require_introducible_by_code(
            self.repository, self.location_service, db, vehicle_model, year, month
        )

    def require_overlaps_year(
        self,
        db: Session,
        location: str,
        vehicle_model: str,
        year: int,
    ) -> tuple[str, str]:
        return require_overlaps_year(
            self.repository, self.location_service, db, location, vehicle_model, year
        )

    def assert_matches_selected(self, selected: str | None, parsed: str | None) -> None:
        assert_matches_selected(selected, parsed)

    def list_introducible(
        self,
        db: Session,
        location: str,
        year: int,
        month: int,
    ) -> list[str]:
        return list_introducible(self.repository, self.location_service, db, location, year, month)

    def list_registered(self, db: Session, location: str) -> list[str]:
        return list_registered(self.repository, self.location_service, db, location)

    def list_filter_codes(self, db: Session, location: str | None = None) -> list[str]:
        return list_filter_codes(self.repository, self.location_service, db, location)

    def list_overlaps_year(self, db: Session, location: str, year: int) -> list[str]:
        return list_overlaps_year(self.repository, self.location_service, db, location, year)

    def list_page(self, db: Session) -> VehicleModelListVO:
        return list_page(self.repository, self.location_service, db)

    def create(
        self,
        db: Session,
        dto: VehicleModelCreateDTO,
        current_user: UserVO,
    ) -> VehicleModelVO:
        return create_vehicle_model(self.repository, self.location_service, db, dto, current_user)

    def update(
        self,
        db: Session,
        location: str,
        vehicle_model: str,
        dto: VehicleModelUpdateDTO,
        current_user: UserVO,
    ) -> VehicleModelVO:
        return update_vehicle_model(self.repository, db, location, vehicle_model, dto, current_user)

    def delete(self, db: Session, location: str, vehicle_model: str) -> None:
        delete_vehicle_model(self.repository, db, location, vehicle_model)

    def process_upload(
        self,
        db: Session,
        file_content: bytes,
        current_user: UserVO,
    ) -> VehicleModelUploadResultVO:
        return process_vehicle_upload(
            self.repository, self.location_service, db, file_content, current_user
        )

    def build_template(self) -> tuple[bytes, str]:
        return build_catalog_template()

    def export_excel(
        self,
        db: Session,
        current_user: UserVO,
        location: str | None = None,
    ) -> tuple[bytes, str]:
        return export_catalog_excel(
            self.repository, self.location_service, db, current_user, location
        )
