"""
ORM 全量注册入口，只给 main.py 启动用。

main.py 里 `from app import models` 会执行本文件，从而把各切片实体
import 一遍，SQLAlchemy 才能在 create_all 时发现全部表。

业务代码不要从这里 import。请从对应切片包导入，例如：
    from app.models.stamping import StampingPart
    from app.models.settings import User
"""

from app.models.async_task import AsyncTask
from app.models.bom import (
    BomAnnualPartPrice,
    BomNode,
    BomPackagingTransportFee,
    BomProcurementObject,
    BomProcurementObjectGenerateLog,
    BomProcurementObjectList,
    BomSnapshot,
    BomWeldingFee,
    BomWeldingFeeCalcLog,
    BomWeldingFeeItem,
    BomWeldingProcessBreakdownGenerateLog,
    BomWeldingProcessBreakdownLine,
    BomWeldingProcessBreakdownNode,
    BomWeldingUnitPrice,
)
from app.models.common import AuditUserMixin
from app.models.costing import (
    AssemblyCost,
    AssemblyCostCalcLog,
    AssemblyCostIndirect,
    AssemblyCostItem,
    CostingEngineRun,
    CostingEngineRunStep,
    StampingPartCost,
    StampingPartCostCalcLog,
    SteelPrice,
    SteelPriceCalcLog,
)
from app.models.file_trace import UploadFile
from app.models.llm import LlmAnalysisReport
from app.models.masterdata import Location, LocationAlias, VehicleModel
from app.models.settings import (
    OperationLog,
    SystemConfig,
    User,
    UserPermission,
    UserToken,
)
from app.models.stamping import (
    StampingDieFee,
    StampingDieFeeCalcLog,
    StampingDieFeeItem,
    StampingDiePart,
    StampingDieProcess,
    StampingDieUnitPrice,
    StampingGaugeFee,
    StampingPart,
    StampingProcess,
    StampingProcessFee,
    StampingProcessFeeCalcLog,
    StampingProcessFeeItem,
    StampingTailorWeldBlank,
    StampingTonnagePrice,
)
from app.models.yishiyiyi import (
    StampingScrapPrice,
    SteelBasePrice,
    SteelGradeCategory,
    SteelPriceLadderItem,
    SteelPricePolicy,
)

__all__ = [
    "AssemblyCost",
    "AssemblyCostCalcLog",
    "AssemblyCostIndirect",
    "AssemblyCostItem",
    "AsyncTask",
    "AuditUserMixin",
    "BomAnnualPartPrice",
    "BomNode",
    "BomPackagingTransportFee",
    "BomProcurementObject",
    "BomProcurementObjectGenerateLog",
    "BomProcurementObjectList",
    "BomSnapshot",
    "BomWeldingFee",
    "BomWeldingFeeCalcLog",
    "BomWeldingFeeItem",
    "BomWeldingProcessBreakdownGenerateLog",
    "BomWeldingProcessBreakdownLine",
    "BomWeldingProcessBreakdownNode",
    "BomWeldingUnitPrice",
    "CostingEngineRun",
    "CostingEngineRunStep",
    "LlmAnalysisReport",
    "Location",
    "LocationAlias",
    "VehicleModel",
    "OperationLog",
    "StampingDieFee",
    "StampingDieFeeCalcLog",
    "StampingDieFeeItem",
    "StampingDiePart",
    "StampingDieProcess",
    "StampingDieUnitPrice",
    "StampingGaugeFee",
    "StampingPart",
    "StampingPartCost",
    "StampingPartCostCalcLog",
    "StampingProcess",
    "StampingProcessFee",
    "StampingProcessFeeCalcLog",
    "StampingProcessFeeItem",
    "StampingScrapPrice",
    "StampingTailorWeldBlank",
    "StampingTonnagePrice",
    "SteelBasePrice",
    "SteelGradeCategory",
    "SteelPrice",
    "SteelPriceCalcLog",
    "SteelPriceLadderItem",
    "SteelPricePolicy",
    "SystemConfig",
    "UploadFile",
    "User",
    "UserPermission",
    "UserToken",
]
