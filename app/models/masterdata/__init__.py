"""主数据切片 ORM。"""

from app.models.masterdata.location import Location, LocationAlias
from app.models.masterdata.steel_grade_category import SteelGradeCategory
from app.models.masterdata.supplier import Supplier, SupplierAlias
from app.models.masterdata.vehicle_model import VehicleModel

__all__ = [
    "Location",
    "LocationAlias",
    "SteelGradeCategory",
    "Supplier",
    "SupplierAlias",
    "VehicleModel",
]
