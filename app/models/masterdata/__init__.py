"""主数据切片 ORM。"""

from app.models.masterdata.assembly_category import AssemblyCategory
from app.models.masterdata.category_billing import AssemblyCategoryBilling
from app.models.masterdata.fee_archive import FeeArchive
from app.models.masterdata.location import Location, LocationAlias
from app.models.masterdata.steel_grade_category import SteelGradeCategory
from app.models.masterdata.steel_mill import SteelMill, SteelMillAlias
from app.models.masterdata.supplier import Supplier, SupplierAlias
from app.models.masterdata.vehicle_model import VehicleModel

__all__ = [
    "AssemblyCategory",
    "AssemblyCategoryBilling",
    "FeeArchive",
    "Location",
    "LocationAlias",
    "SteelGradeCategory",
    "SteelMill",
    "SteelMillAlias",
    "Supplier",
    "SupplierAlias",
    "VehicleModel",
]
