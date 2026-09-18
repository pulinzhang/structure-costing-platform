"""工程变更 VO — 出参。"""

from datetime import datetime

from pydantic import BaseModel, Field, field_serializer

from app.common.timezone import datetime_to_iso


class EngineeringChangeEffectLinkVO(BaseModel):
    """效果链接：前后实体 id + 整本 upload_log_id。"""

    id: int
    upload_log_id: int
    change_order_id: int
    effect_kind: str
    before_id: int | None = None
    after_id: int | None = None
    sort_no: int = 0

    model_config = {"from_attributes": True}


class EngineeringChangeOrderVO(BaseModel):
    """变更单行（样表十列 + excel_row + 实体 id）。"""

    id: int
    upload_log_id: int
    upload_file_id: int
    excel_row: int
    project_code: str
    effective_period_text: str
    change_type: str
    before_assembly_part_number: str
    after_assembly_part_number: str | None = None
    assembly_name: str | None = None
    part_level: str
    before_part_number: str | None = None
    after_part_number: str | None = None
    part_name: str | None = None
    seq_no: int | None = None
    status: str
    created_at: datetime | None = None

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)

    model_config = {"from_attributes": True}


class EngineeringChangeUploadLogVO(BaseModel):
    """上传头（整本删除/回滚用）。变更单十列不落本对象。"""

    id: int
    task_id: str | None = None
    upload_file_id: int
    status: str
    location: str
    vehicle_model: str
    customer_name: str
    effective_year: int
    effective_month: int
    original_filename: str
    message: str | None = None
    process_inserted_count: int = 0
    die_inserted_count: int = 0
    procurement_object_inserted_count: int = 0
    welding_breakdown_inserted_count: int = 0
    not_install_count: int = 0
    has_bom_assembly: bool = False
    created_by: str | None = None
    created_at: datetime | None = None

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)

    model_config = {"from_attributes": True}


class EngineeringChangeListRowVO(BaseModel):
    """列表一行 = 变更单；删除用 upload_log_id 整本回滚。"""

    change_order_id: int | None = None
    upload_log_id: int
    excel_row: int | None = None
    project_code: str | None = None
    effective_period_text: str | None = None
    change_type: str | None = None
    before_assembly_part_number: str | None = None
    after_assembly_part_number: str | None = None
    assembly_name: str | None = None
    part_level: str | None = None
    before_part_number: str | None = None
    after_part_number: str | None = None
    part_name: str | None = None
    seq_no: int | None = None
    change_order_status: str | None = None
    location: str
    vehicle_model: str
    effective_year: int
    effective_month: int
    status: str
    original_filename: str
    task_id: str | None = None
    message: str | None = None
    created_by: str | None = None
    created_at: datetime | None = None
    is_rolled_back: bool = False

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)


class EngineeringChangeDetailVO(BaseModel):
    """详情 = 头 + 变更单行列表 + 效果链接。"""

    log: EngineeringChangeUploadLogVO
    change_orders: list[EngineeringChangeOrderVO] = Field(default_factory=list)
    effect_links: list[EngineeringChangeEffectLinkVO] = Field(default_factory=list)


class EngineeringChangeUploadResultVO(BaseModel):
    """异步任务成功 result。"""

    log_id: int
    change_order_ids: list[int] = Field(default_factory=list)
    change_type: str
    before_assembly_part_number: str
    after_assembly_part_number: str | None = None
    seq_no: int | None = None
    process_inserted_count: int = 0
    die_inserted_count: int = 0
    procurement_object_inserted_count: int = 0
    welding_breakdown_inserted_count: int = 0
    not_install_count: int = 0
    warnings: list[str] = Field(default_factory=list)
