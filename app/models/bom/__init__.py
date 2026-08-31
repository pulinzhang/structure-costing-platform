"""BOM 切片 ORM。"""

from app.models.bom.annual_part_price import BomAnnualPartPrice
from app.models.bom.packaging_transport_fee import BomPackagingTransportFee
from app.models.bom.procurement_object import (
    BomProcurementObject,
    BomProcurementObjectList,
)
from app.models.bom.procurement_object_generate_log import BomProcurementObjectGenerateLog
from app.models.bom.node import BomNode, BomSnapshot
from app.models.bom.welding_fee import BomWeldingFee
from app.models.bom.welding_fee_calc_log import BomWeldingFeeCalcLog
from app.models.bom.welding_fee_item import BomWeldingFeeItem
from app.models.bom.welding_process_breakdown import (
    BomWeldingProcessBreakdownLine,
    BomWeldingProcessBreakdownNode,
)
from app.models.bom.welding_process_breakdown_generate_log import (
    BomWeldingProcessBreakdownGenerateLog,
)
from app.models.bom.welding_unit_price import BomWeldingUnitPrice

__all__ = [
    "BomAnnualPartPrice",
    "BomPackagingTransportFee",
    "BomProcurementObject",
    "BomProcurementObjectGenerateLog",
    "BomProcurementObjectList",
    "BomWeldingFee",
    "BomWeldingFeeCalcLog",
    "BomWeldingFeeItem",
    "BomNode",
    "BomSnapshot",
    "BomWeldingProcessBreakdownGenerateLog",
    "BomWeldingProcessBreakdownLine",
    "BomWeldingProcessBreakdownNode",
    "BomWeldingUnitPrice",
]
