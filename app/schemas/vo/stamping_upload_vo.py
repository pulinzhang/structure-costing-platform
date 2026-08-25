"""
冲压工艺上传 VO - 响应数据结构
"""

from pydantic import BaseModel


class UploadResultVO(BaseModel):
    """上传结果响应 VO"""

    filename: str
    new_filename: str
    size: int
    path: str
    location: str
    vehicle_model: str
    version: str
    parts_count: int
    processes_count: int
    images_count: int
    tailor_weld_assembly_count: int = 0
    tailor_weld_blank_count: int = 0
    warnings: list[str] | None = None
    parse_time_ms: float
