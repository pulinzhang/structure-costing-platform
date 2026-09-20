"""工程变更 VO — 出参。"""

from datetime import datetime

from pydantic import BaseModel, Field, field_serializer

from app.common.timezone import datetime_to_iso


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

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)


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
