"""主数据切片 ORM。"""

from app.models.masterdata.location import Location, LocationAlias
from app.models.masterdata.vehicle_model import VehicleModel

__all__ = ["Location", "LocationAlias", "VehicleModel"]
