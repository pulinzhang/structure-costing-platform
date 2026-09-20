"""冲压工艺导入编排上下文。"""

from __future__ import annotations

from dataclasses import dataclass

from app.parsers.stamping.models.parse_result import ParserResult
from app.parsers.stamping.models.tailor_weld import TailorWeldParseResult
from app.schemas.dto.stamping_upload_dto import FileInfo
from app.services.async_task.worker_runner import ProgressCallback

__all__ = [
    "PipelineBundle",
    "PreparedBundle",
    "ProgressCallback",
    "StampingUploadExecuteArgs",
    "report_progress",
]


@dataclass(slots=True)
class StampingUploadExecuteArgs:
    file_content: bytes
    filename: str


@dataclass(slots=True)
class PreparedBundle:
    filename: str
    file_content: bytes
    parse_result: ParserResult
    tailor_result: TailorWeldParseResult
    location: str
    vehicle_model: str
    version: str
    stamping_supplier: str
    supplier_names: list[str]
    tailor_parent_numbers: set[str]


@dataclass(slots=True)
class PipelineBundle:
    file_info: FileInfo
    saved_images: int
    part_map: dict[str, int]
    process_count: int
    tailor_assemblies: int
    tailor_blanks: int
    warnings: list[str]
    parse_time_ms: float


def report_progress(on_progress: ProgressCallback | None, progress: int, message: str) -> None:
    if on_progress is not None:
        on_progress(progress, message)
