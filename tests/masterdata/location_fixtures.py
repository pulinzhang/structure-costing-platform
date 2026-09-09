"""测试用基地行。生产启动不灌基地。"""

from sqlalchemy.orm import Session

from app.common.audit import SYSTEM_USER
from app.schemas.dto.location_dto import LocationCreateDTO
from app.services.masterdata.location import LocationService

_SAMPLE: tuple[tuple[str, str], ...] = (
    ("大连", "大连基地"),
    ("芜湖", "芜湖基地"),
    ("鄂尔多斯", "鄂尔多斯基地"),
    ("青岛", "青岛基地"),
)


def insert_sample_locations(db: Session) -> None:
    service = LocationService()
    for name, alias in _SAMPLE:
        service.create(
            db,
            LocationCreateDTO(location=name, aliases=[alias]),
            current_user=SYSTEM_USER,
        )
