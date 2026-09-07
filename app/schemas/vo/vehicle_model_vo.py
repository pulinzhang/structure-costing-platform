"""项目主数据 VO。"""

from pydantic import BaseModel, Field

PERIOD_PENDING = "未生效"
PERIOD_INTRODUCIBLE = "可引入"
PERIOD_EXPIRED = "已失效"


class VehicleModelVO(BaseModel):
    """项目一行（含相对墙钟月的期状态）。"""

    model_config = {"from_attributes": True}

    location: str
    vehicle_model: str
    effective_year: int
    effective_month: int
    expiry_year: int | None = None
    expiry_month: int | None = None
    period_status: str = Field(..., description="未生效 | 可引入 | 已失效")


class LocationCardVO(BaseModel):
    """一览表 HUD 基地卡。"""

    location: str
    is_enabled: bool
    project_count: int
    introducible_count: int
    pending_count: int
    expired_count: int


class VehicleModelListVO(BaseModel):
    """一览表全量：墙钟月 + 基地卡 + 全部项目行。"""

    as_of_year: int
    as_of_month: int
    locations: list[LocationCardVO]
    items: list[VehicleModelVO]


class VehicleModelUploadResultVO(BaseModel):
    """同步上传结果。"""

    created_count: int
    skipped_count: int
