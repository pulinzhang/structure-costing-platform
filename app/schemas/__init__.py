# Schemas Package
"""
统一导出所有 Schema，方便各层引用。

目录结构：
├── vo/                              # View Object - 返回给前端
│   ├── stamping_vo.py               # 零件、工序、吨位价格 VO
│   ├── steel_base_price_vo.py
│   └── steel_price_policy_vo.py
│
└── dto/                             # Data Transfer Object - 接收参数
    ├── stamping_dto.py              # 查询 DTO
    ├── stamping_upload_dto.py       # 上传内部 DTO
    ├── steel_base_price_dto.py
    └── steel_price_policy_dto.py
"""

# ---- VO 导出（返回给前端）----
# 冲压零件 & 工序
from app.schemas.vo.stamping_vo import (
    StampingPartQuery,
    StampingPartResponse,
    StampingPartListResponse,
    StampingPartWithProcessesResponse,
    StampingProcessResponse,
    StampingProcessUpdate,
    StampingProcessItemUpdate,
)

# 吨位价格 - DTO（请求参数）
from app.schemas.dto.stamping_tonnage_price_dto import (
    StampingTonnagePriceCreate,
    StampingTonnagePriceUpdate,
    StampingTonnagePriceQuery,
    StampingTonnagePriceBulkCreate,
    StampingTonnagePriceCopyTemplate,
)
# 吨位价格 - VO（响应数据）
from app.schemas.vo.stamping_tonnage_price_vo import (
    StampingTonnagePriceResponse,
)

from app.schemas.vo.steel_base_price_vo import (
    FilterOptionsVO,
    SteelBasePriceResponse,
    SteelBasePriceExportRow,
)

from app.schemas.vo.steel_price_policy_vo import (
    SteelPricePolicyResponse,
    SteelPricePolicyItemResponse,
)

# ---- DTO 导出（内部传输）----
from app.schemas.dto.stamping_upload_dto import (
    FileInfo,
    PartData,
    ProcessData,
    UploadResult,
)

from app.schemas.common.page_result import PageResult

from app.schemas.dto.steel_base_price_dto import (
    FilterOptions as SteelBasePriceFilterOptions,
)

from app.schemas.dto.steel_price_policy_dto import (
    FilterOptions as SteelPricePolicyFilterOptions,
    ExportRow as SteelPricePolicyExportRow,
)

__all__ = [
    # Common
    "PageResult",
    # VO - 冲压
    "StampingPartQuery",
    "StampingPartResponse",
    "StampingPartListResponse",
    "StampingPartWithProcessesResponse",
    "StampingProcessResponse",
    "StampingProcessUpdate",
    "StampingProcessItemUpdate",
    # VO - 吨位价格（仅响应）
    "StampingTonnagePriceResponse",
    # DTO - 吨位价格（请求参数）
    "StampingTonnagePriceCreate",
    "StampingTonnagePriceUpdate",
    "StampingTonnagePriceQuery",
    "StampingTonnagePriceBulkCreate",
    "StampingTonnagePriceCopyTemplate",
    # VO - 钢材基准价格
    "FilterOptionsVO",
    "SteelBasePriceResponse",
    "SteelBasePriceExportRow",
    # VO - 钢价政策
    "SteelPricePolicyResponse",
    "SteelPricePolicyItemResponse",
    # DTO - 上传
    "FileInfo",
    "PartData",
    "ProcessData",
    "UploadResult",
    # DTO - 钢材基准价格
    "SteelBasePriceFilterOptions",
    # DTO - 钢价政策
    "SteelPricePolicyFilterOptions",
    "SteelPricePolicyExportRow",
]
