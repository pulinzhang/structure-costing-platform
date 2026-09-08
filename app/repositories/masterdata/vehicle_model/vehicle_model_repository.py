"""项目主数据 Repository。"""

from sqlalchemy.orm import Session

from app.models.masterdata.location import Location
from app.models.masterdata.vehicle_model import VehicleModel
from app.repositories.persist import apply_payload_fields, model_from_payload
from app.schemas.dto.vehicle_model_dto import VehicleModelInsert, VehicleModelPatch


class VehicleModelRepository:
    """项目数据访问。"""

    def get(
        self,
        db: Session,
        location: str,
        vehicle_model: str,
    ) -> VehicleModel | None:
        return (
            db.query(VehicleModel)
            .filter(
                VehicleModel.location == location,
                VehicleModel.vehicle_model == vehicle_model,
            )
            .first()
        )

    def list_all(self, db: Session) -> list[VehicleModel]:
        return (
            db.query(VehicleModel)
            .join(Location, VehicleModel.location == Location.location)
            .order_by(Location.sort_order.asc(), VehicleModel.vehicle_model.asc())
            .all()
        )

    def list_by_location(self, db: Session, location: str) -> list[VehicleModel]:
        return (
            db.query(VehicleModel)
            .filter(VehicleModel.location == location)
            .order_by(VehicleModel.vehicle_model.asc())
            .all()
        )

    def list_by_code(self, db: Session, vehicle_model: str) -> list[VehicleModel]:
        return (
            db.query(VehicleModel)
            .filter(VehicleModel.vehicle_model == vehicle_model)
            .order_by(VehicleModel.location.asc())
            .all()
        )

    def list_distinct_codes(self, db: Session) -> list[str]:
        rows = (
            db.query(VehicleModel.vehicle_model)
            .distinct()
            .order_by(VehicleModel.vehicle_model.asc())
            .all()
        )
        return [str(code) for (code,) in rows if code]

    def create(self, db: Session, payload: VehicleModelInsert) -> VehicleModel:
        record = model_from_payload(VehicleModel, payload)
        db.add(record)
        db.flush()
        return record

    def apply_patch(
        self,
        db: Session,
        record: VehicleModel,
        patch: VehicleModelPatch,
    ) -> VehicleModel:
        apply_payload_fields(record, patch)
        db.flush()
        return record

    def delete(self, db: Session, record: VehicleModel) -> None:
        db.delete(record)
        db.flush()
